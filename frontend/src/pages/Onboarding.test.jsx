// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => mockNavigate }
})
vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../api/config', () => ({ apiCall: vi.fn() }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))

import { useAuth } from '../contexts/AuthContext'
import { apiCall } from '../api/config'
import ProtectedRoute from '../components/ProtectedRoute'
import Onboarding from './Onboarding'

beforeEach(() => {
  vi.clearAllMocks()
})

function renderGuarded() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<ProtectedRoute><div>DASHBOARD</div></ProtectedRoute>} />
        <Route path="/onboarding" element={<div>ONBOARDING</div>} />
        <Route path="/login" element={<div>LOGIN</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProtectedRoute onboarding guard', () => {
  it('routes a new user without org setup to onboarding', () => {
    useAuth.mockReturnValue({ profile: { role: 'case_manager' }, loading: false, needsOnboarding: true })
    renderGuarded()
    expect(screen.getByText('ONBOARDING')).toBeInTheDocument()
    expect(screen.queryByText('DASHBOARD')).not.toBeInTheDocument()
  })

  it('lets a configured user through to the dashboard', () => {
    useAuth.mockReturnValue({ profile: { role: 'admin' }, loading: false, needsOnboarding: false })
    renderGuarded()
    expect(screen.getByText('DASHBOARD')).toBeInTheDocument()
    expect(screen.queryByText('ONBOARDING')).not.toBeInTheDocument()
  })
})

describe('Onboarding create organization', () => {
  it('does not send role/org_role authority to the backend', async () => {
    useAuth.mockReturnValue({
      profile: { role: 'case_manager' },
      needsOnboarding: true,
      refreshProfile: vi.fn().mockResolvedValue({}),
    })
    apiCall.mockResolvedValue({ user: {}, needs_onboarding: false })

    render(
      <MemoryRouter>
        <Onboarding />
      </MemoryRouter>
    )

    // Open the create-organization form, fill it, submit.
    fireEvent.click(screen.getByText('Create an organization'))
    fireEvent.change(screen.getByPlaceholderText(/Pacific Recovery/i), { target: { value: 'Acme Recovery' } })
    fireEvent.click(screen.getByRole('button', { name: /^Create organization$/i }))

    await waitFor(() => expect(apiCall).toHaveBeenCalled())
    const [endpoint, opts] = apiCall.mock.calls[0]
    expect(endpoint).toBe('/api/auth/onboarding/organization')
    const body = JSON.parse(opts.body)
    expect(body).toEqual({ name: 'Acme Recovery', org_type: 'treatment_center' })
    expect(body.role).toBeUndefined()
    expect(body.org_role).toBeUndefined()
  })
})
