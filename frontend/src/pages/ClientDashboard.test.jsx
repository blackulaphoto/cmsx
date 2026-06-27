// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

vi.mock('../api/config', () => ({ apiFetch: vi.fn() }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))
vi.mock('../hooks/useNotes', () => ({
  default: () => ({
    notes: [],
    loading: false,
    syncing: false,
    addNote: vi.fn(),
    updateNote: vi.fn(),
    deleteNote: vi.fn(),
    syncAllNotes: vi.fn(),
    getFilteredNotes: vi.fn(() => []),
    getNotesStats: vi.fn(() => ({})),
  }),
}))
vi.mock('../hooks/useTasks', () => ({
  default: () => ({
    tasks: [],
    loading: false,
    syncing: false,
    addTask: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    completeTask: vi.fn(),
    syncAllTasks: vi.fn(),
    getFilteredTasks: vi.fn(() => []),
    getTasksStats: vi.fn(() => ({})),
    getTaskById: vi.fn(),
  }),
}))
vi.mock('../components/NoteForm', () => ({ default: () => <div>NOTE_FORM</div> }))
vi.mock('../components/NotesList', () => ({ default: () => <div>NOTES_LIST</div> }))
vi.mock('../components/TaskForm', () => ({ default: () => <div>TASK_FORM</div> }))
vi.mock('../components/TasksList', () => ({ default: () => <div>TASKS_LIST</div> }))
vi.mock('../components/TaskViewModal', () => ({ default: () => <div>TASK_VIEW</div> }))

import { apiFetch } from '../api/config'
import ClientDashboard from './ClientDashboard'

const baseClientData = {
  client: {
    client_id: 'client-1',
    first_name: 'Casey',
    last_name: 'Jones',
    risk_level: 'medium',
    case_status: 'active',
    phone: '555-111-2222',
    email: 'casey@example.com',
    intake_date: '2026-06-20',
  },
  housing: { status: 'Stable' },
  employment: { status: 'Seeking work' },
  benefits: { status: 'Pending' },
  legal: { status: 'Open case' },
  goals: [{ description: 'Legacy dashboard goal', goal_type: 'Legacy' }],
  barriers: [{ description: 'Legacy dashboard barrier', barrier_type: 'Legacy', severity: 'medium' }],
  tasks: [],
  recent_activity: [],
  contact_history: [],
  program_milestones: [],
  services: {},
}

const currentPlan = {
  plan_id: 'tp-1',
  status: 'active',
  goals: [{ description: 'Maintain housing stability', status: 'active' }],
  problems: [{ description: 'Transportation barrier', domain: 'transportation', priority: 'high' }],
  objectives: [{ description: 'Attend weekly case management', measure: 'Weekly attendance' }],
  interventions: [{ description: 'Coordinate bus pass referral', assigned_module: 'benefits', frequency: 'Weekly' }],
  operational_needs: [{ need_key: 'transportation_support', priority: 'high', domain: 'transportation', reason: 'Client needs reliable transportation for appointments' }],
  aftercare_plan: { summary: 'Continue outpatient treatment after discharge', sponsor_needed: true },
}

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/clients/client-1']}>
      <Routes>
        <Route path="/clients/:clientId" element={<ClientDashboard />} />
      </Routes>
    </MemoryRouter>,
  )

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ClientDashboard treatment plan snapshot', () => {
  it('renders treatment plan snapshot content from the treatment plan endpoint', async () => {
    apiFetch.mockImplementation((url) => {
      if (url.includes('/unified-view')) {
        return Promise.resolve({ ok: true, json: async () => ({ success: true, client_data: baseClientData }) })
      }
      if (url.includes('/treatment-plan')) {
        return Promise.resolve({ ok: true, json: async () => ({ success: true, current_plan: currentPlan, plans: [currentPlan] }) })
      }
      return Promise.resolve({ ok: true, json: async () => ({ success: true, recommendations: [] }) })
    })

    renderPage()

    expect(await screen.findByText('Treatment Plan Snapshot')).toBeInTheDocument()
    expect(screen.getByText('Maintain housing stability')).toBeInTheDocument()
    expect(screen.getByText('Transportation barrier')).toBeInTheDocument()
    expect(screen.getAllByText('Attend weekly case management').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Coordinate bus pass referral').length).toBeGreaterThan(0)
    expect(screen.getByText('Continue outpatient treatment after discharge')).toBeInTheDocument()
    expect(screen.getAllByText('Sponsor').length).toBeGreaterThan(0)
    expect(screen.getByText('Client needs reliable transportation for appointments')).toBeInTheDocument()

    const treatmentPlanLink = screen.getByRole('link', { name: /open treatment plan/i })
    expect(treatmentPlanLink).toHaveAttribute('href', '/treatment-plan?client=client-1')

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith('/api/clients/client-1/treatment-plan')
    })
  })

  it('shows the empty state when no current treatment plan exists', async () => {
    apiFetch.mockImplementation((url) => {
      if (url.includes('/unified-view')) {
        return Promise.resolve({ ok: true, json: async () => ({ success: true, client_data: baseClientData }) })
      }
      if (url.includes('/treatment-plan')) {
        return Promise.resolve({ ok: true, json: async () => ({ success: true, current_plan: null, plans: [] }) })
      }
      return Promise.resolve({ ok: true, json: async () => ({ success: true, recommendations: [] }) })
    })

    renderPage()

    expect(await screen.findByText('Treatment Plan Snapshot')).toBeInTheDocument()
    expect(screen.getByText('No treatment plan yet. Generate or create one in Treatment Plan.')).toBeInTheDocument()
  })
})

