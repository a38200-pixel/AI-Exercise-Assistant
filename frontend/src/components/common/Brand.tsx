import { Link } from 'react-router-dom'

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to={compact ? '/dashboard' : '/'} className="inline-flex items-baseline font-extrabold tracking-[-0.04em] text-white">
      <span className={compact ? 'text-xl' : 'text-2xl'}>FitRoute</span><span className="text-lime">.</span>
    </Link>
  )
}
