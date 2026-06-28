// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => vi.fn(), useSearchParams: () => [new URLSearchParams(), vi.fn()] }
})

vi.mock('../api/config', () => ({
  apiFetch: vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }),
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

import SmartDaily from './SmartDaily'

function renderPage() {
  return render(
    <MemoryRouter>
      <SmartDaily />
    </MemoryRouter>
  )
}

describe('SmartDaily — copy-cleanup usability labels (PR copy-cleanup-usability-labels-v1)', () => {
  beforeEach(() => vi.clearAllMocks())

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
