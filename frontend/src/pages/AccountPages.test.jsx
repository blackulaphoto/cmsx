// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../api/config', () => ({
  apiFetch: vi.fn(() => Promise.resolve({ ok: false, json: async () => ({}) })),
  messagesAPI: { unreadCount: vi.fn(() => Promise.resolve({ count: 0 })) },
}))

import { useAuth } from '../contexts/AuthContext'
import Layout from '../components/Layout'
import Profile from './Profile'
import Settings from './Settings'
import Support from './Support'

const ADMIN = {
  profile: {
    full_name: 'Casey Admin', email: 'casey@org.test', role: 'admin', org_role: 'org_admin',
    org_id: 'org_abc123', case_manager_id: 'cm_casey', is_active: true,
  },
  multiTenantEnabled: false,
  logout: vi.fn(),
}

beforeEach(() => { vi.clearAllMocks() })

describe('Account dropdown', () => {
  it('routes My Profile / Settings / Help & Support to real pages with no "Soon" badge', () => {
    useAuth.mockReturnValue(ADMIN)
    render(<MemoryRouter><Layout><div>child</div></Layout></MemoryRouter>)

    // Open the user menu.
    const toggle = screen.getAllByRole('button').find((b) => b.textContent.includes('Casey Admin'))
    fireEvent.click(toggle)

    expect(screen.getByRole('link', { name: /My Profile/i })).toHaveAttribute('href', '/profile')
    expect(screen.getByRole('link', { name: /Settings/i })).toHaveAttribute('href', '/settings')
    expect(screen.getByRole('link', { name: /Help & Support/i })).toHaveAttribute('href', '/support')
    // The three former dead-ends no longer show a "Soon" badge.
    expect(screen.queryByText('Soon')).not.toBeInTheDocument()
  })
})

describe('My Profile page', () => {
  it('renders auth/org info from AuthContext', () => {
    useAuth.mockReturnValue({ ...ADMIN, multiTenantEnabled: true })
    render(<MemoryRouter><Profile /></MemoryRouter>)
    expect(screen.getAllByText('casey@org.test').length).toBeGreaterThan(0)
    expect(screen.getByText('Admin')).toBeInTheDocument()
    expect(screen.getByText('Organization admin')).toBeInTheDocument()
    expect(screen.getByText('org_abc123')).toBeInTheDocument()
    expect(screen.getByText('cm_casey')).toBeInTheDocument()
    expect(screen.getByText('ON')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText(/coming later/i)).toBeInTheDocument()
  })
})

describe('Settings page', () => {
  it('shows Team Management link and Billing placeholder for an admin', () => {
    useAuth.mockReturnValue(ADMIN)
    render(<MemoryRouter><Settings /></MemoryRouter>)
    expect(screen.getByRole('link', { name: /Team Management/i })).toHaveAttribute('href', '/team')
    expect(screen.getByText('Billing')).toBeInTheDocument()
    expect(screen.getAllByText(/Coming later/i).length).toBeGreaterThan(0)
  })

  it('hides Team Management for a non-admin', () => {
    useAuth.mockReturnValue({ profile: { role: 'case_manager', org_id: 'org_x' }, multiTenantEnabled: false })
    render(<MemoryRouter><Settings /></MemoryRouter>)
    expect(screen.queryByRole('link', { name: /Team Management/i })).not.toBeInTheDocument()
  })
})

describe('Help & Support page', () => {
  it('renders support content', () => {
    useAuth.mockReturnValue(ADMIN)
    render(<MemoryRouter><Support /></MemoryRouter>)
    expect(screen.getByText('How to get started')).toBeInTheDocument()
    expect(screen.getByText('AI Assistant tips')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Case Management/i })).toHaveAttribute('href', '/case-management')
    expect(screen.getByText(/Report an issue/i)).toBeInTheDocument()
  })
})
