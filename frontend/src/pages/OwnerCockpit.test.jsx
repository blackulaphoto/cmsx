// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
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
  recent_activity: [],
  stripe_activated: false,
}

function mockOwnerApi(analytics = EMPTY_ANALYTICS) {
  apiCall.mockImplementation((url) => {
    if (url === '/api/owner/analytics/summary') {
      return Promise.resolve(analytics)
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
    expect(screen.getByText('Marketing & Ads')).toBeInTheDocument()
    expect(screen.getByText('Support')).toBeInTheDocument()
    expect(screen.getByText('Dev / System')).toBeInTheDocument()
    expect(screen.getByText('Internal Team')).toBeInTheDocument()
    expect(screen.getByText('Coming next: support queue')).toBeInTheDocument()
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

  it('shows honest empty states when no usage or marketing data exists', async () => {
    mockOwnerApi()
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Top Used Modules')).toBeInTheDocument()
    expect(screen.getAllByText('No usage data yet').length).toBeGreaterThan(0)
    expect(
      screen.getByText('Marketing attribution will appear after tracked visits')
    ).toBeInTheDocument()
  })

  it('renders top module usage when usage data is supplied', async () => {
    mockOwnerApi({
      ...EMPTY_ANALYTICS,
      total_events: 4,
      top_modules: [
        { module: 'dashboard', count: 3 },
        { module: 'housing', count: 1 },
      ],
      marketing_source_breakdown: { google: 2 },
    })
    render(<MemoryRouter><OwnerCockpit /></MemoryRouter>)
    expect(await screen.findByText('Top Used Modules')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('google')).toBeInTheDocument()
    expect(screen.queryByText('Marketing attribution will appear after tracked visits')).not.toBeInTheDocument()
  })
})
