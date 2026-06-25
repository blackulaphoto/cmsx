// @vitest-environment jsdom
import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'

vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../api/config', () => ({
  apiFetch: vi.fn(() => Promise.resolve({ ok: false, json: async () => ({}) })),
  messagesAPI: { unreadCount: vi.fn(() => Promise.resolve({ unread_count: 0 })) },
}))

import { useAuth } from '../contexts/AuthContext'
import Layout from './Layout'

const BASE_AUTH = {
  profile: {
    full_name: 'Casey Admin',
    email: 'casey@org.test',
    role: 'case_manager',
    org_role: 'case_manager',
    org_id: 'org_abc123',
    case_manager_id: 'cm_casey',
    is_active: true,
  },
  logout: vi.fn(),
  isSuperAdmin: false,
}

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location-probe">{location.pathname}</div>
}

function renderLayout(auth = BASE_AUTH, route = '/') {
  useAuth.mockReturnValue(auth)
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route
          path="*"
          element={(
            <>
              <LocationProbe />
              <Layout>
                <div>child</div>
              </Layout>
            </>
          )}
        />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('Layout mobile drawer', () => {
  it('shows the mobile menu button while keeping the desktop sidebar mounted', () => {
    renderLayout()
    expect(screen.getByRole('button', { name: /open navigation menu/i })).toBeInTheDocument()
    expect(screen.getByLabelText('Primary')).toBeInTheDocument()
  })

  it('opens the drawer with grouped navigation items', () => {
    renderLayout()
    fireEvent.click(screen.getByRole('button', { name: /open navigation menu/i }))

    const dialog = screen.getByRole('dialog', { name: /navigation menu/i })
    expect(within(dialog).getByText('Home')).toBeInTheDocument()
    expect(within(dialog).getByText('Daily Work')).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /Dashboard/i })).toHaveAttribute('aria-current', 'page')
  })

  it('closes the drawer when the close button is clicked', async () => {
    renderLayout()
    fireEvent.click(screen.getByRole('button', { name: /open navigation menu/i }))
    fireEvent.click(screen.getByRole('button', { name: /close navigation menu/i }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /navigation menu/i })).not.toBeInTheDocument()
    })
  })

  it('closes the drawer after selecting a nav item and follows the route change', async () => {
    renderLayout()
    fireEvent.click(screen.getByRole('button', { name: /open navigation menu/i }))

    const dialog = screen.getByRole('dialog', { name: /navigation menu/i })
    fireEvent.click(within(dialog).getByRole('link', { name: /Case Management/i }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /navigation menu/i })).not.toBeInTheDocument()
    })
    expect(screen.getByTestId('location-probe')).toHaveTextContent('/case-management')
  })

  it('preserves role gating in the mobile drawer', () => {
    renderLayout()
    fireEvent.click(screen.getByRole('button', { name: /open navigation menu/i }))
    const caseManagerDialog = screen.getByRole('dialog', { name: /navigation menu/i })
    expect(within(caseManagerDialog).queryByRole('link', { name: /Supervisor/i })).not.toBeInTheDocument()

    cleanup()
    renderLayout({
      ...BASE_AUTH,
      profile: { ...BASE_AUTH.profile, role: 'admin', org_role: 'org_admin' },
    })
    fireEvent.click(screen.getByRole('button', { name: /open navigation menu/i }))

    const adminDialog = screen.getByRole('dialog', { name: /navigation menu/i })
    expect(within(adminDialog).getByText('Team & Admin')).toBeInTheDocument()
    expect(within(adminDialog).getByRole('link', { name: /Supervisor/i })).toHaveAttribute('href', '/supervisor-dashboard')
  })
})

describe('Layout breadcrumbs', () => {
  it('renders app breadcrumbs in the authenticated shell without breaking the sidebar', () => {
    renderLayout(BASE_AUTH, '/case-management')
    const nav = screen.getByRole('navigation', { name: /breadcrumb/i })
    expect(within(nav).getByText('Case Management')).toBeInTheDocument()
    // Desktop sidebar remains mounted alongside the breadcrumbs.
    expect(screen.getByLabelText('Primary')).toBeInTheDocument()
  })

  it('shows a single Dashboard crumb on the dashboard route (no duplicate)', () => {
    renderLayout(BASE_AUTH, '/')
    const nav = screen.getByRole('navigation', { name: /breadcrumb/i })
    expect(within(nav).getAllByRole('listitem')).toHaveLength(1)
  })
})

describe('Layout header actions', () => {
  it('renders the required header actions, including the notifications/alerts button', () => {
    renderLayout()

    // Hamburger / mobile menu trigger.
    expect(screen.getByRole('button', { name: /open navigation menu/i })).toBeInTheDocument()
    // Notifications / alerts button must be present (restored on mobile).
    expect(screen.getByRole('button', { name: /action alerts/i })).toBeInTheDocument()
    // Existing header actions that should remain visible.
    expect(screen.getByRole('link', { name: /messenger/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /user menu/i })).toBeInTheDocument()
  })

  it('opens the alerts dropdown when the notifications button is clicked', () => {
    renderLayout()
    fireEvent.click(screen.getByRole('button', { name: /action alerts/i }))
    expect(screen.getByText('Action Alerts')).toBeInTheDocument()
  })
})
