import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

function ProtectedRoute({ children, roles, allowOnboarding = false }) {
  const { profile, loading, needsOnboarding } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-white">Loading...</div>
  }

  if (!profile) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  // First-login front door: users who haven't completed org/workspace setup are
  // sent to onboarding. `allowOnboarding` exempts the onboarding route itself
  // (so it can render) and prevents a redirect loop.
  if (needsOnboarding && !allowOnboarding) {
    return <Navigate to="/onboarding" replace />
  }

  if (roles && !roles.includes(profile.role)) {
    return <Navigate to="/" replace />
  }

  return children
}

export default ProtectedRoute
