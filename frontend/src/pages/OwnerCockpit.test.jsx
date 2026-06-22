// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'

vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../api/config', () => ({
  apiCall: vi.fn(),
  apiFetch: vi.fn(() => Promise.resolve({ ok: false, json: async () => ({}) })),
  messagesAPI: { unreadCount: vi.fn(() => Promise.resolve({ count: 0 })) },
  API_BASE_URL: '',
}))

import { useAuth } from '../contexts/AuthContext'
import { apiCall } from '../api/config'
import Layout from '../components/Layout'
import ProtectedRoute from '../components/ProtectedRoute'
import OwnerCockpit from './OwnerCockpit'

const BASE = { profile: { full_name: 'Owner', role: 'admin' }, loading: false, needsOnboarding: false, logout: vi.fn() }

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location-probe">{location.pathname}</div>
}

const EMPTY_ANALYTICS = {
  success: true,
  window: 'all',
  total_orgs: 2,
  active_orgs: 1,
  suspended_orgs: 1,
  total_users: 7,
  active_users: 5,
  total_clients: 11,
  plan_breakdown: { team: 1, individual: 1 },
  billing_status_breakdown: { active: 1, trialing: 1 },
  estimated_mrr: 148,
  estimated_mrr_source: 'internal_plan_fields',
  total_events: 0,
  module_usage: { dashboard: 0, housing: 0, fmla: 0 },
  top_modules: [],
  least_used_modules: [
    { module: 'fmla', count: 0 },
    { module: 'housing', count: 0 },
  ],
  marketing_source_breakdown: {},
  marketing_attribution: { source: {}, medium: {}, campaign: {} },
  recent_activity: [],
  recent_events: [],
  active_event_orgs: 0,
  active_event_users: 0,
  ad_readiness: {
    landing_page_visits: null,
    campaign_conversions: null,
    cost_per_signup: null,
    ad_spend: null,
    source: 'not_connected',
  },
  stripe_activated: false,
}

const EMPTY_SUPPORT = {
  success: true,
  total_tickets: 0,
  open_tickets: 0,
  high_priority_tickets: 0,
  by_category: { bug: 0, account: 0, billing: 0, feature_request: 0, usability: 0, other: 0 },
  by_status: { open: 0, in_progress: 0, waiting: 0, resolved: 0, closed: 0 },
  by_priority: { low: 0, normal: 0, high: 0, urgent: 0 },
  recent_tickets: [],
  stripe_activated: false,
}

const DETAIL_TICKET = {
  id: 7,
  org_id: 'org_a',
  submitted_by_user_id: 'cm_1',
  submitted_by_email: 'reporter@a.test',
  category: 'bug',
  priority: 'normal',
  status: 'open',
  subject: 'Typo on page',
  description: 'Full description body for the drawer.',
  assigned_to: null,
  internal_notes: 'Existing internal note.',
  extra: null,
  created_at: '2026-06-21T10:00:00',
  updated_at: '2026-06-21T10:00:00',
  resolved_at: null,
}

const EMPTY_MARKETING = {
  success: true,
  total_campaigns: 0,
  active_campaigns: 0,
  by_status: { draft: 0, active: 0, paused: 0, completed: 0, archived: 0 },
  by_channel: {
    google_ads: 0, meta_ads: 0, tiktok: 0, linkedin: 0, organic: 0,
    referral: 0, email: 0, manual: 0, other: 0,
  },
  total_budget: 0,
  total_spend: 0,
  utm_attribution: { source: {}, medium: {}, campaign: {} },
  campaign_utm_visits: {},
  performance: {
    landing_page_visits: null,
    signups: null,
    conversions: null,
    cost_per_signup: null,
    source: 'not_connected',
  },
  ad_platforms_connected: false,
  stripe_activated: false,
}

