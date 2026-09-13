import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { AuthCard } from '../components/common/AuthCard'
import { useAuth } from '../contexts/AuthContext'
import { isSupabaseConfigured, supabase } from '../lib/supabase'

export function LoginPage() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  if (session) return <Navigate to="/dashboard" replace />

  async function submit(event: FormEvent) {
    event.preventDefault(); setError('')
    if (!isSupabaseConfigured) { setError('Frontend 환경변수에 Supabase 연결 정보를 설정해 주세요.'); return }
    setSubmitting(true)
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password })
    setSubmitting(false)
    if (signInError) { setError('이메일 또는 비밀번호를 확인해 주세요.'); return }
    const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/dashboard'
    navigate(destination, { replace: true })
  }

  return <AuthCard title="다시 만나서 반가워요" subtitle="계속해서 건강한 기록을 확인해 보세요." footer={<>아직 계정이 없나요? <Link className="font-bold text-lime" to="/signup">회원가입</Link></>}>
    <form onSubmit={submit} className="space-y-5">
      <label className="form-label">이메일<input className="form-input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" /></label>
      <label className="form-label">비밀번호<input className="form-input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="비밀번호 입력" /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="btn-primary w-full justify-center py-3.5" disabled={submitting}>{submitting ? '로그인 중...' : '로그인'}</button>
    </form>
  </AuthCard>
}
