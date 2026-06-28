// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

// Controllable search params — reassigned per describe/test in beforeEach
let currentSearchParams = new URLSearchParams()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useSearchParams: () => [currentSearchParams, vi.fn()],
  }
})

vi.mock('../api/config', () => ({
  apiFetch: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ profile: { case_manager_id: 'cm-test-1', role: 'case_manager' } }),
}))

vi.mock('../components/StatsCard', () => ({ default: () => <div data-testid="stats-card" /> }))
vi.mock('../components/ClientSelector', () => ({
  default: ({ placeholder }) => <div data-testid="client-selector">{placeholder}</div>,
}))

import { apiFetch } from '../api/config'
import SmartDaily from './SmartDaily'

// ── fixtures ─────────────────────────────────────────────────────────────────
// Two clients in the same case manager's workload — mimics the production scenario.
const MIXED_BUCKETS = {
  overdue: [
    {
      task_id: 't-other',
      title: 'Medical filter validation test',
      client_id: 'other-client',
      client_name: 'Other Client',
      status: 'pending',
    },
  ],
  today: [],
  next_3_days: [
    {
      task_id: 't-a',
      title: 'STD exam',
      client_id: 'client-A',
      client_name: 'QA TestClient-Eval',
      status: 'pending',
    },
  ],
  this_week: [],
  treatment_plan: [],
  high_priority_no_date: [],
  later: [],
}
// This is the global ai_summary the backend generates from ALL tasks.
const GLOBAL_SUMMARY = 'You have 1 overdue task — start with "Medical filter validation test".'

function setupMixedApiFetch() {
  apiFetch.mockImplementation(url => {
    if (url.includes('/prioritized/')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          buckets: MIXED_BUCKETS,
          ai_summary: GLOBAL_SUMMARY,
          counts: { overdue: 1, today: 0, next_3_days: 1 },
          total_active: 2,
        }),
      })
    }
    return Promise.resolve({ ok: true, json: async () => ({ dashboard: { today_tasks: [] } }) })
  })
}

function renderPage() {
  return render(
    <MemoryRouter>
      <SmartDaily />
    </MemoryRouter>
  )
}

// ── Tests: copy-cleanup labels ────────────────────────────────────────────────
describe('SmartDaily — copy-cleanup usability labels (PR copy-cleanup-usability-labels-v1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    currentSearchParams = new URLSearchParams()
    apiFetch.mockResolvedValue({ ok: true, json: async () => ({}) })
  })

  it('renders "Today\'s Focus" as the client-binding section heading', () => {
    renderPage()
    expect(screen.getByText("Today's Focus")).toBeInTheDocument()
  })

  it('does NOT render the developer-jargon heading "Universal Smart Daily client binding"', () => {
    renderPage()
    expect(screen.queryByText('Universal Smart Daily client binding')).toBeNull()
  })

  it('renders "Add Task" as the task section heading', () => {
    renderPage()
    expect(screen.getByText('Add Task')).toBeInTheDocument()
  })

  it('does NOT render "Task Intake" as a heading', () => {
    renderPage()
    expect(screen.queryByText('Task Intake')).toBeNull()
  })
})

// ── Tests: client-scoped summary ──────────────────────────────────────────────
describe('SmartDaily — client-scoped Smart Summary (PR smart-daily-client-filter-summary-v1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    currentSearchParams = new URLSearchParams()
    setupMixedApiFetch()
  })

  it('with no client selected, shows the global backend ai_summary (all-client tasks)', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByTestId('ai-suggestion')).toBeInTheDocument())
    expect(screen.getByTestId('ai-suggestion').textContent).toContain('Medical filter validation test')
  })

  it('with client-A selected via URL, Smart Summary reflects only client-A\'s tasks', async () => {
    currentSearchParams = new URLSearchParams('client=client-A')
    renderPage()
    await waitFor(() => expect(screen.getByTestId('ai-suggestion')).toBeInTheDocument())
    // client-A has a next_3_days task — summary should mention it
    expect(screen.getByTestId('ai-suggestion').textContent).toContain('coming up in the next 3 days')
    // task from other-client must NOT appear
    expect(screen.getByTestId('ai-suggestion').textContent).not.toContain('Medical filter validation test')
  })

  it('with client selected, Smart Summary does not bleed in other clients\' task titles', async () => {
    currentSearchParams = new URLSearchParams('client=client-A')
    renderPage()
    await waitFor(() => expect(screen.getByTestId('ai-suggestion')).toBeInTheDocument())
    const text = screen.getByTestId('ai-suggestion').textContent
    expect(text).not.toContain('Medical filter validation test')
    expect(text).not.toContain('Other Client')
  })

  it('with a client selected that has no tasks, Smart Summary banner is hidden', async () => {
    currentSearchParams = new URLSearchParams('client=no-tasks-client')
    renderPage()
    await waitFor(() => expect(screen.queryByTestId('loading-indicator')).toBeNull())
    // Allow async fetchData to complete
    await new Promise(r => setTimeout(r, 50))
    expect(document.querySelector('[data-testid="ai-suggestion"]')).toBeNull()
  })
})
