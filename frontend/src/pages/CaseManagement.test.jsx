// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

// ── mocks ────────────────────────────────────────────────────────────────────
const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../api/config', () => ({
  apiFetch: vi.fn(),
  clientsAPI: { getAll: vi.fn(), create: vi.fn(), update: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ profile: { case_manager_id: 'cm-test-1', role: 'case_manager' } }),
}))

vi.mock('../components/StatsCard', () => ({ default: () => <div data-testid="stats-card" /> }))
vi.mock('../components/DocumentationAssistPanel', () => ({ default: () => <div data-testid="doc-panel" /> }))
vi.mock('../components/TreatmentPlanAssistCard', () => ({ default: () => <div data-testid="treatment-card" /> }))
vi.mock('../components/LocationSelector', () => ({ default: () => <div data-testid="location-selector" /> }))
vi.mock('../utils/locationIntelligence', () => ({
  getStateOptions: vi.fn().mockResolvedValue([{ code: 'CA', name: 'California' }]),
}))

import { apiFetch, clientsAPI } from '../api/config'
import CaseManagement from './CaseManagement'

// ── fixtures ─────────────────────────────────────────────────────────────────
const fakeClients = [
  {
    client_id: 'client-abc',
    first_name: 'Jordan',
    last_name: 'Rivera',
    phone: '555-100-2000',
    email: 'jordan@example.com',
    case_status: 'active',
    risk_level: 'medium',
    progress: 50,
    last_contact: null,
    needs: [],
  },
  {
    client_id: 'client-def',
    first_name: 'Alex',
    last_name: 'Kim',
    phone: '555-200-3000',
    email: 'alex@example.com',
    case_status: 'active',
    risk_level: 'high',
    progress: 20,
    last_contact: null,
    needs: [],
  },
]

function setupMocks(clients = fakeClients) {
  clientsAPI.getAll.mockResolvedValue({ clients, count: clients.length })
  apiFetch.mockResolvedValue({ ok: true, json: async () => ({}) })
}

function renderCaseManagement() {
  return render(
    <MemoryRouter>
      <CaseManagement />
    </MemoryRouter>
  )
}

// ── tests ─────────────────────────────────────────────────────────────────────
describe('CaseManagement — client row actions (PR 2 clarity fix)', () => {

  beforeEach(() => {
    vi.clearAllMocks()
    setupMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(false)
  })

  // 1. Client list renders existing clients
  it('renders existing clients in the list', async () => {
    renderCaseManagement()
    await waitFor(() => {
      expect(screen.getByText('Jordan Rivera')).toBeInTheDocument()
      expect(screen.getByText('Alex Kim')).toBeInTheDocument()
    })
  })

  // 2. "Open Client File" label is present
  it('renders "Open Client File" action buttons', async () => {
    renderCaseManagement()
    await waitFor(() => {
      const btns = screen.getAllByRole('button', { name: /open client file/i })
      expect(btns.length).toBeGreaterThan(0)
    })
  })

  // 3. "View Dashboard" is no longer the user-facing label
  it('does NOT show "View Dashboard" as any button label or title', async () => {
    renderCaseManagement()
    await waitFor(() => screen.getByText('Jordan Rivera'))
    const allBtns = document.querySelectorAll('button')
    const viewDashboardBtns = Array.from(allBtns).filter(
      (b) => b.title === 'View Dashboard' || b.textContent.trim() === 'View Dashboard'
    )
    expect(viewDashboardBtns).toHaveLength(0)
  })

  // 4. "View Profile" redundant action is no longer rendered
  it('does NOT render a "View Profile" button', async () => {
    renderCaseManagement()
    await waitFor(() => screen.getByText('Jordan Rivera'))
    const allBtns = document.querySelectorAll('button')
    const viewProfileBtns = Array.from(allBtns).filter(
      (b) => b.title === 'View Profile' || /view profile/i.test(b.textContent)
    )
    expect(viewProfileBtns).toHaveLength(0)
  })

  // 5. Clicking "Open Client File" navigates to /client/{id}
  it('navigates to /client/{id} when Open Client File is clicked', async () => {
    renderCaseManagement()
    await waitFor(() => screen.getByText('Jordan Rivera'))
    const btns = screen.getAllByRole('button', { name: /open client file/i })
    fireEvent.click(btns[0])
    expect(mockNavigate).toHaveBeenCalledWith('/client/client-abc')
  })

  // 6. Edit Client action still exists
  it('renders Edit action for each client row', async () => {
    renderCaseManagement()
    await waitFor(() => screen.getByText('Jordan Rivera'))
    const editBtns = screen.getAllByRole('button', { name: /edit client/i })
    expect(editBtns.length).toBeGreaterThan(0)
  })

  // 7. Delete Client action still exists
  it('renders Delete action for each client row', async () => {
    renderCaseManagement()
    await waitFor(() => screen.getByText('Jordan Rivera'))
    const deleteBtns = screen.getAllByRole('button', { name: /delete client/i })
    expect(deleteBtns.length).toBeGreaterThan(0)
  })

  // 8. Delete requires confirmation before proceeding
  it('calls confirm() before deleting a client', async () => {
    renderCaseManagement()
    await waitFor(() => screen.getByText('Jordan Rivera'))
    const deleteBtns = screen.getAllByRole('button', { name: /delete client/i })
    fireEvent.click(deleteBtns[0])
    expect(window.confirm).toHaveBeenCalled()
  })

  // 9. Add Client button still renders
  it('renders the Add Client button', async () => {
    renderCaseManagement()
    await waitFor(() => {
      const addBtn = screen.getByRole('button', { name: /add client/i })
      expect(addBtn).toBeInTheDocument()
    })
  })

  // 10. Add Client form uses "Client's own words", not "CT's own words"
  it('Add Client form labels say "Client\'s own words" not "CT\'s own words"', async () => {
    renderCaseManagement()
    await waitFor(() => screen.getByRole('button', { name: /add client/i }))
    fireEvent.click(screen.getByRole('button', { name: /add client/i }))
    await waitFor(() => {
      const allText = document.body.textContent
      expect(allText).toMatch(/Client's own words/)
      expect(allText).not.toMatch(/CT's own words/)
    })
  })

})
