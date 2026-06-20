// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

vi.mock('../api/config', () => ({ apiCall: vi.fn() }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))
vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }))

import { apiCall } from '../api/config'
import { useAuth } from '../contexts/AuthContext'
import TeamManagement from './TeamManagement'
import ProtectedRoute from '../components/ProtectedRoute'

const STAFF = [
  { firebase_uid: 'u1', email: 'admin@a.test', full_name: 'Admin A', role: 'admin', org_role: 'org_admin', is_active: true, status: 'active' },
  { firebase_uid: 'u2', email: 'cm@a.test', full_name: 'Case Mgr', role: 'case_manager', org_role: 'member', is_active: true, status: 'active' },
]
const INVITES = [
  { invite_id: 'inv_1', email: 'pending@a.test', org_role: 'member', status: 'pending', expires_at: '2026-07-01T00:00:00', token: 'TOK123' },
]

function mockApi() {
  apiCall.mockImplementation((url, opts) => {
    const method = opts?.method
    if (url === '/api/team/staff') return Promise.resolve({ staff: STAFF })
    if (url === '/api/team/invites' && method !== 'POST') return Promise.resolve({ invites: INVITES })
    if (url === '/api/team/invites' && method === 'POST') return Promise.resolve({ invite: { invite_id: 'inv_new', email: 'new@a.test', org_role: 'member', status: 'pending', token: 'NEWTOK' } })
    return Promise.resolve({})
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  mockApi()
})

describe('TeamManagement page', () => {
  it('renders staff and pending invites for an admin', async () => {
    render(<MemoryRouter><TeamManagement /></MemoryRouter>)
    expect(await screen.findByText('Team Management')).toBeInTheDocument()
    expect(await screen.findByText('pending@a.test')).toBeInTheDocument()
    expect(await screen.findByText('Case Mgr')).toBeInTheDocument()
  })

  it('create invite submits only email/role/name — no org authority', async () => {
    render(<MemoryRouter><TeamManagement /></MemoryRouter>)
    await screen.findByText('Team Management')
    fireEvent.change(screen.getByPlaceholderText('name@example.com'), { target: { value: 'new@a.test' } })
    fireEvent.click(screen.getByRole('button', { name: /Create invite/i }))

    await waitFor(() => {
      const post = apiCall.mock.calls.find(([u, o]) => u === '/api/team/invites' && o?.method === 'POST')
      expect(post).toBeTruthy()
      const body = JSON.parse(post[1].body)
      expect(Object.keys(body).sort()).toEqual(['email', 'role'])
      expect(body.org_id).toBeUndefined()
      expect(body.org_role).toBeUndefined()
      expect(['org_admin', 'member']).toContain(body.role)
    })
    // The created invite link is surfaced for manual sharing.
    expect(await screen.findByText(/Invite created for new@a.test/i)).toBeInTheDocument()
  })

  it('cancel invite calls the cancel endpoint', async () => {
    render(<MemoryRouter><TeamManagement /></MemoryRouter>)
    await screen.findByText('pending@a.test')
    fireEvent.click(screen.getByRole('button', { name: /^Cancel$/i }))
    await waitFor(() => {
      expect(apiCall.mock.calls.some(([u, o]) => u === '/api/team/invites/inv_1/cancel' && o?.method === 'POST')).toBe(true)
    })
  })

  it('remove staff calls the remove endpoint', async () => {
    render(<MemoryRouter><TeamManagement /></MemoryRouter>)
    await screen.findByText('Case Mgr')
    const removeButtons = screen.getAllByRole('button', { name: /Remove/i })
    fireEvent.click(removeButtons[0])
    await waitFor(() => {
      expect(apiCall.mock.calls.some(([u, o]) => /\/api\/team\/staff\/u\d\/remove$/.test(u) && o?.method === 'POST')).toBe(true)
    })
  })
})

describe('Team route access control', () => {
  it('redirects a non-admin away from the admin-only team route', () => {
    useAuth.mockReturnValue({ profile: { role: 'case_manager' }, loading: false, needsOnboarding: false })
    render(
      <MemoryRouter initialEntries={['/team']}>
        <Routes>
          <Route path="/team" element={<ProtectedRoute roles={['admin']}><div>TEAM_PAGE</div></ProtectedRoute>} />
          <Route path="/" element={<div>HOME</div>} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('HOME')).toBeInTheDocument()
    expect(screen.queryByText('TEAM_PAGE')).not.toBeInTheDocument()
  })

  it('allows an admin into the team route', () => {
    useAuth.mockReturnValue({ profile: { role: 'admin' }, loading: false, needsOnboarding: false })
    render(
      <MemoryRouter initialEntries={['/team']}>
        <Routes>
          <Route path="/team" element={<ProtectedRoute roles={['admin']}><div>TEAM_PAGE</div></ProtectedRoute>} />
          <Route path="/" element={<div>HOME</div>} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('TEAM_PAGE')).toBeInTheDocument()
  })
})
