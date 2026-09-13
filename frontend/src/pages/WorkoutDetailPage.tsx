import { Activity, ArrowLeft, Clock3, Layers3, PersonStanding } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CardSkeleton, ErrorState } from '../components/common/States'
import { SessionTimeline } from '../components/history/SessionTimeline'
import { useAuth } from '../contexts/AuthContext'
import { ApiError, workoutApi } from '../lib/api'
import { formatDuration, formatKoreanDate } from '../lib/format'
import type { DailyWorkoutSummary, WorkoutSession } from '../types/workout'

export function WorkoutDetailPage() {
  const { date = '' } = useParams()
  const [summary, setSummary] = useState<DailyWorkoutSummary | null>(null)
  const [sessions, setSessions] = useState<WorkoutSession[]>([])
  const [loading, setLoading] = useState(true); const [failed, setFailed] = useState(false)
  const { signOut } = useAuth(); const navigate = useNavigate()
  const load = useCallback(async () => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) { setFailed(true); setLoading(false); return }
    setLoading(true); setFailed(false)
    try { const [daily, raw] = await Promise.all([workoutApi.dailyDetail(date), workoutApi.sessions(date)]); setSummary(daily); setSessions(raw) }
    catch (error) { if (error instanceof ApiError && error.status === 401) { await signOut(); navigate('/login', { replace: true }); return } setFailed(true) }
    finally { setLoading(false) }
  }, [date, navigate, signOut])
  useEffect(() => { void load() }, [load])

  return <div className="page-wrap dark-detail-page"><div className="mb-7"><Link to="/history" className="inline-flex items-center gap-2 text-sm font-bold text-white/55 hover:text-lime"><ArrowLeft size={17} /> 운동 기록</Link><h1 className="mt-5 text-2xl font-extrabold text-white sm:text-3xl">{date ? `${formatKoreanDate(date, false)} 운동` : '운동 세션 상세'}</h1><p className="mt-2 text-sm text-white/40">일일 합계와 원본 세션을 구분해 확인하세요.</p></div>{failed ? <ErrorState retry={() => void load()} /> : loading || !summary ? <><CardSkeleton /><CardSkeleton className="mt-5 h-96" /></> : <><section className="grid gap-3 sm:grid-cols-4">{[{ label: '스쿼트', value: `${summary.squat_count}회`, icon: PersonStanding }, { label: '스트레칭', value: formatDuration(summary.stretch_seconds), icon: Activity }, { label: '총 운동 시간', value: formatDuration(summary.workout_seconds), icon: Clock3 }, { label: '세션', value: `${summary.session_count}회`, icon: Layers3 }].map(({ label, value, icon: Icon }) => <article key={label} className="detail-metric"><span className="metric-icon"><Icon size={20} /></span><p>{label}</p><strong>{value}</strong></article>)}</section><section className="mt-7"><div className="mb-5"><h2 className="text-xl font-extrabold text-white">운동 타임라인</h2><p className="mt-1 text-sm text-white/40">시각은 Asia/Seoul 기준입니다.</p></div><SessionTimeline sessions={sessions} /></section></>}</div>
}
