// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../api/config', () => ({ apiFetch: vi.fn() }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ profile: { case_manager_id: 'cm_1' } }) }))
vi.mock('../utils/clientOperationalContext', () => ({
  fetchClientWithOperationalContext: vi.fn(),
  getIntakeContext: () => ({}),
}))
// Stub ClientSelector with a button that selects a client on click.
vi.mock('../components/ClientSelector', () => ({
  default: ({ onClientSelect }) => (
    <button onClick={() => onClientSelect({ client_id: 'client-1', full_name: 'Test Client' })}>
      SELECT_CLIENT
    </button>
  ),
}))

import { apiFetch } from '../api/config'
import TreatmentPlan from './TreatmentPlan'

const draftPlan = {
  plan_id: 'txp_1',
  status: 'draft',
  created_at: '2026-06-24T00:00:00Z',
  problems: [],
  goals: [{ goal_id: 'g1', description: 'Old goal', status: 'draft' }],
  objectives: [],
  interventions: [],
  completion_criteria: [],
  operational_needs: [],
  aftercare_plan: {},
}

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/treatment-plan']}>
      <TreatmentPlan />
    </MemoryRouter>,
  )

beforeEach(() => {
  vi.clearAllMocks()
})

describe('TreatmentPlan draft edit mode', () => {
  it('edits a draft and saves via the PATCH endpoint', async () => {
    apiFetch.mockImplementation((url, opts) => {
      if (opts?.method === 'PATCH') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, plan: { ...draftPlan, goals: [{ goal_id: 'g1', description: 'New goal', status: 'draft' }] } }),
        })
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ success: true, current_plan: draftPlan, plans: [draftPlan], count: 1 }),
      })
    })

    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))

    const editBtn = await screen.findByText('Edit Draft')
    fireEvent.click(editBtn)

    const goalField = await screen.findByDisplayValue('Old goal')
    fireEvent.change(goalField, { target: { value: 'New goal' } })

    fireEvent.click(screen.getByText('Save Changes'))

    await waitFor(() => {
      const patchCall = apiFetch.mock.calls.find(([, opts]) => opts?.method === 'PATCH')
      expect(patchCall).toBeTruthy()
      expect(patchCall[0]).toContain('/api/clients/client-1/treatment-plan/txp_1')
      const body = JSON.parse(patchCall[1].body)
      expect(body.goals[0].description).toBe('New goal')
    })
  })

  it('locks approved plans and shows revision helper text', async () => {
    const activePlan = { ...draftPlan, status: 'active', approved_at: '2026-06-24T00:00:00Z' }
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, current_plan: activePlan, plans: [activePlan], count: 1 }),
    })

    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))

    expect(await screen.findByText('Approved plans require a revision before editing.')).toBeInTheDocument()
    expect(screen.queryByText('Edit Draft')).not.toBeInTheDocument()
  })
})
