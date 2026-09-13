import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { MobileBottomNav } from './MobileBottomNav'

export function AppShell() {
  return (
    <div className="min-h-screen bg-app">
      <Sidebar />
      <main className="min-h-screen pb-28 lg:ml-64 lg:pb-0"><Outlet /></main>
      <MobileBottomNav />
    </div>
  )
}
