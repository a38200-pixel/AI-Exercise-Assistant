import { BarChart3, CalendarDays, Home, LayoutDashboard, LogOut, UserRound } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { Brand } from '../common/Brand'

const links = [
  { to: '/exercise', label: '홈', icon: Home },
  { to: '/dashboard', label: '대시보드', icon: LayoutDashboard },
  { to: '/history', label: '운동 기록', icon: CalendarDays },
  { to: '/statistics', label: '통계 분석', icon: BarChart3 },
  { to: '/profile', label: '프로필', icon: UserRound },
]

export function Sidebar() {
  const { signOut } = useAuth()
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-white/7 bg-ink px-5 py-7 lg:flex">
      <div className="px-3"><Brand /></div>
      <nav className="mt-12 flex flex-1 flex-col gap-2" aria-label="주 메뉴">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `side-link ${isActive ? 'side-link-active' : ''}`}>
            <Icon size={19} strokeWidth={1.8} />{label}
          </NavLink>
        ))}
      </nav>
      <button className="side-link w-full" onClick={() => void signOut()}><LogOut size={19} />로그아웃</button>
      <p className="mt-5 px-3 text-[11px] leading-5 text-white/30">AI와 함께 만드는<br />더 건강한 일상</p>
    </aside>
  )
}
