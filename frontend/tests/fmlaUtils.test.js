import { describe, expect, it } from 'vitest'
import {
  filterFmlaCases,
  getCaseDisplayName,
  getCurrentWorkflowStage,
  getDeadlineState,
  getDeadlineBuckets,
  getMissingChecklist,
  normalizeFmlaStatusValue,
  getWorkflowSnapshot
} from '../src/utils/fmla'

describe('FMLA utilities', () => {
  it('filters cases by status and search', () => {
    const cases = [
      { client_name: 'Taylor Jones', employer_name: 'ACME Logistics', assigned_case_manager: 'cm_001', status: 'approved', paperwork_deadline: '2030-01-10', case_subject_type: 'client' },
      { staff_name: 'Jordan Smith', staff_identifier: 'emp-2', employer_name: 'Northwind Health', assigned_case_manager: 'cm_001', status: 'denied', paperwork_deadline: '2030-01-11', case_subject_type: 'staff' }
    ]
    const result = filterFmlaCases(cases, { search: 'taylor', status: 'approved', employer: '', case_manager: '', deadline: '', case_subject_type: 'client' })
    expect(result).toHaveLength(1)
    expect(result[0].client_name).toBe('Taylor Jones')
  })

  it('flags deadline windows correctly', () => {
    const today = new Date()
    const dueSoon = new Date(today)
    dueSoon.setDate(today.getDate() + 3)
    const overdue = new Date(today)
    overdue.setDate(today.getDate() - 2)

    expect(getDeadlineState(dueSoon.toISOString().slice(0, 10)).tone).toBe('warning')
    expect(getDeadlineState(overdue.toISOString().slice(0, 10)).tone).toBe('danger')
  })

  it('identifies missing paperwork checklist items', () => {
    const checklist = getMissingChecklist(
      {
        case_subject_type: 'client',
        leave_type: 'intermittent',
        paperwork_received_date: '',
        paperwork_completed_date: '',
        paperwork_sent_date: '',
        confirmation_received: false,
        expected_return_date: '',
        certification_expiration_date: ''
      },
      [
        { document_type: 'employer packet', document_status: 'needed' }
      ]
    )
    expect(checklist).toContain('Paperwork not received')
    expect(checklist).toContain('Open document requests')
    expect(checklist).toContain('Expected return date not set')
    expect(checklist).toContain('Certification expiration date not set')
  })

  it('prefers staff identifiers for staff cases', () => {
    expect(getCaseDisplayName({ case_subject_type: 'staff', staff_name: 'Alex Worker' })).toBe('Alex Worker')
  })

  it('maps legacy statuses to the current backend vocabulary', () => {
    expect(normalizeFmlaStatusValue('Confirmation pending')).toBe('submitted')
    expect(normalizeFmlaStatusValue('Waiting on employer')).toBe('pending documents')
  })

  it('combines case and reminder deadlines', () => {
    const buckets = getDeadlineBuckets(
      {
        paperwork_deadline: '2030-01-10',
        employer_response_deadline: '2030-01-11'
      },
      [
        { reminder_id: 'r1', reminder_reason: 'Follow up', due_date: '2030-01-09' }
      ]
    )
    expect(buckets).toHaveLength(3)
  })

  it('derives workflow stage from existing case fields', () => {
    const stage = getCurrentWorkflowStage(
      {
        employer_name: 'ACME Logistics',
        employer_response_deadline: '2030-01-10',
        paperwork_received_date: '2030-01-11',
        paperwork_completed_date: '2030-01-13',
        paperwork_sent_date: ''
      },
      [{ document_type: 'medical certification', document_status: 'completed' }],
      []
    )
    expect(stage).toBe('Provider Completed')
  })

  it('builds a workflow snapshot with action bucket and next action', () => {
    const snapshot = getWorkflowSnapshot(
      {
        employer_name: 'ACME Logistics',
        employer_response_deadline: '2030-01-10',
        paperwork_received_date: '2030-01-11'
      },
      [],
      [],
      [{ reminder_id: 'r1', due_date: '2030-01-09', reminder_reason: 'Provider follow-up' }]
    )
    expect(snapshot.stage).toBe('Packet Received')
    expect(snapshot.nextAction).toContain('send to provider')
    expect(snapshot.actionBucket).toBeTruthy()
  })

  it('does not crash when no next due date exists', () => {
    const snapshot = getWorkflowSnapshot(
      {
        client_name: 'Taylor Jones',
        status: 'draft'
      },
      [],
      [],
      []
    )
    expect(snapshot.nextDue).toBeNull()
    expect(snapshot.nextAction).toBeTruthy()
    expect(snapshot.actionBucket).toBeTruthy()
  })
})