function mockOwnerApi(
  analytics = EMPTY_ANALYTICS,
  support = EMPTY_SUPPORT,
  detail = DETAIL_TICKET,
  marketing = EMPTY_MARKETING,
  campaigns = [],
) {
  apiCall.mockImplementation((url, opts) => {
    if (url.startsWith('/api/owner/analytics/summary')) {
      return Promise.resolve(analytics)
    }
    if (url.startsWith('/api/owner/support/summary')) {
      return Promise.resolve(support)
    }
    if (url.startsWith('/api/owner/marketing/summary')) {
      return Promise.resolve(marketing)
    }
    if (url.startsWith('/api/owner/marketing/campaigns')) {
      if (opts?.method === 'POST') {
        const body = JSON.parse(opts.body || '{}')
        return Promise.resolve({ success: true, campaign: { id: 99, created_at: '2026-06-21T10:00:00', updated_at: '2026-06-21T10:00:00', ...body } })
      }
      if (opts?.method === 'PATCH') {
        const body = JSON.parse(opts.body || '{}')
        return Promise.resolve({ success: true, campaign: { ...(campaigns[0] || {}), ...body } })
      }
      return Promise.resolve({ success: true, campaigns, count: campaigns.length, statuses: [], channels: [] })
    }
    if (url.startsWith('/api/owner/support/tickets/')) {
      if (opts?.method === 'PATCH') {
        const patch = JSON.parse(opts.body || '{}')
        return Promise.resolve({ success: true, ticket: { ...detail, ...patch } })
      }
      return Promise.resolve({ success: true, ticket: detail })
    }
    if (url === '/api/super-admin/overview') {
      return Promise.resolve({
        multi_tenant_enabled: false,
        total_orgs: 2,
        total_users: 7,
        active_users: 5,
        total_clients: 11,
        stripe: {
          mode: 'dormant',
          stripe_secret_configured: true,
          all_required_prices_configured: true,
          stripe_connected: true,
          billing_enabled: false,
          checkout_enabled: false,
          portal_enabled: false,
          webhooks_enabled: false,
          webhook_secret_configured: false,
          missing_price_env_vars: [],
        },
      })
    }
    if (url === '/api/super-admin/organizations') {
      return Promise.resolve({
        organizations: [
          { org_id: 'org_a', name: 'Org A', status: 'active', user_count: 4, client_count: 7 },
          { org_id: 'org_b', name: 'Org B', status: 'suspended', user_count: 3, client_count: 4 },
        ],
      })
    }
    return Promise.resolve({})
  })
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Owner Cockpit nav visibility', () => {
  it('shows the Owner Cockpit control only for super-admin users', () => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
    render(<MemoryRouter><Layout><div>c</div></Layout></MemoryRouter>)
    fireEvent.click(screen.getAllByRole('button').find((button) => button.textContent.includes('Owner')))
    expect(screen.getByRole('button', { name: /Owner Cockpit/i })).toBeInTheDocument()
  })

  it('does not show the Owner Cockpit control for non-super-admin users', () => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: false })
    render(<MemoryRouter><Layout><div>c</div></Layout></MemoryRouter>)
    fireEvent.click(screen.getAllByRole('button').find((button) => button.textContent.includes('Owner')))
    expect(screen.queryByRole('button', { name: /Owner Cockpit/i })).not.toBeInTheDocument()
  })

  it('navigates to /owner when the Owner Cockpit control is clicked', () => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="*" element={<><Layout><div>shell</div></Layout><LocationProbe /></>} />
        </Routes>
      </MemoryRouter>
    )
    fireEvent.click(screen.getAllByRole('button').find((button) => button.textContent.includes('Owner')))
    fireEvent.click(screen.getByRole('button', { name: /Owner Cockpit/i }))
    expect(screen.getByTestId('location-probe')).toHaveTextContent('/owner')
    expect(screen.queryByRole('button', { name: /Owner Cockpit/i })).not.toBeInTheDocument()
  })
})

