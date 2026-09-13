export interface DailyWorkoutSummary {
  workout_date: string
  squat_count: number
  stretch_seconds: number
  workout_seconds: number
  session_count: number
}

export interface WorkoutSession {
  id: string
  workout_date: string
  started_at: string
  ended_at: string
  workout_seconds: number
  squat_count: number
  stretch_seconds: number
}
