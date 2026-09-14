import { BarChart3, CalendarDays, Dumbbell, LayoutDashboard, UserRound } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const items = [
  { to: '/exercise', label: '홈', icon: Dumbbell },
  { to: '/dashboard', label: '대시', icon: LayoutDashboard },
  { to: '/history', label: '기록', icon: CalendarDays },
  { to: '/statistics', label: '통계', icon: BarChart3 },
  { to: '/profile', label: '프로필', icon: UserRound },
]

export function MobileBottomNav() {
  return (
    <nav className="mobile-nav" aria-label="모바일 주 메뉴">
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink key={to} to={to} className={({ isActive }) => `mobile-link ${isActive ? 'text-lime' : 'text-white/45'}`}>
          <Icon size={20} /><span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