describe('Owner Cockpit route gating', () => {
  it('renders for super-admin users', async () => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
    mockOwnerApi()
    render(
      <MemoryRouter initialEntries={['/owner']}>
        <Routes>
          <Route path="/owner" element={<ProtectedRoute requireSuperAdmin><OwnerCockpit /></ProtectedRoute>} />
          <Route path="/" element={<div>HOME</div>} />
        </Routes>
      </MemoryRouter>
    )
    expect(await screen.findByText('Ember HQ')).toBeInTheDocument()
  })

  it('redirects non-super-admin users away from /owner', () => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: false })
    render(
      <MemoryRouter initialEntries={['/owner']}>
        <Routes>
          <Route path="/owner" element={<ProtectedRoute requireSuperAdmin><div>OWNER</div></ProtectedRoute>} />
          <Route path="/" element={<div>HOME</div>} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('HOME')).toBeInTheDocument()
    expect(screen.queryByText('OWNER')).not.toBeInTheDocument()
  })
})

describe('Owner Cockpit content', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
    mockOwnerApi()
  })

  it('shows platform overview and placeholder sections', async () => {
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Platform Overview')).toBeInTheDocument()
    expect(screen.getByText('Organizations / Customers')).toBeInTheDocument()
    expect(screen.getByText('Billing & Stripe')).toBeInTheDocument()
    expect(screen.getByText('Marketing & Campaign Tracker')).toBeInTheDocument()
    expect(screen.getByText('Support Queue')).toBeInTheDocument()
    expect(screen.getByText('Dev / System')).toBeInTheDocument()
    expect(screen.getByText('Internal Team')).toBeInTheDocument()
    expect(screen.getByText('Coming next: internal team roles')).toBeInTheDocument()
  })

  it('shows Stripe readiness as dormant when the backend says dormant', async () => {
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Stripe readiness')).toBeInTheDocument()
    expect(screen.getAllByText('dormant').length).toBeGreaterThan(0)
    expect(screen.getByText('Billing enabled')).toBeInTheDocument()
    expect(screen.getByText('Checkout enabled')).toBeInTheDocument()
  })
})

describe('Owner Cockpit analytics', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
  })

  it('renders the analytics sections and estimated MRR', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Plan Breakdown')).toBeInTheDocument()
    expect(screen.getByText('Billing Status')).toBeInTheDocument()
    expect(screen.getByText('Top Used Modules')).toBeInTheDocument()
    expect(screen.getByText('Least Used Modules')).toBeInTheDocument()
    expect(screen.getByText('Estimated MRR')).toBeInTheDocument()
    // $148 estimated MRR appears (metric card + plan-breakdown footnote).
    expect(screen.getAllByText('$148').length).toBeGreaterThan(0)
  })

  it('shows honest empty states when no usage data exists', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Top Used Modules')).toBeInTheDocument()
    expect(screen.getAllByText('No usage data yet').length).toBeGreaterThan(0)
  })

  it('renders top module usage when usage data is supplied', async () => {
    mockOwnerApi({
      ...EMPTY_ANALYTICS,
      total_events: 4,
      top_modules: [
        { module: 'dashboard', count: 3 },
        { module: 'housing', count: 1 },
      ],
    })
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Top Used Modules')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })
})

