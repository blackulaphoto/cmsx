import { describe, expect, it } from 'vitest'
import {
  filterFmlaCases,
  getDeadlineState,
  getMissingChecklist
} from '../src/utils/fmla'

describe('FMLA utilities', () => {
  it('filters cases by status and search', () => {
    const cases = [
      { client_name: 'Taylor Jones', employer_name: 'ACME Logistics', assigned_case_manager: 'cm_001', status: 'Approved', paperwork_deadline: '2030-01-10' },
      { client_name: 'Jordan Smith', employer_name: 'Northwind Health', assigned_case_manager: 'cm_001', status: 'Denied', paperwork_deadline: '2030-01-11' }
    ]
    const result = filterFmlaCases(cases, { search: 'taylor', status: 'Approved', employer: '', case_manager: '', deadline: '' })
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
        paperwork_received_date: '',
        paperwork_completed_date: '',
        paperwork_sent_date: '',
        confirmation_received: false
      },
      [
        { document_type: 'employer packet', document_status: 'needed' }
      ]
    )
    expect(checklist).toContain('Paperwork not received')
    expect(checklist).toContain('Open document requests')
  })
})
