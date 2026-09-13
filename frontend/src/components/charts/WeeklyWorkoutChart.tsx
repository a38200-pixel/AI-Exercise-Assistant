import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { format, parseISO } from 'date-fns'
import { ko } from 'date-fns/locale'
import type { DailyWorkoutSummary } from '../../types/workout'

export function WeeklyWorkoutChart({ data }: { data: DailyWorkoutSummary[] }) {
  const chartData = data.map((day) => ({
    day: format(parseISO(day.workout_date), 'EEE', { locale: ko }),
    운동시간: Math.round(day.workout_seconds / 60),
    스쿼트: day.squat_count,
  }))
  return (
    <div className="h-64 w-full" aria-label="최근 7일 운동 현황 차트">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 12, right: 4, left: -24, bottom: 0 }}>
          <CartesianGrid stroke="#dfe7dc" strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="day" tickLine={false} axisLine={false} tick={{ fill: '#718078', fontSize: 12 }} />
          <YAxis tickLine={false} axisLine={false} tick={{ fill: '#8a958f', fontSize: 11 }} />
          <Tooltip cursor={{ fill: 'rgba(116,185,78,.07)' }} contentStyle={{ borderRadius: 14, border: '1px solid #e2e8df', boxShadow: '0 12px 30px rgba(11,17,14,.08)' }} />
          <Bar dataKey="운동시간" fill="#b7ff63" radius={[6, 6, 2, 2]} maxBarSize={22} />
          <Bar dataKey="스쿼트" fill="#4f8250" radius={[6, 6, 2, 2]} maxBarSize={22} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