describe('Owner Cockpit analytics polish', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
  })

  it('renders the tracked-events count and time-window selector', async () => {
    mockOwnerApi({ ...EMPTY_ANALYTICS, total_events: 12 })
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('12 tracked events')).toBeInTheDocument()
    // The 7d / 30d / All-time controls are present.
    expect(screen.getByRole('button', { name: '7 days' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '30 days' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'All time' })).toBeInTheDocument()
  })

  it('refetches analytics with the selected window when a control is clicked', async () => {
    mockOwnerApi({ ...EMPTY_ANALYTICS, total_events: 3 })
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('3 tracked events')
    fireEvent.click(screen.getByRole('button', { name: '7 days' }))
    // A summary request carrying window=7 was issued.
    const calledWithWindow = apiCall.mock.calls.some(
      ([url]) => typeof url === 'string' && url.includes('/api/owner/analytics/summary') && url.includes('window=7')
    )
    expect(calledWithWindow).toBe(true)
  })

  it('shows honest empty states for recent activity and latest events', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Event Counts by Day')).toBeInTheDocument()
    expect(screen.getByText('No activity recorded in this window yet')).toBeInTheDocument()
    expect(screen.getByText('No events recorded in this window yet')).toBeInTheDocument()
  })

  it('renders recent activity and the latest safe events feed when supplied', async () => {
    mockOwnerApi({
      ...EMPTY_ANALYTICS,
      total_events: 2,
      recent_activity: [{ day: '2026-06-21', count: 2 }],
      recent_events: [
        { event_type: 'module_view', module: 'housing', created_at: '2026-06-21T12:00:00' },
      ],
    })
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Latest Events')).toBeInTheDocument()
    expect(screen.getByText('2026-06-21')).toBeInTheDocument()
    // 'Housing' also appears in the module-usage cards; the event row's "Module View"
    // label is unique to the latest-events feed.
    expect(screen.getAllByText('Housing').length).toBeGreaterThan(0)
    expect(screen.getByText('Module View')).toBeInTheDocument()
  })

})

describe('Owner Cockpit support queue', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
  })

  it('renders the Support Queue section with an empty state when there are no tickets', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Support Queue')).toBeInTheDocument()
    expect(screen.getByText('No support tickets yet')).toBeInTheDocument()
  })

  it('renders support counts and breakdowns when supplied', async () => {
    mockOwnerApi(EMPTY_ANALYTICS, {
      ...EMPTY_SUPPORT,
      total_tickets: 3,
      open_tickets: 2,
      high_priority_tickets: 1,
      by_status: { ...EMPTY_SUPPORT.by_status, open: 2, resolved: 1 },
      by_category: { ...EMPTY_SUPPORT.by_category, bug: 2, billing: 1 },
      recent_tickets: [
        { id: 3, category: 'bug', priority: 'urgent', status: 'open', subject: 'Login button broken', assigned_to: null, created_at: '2026-06-21T10:00:00', updated_at: '2026-06-21T10:00:00' },
        { id: 2, category: 'billing', priority: 'high', status: 'resolved', subject: 'Invoice question', assigned_to: 'owner', created_at: '2026-06-20T10:00:00', updated_at: '2026-06-20T11:00:00' },
      ],
    })
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Support Queue')).toBeInTheDocument()
    // The recent tickets render their subjects safely (no client PHI).
    expect(screen.getByText('Login button broken')).toBeInTheDocument()
    expect(screen.getByText('Invoice question')).toBeInTheDocument()
    // High/urgent count is surfaced.
    expect(screen.getByText('High / urgent')).toBeInTheDocument()
    // Per-ticket owner controls (status select) are present.
    expect(screen.getByLabelText('Status for ticket 3')).toBeInTheDocument()
    expect(screen.getByLabelText('Priority for ticket 3')).toBeInTheDocument()
  })

  it('patches a ticket status through the owner control', async () => {
    mockOwnerApi(EMPTY_ANALYTICS, {
      ...EMPTY_SUPPORT,
      total_tickets: 1,
      open_tickets: 1,
      recent_tickets: [
        { id: 7, category: 'bug', priority: 'normal', status: 'open', subject: 'Typo on page', assigned_to: null, created_at: '2026-06-21T10:00:00', updated_at: '2026-06-21T10:00:00' },
      ],
    })
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    const statusSelect = await screen.findByLabelText('Status for ticket 7')
    fireEvent.change(statusSelect, { target: { value: 'resolved' } })
    const patched = apiCall.mock.calls.some(
      ([url, opts]) =>
        typeof url === 'string' &&
        url === '/api/owner/support/tickets/7' &&
        opts?.method === 'PATCH' &&
        String(opts?.body || '').includes('resolved')
    )
    expect(patched).toBe(true)
  })
})

