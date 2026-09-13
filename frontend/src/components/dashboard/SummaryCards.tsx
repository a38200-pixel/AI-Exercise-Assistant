import { Activity, Clock3, PersonStanding } from 'lucide-react'
import { formatDuration } from '../../lib/format'
import type { DailyWorkoutSummary } from '../../types/workout'

const toneClasses = ['bg-[#f7fbf3]', 'bg-[#f4faef]', 'bg-[#f7fbf3]']

export function SummaryCards({ summary }: { summary: DailyWorkoutSummary }) {
  const cards = [
    { label: '스쿼트', value: `${summary.squat_count}`, unit: '회', hint: `${summary.session_count}개 세션`, icon: PersonStanding },
    { label: '스트레칭', value: formatDuration(summary.stretch_seconds), unit: '', hint: '누적 유지 시간', icon: Activity },
    { label: '총 운동 시간', value: formatDuration(summary.workout_seconds), unit: '', hint: '오늘의 기록', icon: Clock3 },
  ]
  return (
    <section className="lime-panel" aria-labelledby="today-summary-title">
      <div className="mb-4 flex items-center justify-between"><h2 id="today-summary-title" className="section-title">오늘의 운동 요약</h2><span className="status-pill">LIVE DATA</span></div>
      <div className="grid gap-3 sm:grid-cols-3">
        {cards.map(({ label, value, unit, hint, icon: Icon }, index) => (
          <article key={label} className={`summary-card ${toneClasses[index]}`}>
            <span className="metric-icon"><Icon size={21} /></span>
            <div className="min-w-0"><p className="text-xs font-semibold text-muted">{label}</p><p className="mt-1 truncate text-2xl font-extrabold tracking-[-0.04em] text-ink sm:text-[1.7rem]">{value} <small className="text-sm font-bold">{unit}</small></p><p className="mt-1 text-xs text-muted/80">{hint}</p></div>
          </article>
        ))}
      </div>
    </section>
  )
}
