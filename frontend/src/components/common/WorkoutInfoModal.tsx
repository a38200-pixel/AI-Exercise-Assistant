import { Download, MonitorUp, RefreshCw, Terminal, X } from 'lucide-react'
import { DESKTOP_CLIENT_DOWNLOAD_URL } from '../../lib/desktopClient'

export function WorkoutInfoModal({ close, retry, exercise = 'squat' }: { close: () => void; retry: () => void; exercise?: 'squat' }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/70 p-5 backdrop-blur-sm" role="presentation" onMouseDown={close}>
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-surface p-6 text-white shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="workout-info" onMouseDown={(event) => event.stopPropagation()}>
        <div className="flex items-start justify-between"><span className="metric-icon"><MonitorUp size={20} /></span><button className="icon-button-dark" onClick={close} aria-label="닫기"><X size={19} /></button></div>
        <h2 id="workout-info" className="mt-5 text-xl font-extrabold">FitRoute AI Client가 필요합니다</h2>
        <p className="mt-3 text-sm leading-6 text-white/60">실시간 카메라 자세 분석은 Windows용 FitRoute AI Client에서 실행됩니다. 이미 설치했다면 브라우저의 외부 앱 실행 확인에서 FitRoute 열기를 허용해 주세요.</p>
        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          {DESKTOP_CLIENT_DOWNLOAD_URL ? (
            <a className="btn-primary justify-center" href={DESKTOP_CLIENT_DOWNLOAD_URL}><Download size={16} /> AI Client 설치하기</a>
          ) : (
            <button className="btn-primary justify-center" disabled><Download size={16} /> 다운로드 준비 중</button>
          )}
          <button className="btn-outline justify-center px-4 py-2.5" onClick={retry}><RefreshCw size={16} /> 다시 시도</button>
        </div>
        {!DESKTOP_CLIENT_DOWNLOAD_URL && <p className="mt-3 rounded-xl border border-amber-300/10 bg-amber-300/5 p-3 text-xs leading-5 text-amber-100/60">설치 파일의 공개 다운로드 주소가 아직 설정되지 않았습니다. 개발 환경에서는 아래 명령을 사용할 수 있습니다.</p>}
        <div className="mt-3 flex items-center gap-3 rounded-2xl border border-white/8 bg-black/25 p-4 text-left">
          <Terminal className="shrink-0 text-lime" size={18} />
          <code className="min-w-0 break-all text-xs text-white/80">python src/main.py --exercise {exercise}</code>
        </div>
        <p className="mt-3 text-xs leading-5 text-white/38">설치 파일은 브라우저가 실행하지 않습니다. 다운로드 후 사용자가 직접 설치를 승인해야 합니다.</p>
        <button className="mt-5 w-full rounded-xl px-4 py-2.5 text-sm font-bold text-white/45 hover:bg-white/5 hover:text-white" onClick={close}>취소</button>
      </div>
    </div>
  )
}