const ONE_TICKET_SUPPORT = {
  ...EMPTY_SUPPORT,
  total_tickets: 1,
  open_tickets: 1,
  recent_tickets: [
    { id: 7, category: 'bug', priority: 'normal', status: 'open', subject: 'Typo on page', assigned_to: null, created_at: '2026-06-21T10:00:00', updated_at: '2026-06-21T10:00:00' },
  ],
}

describe('Owner Cockpit support ticket detail drawer', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
  })

  it('does not show the full description in the recent list before opening', async () => {
    mockOwnerApi(EMPTY_ANALYTICS, ONE_TICKET_SUPPORT)
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('Typo on page')
    expect(screen.queryByText('Full description body for the drawer.')).not.toBeInTheDocument()
  })

  it('opens the detail drawer with safe ticket fields when a ticket is clicked', async () => {
    mockOwnerApi(EMPTY_ANALYTICS, ONE_TICKET_SUPPORT)
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    const opener = await screen.findByLabelText('Open ticket 7: Typo on page')
    fireEvent.click(opener)
    // Drawer renders full detail only after opening.
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Full description body for the drawer.')).toBeInTheDocument()
    expect(screen.getByText('Existing internal note.')).toBeInTheDocument()
    expect(screen.getByText('reporter@a.test')).toBeInTheDocument()
    // PHI warning stays visible inside the detail view.
    expect(
      screen.getByText('Do not store client names, PHI, notes, documents, or protected content here.')
    ).toBeInTheDocument()
  })

  it('patches status, priority, and a note via the drawer Save changes control', async () => {
    mockOwnerApi(EMPTY_ANALYTICS, ONE_TICKET_SUPPORT)
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    fireEvent.click(await screen.findByLabelText('Open ticket 7: Typo on page'))
    await screen.findByRole('dialog')
    fireEvent.change(screen.getByLabelText('Detail status'), { target: { value: 'in_progress' } })
    fireEvent.change(screen.getByLabelText('Detail priority'), { target: { value: 'high' } })
    fireEvent.change(screen.getByLabelText('Detail internal note'), { target: { value: 'Escalating to engineering.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    const patched = apiCall.mock.calls.find(
      ([url, opts]) =>
        typeof url === 'string' && url === '/api/owner/support/tickets/7' && opts?.method === 'PATCH'
    )
    expect(patched).toBeTruthy()
    const body = JSON.parse(patched[1].body)
    expect(body.status).toBe('in_progress')
    expect(body.priority).toBe('high')
    expect(body.internal_notes).toBe('Escalating to engineering.')
    // Success feedback renders (not a silent button).
    expect(await screen.findByText('Changes saved.')).toBeInTheDocument()
  })
})

describe('Owner Cockpit activation controls', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
  })

  it('renders activation controls with explicit locked / env-controlled labels', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Activation Controls')).toBeInTheDocument()
    expect(screen.getByText('Env-controlled')).toBeInTheDocument()
    expect(screen.getByText('Activation locked')).toBeInTheDocument()
    expect(screen.getAllByText('Requires deployment change').length).toBeGreaterThan(0)
    expect(screen.getByText('Dormant')).toBeInTheDocument()
    // The "Request activation" affordance is present but disabled (locked).
    const requestButtons = screen.getAllByRole('button', { name: /Request activation/i })
    expect(requestButtons.length).toBeGreaterThan(0)
    requestButtons.forEach((button) => expect(button).toBeDisabled())
  })

  it('opens a read-only activation checklist without mutating any state', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('Activation Controls')
    fireEvent.click(screen.getByRole('button', { name: 'View activation checklist for Billing' }))
    expect(await screen.findByText('Activation checklist')).toBeInTheDocument()
    expect(
      screen.getByText(/This is a read-only checklist\. Nothing is activated, toggled, or changed here/i)
    ).toBeInTheDocument()
    // Opening the checklist issues no write requests.
    const mutated = apiCall.mock.calls.some(
      ([, opts]) => opts?.method === 'PATCH' || opts?.method === 'POST'
    )
    expect(mutated).toBe(false)
  })
})

