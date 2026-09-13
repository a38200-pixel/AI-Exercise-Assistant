import { AlertCircle, LoaderCircle, RefreshCw } from 'lucide-react'

export function FullPageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-ink text-white" role="status">
      <LoaderCircle className="h-7 w-7 animate-spin text-lime" />
      <span className="sr-only">불러오는 중</span>
    </div>
  )
}

export function CardSkeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton min-h-36 rounded-3xl ${className}`} aria-label="데이터를 불러오는 중" />
}

export function ErrorState({ retry }: { retry: () => void }) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center gap-3 rounded-3xl border border-red-900/20 bg-white p-8 text-center">
      <span className="rounded-full bg-red-50 p-3 text-red-600"><AlertCircle /></span>
      <div><h3 className="font-bold text-ink">운동 기록을 불러오지 못했습니다.</h3><p className="mt-1 text-sm text-muted">서버 상태를 확인한 뒤 다시 시도해 주세요.</p></div>
      <button className="btn-secondary" onClick={retry}><RefreshCw size={16} /> 다시 시도</button>
    </div>
  )
}

export function EmptyState({ title = '운동 기록이 아직 없습니다.', description = '운동을 시작하면 여기에 기록이 표시됩니다.' }) {
  return (
    <div className="flex min-h-40 flex-col items-center justify-center rounded-2xl border border-dashed border-forest/15 bg-mist/60 px-5 text-center">
      <div className="mb-3 h-2 w-2 rounded-full bg-lime shadow-[0_0_0_7px_rgba(183,255,99,.2)]" />
      <p className="font-bold text-ink">{title}</p><p className="mt-1 text-sm text-muted">{description}</p>
    </div>
  )
}
