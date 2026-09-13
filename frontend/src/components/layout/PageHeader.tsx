import { Bell } from 'lucide-react'
import type { ReactNode } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { formatKoreanDate, initials } from '../../lib/format'
import { Brand } from '../common/Brand'

export function PageHeader({ title, subtitle, action }: { title?: string; subtitle?: string; action?: ReactNode }) {
  const { user } = useAuth()
  const nickname = user?.user_metadata?.nickname as string | undefined
  return (
    <header className="mb-7 flex items-start justify-between gap-4">
      <div>
        <div className="mb-7 lg:hidden"><Brand compact /></div>
        <h1 className="text-2xl font-extrabold tracking-[-0.03em] text-ink sm:text-3xl">{title || `안녕하세요, ${nickname || '회원'}님! 👋`}</h1>
        <p className="mt-1.5 text-sm text-muted sm:text-base">{subtitle || '오늘도 건강한 하루를 만들어가고 있네요.'}</p>
      </div>
      <div className="flex items-center gap-3 pt-1">
        {action}
        <span className="hidden text-sm font-medium text-muted sm:block">{formatKoreanDate(new Date())}</span>
        <button className="icon-button" aria-label="알림"><Bell size={19} /></button>
        <span className="avatar" aria-label="사용자 아바타">{initials(nickname, user?.email)}</span>
      </div>
    </header>
  )
}
