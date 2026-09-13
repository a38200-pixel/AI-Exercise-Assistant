import { ArrowRight, Clock3 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatDuration, formatSeoulTime } from '../../lib/format'
import type { WorkoutSession } from '../../types/workout'
import { EmptyState } from '../common/States'

export function RecentSessionList({ sessions, date }: { sessions: WorkoutSession[]; date: string }) {
  if (!sessions.length) return <EmptyState title="최근 세션이 없습니다." />
  return (
    <div className="space-y-2">
      {sessions.slice(-4).reverse().map((session) => (
        <div key={session.id} className="flex items-center gap-3 rounded-2xl border border-forest/8 bg-white p-3.5">
          <span className="metric-icon shrink-0"><Clock3 size={18} /></span>
          <div className="min-w-0 flex-1"><p className="truncate text-sm font-bold text-ink">{formatSeoulTime(session.started_at)} 운동</p><p className="mt-0.5 text-xs text-muted">스쿼트 {session.squat_count}회 · {formatDuration(session.workout_seconds)}</p></div>
          <span className="text-xs font-semibold text-forest">{formatDuration(session.stretch_seconds)}</span>
        </div>
      ))}
      <Link to={`/history/${date}`} className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-forest hover:text-leaf">상세 기록 <ArrowRight size={15} /></Link>
    </div>
  )
}
