// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

vi.mock('../api/config', () => ({ apiCall: vi.fn() }))
vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }))

import { apiCall } from '../api/config'
import { useAuth } from '../contexts/AuthContext'
import Billing from './Billing'
import Settings from './Settings'

const STATUS = {
  success: true,
  org_id: 'org_a',
  billing_status: 'trialing',
  plan_code: 'team',
  plan: {
    plan_code: 'team', display_name: 'Team', price: 99, price_label: '$99/month',
    included_users: 3, extra_user_price: 29, max_active_clients: 75,
    ai_limit_label: 'standard team usage', intended_for: 'small team',
  },
  trial_ends_at: '2026-07-04T00:00:00',
  stripe_connected: false,
  usage: { active_users: 6, active_clients: 40, ai_usage_placeholder: 0 },
  estimated_monthly_price: 186,
  limit_status: {
    clients: { used: 40, limit: 75, over_limit: false },
    users: { used: 6, included: 3, limit: null, over_limit: false, extra_billable: true },
    over_limit: false,
  },
  recommended_plan: 'organization',
  payments_enabled: false,
  plans: [
    { plan_code: 'team', display_name: 'Team', price_label: '$99/month', included_users: 3, extra_user_price: 29, max_active_clients: 75, ai_limit_label: 'standard team usage' },
    { plan_code: 'organization', display_name: 'Organization', price_label: '$199/month', included_users: 5, extra_user_price: 25, max_active_clients: 250, ai_limit_label: 'expanded org usage' },
  ],
}

beforeEach(() => { vi.clearAllMocks() })

describe('Billing page', () => {
  it('renders plan, status, price estimate and usage', async () => {
    apiCall.mockResolvedValue(STATUS)
    render(<MemoryRouter><Billing /></MemoryRouter>)
    expect(await screen.findByRole('heading', { name: 'Team', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('$186/month')).toBeInTheDocument()      // estimated price
    expect(screen.getByText(/trialing/i)).toBeInTheDocument()
    expect(screen.getByText('Staff users')).toBeInTheDocument()
    expect(screen.getByText('Active clients')).toBeInTheDocument()
    expect(screen.getByText(/Trial ends 2026-07-04/)).toBeInTheDocument()
  })

  it('disables Upgrade / Manage Billing and says Stripe is coming soon', async () => {
    apiCall.mockResolvedValue(STATUS)
    render(<MemoryRouter><Billing /></MemoryRouter>)
    const upgrade = await screen.findByRole('button', { name: /Upgrade plan/i })
    const manage = screen.getByRole('button', { name: /Manage billing/i })
    expect(upgrade).toBeDisabled()
    expect(manage).toBeDisabled()
    expect(screen.getByText(/Stripe billing connection is coming soon/i)).toBeInTheDocument()
  })

  it('makes no Stripe/checkout call — only the billing status read', async () => {
    apiCall.mockResolvedValue(STATUS)
    render(<MemoryRouter><Billing /></MemoryRouter>)
    await screen.findByRole('heading', { name: 'Team', level: 2 })
    const urls = apiCall.mock.calls.map((c) => String(c[0]))
    expect(urls).toContain('/api/billing/status')
    expect(urls.some((u) => /stripe|checkout/i.test(u))).toBe(false)
  })

  it('surfaces an error without crashing', async () => {
    apiCall.mockRejectedValue(new Error('boom'))
    render(<MemoryRouter><Billing /></MemoryRouter>)
    expect(await screen.findByText('boom')).toBeInTheDocument()
  })
})

describe('Settings → Billing link', () => {
  it('routes the Billing card to the billing page', async () => {
    apiCall.mockResolvedValue(STATUS)
    useAuth.mockReturnValue({ profile: { role: 'admin', org_id: 'org_a' }, multiTenantEnabled: false })
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <Routes>
          <Route path="/settings" element={<Settings />} />
          <Route path="/billing" element={<Billing />} />
        </Routes>
      </MemoryRouter>
    )
    const link = screen.getByRole('link', { name: /Billing/i })
    expect(link).toHaveAttribute('href', '/billing')
    fireEvent.click(link)
    expect(await screen.findByRole('heading', { name: 'Team', level: 2 })).toBeInTheDocument()  // billing page rendered
  })
})
