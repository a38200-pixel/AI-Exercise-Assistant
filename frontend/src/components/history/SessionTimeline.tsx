import { Activity, Clock3, PersonStanding } from 'lucide-react'
import { formatDuration, formatSeoulTime } from '../../lib/format'
import type { WorkoutSession } from '../../types/workout'
import { EmptyState } from '../common/States'

export function SessionTimeline({ sessions }: { sessions: WorkoutSession[] }) {
  if (!sessions.length) return <EmptyState title="이 날짜에는 원본 세션이 없습니다." />
  return <ol className="timeline">{sessions.map((session, index) => <li key={session.id} className="timeline-item"><span className="timeline-dot">{index + 1}</span><article className="dark-session-card"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-xs font-semibold uppercase tracking-widest text-lime/70">Session {index + 1}</p><h3 className="mt-1 text-lg font-extrabold text-white">{formatSeoulTime(session.started_at)} – {formatSeoulTime(session.ended_at)}</h3></div><span className="dark-pill"><Clock3 size={14} /> {formatDuration(session.workout_seconds)}</span></div><div className="mt-5 grid grid-cols-2 gap-3"><div className="dark-metric"><PersonStanding size={18} /><span>스쿼트</span><strong>{session.squat_count}회</strong></div><div className="dark-metric"><Activity size={18} /><span>스트레칭</span><strong>{formatDuration(session.stretch_seconds)}</strong></div></div></article></li>)}</ol>
}