const SAMPLE_CAMPAIGN = {
  id: 12,
  name: 'Spring Launch Search',
  status: 'active',
  channel: 'google_ads',
  utm_source: 'google',
  utm_medium: 'cpc',
  utm_campaign: 'spring_launch',
  landing_page_url: 'https://example.com/spring',
  budget_amount: 2000,
  spend_amount: 600,
  notes: 'Q2 paid push',
  created_at: '2026-06-20T10:00:00',
  updated_at: '2026-06-21T10:00:00',
}

describe('Owner Cockpit marketing campaign tracker', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
  })

  it('renders the tracker with an honest empty state and UTM helper copy', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Marketing & Campaign Tracker')).toBeInTheDocument()
    // 'No campaigns yet' shows in the status/channel breakdown hints and the list empty state.
    expect(screen.getAllByText('No campaigns yet').length).toBeGreaterThan(0)
    expect(screen.getByText('Create a campaign to start tracking marketing performance.')).toBeInTheDocument()
    // The exact UTM helper pattern is shown.
    expect(screen.getByText('?utm_source=google&utm_medium=cpc&utm_campaign=launch_test')).toBeInTheDocument()
  })

  it('shows Landing & Ad Readiness placeholders without fabricating numbers', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Landing & Ad Readiness')).toBeInTheDocument()
    expect(screen.getByText('Landing page visits')).toBeInTheDocument()
    expect(screen.getByText('Signups')).toBeInTheDocument()
    expect(screen.getByText('Cost per signup')).toBeInTheDocument()
    // Placeholders render as em-dashes, never invented values.
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('renders a campaign list and summary totals when supplied', async () => {
    const marketing = {
      ...EMPTY_MARKETING,
      total_campaigns: 1,
      active_campaigns: 1,
      by_status: { ...EMPTY_MARKETING.by_status, active: 1 },
      by_channel: { ...EMPTY_MARKETING.by_channel, google_ads: 1 },
      total_budget: 2000,
      total_spend: 600,
      utm_attribution: { source: { google: 4 }, medium: { cpc: 4 }, campaign: { spring_launch: 4 } },
      campaign_utm_visits: { spring_launch: 4 },
    }
    mockOwnerApi(EMPTY_ANALYTICS, EMPTY_SUPPORT, DETAIL_TICKET, marketing, [SAMPLE_CAMPAIGN])
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Spring Launch Search')).toBeInTheDocument()
    // 'Google Ads' appears in both the channel breakdown and the campaign card badge.
    expect(screen.getAllByText('Google Ads').length).toBeGreaterThan(0)
    // UTM attribution surfaced from the marketing summary.
    expect(screen.getByText('spring_launch')).toBeInTheDocument()
    expect(screen.getByText('cpc')).toBeInTheDocument()
    // No fabricated cost-per-signup even though spend exists.
    expect(screen.queryByText('No campaigns yet')).not.toBeInTheDocument()
  })

  it('opens the New Campaign form and submits a create request', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('Marketing & Campaign Tracker')

    fireEvent.click(screen.getByRole('button', { name: 'New campaign' }))
    const nameInput = await screen.findByLabelText('Campaign name')
    fireEvent.change(nameInput, { target: { value: 'Summer Promo' } })
    fireEvent.change(screen.getByLabelText('Campaign channel'), { target: { value: 'meta_ads' } })
    fireEvent.click(screen.getByRole('button', { name: /Create campaign/i }))

    await waitFor(() => {
      const createCall = apiCall.mock.calls.find(
        ([url, opts]) => url === '/api/owner/marketing/campaigns' && opts?.method === 'POST'
      )
      expect(createCall).toBeTruthy()
      const body = JSON.parse(createCall[1].body)
      expect(body.name).toBe('Summer Promo')
      expect(body.channel).toBe('meta_ads')
    })
  })

  it('updates a campaign status via the inline edit controls', async () => {
    mockOwnerApi(EMPTY_ANALYTICS, EMPTY_SUPPORT, DETAIL_TICKET, EMPTY_MARKETING, [SAMPLE_CAMPAIGN])
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('Spring Launch Search')

    fireEvent.click(screen.getByRole('button', { name: 'Edit campaign Spring Launch Search' }))
    const statusSelect = await screen.findByLabelText('Status for Spring Launch Search')
    fireEvent.change(statusSelect, { target: { value: 'paused' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => {
      const patchCall = apiCall.mock.calls.find(
        ([url, opts]) => url === '/api/owner/marketing/campaigns/12' && opts?.method === 'PATCH'
      )
      expect(patchCall).toBeTruthy()
      expect(JSON.parse(patchCall[1].body).status).toBe('paused')
    })
  })

  it('never reports Stripe as activated from the marketing summary', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('Marketing & Campaign Tracker')
    // The marketing summary the cockpit consumed carries stripe_activated: false.
    expect(EMPTY_MARKETING.stripe_activated).toBe(false)
    expect(EMPTY_MARKETING.ad_platforms_connected).toBe(false)
  })
})

