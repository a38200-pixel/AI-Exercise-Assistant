import { addMonths, endOfMonth, format, startOfMonth } from 'date-fns'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CardSkeleton, ErrorState } from '../components/common/States'
import { DailySummaryPanel } from '../components/history/DailySummaryPanel'
import { WorkoutCalendar } from '../components/history/WorkoutCalendar'
import { PageHeader } from '../components/layout/PageHeader'
import { useAuth } from '../contexts/AuthContext'
import { ApiError, workoutApi } from '../lib/api'
import type { DailyWorkoutSummary } from '../types/workout'

const empty = (workoutDate: string): DailyWorkoutSummary => ({ workout_date: workoutDate, squat_count: 0, stretch_seconds: 0, workout_seconds: 0, session_count: 0 })

export function HistoryPage() {
  const [month, setMonth] = useState(startOfMonth(new Date()))
  const [selected, setSelected] = useState(new Date())
  const [records, setRecords] = useState<DailyWorkoutSummary[]>([])
  const [summary, setSummary] = useState<DailyWorkoutSummary>(empty(format(new Date(), 'yyyy-MM-dd')))
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const { signOut } = useAuth(); const navigate = useNavigate()

  const loadMonth = useCallback(async () => {
    setLoading(true); setFailed(false)
    try {
      const data = await workoutApi.daily(format(startOfMonth(month), 'yyyy-MM-dd'), format(endOfMonth(month), 'yyyy-MM-dd'))
      setRecords(data)
      const selectedKey = format(selected, 'yyyy-MM-dd')
      setSummary(data.find((item) => item.workout_date === selectedKey) || empty(selectedKey))
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) { await signOut(); navigate('/login', { replace: true }); return }
      setFailed(true)
    } finally { setLoading(false) }
  }, [month, navigate, selected, signOut])
  useEffect(() => { void loadMonth() }, [loadMonth])

  function chooseDate(day: Date) { setSelected(day); const key = format(day, 'yyyy-MM-dd'); setSummary(records.find((item) => item.workout_date === key) || empty(key)) }
  function changeMonth(offset: number) { const next = startOfMonth(addMonths(month, offset)); setMonth(next); setSelected(next) }

  return <div className="page-wrap"><PageHeader title="운동 기록" subtitle="하루하루 쌓인 움직임을 달력에서 확인하세요." />{failed ? <ErrorState retry={() => void loadMonth()} /> : loading ? <div className="grid gap-5 xl:grid-cols-[1.35fr_.65fr]"><CardSkeleton className="h-[34rem]" /><CardSkeleton className="h-[34rem]" /></div> : <div className="grid gap-5 xl:grid-cols-[1.35fr_.65fr]"><WorkoutCalendar month={month} selected={selected} records={records} changeMonth={changeMonth} selectDate={chooseDate} /><DailySummaryPanel summary={summary} /></div>}</div>
}
