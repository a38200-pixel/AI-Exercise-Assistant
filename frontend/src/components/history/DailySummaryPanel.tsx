import { Activity, ArrowRight, Clock3, Layers3, PersonStanding } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatDuration, formatKoreanDate } from '../../lib/format'
import type { DailyWorkoutSummary } from '../../types/workout'
import { EmptyState } from '../common/States'

export function DailySummaryPanel({ summary }: { summary: DailyWorkoutSummary }) {
  const rows = [{ label: '스쿼트', value: `${summary.squat_count} 회`, icon: PersonStanding }, { label: '스트레칭', value: formatDuration(summary.stretch_seconds), icon: Activity }, { label: '총 운동 시간', value: formatDuration(summary.workout_seconds), icon: Clock3 }, { label: '세션', value: `${summary.session_count} 회`, icon: Layers3 }]
  return <section className="content-card"><h2 className="text-lg font-extrabold text-ink">{formatKoreanDate(summary.workout_date)}</h2><p className="mt-1 text-xs text-muted">일일 합산 기록</p>{summary.session_count === 0 ? <div className="mt-6"><EmptyState /></div> : <><div className="mt-6 grid gap-2">{rows.map(({ label, value, icon: Icon }) => <div key={label} className="summary-row"><span className="metric-icon"><Icon size={18} /></span><span className="flex-1 text-sm font-semibold text-muted">{label}</span><strong className="text-ink">{value}</strong></div>)}</div><Link className="btn-dark mt-5 w-full justify-center" to={`/history/${summary.workout_date}`}>세션 상세 보기 <ArrowRight size={16} /></Link></>}</section>
}
