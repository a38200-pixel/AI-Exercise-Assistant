import { ExternalLink, X } from 'lucide-react'

export function WorkoutInfoModal({ close }: { close: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/70 p-5 backdrop-blur-sm" role="presentation" onMouseDown={close}>
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-surface p-6 text-white shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="workout-info" onMouseDown={(event) => event.stopPropagation()}>
        <div className="flex items-start justify-between"><span className="metric-icon"><ExternalLink size={20} /></span><button className="icon-button-dark" onClick={close} aria-label="닫기"><X size={19} /></button></div>
        <h2 id="workout-info" className="mt-5 text-xl font-extrabold">AI 운동은 데스크톱에서 시작해요</h2>
        <p className="mt-3 text-sm leading-6 text-white/60">AI 운동 프로그램에서 운동을 시작하면 완료된 기록이 이 대시보드에 반영됩니다. 브라우저 카메라 운동 기능은 아직 제공하지 않습니다.</p>
        <button className="btn-primary mt-6 w-full justify-center" onClick={close}>확인</button>
      </div>
    </div>
  )
}
