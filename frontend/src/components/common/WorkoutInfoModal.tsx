import { MonitorUp, Terminal, X } from 'lucide-react'

export function WorkoutInfoModal({ close, exercise = 'squat' }: { close: () => void; exercise?: 'squat' }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/70 p-5 backdrop-blur-sm" role="presentation" onMouseDown={close}>
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-surface p-6 text-white shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="workout-info" onMouseDown={(event) => event.stopPropagation()}>
        <div className="flex items-start justify-between"><span className="metric-icon"><MonitorUp size={20} /></span><button className="icon-button-dark" onClick={close} aria-label="닫기"><X size={19} /></button></div>
        <h2 id="workout-info" className="mt-5 text-xl font-extrabold">Squat 운동을 준비했어요</h2>
        <p className="mt-3 text-sm leading-6 text-white/60">현재 AI 카메라는 Python 데스크톱 프로그램으로 실행됩니다. 프로젝트 터미널에서 아래 명령을 실행하면 선택한 스쿼트 모드로 시작합니다.</p>
        <div className="mt-5 flex items-center gap-3 rounded-2xl border border-white/8 bg-black/25 p-4 text-left">
          <Terminal className="shrink-0 text-lime" size={18} />
          <code className="min-w-0 break-all text-xs text-white/80">python src/main.py --exercise {exercise}</code>
        </div>
        <p className="mt-3 text-xs leading-5 text-white/38">브라우저 보안을 위해 웹에서 로컬 프로그램을 자동 실행하지 않습니다. 카메라에서 S 키로 세션을 시작하세요.</p>
        <button className="btn-primary mt-6 w-full justify-center" onClick={close}>확인</button>
      </div>
    </div>
  )
}
