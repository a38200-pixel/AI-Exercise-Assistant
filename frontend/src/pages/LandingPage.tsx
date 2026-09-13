import { Activity, ArrowRight, BarChart3, Check, Dumbbell, Menu, ShieldCheck, Smartphone } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/common/Brand'

export function LandingPage() {
  return (
    <div className="min-h-screen overflow-hidden bg-ink text-white">
      <header className="landing-nav">
        <Brand />
        <nav className="hidden items-center gap-8 text-sm text-white/60 md:flex" aria-label="소개 메뉴">
          <a href="#service">서비스</a><a href="#features">기능</a><Link to="/history">기록</Link>
        </nav>
        <div className="hidden items-center gap-3 sm:flex"><Link className="px-4 py-2 text-sm font-semibold text-white/65" to="/login">로그인</Link><Link className="btn-primary" to="/signup">회원가입</Link></div>
        <Link to="/login" className="icon-button-dark sm:hidden" aria-label="메뉴"><Menu /></Link>
      </header>

      <main>
        <section className="hero-shell">
          <div className="relative z-10 max-w-2xl py-16 lg:py-24">
            <p className="eyebrow">YOUR DAILY FITNESS ROUTE</p>
            <h1 className="mt-5 text-6xl font-black tracking-[-0.065em] sm:text-7xl lg:text-[6.3rem]">FitRoute<span className="text-lime">.</span></h1>
            <h2 className="mt-5 text-2xl font-bold tracking-tight sm:text-3xl">오늘도, 더 건강한 나를 향한 한 걸음</h2>
            <p className="mt-6 max-w-lg text-base leading-7 text-white/58 sm:text-lg">AI 기반 운동 인식으로 완성한 기록을 한 곳에서 확인하세요. 매일의 움직임이 선명한 변화가 됩니다.</p>
            <div className="mt-9 flex flex-wrap gap-3"><Link className="btn-primary px-6 py-3.5" to="/signup">지금 시작하기 <ArrowRight size={18} /></Link><a className="btn-outline px-6 py-3.5" href="#features">기능 알아보기</a></div>
          </div>

          <div className="hero-visual" aria-label="AI 운동 분석 데모 비주얼">
            <div className="pose-orbit pose-orbit-one" /><div className="pose-orbit pose-orbit-two" />
            <div className="pose-figure" aria-hidden="true"><span className="pose-head" /><span className="pose-body" /><span className="pose-arm" /><span className="pose-leg pose-leg-one" /><span className="pose-leg pose-leg-two" /></div>
            <div className="analysis-card"><div className="flex items-center justify-between"><span className="text-xs text-white/45">AI Pose Analysis</span><span className="demo-pill">DEMO</span></div><div className="mt-6 flex items-center gap-3"><span className="metric-icon"><Activity size={20} /></span><div><p className="text-xs text-white/45">Movement</p><p className="font-bold">Squat</p></div></div><div className="mt-5 flex items-center justify-between text-sm"><span className="text-white/50">Confidence</span><strong>92.4%</strong></div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full w-[92%] rounded-full bg-lime" /></div></div>
          </div>
        </section>

        <section id="features" className="feature-strip">
          {[{ icon: Dumbbell, title: 'AI 운동 인식', text: '정확한 운동 기록' }, { icon: BarChart3, title: '기록과 통계', text: '날짜별 변화 확인' }, { icon: Smartphone, title: '어디서나 확인', text: '반응형 웹 대시보드' }].map(({ icon: Icon, title, text }) => <div key={title} className="flex items-center gap-4"><span className="landing-icon"><Icon size={21} /></span><div><h3 className="font-bold">{title}</h3><p className="mt-1 text-xs text-white/40">{text}</p></div></div>)}
        </section>

        <section id="service" className="mx-auto max-w-7xl px-6 py-24 lg:px-10">
          <div className="grid gap-5 md:grid-cols-3">
            {[['안전한 인증', 'Supabase Auth와 사용자별 데이터 정책을 사용합니다.', ShieldCheck], ['실제 운동 데이터', '임의의 목표나 기록 없이 저장된 데이터만 보여줍니다.', Check], ['간결한 흐름', '오늘, 기록, 통계를 빠르게 오갈 수 있습니다.', Activity]].map(([title, text, Icon]) => { const FeatureIcon = Icon as typeof Activity; return <article key={title as string} className="dark-feature-card"><FeatureIcon className="text-lime" /><h3 className="mt-8 text-xl font-bold">{title as string}</h3><p className="mt-3 text-sm leading-6 text-white/48">{text as string}</p></article> })}
          </div>
        </section>
      </main>
    </div>
  )
}
