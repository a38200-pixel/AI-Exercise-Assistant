import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AuthCard } from '../components/common/AuthCard'
import { isSupabaseConfigured, supabase } from '../lib/supabase'

export function SignupPage() {
  const [form, setForm] = useState({ email: '', password: '', confirm: '', nickname: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setMessage('')
    if (form.password !== form.confirm) { setError('비밀번호가 서로 일치하지 않습니다.'); return }
    if (form.password.length < 8) { setError('비밀번호는 8자 이상 입력해 주세요.'); return }
    if (!isSupabaseConfigured) { setError('Frontend 환경변수에 Supabase 연결 정보를 설정해 주세요.'); return }
    setSubmitting(true)
    const { data, error: signUpError } = await supabase.auth.signUp({ email: form.email, password: form.password, options: { data: form.nickname.trim() ? { nickname: form.nickname.trim() } : undefined } })
    setSubmitting(false)
    if (signUpError) { setError('회원가입을 완료하지 못했습니다. 입력값을 확인해 주세요.'); return }
    setMessage(data.session ? '가입이 완료되었습니다. 대시보드로 이동해 주세요.' : '가입 확인 메일을 보냈습니다. 이메일 인증이 필요합니다.')
  }

  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }))
  return <AuthCard title="새로운 루트를 시작하세요" subtitle="운동 기록을 안전하게 한곳에 모아보세요." footer={<>이미 계정이 있나요? <Link className="font-bold text-lime" to="/login">로그인</Link></>}>
    <form onSubmit={submit} className="space-y-4">
      <label className="form-label">닉네임 <span className="font-normal text-white/30">(선택)</span><input className="form-input" value={form.nickname} onChange={(e) => update('nickname', e.target.value)} /></label>
      <label className="form-label">이메일<input className="form-input" type="email" autoComplete="email" required value={form.email} onChange={(e) => update('email', e.target.value)} /></label>
      <label className="form-label">비밀번호<input className="form-input" type="password" autoComplete="new-password" required value={form.password} onChange={(e) => update('password', e.target.value)} /></label>
      <label className="form-label">비밀번호 확인<input className="form-input" type="password" autoComplete="new-password" required value={form.confirm} onChange={(e) => update('confirm', e.target.value)} /></label>
      {error && <p className="form-error" role="alert">{error}</p>}{message && <p className="rounded-xl bg-lime/10 p-3 text-sm text-lime" role="status">{message}</p>}
      <button className="btn-primary w-full justify-center py-3.5" disabled={submitting}>{submitting ? '가입 중...' : '회원가입'}</button>
    </form>
  </AuthCard>
}
