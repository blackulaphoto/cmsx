// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../api/config', () => ({ apiFetch: vi.fn() }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))

import { apiFetch } from '../api/config'
import SupervisorDashboard from './SupervisorDashboard'

beforeEach(() => {
  apiFetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      overview: {
        team_summary: {
          case_manager_count: 3,
          total_clients: 42,
          high_risk_clients: 5,
          clients_with_barriers: 8,
          overdue_reminders: 2,
          open_benefits_applications: 7,
          active_legal_cases: 4,
          active_fmla_cases: 1,
        },
        case_managers: [],
        alerts: {
          highest_overdue_workloads: [],
          highest_risk_caseloads: [],
        },
      },
    }),
  })
})

function renderDashboard() {
  return render(
    <MemoryRouter>
      <SupervisorDashboard />
    </MemoryRouter>
  )
}

describe('SupervisorDashboard — dev-facing infra copy removed', () => {
  it('does NOT render the System / SaaS Status heading', async () => {
    renderDashboard()
    expect(screen.queryByText(/System \/ SaaS Status/i)).toBeNull()
  })

  it('does NOT render SaaS mode badge text', async () => {
    renderDashboard()
    expect(screen.queryByText(/SaaS mode/i)).toBeNull()
  })

  it('does NOT render MULTI_TENANT_ENABLED env flag text', async () => {
    renderDashboard()
    expect(screen.queryByText(/MULTI_TENANT_ENABLED/i)).toBeNull()
  })

  it('does NOT render Single-org mode copy', async () => {
    renderDashboard()
    expect(screen.queryByText(/Single-org mode/i)).toBeNull()
  })

  it('DOES render the Supervisor Dashboard heading', () => {
    renderDashboard()
    expect(screen.getByText(/Supervisor Dashboard/i)).toBeInTheDocument()
  })

  it('DOES render the Team Caseload View heading', () => {
    renderDashboard()
    expect(screen.getByText(/Team Caseload View/i)).toBeInTheDocument()
  })

  it('DOES render the Highest Overdue Workloads section', () => {
    renderDashboard()
    expect(screen.getByText(/Highest Overdue Workloads/i)).toBeInTheDocument()
  })

  it('DOES render the Highest Risk Caseloads section', () => {
    renderDashboard()
    expect(screen.getByText(/Highest Risk Caseloads/i)).toBeInTheDocument()
  })

  it('DOES render the Admin Tools section', () => {
    renderDashboard()
    expect(screen.getByText(/Admin Tools/i)).toBeInTheDocument()
  })
})