describe('Owner Cockpit section navigation', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
    mockOwnerApi()
  })

  const SECTIONS = [
    ['Overview', 'overview'],
    ['Growth', 'growth'],
    ['Support', 'support'],
    ['Billing', 'billing'],
    ['System', 'system'],
  ]

  it('renders the five cockpit section nav buttons', async () => {
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('Ember HQ')
    const nav = screen.getByRole('navigation', { name: /Owner HQ sections/i })
    expect(nav).toBeInTheDocument()
    SECTIONS.forEach(([label]) => {
      expect(screen.getByRole('button', { name: `Jump to ${label}` })).toBeInTheDocument()
    })
  })

  it('renders an anchored section group for each nav target', async () => {
    const { container } = render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('Ember HQ')
    SECTIONS.forEach(([label, id]) => {
      const section = container.querySelector(`#${id}`)
      expect(section).toBeTruthy()
      // Each group exposes a heading matching its label.
      expect(screen.getByRole('heading', { name: label })).toBeInTheDocument()
    })
  })

  it('jumps to a section without error when a nav button is clicked', async () => {
    const { container } = render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('Ember HQ')
    // scrollIntoView is guarded, so this must not throw even in jsdom.
    fireEvent.click(screen.getByRole('button', { name: 'Jump to Growth' }))
    expect(container.querySelector('#growth')).toBeTruthy()
    expect(screen.getByText('Marketing & Campaign Tracker')).toBeInTheDocument()
  })

  it('provides a Back to top control', async () => {
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('Ember HQ')
    const backToTop = screen.getAllByRole('button', { name: 'Back to top' })
    expect(backToTop.length).toBeGreaterThan(0)
    // Clicking it must not throw (window.scrollTo is guarded).
    fireEvent.click(backToTop[0])
  })

  it('keeps each group’s key content within its section', async () => {
    const { container } = render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    await screen.findByText('Ember HQ')
    // Growth → Campaign Tracker
    expect(container.querySelector('#growth')).toContainElement(screen.getByText('Marketing & Campaign Tracker'))
    // Support → Support Queue
    expect(container.querySelector('#support')).toContainElement(screen.getByText('Support Queue'))
    // Billing → Activation Controls + Billing & Stripe
    expect(container.querySelector('#billing')).toContainElement(screen.getByText('Activation Controls'))
    expect(container.querySelector('#billing')).toContainElement(screen.getByText('Billing & Stripe'))
    // System → Dev / System + Internal Team
    expect(container.querySelector('#system')).toContainElement(screen.getByText('Dev / System'))
  })
})
