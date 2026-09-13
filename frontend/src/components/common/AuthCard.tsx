import type { ReactNode } from 'react'
import { Brand } from './Brand'

export function AuthCard({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer: ReactNode }) {
  return (
    <div className="auth-page">
      <div className="absolute left-6 top-6 sm:left-10 sm:top-8"><Brand /></div>
      <div className="auth-glow" />
      <main className="auth-card">
        <p className="eyebrow">FITROUTE ACCOUNT</p><h1 className="mt-4 text-3xl font-extrabold tracking-tight text-white">{title}</h1><p className="mt-2 text-sm text-white/45">{subtitle}</p>
        <div className="mt-8">{children}</div><div className="mt-6 text-center text-sm text-white/45">{footer}</div>
      </main>
    </div>
  )
}
