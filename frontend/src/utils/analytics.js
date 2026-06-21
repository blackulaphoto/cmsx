/**
 * Lightweight first-party analytics client for Ember.
 *
 * Sends only SAFE product-usage signals to `POST /api/analytics/event`:
 * event type, route, module, and coarse marketing attribution (UTM). It never
 * sends PHI or protected client content — callers should pass only generic
 * metadata (tab names, counts, flags), and the backend sanitizes again anyway.
 *
 * Tracking is best-effort and fire-and-forget: failures are swallowed so a
 * missing/disabled analytics endpoint can never break navigation.
 */
import { apiCall } from '../api/config'

export const ALLOWED_EVENT_TYPES = [
  'page_view',
  'route_view',
  'module_view',
  'feature_use',
  'session_start',
  'owner_view',
  'super_admin_view',
]

const UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']
const ATTRIBUTION_STORAGE_KEY = 'cmsx:attribution'

// Path → module mapping for the major trackable modules.
const MODULE_BY_PREFIX = [
  ['/case-management', 'case_management'],
  ['/client', 'case_management'],
  ['/admissions', 'admissions'],
  ['/documentation', 'documentation'],
  ['/housing', 'housing'],
  ['/sober-living', 'sober_living'],
  ['/benefits', 'benefits'],
  ['/fmla', 'fmla'],
  ['/owner', 'owner'],
  ['/super-admin', 'super_admin'],
]

const safeSession = () => {
  try {
    if (typeof window === 'undefined' || !window.sessionStorage) return null
    return window.sessionStorage
  } catch {
    return null
  }
}

/** Resolve the canonical module name for a route path, or null if not a tracked module. */
export function moduleForPath(pathname) {
  const path = String(pathname || '')
  if (path === '/' || path === '' || path === '/enhanced-dashboard') return 'dashboard'
  for (const [prefix, mod] of MODULE_BY_PREFIX) {
    if (path === prefix || path.startsWith(`${prefix}/`)) return mod
  }
  return null
}

/**
 * Read UTM params from a location-like search string and persist any present
 * attribution to sessionStorage (first-touch wins for the session). Returns the
 * stored attribution object.
 */
export function captureUtmFromSearch(search) {
  const store = safeSession()
  let params
  try {
    params = new URLSearchParams(search || '')
  } catch {
    params = new URLSearchParams('')
  }
  const found = {}
  for (const key of UTM_KEYS) {
    const value = (params.get(key) || '').trim()
    if (value) found[key] = value.slice(0, 200)
  }
  if (Object.keys(found).length === 0) {
    return getStoredAttribution()
  }
  // First-touch: don't overwrite an attribution already captured this session.
  const existing = getStoredAttribution()
  if (existing && Object.keys(existing).length > 0) {
    return existing
  }
  if (store) {
    try {
      store.setItem(ATTRIBUTION_STORAGE_KEY, JSON.stringify(found))
    } catch {
      /* ignore quota/availability errors */
    }
  }
  return found
}

export function getStoredAttribution() {
  const store = safeSession()
  if (!store) return {}
  try {
    const raw = store.getItem(ATTRIBUTION_STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

/** Map stored UTM attribution onto the safe analytics event fields. */
function attributionFields() {
  const a = getStoredAttribution() || {}
  const fields = {}
  if (a.utm_source) fields.source = a.utm_source
  if (a.utm_medium) fields.medium = a.utm_medium
  if (a.utm_campaign) fields.campaign = a.utm_campaign
  return fields
}

/**
 * Send one usage event. Best-effort; resolves to true on success, false on any
 * failure (never throws). Unknown event types are skipped client-side.
 */
export async function trackEvent(eventType, { route, module, metadata } = {}) {
  if (!ALLOWED_EVENT_TYPES.includes(eventType)) return false
  const referrer =
    typeof document !== 'undefined' && document.referrer ? document.referrer.slice(0, 500) : undefined
  const payload = {
    event_type: eventType,
    route: route ? String(route).slice(0, 500) : undefined,
    module: module || undefined,
    referrer,
    ...attributionFields(),
  }
  if (metadata && typeof metadata === 'object') {
    payload.metadata = metadata
  }
  try {
    await apiCall('/api/analytics/event', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    return true
  } catch {
    // Analytics is non-critical — swallow errors so nav/UX never breaks.
    return false
  }
}

/** Convenience: track a module/route view for the given pathname. */
export async function trackModuleView(pathname) {
  const module = moduleForPath(pathname)
  if (!module) return false
  return trackEvent('module_view', { route: pathname, module })
}
