// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../api/config', () => ({ apiFetch: vi.fn() }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))

const navigateMock = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

import { apiFetch } from '../api/config'
import TreatmentPlanAssistCard from './TreatmentPlanAssistCard'

const suggestionResult = {
  aftercare_plan: 'Step down to sober living and outpatient care.',
  progress_summary: 'Client engaged in discharge planning.',
  problems: [
    {
      number: 1,
      title: 'Discharge Planning',
      goal: 'Client will identify discharge supports.',
      objective: 'Client will review sober living options each week.',
      plan_items: [
        'CM will assist client in identifying sober living options.',
        'CM will coordinate outpatient referrals.',
      ],
      frequency: '1x weekly',
      target_date: '07/30/2026',
      status: 'open',
      outcome: 'in progress',
      comment: 'initial goal developed',
    },
  ],
}

const renderCard = () =>
  render(
    <MemoryRouter>
      <TreatmentPlanAssistCard
        clientId="client-1"
        clientName="QA TestClient-Eval"
        clientGoals="Maintain sobriety and stabilize housing."
        barriers="Housing instability"
        aftercarePlan="Return to sober living."
        needs={['housing', 'employment']}
      />
    </MemoryRouter>,
  )

beforeEach(() => {
  vi.clearAllMocks()
})

describe('TreatmentPlanAssistCard', () => {
  it('creates a canonical treatment plan draft from structured assist output', async () => {
    apiFetch.mockImplementation((url, options) => {
      if (url === '/api/ai-documentation/treatment-plan-suggestions') {
        return Promise.resolve({ ok: true, json: async () => suggestionResult })
      }
      if (url === '/api/clients/client-1/treatment-plan/draft') {
        return Promise.resolve({ ok: true, json: async () => ({ success: true, plan: { plan_id: 'txp_1' } }) })
      }
      return Promise.resolve({ ok: true, json: async () => ({}) })
    })

    renderCard()

    fireEvent.click(screen.getByRole('button', { name: /Generate Treatment Plan/i }))
    expect(await screen.findByText('TREATMENT PLAN REVIEW')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Create Treatment Plan Draft/i }))

    await waitFor(() => {
      const draftCall = apiFetch.mock.calls.find(([url]) => url === '/api/clients/client-1/treatment-plan/draft')
      expect(draftCall).toBeTruthy()
    })

    const [, options] = apiFetch.mock.calls.find(([url]) => url === '/api/clients/client-1/treatment-plan/draft')
    const body = JSON.parse(options.body)

    expect(body.source).toBe('treatment_plan_assist')
    expect(body.problems[0]).toMatchObject({
      domain: 'discharge_planning',
      description: 'Discharge Planning',
      source: 'treatment_plan_assist',
    })
    expect(body.goals[0].description).toBe('Client will identify discharge supports.')
    expect(body.objectives[0]).toMatchObject({
      description: 'Client will review sober living options each week.',
      measure: '1x weekly',
    })
    expect(body.interventions).toHaveLength(2)
    expect(body.aftercare_plan).toMatchObject({
      summary: 'Step down to sober living and outpatient care.',
      notes: 'Client engaged in discharge planning.',
      source: 'treatment_plan_assist',
    })
    expect(body.operational_needs).toHaveLength(2)

    expect(navigateMock).toHaveBeenCalledWith('/treatment-plan?client=client-1')
  })
})