describe('ClientDashboard — ROI / Releases tab & Documents restoration', () => {
  beforeEach(() => {
    apiFetch.mockImplementation((url) => {
      if (url.includes('/unified-view')) {
        return Promise.resolve({ ok: true, json: async () => ({ success: true, client_data: baseClientData }) })
      }
      // Everything else (treatment-plan, documents, roi-records, packet, etc.)
      // resolves to a harmless empty success payload.
      return Promise.resolve({ ok: true, json: async () => ({ success: true }) })
    })
  })

  it('keeps the full ROI manager out of the Documents tab, showing only a compact link', async () => {
    renderPage()
    const docsTab = await screen.findByRole('button', { name: 'Documents' })
    fireEvent.click(docsTab)

    // The general document vault is the primary content of the Documents tab.
    expect(screen.getByText('Client Documents')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Upload Document/i })).toBeInTheDocument()

    // Only a compact ROI summary + link lives here — not the full manager.
    expect(screen.getByRole('button', { name: /Open ROI \/ Releases/i })).toBeInTheDocument()
    expect(screen.queryByText('Client ROI Records')).toBeNull()
    expect(screen.queryByText('Packet consent forms')).toBeNull()
    expect(screen.queryByText('Uploaded Signed ROIs')).toBeNull()
  })

  it('renders the full ROI manager on the dedicated ROI / Releases tab', async () => {
    renderPage()
    const roiTab = await screen.findByRole('button', { name: /ROI \/ Releases/i })
    fireEvent.click(roiTab)

    // The full three-layer manager renders only here.
    expect(await screen.findByText('Client ROI Records')).toBeInTheDocument()
    expect(screen.getByText('Packet consent forms')).toBeInTheDocument()
    expect(screen.getByText('Uploaded Signed ROIs')).toBeInTheDocument()

    // The general document vault is NOT part of the ROI tab.
    expect(screen.queryByText('Client Documents')).toBeNull()
  })

  it('jumps from the Documents compact link to the ROI / Releases tab', async () => {
    renderPage()
    const docsTab = await screen.findByRole('button', { name: 'Documents' })
    fireEvent.click(docsTab)

    fireEvent.click(screen.getByRole('button', { name: /Open ROI \/ Releases/i }))

    // Now on the dedicated ROI tab → full manager visible, vault gone.
    expect(await screen.findByText('Client ROI Records')).toBeInTheDocument()
    expect(screen.queryByText('Client Documents')).toBeNull()
  })
})
