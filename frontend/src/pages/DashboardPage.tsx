import { addDays, format, startOfDay, subDays } from 'date-fns'
import { ArrowRight, Play, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { WeeklyWorkoutChart } from '../components/charts/WeeklyWorkoutChart'
import { CardSkeleton, EmptyState, ErrorState } from '../components/common/States'
import { RecentSessionList } from '../components/dashboard/RecentSessionList'
import { SummaryCards } from '../components/dashboard/SummaryCards'
import { WorkoutTimeRing } from '../components/dashboard/WorkoutTimeRing'
import { PageHeader } from '../components/layout/PageHeader'
import { useAuth } from '../contexts/AuthContext'
import { ApiError, workoutApi } from '../lib/api'
import { seoulToday } from '../lib/format'
import type { DailyWorkoutSummary, WorkoutSession } from '../types/workout'

const emptySummary = (date: string): DailyWorkoutSummary => ({ workout_date: date, squat_count: 0, stretch_seconds: 0, workout_seconds: 0, session_count: 0 })

export function DashboardPage() {
  const today = seoulToday()
  const [summary, setSummary] = useState<DailyWorkoutSummary | null>(null)
  const [weekly, setWeekly] = useState<DailyWorkoutSummary[]>([])
  const [sessions, setSessions] = useState<WorkoutSession[]>([])
  const [sessionDate, setSessionDate] = useState(today)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const { signOut } = useAuth()
  const navigate = useNavigate()

  const load = useCallback(async () => {
    setLoading(true); setFailed(false)
    const firstDay = format(subDays(startOfDay(new Date()), 6), 'yyyy-MM-dd')
    try {
      const [todayData, dailyData] = await Promise.all([workoutApi.today(), workoutApi.daily(firstDay, today)])
      const byDate = new Map(dailyData.map((item) => [item.workout_date, item]))
      const filled = Array.from({ length: 7 }, (_, index) => {
        const key = format(addDays(parseLocalDate(firstDay), index), 'yyyy-MM-dd')
        return byDate.get(key) || emptySummary(key)
      })
      const recentDate = dailyData[0]?.workout_date || today
      const recentSessions = dailyData.length ? await workoutApi.sessions(recentDate) : []
      setSummary(todayData); setWeekly(filled); setSessions(recentSessions); setSessionDate(recentDate)
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) { await signOut(); navigate('/login', { replace: true }); return }
      setFailed(true)
    } finally { setLoading(false) }
  }, [navigate, signOut, today])

  useEffect(() => { void load() }, [load])

  return (
    <div className="page-wrap">
      <PageHeader action={<button className="icon-button" onClick={() => void load()} disabled={loading} aria-label="대시보드 새로고침"><RefreshCw size={18} className={loading ? 'animate-spin' : ''} /></button>} />
      {failed ? <ErrorState retry={() => void load()} /> : loading || !summary ? <div className="grid gap-5"><CardSkeleton /><div className="grid gap-5 lg:grid-cols-2"><CardSkeleton className="h-80" /><CardSkeleton className="h-80" /></div></div> : <>
        <div className="hidden md:block"><SummaryCards summary={summary} /></div>
        <section className="mobile-hero-card md:hidden">
          <WorkoutTimeRing seconds={summary.workout_seconds} />
          <div className="mt-5 grid grid-cols-2 gap-3"><div className="mobile-metric"><span>스쿼트</span><strong>{summary.squat_count}<small> 회</small></strong></div><div className="mobile-metric"><span>스트레칭</span><strong>{Math.floor(summary.stretch_seconds / 60).toString().padStart(2, '0')}:{Math.floor(summary.stretch_seconds % 60).toString().padStart(2, '0')}</strong></div></div>
        </section>

        {summary.session_count === 0 && <div className="mt-5"><EmptyState title="오늘의 운동 기록이 아직 없습니다." /></div>}
        <div className="mt-5 grid gap-5 xl:grid-cols-[1.1fr_.9fr]">
          <section className="content-card"><div className="card-heading"><div><h2 className="section-title">주간 운동 현황</h2><p>최근 7일의 운동 시간(분)과 스쿼트 횟수</p></div><Link to="/statistics" className="text-link">통계 보기 <ArrowRight size={15} /></Link></div><WeeklyWorkoutChart data={weekly} /></section>
          <section className="content-card"><div className="card-heading"><div><h2 className="section-title">최근 운동 세션</h2><p>{sessionDate} 원본 기록</p></div><Link to="/history" className="text-link">더 보기 <ArrowRight size={15} /></Link></div><RecentSessionList sessions={sessions} date={sessionDate} /></section>
        </div>
        <section className="cta-banner"><div><p className="eyebrow text-forest">DESKTOP AI WORKOUT</p><h2 className="mt-2 text-xl font-extrabold text-ink">꾸준함이 만드는 놀라운 변화</h2><p className="mt-1 text-sm text-muted">AI 프로그램의 운동 기록이 이곳에 안전하게 쌓입니다.</p></div><Link className="btn-dark" to="/exercise"><Play size={17} fill="currentColor" /> 운동 선택하기</Link></section>
      </>}
    </div>
  )
}

function parseLocalDate(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}
