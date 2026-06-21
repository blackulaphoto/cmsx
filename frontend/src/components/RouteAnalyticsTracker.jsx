import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { captureUtmFromSearch, trackModuleView } from '../utils/analytics'

/**
 * Invisible tracker mounted inside the authenticated shell. Captures UTM
 * attribution once on entry, then emits a safe `module_view` event whenever the
 * route changes to a tracked module. Renders nothing and never blocks the UI —
 * all tracking is best-effort.
 */
export default function RouteAnalyticsTracker() {
  const location = useLocation()
  const { profile } = useAuth()
  const lastTracked = useRef(null)

  // Capture UTM attribution one time on first mount.
  useEffect(() => {
    if (typeof window !== 'undefined') {
      captureUtmFromSearch(window.location.search)
    }
  }, [])

  // Track module views on path change, only for authenticated users.
  useEffect(() => {
    if (!profile) return
    const path = location.pathname
    if (lastTracked.current === path) return
    lastTracked.current = path
    trackModuleView(path)
  }, [location.pathname, profile])

  return null
}
