// @vitest-environment jsdom
import React from 'react'
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

import AppBreadcrumbs from './AppBreadcrumbs'
import { buildBreadcrumbs, isPublicPath } from '../config/breadcrumbs'

afterEach(() => cleanup())

function renderAt(route) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AppBreadcrumbs />
    </MemoryRouter>
  )
}

describe('buildBreadcrumbs', () => {
  it('returns a single, non-clickable Dashboard crumb at the root (no duplicate)', () => {
    const crumbs = buildBreadcrumbs('/')
    expect(crumbs).toEqual([{ label: 'Dashboard', to: null }])
  })

  it('builds a known top-level module crumb under Dashboard', () => {
    expect(buildBreadcrumbs('/case-management')).toEqual([
      { label: 'Dashboard', to: '/' },
      { label: 'Case Management', to: null },
    ])
  })

  it('maps UR to its human-friendly Utilization Review label', () => {
    expect(buildBreadcrumbs('/ur')).toEqual([
      { label: 'Dashboard', to: '/' },
      { label: 'Utilization Review', to: null },
    ])
  })

  it('supports the client profile deep route with a safe parent link', () => {
    expect(buildBreadcrumbs('/client/abc123')).toEqual([
      { label: 'Dashboard', to: '/' },
      { label: 'Case Management', to: '/case-management' },
      { label: 'Client Profile', to: null },
    ])
  })

  it('supports the new admissions intake deep route', () => {
    expect(buildBreadcrumbs('/admissions/new')).toEqual([
      { label: 'Dashboard', to: '/' },
      { label: 'Admissions', to: '/admissions' },
      { label: 'New Intake', to: null },
    ])
  })

  it('supports the admissions form deep route with two safe parents', () => {
    expect(buildBreadcrumbs('/admissions/c-42/forms/intake')).toEqual([
      { label: 'Dashboard', to: '/' },
      { label: 'Admissions', to: '/admissions' },
      { label: 'Client Detail', to: '/admissions/c-42' },
      { label: 'Form', to: null },
    ])
  })

  it('handles the sober living directory under Housing-area routing', () => {
    expect(buildBreadcrumbs('/sober-living-directory')).toEqual([
      { label: 'Dashboard', to: '/' },
      { label: 'Sober Living Directory', to: null },
    ])
  })

  it('ignores query strings and trailing slashes', () => {
    expect(buildBreadcrumbs('/benefits/?tab=overview')).toEqual([
      { label: 'Dashboard', to: '/' },
      { label: 'Benefits', to: null },
    ])
  })

  it('never marks the current (last) crumb clickable', () => {
    const crumbs = buildBreadcrumbs('/groups/sessions/s-9')
    expect(crumbs[crumbs.length - 1].to).toBeNull()
  })
})

describe('isPublicPath', () => {
  it('flags public legal/auth routes', () => {
    for (const p of ['/login', '/privacy', '/terms', '/data-security', '/compliance', '/hipaa-baa', '/onboarding']) {
      expect(isPublicPath(p)).toBe(true)
    }
  })

  it('does not flag authenticated routes', () => {
    expect(isPublicPath('/case-management')).toBe(false)
    expect(isPublicPath('/')).toBe(false)
  })
})

describe('AppBreadcrumbs rendering', () => {
  it('renders a labelled breadcrumb nav in the authenticated shell', () => {
    renderAt('/case-management')
    const nav = screen.getByRole('navigation', { name: /breadcrumb/i })
    expect(nav).toBeInTheDocument()
    expect(within(nav).getByText('Case Management')).toBeInTheDocument()
  })

  it('renders Dashboard as a link and the current page as aria-current', () => {
    renderAt('/admissions/new')
    const nav = screen.getByRole('navigation', { name: /breadcrumb/i })
    expect(within(nav).getByRole('link', { name: /Dashboard/i })).toHaveAttribute('href', '/')
    expect(within(nav).getByRole('link', { name: /Admissions/i })).toHaveAttribute('href', '/admissions')
    expect(within(nav).getByText('New Intake')).toHaveAttribute('aria-current', 'page')
  })

  it('renders only a single Dashboard crumb on the dashboard route', () => {
    renderAt('/')
    const nav = screen.getByRole('navigation', { name: /breadcrumb/i })
    expect(within(nav).getAllByRole('listitem')).toHaveLength(1)
    // Current dashboard crumb is not a link.
    expect(within(nav).queryByRole('link')).not.toBeInTheDocument()
  })

  it('does not render breadcrumbs on public routes', () => {
    renderAt('/privacy')
    expect(screen.queryByRole('navigation', { name: /breadcrumb/i })).not.toBeInTheDocument()
  })
})
