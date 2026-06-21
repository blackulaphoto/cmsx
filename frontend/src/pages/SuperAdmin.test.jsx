// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))
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
import SuperAdmin from './SuperAdmin'

const BASE = { profile: { full_name: 'Owner', role: 'admin' }, loading: false, needsOnboarding: false, logout: vi.fn() }

function mockSuperApi() {
  apiCall.mockImplementation((url) => {
    if (url === '/api/super-admin/overview') return Promise.resolve({ multi_tenant_enabled: false, total_orgs: 2, total_users: 3, total_clients: 3,
      stripe: { mode: 'dormant', stripe_secret_configured: true, all_required_prices_configured: false, stripe_connected: false,
        billing_enabled: false, checkout_enabled: false, portal_enabled: false, webhooks_enabled: false, webhook_secret_configured: false,
        missing_price_env_vars: ['STRIPE_PRICE_TEAM_BASE_MONTHLY'] } })
    if (url === '/api/super-admin/organizations') return Promise.resolve({ organizations: [
      { org_id: 'org_a', name: 'Org A', org_type: 'sober_living', status: 'active', user_count: 2, client_count: 2, created_at: '2026-06-01T00:00:00',
        plan_code: 'free_trial', billing_status: 'trialing', estimated_monthly_price: 0, limit_status: { over_limit: false } },
    ] })
    if (url === '/api/super-admin/organizations/org_a') return Promise.resolve({
      organization: { org_id: 'org_a', name: 'Org A', status: 'active' },
      staff: [{ firebase_uid: 'u1', full_name: 'Staff One', email: 's1@a.test', org_role: 'member', is_active: true }],
      pending_invites: 1, client_count: 2,
      billing: {
        plan_code: 'free_trial', billing_status: 'trialing', estimated_monthly_price: 0,
        plan: { display_name: 'Free Trial', plan_code: 'free_trial' },
        usage: { active_users: 2, active_clients: 2, ai_usage_placeholder: 0 },
        limit_status: { over_limit: false },
      },
    })
    return Promise.resolve({})
  })
}

beforeEach(() => { vi.clearAllMocks() })

describe('Super Admin link visibility', () => {
  it('hides the Super Admin link for non-super-admins', () => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: false })
    render(<MemoryRouter><Layout><div>c</div></Layout></MemoryRouter>)
    fireEvent.click(screen.getAllByRole('button').find((b) => b.textContent.includes('Owner')))
    expect(screen.queryByRole('link', { name: /Super Admin/i })).not.toBeInTheDocument()
  })

  it('shows the Super Admin link for super-admins', () => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true })
    render(<MemoryRouter><Layout><div>c</div></Layout></MemoryRouter>)
    fireEvent.click(screen.getAllByRole('button').find((b) => b.textContent.includes('Owner')))
    expect(screen.getByRole('link', { name: /Super Admin/i })).toHaveAttribute('href', '/super-admin')
  })
})

describe('Super Admin route gating', () => {
  it('redirects a non-super-admin away from /super-admin', () => {
    useAuth.mockReturnValue({ ...BASE, isSuperAdmin: false })
    render(
      <MemoryRouter initialEntries={['/super-admin']}>
        <Routes>
          <Route path="/super-admin" element={<ProtectedRoute requireSuperAdmin><div>PANEL</div></ProtectedRoute>} />
          <Route path="/" element={<div>HOME</div>} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('HOME')).toBeInTheDocument()
    expect(screen.queryByText('PANEL')).not.toBeInTheDocument()
  })
})

describe('Super Admin panel', () => {
  beforeEach(() => { useAuth.mockReturnValue({ ...BASE, isSuperAdmin: true }); mockSuperApi() })

  it('renders platform status and the organizations table', async () => {
    render(<MemoryRouter><SuperAdmin /></MemoryRouter>)
    expect(await screen.findByText('Super Admin')).toBeInTheDocument()
    expect(await screen.findByText('Org A')).toBeInTheDocument()       // org table row
    expect(screen.getByText('Created')).toBeInTheDocument()            // org table header
    // Platform status card present (unique SaaS-mode label).
    expect(screen.getByText('SaaS mode: OFF')).toBeInTheDocument()
  })

  it('shows the Stripe readiness panel with dormant mode and missing prices', async () => {
    render(<MemoryRouter><SuperAdmin /></MemoryRouter>)
    expect(await screen.findByText('Stripe readiness')).toBeInTheDocument()
    expect(screen.getByText('dormant')).toBeInTheDocument()
    expect(screen.getByText(/Missing price env vars:/i)).toBeInTheDocument()
    expect(screen.getByText(/STRIPE_PRICE_TEAM_BASE_MONTHLY/)).toBeInTheDocument()
  })

  it('opens org detail with counts and staff metadata', async () => {
    render(<MemoryRouter><SuperAdmin /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: /^View$/i }))
    expect(await screen.findByText('Staff One')).toBeInTheDocument()
    expect(screen.getByText('Pending invites')).toBeInTheDocument()
  })

  it('shows plan + billing status in the org table', async () => {
    render(<MemoryRouter><SuperAdmin /></MemoryRouter>)
    await screen.findByText('Org A')
    expect(screen.getByText('Plan')).toBeInTheDocument()             // table header
    expect(screen.getAllByText('Billing').length).toBeGreaterThan(0) // header + panel
    expect(screen.getAllByText('free_trial').length).toBeGreaterThan(0)
    expect(screen.getByText('trialing')).toBeInTheDocument()
  })

  it('org detail drawer shows billing fields and a manual override (no card fields)', async () => {
    render(<MemoryRouter><SuperAdmin /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: /^View$/i }))
    expect(await screen.findByRole('button', { name: /Save billing/i })).toBeInTheDocument()
    expect(screen.getAllByText('Free Trial').length).toBeGreaterThan(0)         // plan display name + option
    expect(screen.getByText('AI usage tracking: Coming later')).toBeInTheDocument()
    // Manual override collects no payment data and triggers no checkout action.
    expect(screen.queryByText(/card number/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/checkout session/i)).not.toBeInTheDocument()
  })
})
