import { describe, expect, it } from 'vitest'
import {
  buildStatusBanner,
  deriveCurrentWorkflowStep,
  deriveNextAction,
  formatUrLabel,
  getApprovalRate,
  getDeniedDays,
  getSummaryCards,
  sortEventsNewestFirst
} from '../src/utils/ur'

describe('UR utilities', () => {
  it('calculates approval rate from requested and approved days', () => {
    expect(getApprovalRate({ requested_days: 14, approved_days: 7 })).toBe(0.5)
  })

  it('falls back denied days to requested minus approved', () => {
    expect(getDeniedDays({ requested_days: 14, approved_days: 7, denied_days: '' })).toBe(7)
  })

  it('formats summary cards including revenue at risk', () => {
    const cards = getSummaryCards({
      total_authorized_days: 21,
      total_denied_days: 7,
      average_approval_rate: 0.75,
      revenue_at_risk: 4200
    })
    expect(cards.find((card) => card.key === 'total_authorized_days')?.value).toBe(21)
    expect(cards.find((card) => card.key === 'average_approval_rate')?.value).toBe('75%')
    expect(cards.find((card) => card.key === 'revenue_at_risk')?.value).toContain('$4,200')
  })

  it('builds a status banner with derived next action', () => {
    const banner = buildStatusBanner({
      status: 'approved',
      approved_days: 7,
      approved_end_date: '2030-06-15',
      next_review_date: '2030-06-13',
      reviewer_name: 'Jane Smith',
      reviewer_company: 'Health Net'
    })
    expect(banner.statusLabel).toBe('Approved')
    expect(banner.reviewerCompanyLabel).toBe('Health Net')
    expect(banner.nextAction).toBeTruthy()
  })

  it('maps cases into workflow coach steps', () => {
    expect(deriveCurrentWorkflowStep({ status: 'auth_needed' })).toBe(0)
    expect(deriveCurrentWorkflowStep({ status: 'submitted' })).toBe(1)
    expect(deriveCurrentWorkflowStep({ status: 'approved', next_review_date: '2030-01-02' })).toBe(3)
    expect(deriveCurrentWorkflowStep({ status: 'closed' })).toBe(6)
  })

  it('derives denial next action from active deadlines', () => {
    const action = deriveNextAction({
      status: 'denied',
      peer_review_deadline: new Date().toISOString().slice(0, 10)
    })
    expect(action.toLowerCase()).toContain('peer review')
  })

  it('sorts events newest first', () => {
    const events = sortEventsNewestFirst([
      { event_id: 'a', event_date: '2030-01-01T09:00:00' },
      { event_id: 'b', event_date: '2030-01-03T09:00:00' }
    ])
    expect(events[0].event_id).toBe('b')
  })

  it('formats underscored labels for display', () => {
    expect(formatUrLabel('appeal_pending')).toBe('Appeal Pending')
  })
})
