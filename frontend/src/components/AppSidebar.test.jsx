// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

import AppSidebar from './AppSidebar'
import { getVisibleNavGroups } from '../config/navigation'

function renderSidebar(roleCtx, { route = '/', messagesUnreadCount = 0 } = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AppSidebar roleCtx={roleCtx} messagesUnreadCount={messagesUnreadCount} />
    </MemoryRouter>
  )
}

describe('AppSidebar grouped navigation', () => {
  it('renders the standard groups and primary links for a case manager', () => {
    renderSidebar({ isAdmin: false, isSuperAdmin: false })
    // Group labels.
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Daily Work')).toBeInTheDocument()
    expect(screen.getByText('Clients & Care')).toBeInTheDocument()
    expect(screen.getByText('Clinical & Documentation')).toBeInTheDocument()
    expect(screen.getByText('Housing & Resources')).toBeInTheDocument()
    expect(screen.getByText('Workforce & Reentry')).toBeInTheDocument()
    // Representative links resolve to their existing routes.
    expect(screen.getByRole('link', { name: /Dashboard/i })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: /Case Management/i })).toHaveAttribute('href', '/case-management')
    expect(screen.getByRole('link', { name: /Housing/i })).toHaveAttribute('href', '/housing')
  })

  it('hides the admin group and Supervisor link for non-admins', () => {
    renderSidebar({ isAdmin: false, isSuperAdmin: false })
    expect(screen.queryByText('Team & Admin')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Supervisor/i })).not.toBeInTheDocument()
  })

  it('shows the Team & Admin group with Supervisor for admins', () => {
    renderSidebar({ isAdmin: true, isSuperAdmin: false })
    expect(screen.getByText('Team & Admin')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Supervisor/i })).toHaveAttribute('href', '/supervisor-dashboard')
  })

  it('does not surface Owner Cockpit / Super Admin / account links (they stay in the header dropdown)', () => {
    renderSidebar({ isAdmin: true, isSuperAdmin: true })
    expect(screen.queryByRole('link', { name: /Owner Cockpit/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Super Admin/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /My Profile/i })).not.toBeInTheDocument()
  })

  it('marks the active item, including nested deep routes, via aria-current', () => {
    renderSidebar({ isAdmin: false, isSuperAdmin: false }, { route: '/admissions/abc123/forms/intake' })
    const admissions = screen.getByRole('link', { name: /Admissions/i })
    expect(admissions).toHaveAttribute('aria-current', 'page')
    // Dashboard ('/') must NOT falsely match a deep route.
    expect(screen.getByRole('link', { name: /Dashboard/i })).not.toHaveAttribute('aria-current')
  })

  it('renders the unread message badge when a count is supplied', () => {
    renderSidebar({ isAdmin: false, isSuperAdmin: false }, { messagesUnreadCount: 4 })
    const messages = screen.getByRole('link', { name: /Messages/i })
    expect(within(messages).getByText('4')).toBeInTheDocument()
  })
})

describe('getVisibleNavGroups role filtering', () => {
  it('drops the admin group entirely for a non-admin (no empty group label)', () => {
    const groups = getVisibleNavGroups({ isAdmin: false, isSuperAdmin: false })
    expect(groups.some((g) => g.id === 'admin')).toBe(false)
    // Every returned group has at least one visible item.
    groups.forEach((g) => expect(g.items.length).toBeGreaterThan(0))
  })

  it('includes the admin group for an admin', () => {
    const groups = getVisibleNavGroups({ isAdmin: true, isSuperAdmin: false })
    const admin = groups.find((g) => g.id === 'admin')
    expect(admin).toBeTruthy()
    expect(admin.items.map((i) => i.path)).toContain('/supervisor-dashboard')
  })
})
