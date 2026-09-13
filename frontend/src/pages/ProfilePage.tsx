import { Lock, LogOut, Mail, MapPin, Moon, UserRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/layout/PageHeader'
import { useAuth } from '../contexts/AuthContext'
import { initials } from '../lib/format'

export function ProfilePage() {
  const { user, signOut } = useAuth(); const navigate = useNavigate()
  const nickname = user?.user_metadata?.nickname as string | undefined
  async function logout() { await signOut(); navigate('/login', { replace: true }) }
  return <div className="page-wrap"><PageHeader title="프로필 설정" subtitle="계정과 서비스 환경을 확인하세요." /><div className="mx-auto max-w-3xl"><section className="profile-hero"><span className="profile-avatar">{initials(nickname, user?.email)}</span><div><h2 className="text-2xl font-extrabold text-white">{nickname || 'FitRoute 회원'}</h2><p className="mt-1 text-sm text-white/45">better everyday <span className="text-lime">●</span></p></div></section><section className="content-card mt-5"><h2 className="section-title">계정 정보</h2><div className="setting-list"><div className="setting-row"><Mail /><span>이메일</span><strong>{user?.email || '-'}</strong><em>읽기 전용</em></div><div className="setting-row"><UserRound /><span>닉네임</span><strong>{nickname || '설정되지 않음'}</strong><em>읽기 전용</em></div><div className="setting-row"><MapPin /><span>시간대</span><strong>Asia/Seoul</strong><em>고정</em></div></div></section><section className="content-card mt-5"><h2 className="section-title">테마 설정</h2><div className="setting-list"><div className="setting-row"><Moon /><span>다크 내비게이션</span><strong>사용 중</strong><em>Coming Soon</em></div><div className="setting-row"><Lock /><span>프로필 수정</span><strong>Backend API 필요</strong><em>Coming Soon</em></div></div></section><button className="btn-danger mt-5 w-full justify-center" onClick={() => void logout()}><LogOut size={18} /> 로그아웃</button></div></div>
}
