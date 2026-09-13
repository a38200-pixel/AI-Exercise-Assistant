import { addDays, endOfMonth, format, parseISO, startOfMonth, subDays } from 'date-fns'
import { Activity, CalendarCheck, Clock3, PersonStanding } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CardSkeleton, EmptyState, ErrorState } from '../components/common/States'
import { PageHeader } from '../components/layout/PageHeader'
import { useAuth } from '../contexts/AuthContext'
import { ApiError, workoutApi } from '../lib/api'
import { formatDuration } from '../lib/format'
import type { DailyWorkoutSummary } from '../types/workout'

type Range = 'week' | 'month'

export function StatisticsPage() {
  const [range, setRange] = useState<Range>('week'); const [data, setData] = useState<DailyWorkoutSummary[]>([])
  const [loading, setLoading] = useState(true); const [failed, setFailed] = useState(false)
  const { signOut } = useAuth(); const navigate = useNavigate()
  const today = new Date(); const start = range === 'week' ? subDays(today, 6) : startOfMonth(today); const end = range === 'week' ? today : endOfMonth(today)
  const load = useCallback(async () => {
    setLoading(true); setFailed(false)
    try { setData(await workoutApi.daily(format(start, 'yyyy-MM-dd'), format(end, 'yyyy-MM-dd'))) }
    catch (error) { if (error instanceof ApiError && error.status === 401) { await signOut(); navigate('/login', { replace: true }); return } setFailed(true) }
    finally { setLoading(false) }
  // start/end are intentionally represented by stable formatted values.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range, navigate, signOut])
  useEffect(() => { void load() }, [load])

  const totals = useMemo(() => data.reduce((acc, item) => ({ squats: acc.squats + item.squat_count, stretch: acc.stretch + item.stretch_seconds, workout: acc.workout + item.workout_seconds, sessions: acc.sessions + item.session_count }), { squats: 0, stretch: 0, workout: 0, sessions: 0 }), [data])
  const chartData = useMemo(() => {
    const byDate = new Map(data.map((item) => [item.workout_date, item]))
    const count = Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1
    return Array.from({ length: count }, (_, index) => { const key = format(addDays(start, index), 'yyyy-MM-dd'); const item = byDate.get(key); return { label: format(parseISO(key), range === 'week' ? 'M/d' : 'd'), 운동시간: Math.round((item?.workout_seconds || 0) / 60), 스쿼트: item?.squat_count || 0 } })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, range])

  return <div className="page-wrap"><PageHeader title="통계 분석" subtitle="기록된 데이터로 운동 흐름을 간결하게 확인하세요." /><div className="segmented" role="group" aria-label="통계 기간"><button className={range === 'week' ? 'active' : ''} onClick={() => setRange('week')}>주간</button><button className={range === 'month' ? 'active' : ''} onClick={() => setRange('month')}>월간</button></div>{failed ? <div className="mt-5"><ErrorState retry={() => void load()} /></div> : loading ? <div className="mt-5 grid gap-5"><CardSkeleton /><CardSkeleton className="h-96" /></div> : <><section className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{[{ label: '총 스쿼트', value: `${totals.squats}회`, icon: PersonStanding }, { label: '총 스트레칭', value: formatDuration(totals.stretch), icon: Activity }, { label: '총 운동 시간', value: formatDuration(totals.workout), icon: Clock3 }, { label: '활동일 / 세션', value: `${data.length}일 · ${totals.sessions}회`, icon: CalendarCheck }].map(({ label, value, icon: Icon }) => <article className="stat-card" key={label}><span className="metric-icon"><Icon size={19} /></span><p>{label}</p><strong>{value}</strong></article>)}</section><section className="content-card mt-5"><div className="card-heading"><div><h2 className="section-title">운동 시간 추이</h2><p>일별 총 운동 시간 · 분</p></div></div>{data.length === 0 ? <EmptyState /> : <div className="h-80"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 15, right: 12, left: -22, bottom: 0 }}><CartesianGrid vertical={false} stroke="#dfe7dc" strokeDasharray="3 5" /><XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: '#718078', fontSize: 11 }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#718078', fontSize: 11 }} /><Tooltip contentStyle={{ borderRadius: 14, border: '1px solid #e2e8df' }} /><Line type="monotone" dataKey="운동시간" stroke="#4f8250" strokeWidth={3} dot={{ fill: '#b7ff63', stroke: '#23432d', strokeWidth: 2, r: 4 }} activeDot={{ r: 6 }} /></LineChart></ResponsiveContainer></div>}</section><section className="mt-5 grid gap-5 md:grid-cols-2"><div className="content-card"><h2 className="section-title">스쿼트</h2><p className="mt-2 text-sm text-muted">반복 횟수 단위로 집계합니다.</p><strong className="mt-8 block text-4xl font-black tracking-tight text-ink">{totals.squats}<small className="ml-1 text-base">회</small></strong></div><div className="content-card"><h2 className="section-title">스트레칭</h2><p className="mt-2 text-sm text-muted">유지 시간 단위로 집계합니다.</p><strong className="mt-8 block text-4xl font-black tracking-tight text-ink">{formatDuration(totals.stretch)}</strong></div></section></>}</div>
}
