import { format, parseISO } from 'date-fns'
import { ko } from 'date-fns/locale'

export function formatDuration(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds))
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  const remainingSeconds = safeSeconds % 60
  const short = `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`
  return hours > 0 ? `${String(hours).padStart(2, '0')}:${short}` : short
}

export function formatKoreanDate(value: Date | string, includeWeekday = true): string {
  const date = typeof value === 'string' ? parseISO(value) : value
  return format(date, includeWeekday ? 'yyyy년 M월 d일 (EEE)' : 'yyyy년 M월 d일', { locale: ko })
}

export function formatSeoulTime(iso: string): string {
  return new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(iso))
}

export function seoulToday(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

export function initials(nickname?: string | null, email?: string | null): string {
  return (nickname?.trim()[0] || email?.trim()[0] || 'F').toUpperCase()
}
