import { eachDayOfInterval, endOfMonth, endOfWeek, format, isSameDay, isSameMonth, startOfMonth, startOfWeek } from 'date-fns'
import { ko } from 'date-fns/locale'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { DailyWorkoutSummary } from '../../types/workout'

export function WorkoutCalendar({ month, selected, records, changeMonth, selectDate }: { month: Date; selected: Date; records: DailyWorkoutSummary[]; changeMonth: (offset: number) => void; selectDate: (date: Date) => void }) {
  const days = eachDayOfInterval({ start: startOfWeek(startOfMonth(month), { weekStartsOn: 0 }), end: endOfWeek(endOfMonth(month), { weekStartsOn: 0 }) })
  const recordDates = new Set(records.filter((record) => record.session_count > 0).map((record) => record.workout_date))
  return (
    <section className="content-card min-w-0">
      <div className="mb-6 flex items-center justify-between"><button className="calendar-arrow" onClick={() => changeMonth(-1)} aria-label="이전 달"><ChevronLeft size={18} /></button><h2 className="font-extrabold text-ink">{format(month, 'yyyy년 M월', { locale: ko })}</h2><button className="calendar-arrow" onClick={() => changeMonth(1)} aria-label="다음 달"><ChevronRight size={18} /></button></div>
      <div className="calendar-grid mb-2 text-xs font-semibold text-muted">{['일', '월', '화', '수', '목', '금', '토'].map((day) => <span key={day}>{day}</span>)}</div>
      <div className="calendar-grid">
        {days.map((day) => {
          const key = format(day, 'yyyy-MM-dd'); const hasRecord = recordDates.has(key); const selectedDay = isSameDay(day, selected); const today = isSameDay(day, new Date())
          return <button key={key} onClick={() => selectDate(day)} className={`calendar-day ${selectedDay ? 'calendar-selected' : ''} ${!isSameMonth(day, month) ? 'calendar-outside' : ''} ${today && !selectedDay ? 'calendar-today' : ''}`} aria-label={`${format(day, 'yyyy년 M월 d일')}${hasRecord ? ', 운동 기록 있음' : ''}`}><span>{format(day, 'd')}</span>{hasRecord && <i aria-hidden="true" />}</button>
        })}
      </div>
      <div className="mt-6 flex flex-wrap gap-4 border-t border-forest/8 pt-5 text-xs text-muted"><span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-lime-strong" />운동 기록 있음</span><span className="flex items-center gap-2"><i className="h-4 w-4 rounded-full border border-forest" />오늘</span><span className="flex items-center gap-2"><i className="h-4 w-4 rounded-full bg-lime" />선택</span></div>
    </section>
  )
}
