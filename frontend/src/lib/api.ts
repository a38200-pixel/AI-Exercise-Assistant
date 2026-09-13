import { supabase } from './supabase'
import type { DailyWorkoutSummary, WorkoutSession } from '../types/workout'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const REQUEST_TIMEOUT_MS = 10_000

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message)
  }
}

async function apiRequest<T>(path: string): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session?.access_token) throw new ApiError('로그인이 필요합니다.', 401)

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    })
  } catch {
    throw new ApiError('서버에 연결할 수 없습니다.')
  }

  if (response.status === 401) throw new ApiError('로그인 세션이 만료되었습니다.', 401)
  if (!response.ok) throw new ApiError('운동 기록을 불러오지 못했습니다.', response.status)
  return response.json() as Promise<T>
}

export const workoutApi = {
  today: () => apiRequest<DailyWorkoutSummary>('/api/workouts/today'),
  daily: (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams()
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    const query = params.size ? `?${params}` : ''
    return apiRequest<DailyWorkoutSummary[]>(`/api/workouts/daily${query}`)
  },
  dailyDetail: (workoutDate: string) =>
    apiRequest<DailyWorkoutSummary>(`/api/workouts/daily/${workoutDate}`),
  sessions: (workoutDate: string) =>
    apiRequest<WorkoutSession[]>(`/api/workouts/sessions/${workoutDate}`),
}
