import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { FullPageLoader } from '../components/common/States'

export function ProtectedRoute() {
  const { session, loading } = useAuth()
  const location = useLocation()
  if (loading) return <FullPageLoader />
  if (!session) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}
