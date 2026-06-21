// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../api/config', () => ({ apiCall: vi.fn(() => Promise.resolve({ success: true, event_id: 1 })) }))

import { apiCall } from '../api/config'
import {
  moduleForPath,
  captureUtmFromSearch,
  getStoredAttribution,
  trackEvent,
  trackModuleView,
} from './analytics'

beforeEach(() => {
  vi.clearAllMocks()
  window.sessionStorage.clear()
})

describe('moduleForPath', () => {
  it('maps known routes to canonical module names', () => {
    expect(moduleForPath('/')).toBe('dashboard')
    expect(moduleForPath('/case-management')).toBe('case_management')
    expect(moduleForPath('/client/123')).toBe('case_management')
    expect(moduleForPath('/housing/case-manager')).toBe('housing')
    expect(moduleForPath('/owner')).toBe('owner')
    expect(moduleForPath('/super-admin')).toBe('super_admin')
  })

  it('returns null for untracked routes', () => {
    expect(moduleForPath('/settings')).toBeNull()
    expect(moduleForPath('/profile')).toBeNull()
  })
})

describe('UTM attribution capture', () => {
  it('captures UTM params and is first-touch (does not overwrite)', () => {
    const first = captureUtmFromSearch('?utm_source=google&utm_medium=cpc&utm_campaign=launch')
    expect(first).toEqual({ utm_source: 'google', utm_medium: 'cpc', utm_campaign: 'launch' })
    // Second visit with different params must NOT overwrite the first-touch value.
    captureUtmFromSearch('?utm_source=bing')
    expect(getStoredAttribution()).toEqual(first)
  })

  it('returns empty attribution when no UTM params are present', () => {
    expect(captureUtmFromSearch('?foo=bar')).toEqual({})
  })
})

describe('trackEvent', () => {
  it('skips unknown event types without calling the API', async () => {
    const ok = await trackEvent('not_a_real_event', { module: 'dashboard' })
    expect(ok).toBe(false)
    expect(apiCall).not.toHaveBeenCalled()
  })

  it('posts a safe payload including attribution for known events', async () => {
    captureUtmFromSearch('?utm_source=google&utm_medium=cpc')
    await trackEvent('module_view', { route: '/owner', module: 'owner' })
    expect(apiCall).toHaveBeenCalledTimes(1)
    const [url, options] = apiCall.mock.calls[0]
    expect(url).toBe('/api/analytics/event')
    const body = JSON.parse(options.body)
    expect(body.event_type).toBe('module_view')
    expect(body.module).toBe('owner')
    expect(body.source).toBe('google')
    expect(body.medium).toBe('cpc')
  })

  it('trackModuleView is a no-op for untracked routes', async () => {
    const ok = await trackModuleView('/settings')
    expect(ok).toBe(false)
    expect(apiCall).not.toHaveBeenCalled()
  })

  it('never throws when the API call fails', async () => {
    apiCall.mockRejectedValueOnce(new Error('network down'))
    await expect(trackEvent('page_view', { module: 'dashboard' })).resolves.toBe(false)
  })
})
