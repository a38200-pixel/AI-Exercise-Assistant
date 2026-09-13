import { formatDuration } from '../../lib/format'

export function WorkoutTimeRing({ seconds }: { seconds: number }) {
  const circumference = 2 * Math.PI * 54
  const decorativeProgress = seconds === 0 ? 0.12 : Math.min(0.9, 0.3 + (seconds % 1800) / 3000)
  return (
    <div className="relative mx-auto h-44 w-44 sm:h-48 sm:w-48">
      <svg viewBox="0 0 128 128" className="h-full w-full -rotate-90" aria-hidden="true">
        <circle cx="64" cy="64" r="54" fill="none" stroke="rgba(255,255,255,.11)" strokeWidth="9" />
        <circle cx="64" cy="64" r="54" fill="none" stroke="#b7ff63" strokeLinecap="round" strokeWidth="9" strokeDasharray={circumference} strokeDashoffset={circumference * (1 - decorativeProgress)} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center"><span className="text-xs text-white/60">오늘 운동 시간</span><strong className="mt-1 text-3xl tracking-tight text-white">{formatDuration(seconds)}</strong><span className="mt-1 text-[10px] text-white/35">목표값 없는 기록 표시</span></div>
    </div>
  )
}
