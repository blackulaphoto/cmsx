import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

function ProtectedRoute({ children, roles }) {
  const { profile, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-white">Loading...</div>
  }

  if (!profile) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (roles && !roles.includes(profile.role)) {
    return <Navigate to="/" replace />
  }

  return children
}

export default ProtectedRoute
