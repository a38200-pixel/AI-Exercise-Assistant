-- AI Exercise Assistant - Supabase PostgreSQL initial schema

create extension if not exists pgcrypto;

-- ============================================================
-- Profiles
-- Supabase Auth가 비밀번호와 인증정보를 관리하며 public에는 확장 정보만 둔다.
-- ============================================================

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    nickname text,
    timezone text not null default 'Asia/Seoul',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ============================================================
-- Workout Sessions
-- S부터 E까지의 원본 세션은 합치거나 덮어쓰지 않고 매번 한 row로 저장한다.
-- ============================================================

create table if not exists public.workout_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    workout_date date not null,
    started_at timestamptz not null,
    ended_at timestamptz not null,
    workout_seconds double precision not null,
    squat_count integer not null default 0,
    stretch_seconds double precision not null default 0,
    created_at timestamptz not null default now(),
    constraint workout_sessions_nonnegative_workout check (workout_seconds >= 0),
    constraint workout_sessions_nonnegative_squat check (squat_count >= 0),
    constraint workout_sessions_nonnegative_stretch check (stretch_seconds >= 0),
    constraint workout_sessions_time_order check (ended_at >= started_at)
);

-- ============================================================
-- Daily Workout Summary
-- 사용자와 workout_date 조합당 정확히 한 row에 세션 합계를 보관한다.
-- ============================================================

create table if not exists public.daily_workout_summary (
    user_id uuid not null references auth.users(id) on delete cascade,
    workout_date date not null,
    squat_count integer not null default 0,
    stretch_seconds double precision not null default 0,
    workout_seconds double precision not null default 0,
    session_count integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (user_id, workout_date),
    constraint daily_summary_nonnegative_squat check (squat_count >= 0),
    constraint daily_summary_nonnegative_stretch check (stretch_seconds >= 0),
    constraint daily_summary_nonnegative_workout check (workout_seconds >= 0),
    constraint daily_summary_nonnegative_sessions check (session_count >= 0)
);

-- ============================================================
-- Indexes
-- ============================================================

create index if not exists workout_sessions_user_date_idx
    on public.workout_sessions (user_id, workout_date desc);

-- ============================================================
-- updated_at Trigger
-- ============================================================

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

-- ============================================================
-- New User Trigger
-- auth.users 가입 시 비밀번호가 아닌 profile 확장 정보만 복사한다.
-- ============================================================

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (id, nickname)
    values (new.id, new.raw_user_meta_data ->> 'nickname')
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- ============================================================
-- RLS
-- 테이블 직접 쓰기는 허용하지 않고, workout 저장은 아래 atomic RPC만 사용한다.
-- ============================================================

alter table public.profiles enable row level security;
alter table public.workout_sessions enable row level security;
alter table public.daily_workout_summary enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
on public.profiles for select
to authenticated
using ((select auth.uid()) is not null and (select auth.uid()) = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
on public.profiles for update
to authenticated
using ((select auth.uid()) is not null and (select auth.uid()) = id)
with check ((select auth.uid()) is not null and (select auth.uid()) = id);

drop policy if exists "workout_sessions_select_own" on public.workout_sessions;
create policy "workout_sessions_select_own"
on public.workout_sessions for select
to authenticated
using ((select auth.uid()) is not null and (select auth.uid()) = user_id);

drop policy if exists "daily_summary_select_own" on public.daily_workout_summary;
create policy "daily_summary_select_own"
on public.daily_workout_summary for select
to authenticated
using ((select auth.uid()) is not null and (select auth.uid()) = user_id);

revoke all on table public.profiles from anon, authenticated;
revoke all on table public.workout_sessions from anon, authenticated;
revoke all on table public.daily_workout_summary from anon, authenticated;

grant select on table public.profiles to authenticated;
grant update (nickname, timezone) on table public.profiles to authenticated;
grant select on table public.workout_sessions to authenticated;
grant select on table public.daily_workout_summary to authenticated;

-- ============================================================
-- Workout RPC
-- SECURITY DEFINER가 필요한 이유는 table 직접 쓰기를 막고 이 검증된 transaction만
-- 허용하기 위해서다. search_path는 비우고 모든 객체를 schema-qualified로 참조한다.
-- ============================================================

create or replace function public.record_workout_session(
    p_workout_date date,
    p_started_at timestamptz,
    p_ended_at timestamptz,
    p_workout_seconds double precision,
    p_squat_count integer,
    p_stretch_seconds double precision
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_user_id uuid := auth.uid();
    v_session_id uuid;
begin
    if v_user_id is null then
        raise exception 'Authentication required' using errcode = '42501';
    end if;
    if p_ended_at < p_started_at then
        raise exception 'ended_at must not precede started_at' using errcode = '22023';
    end if;
    if p_workout_seconds < 0 or p_squat_count < 0 or p_stretch_seconds < 0 then
        raise exception 'Workout values must be nonnegative' using errcode = '22023';
    end if;

    insert into public.workout_sessions (
        user_id,
        workout_date,
        started_at,
        ended_at,
        workout_seconds,
        squat_count,
        stretch_seconds
    )
    values (
        v_user_id,
        p_workout_date,
        p_started_at,
        p_ended_at,
        p_workout_seconds,
        p_squat_count,
        p_stretch_seconds
    )
    returning id into v_session_id;

    insert into public.daily_workout_summary (
        user_id,
        workout_date,
        squat_count,
        stretch_seconds,
        workout_seconds,
        session_count
    )
    values (
        v_user_id,
        p_workout_date,
        p_squat_count,
        p_stretch_seconds,
        p_workout_seconds,
        1
    )
    on conflict (user_id, workout_date)
    do update set
        squat_count = public.daily_workout_summary.squat_count + excluded.squat_count,
        stretch_seconds = public.daily_workout_summary.stretch_seconds + excluded.stretch_seconds,
        workout_seconds = public.daily_workout_summary.workout_seconds + excluded.workout_seconds,
        session_count = public.daily_workout_summary.session_count + 1,
        updated_at = now();

    return v_session_id;
end;
$$;

revoke execute on function public.record_workout_session(
    date, timestamptz, timestamptz, double precision, integer, double precision
) from public, anon;

grant execute on function public.record_workout_session(
    date, timestamptz, timestamptz, double precision, integer, double precision
) to authenticated;

revoke execute on function public.handle_new_user() from public, anon, authenticated;
revoke execute on function public.set_updated_at() from public, anon, authenticated;

