export const DESKTOP_CLIENT_DOWNLOAD_URL = (import.meta.env.VITE_DESKTOP_CLIENT_DOWNLOAD_URL || '').trim()

const PROTOCOL_FALLBACK_MS = 1800

export function desktopClientUrl(exercise: 'squat'): string {
  return `fitroute://start?exercise=${encodeURIComponent(exercise)}`
}

/**
 * 브라우저는 protocol handler 설치 여부를 확정적으로 알려주지 않는다.
 * blur/hidden은 외부 앱 전환 신호로만 사용하고, 신호가 없으면 설치 안내를 띄운다.
 */
export function requestDesktopClientLaunch(
  exercise: 'squat',
  showFallback: () => void,
  externalAppSignaled: () => void,
): () => void {
  let finished = false

  const cleanup = () => {
    window.clearTimeout(fallbackTimer)
    window.removeEventListener('blur', handleExternalSignal)
    document.removeEventListener('visibilitychange', handleVisibilityChange)
  }
  const handleExternalSignal = () => {
    if (finished) return
    finished = true
    cleanup()
    externalAppSignaled()
  }
  const handleVisibilityChange = () => {
    if (document.visibilityState === 'hidden') handleExternalSignal()
  }
  const fallbackTimer = window.setTimeout(() => {
    if (finished) return
    finished = true
    cleanup()
    showFallback()
  }, PROTOCOL_FALLBACK_MS)

  window.addEventListener('blur', handleExternalSignal)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.location.href = desktopClientUrl(exercise)

  return cleanup
}
