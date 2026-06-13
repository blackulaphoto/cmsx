import { describe, expect, it } from 'vitest'

import {
  PROFILE_META_KEY,
  applySharedProfile,
  buildSharedProfile,
  buildSharedProfileFromClient,
  getTouchedFields,
  withProfileMeta,
} from '../src/utils/admissionsProfile'

describe('Admissions profile utilities', () => {
  it('builds a normalized shared profile from create-new admissions data', () => {
    const profile = buildSharedProfile({
      first_name: '  Jane ',
      last_name: ' Doe  ',
      date_of_birth: '2000-06-12',
      zip_code: '90012',
      intake_date: '2026-06-01',
      program_type: 'Residential',
      legal_probation_status: 'Active',
    })

    expect(profile.full_name).toBe('Jane Doe')
    expect(profile.zip).toBe('90012')
    expect(profile.admission_date).toBe('2026-06-01')
    expect(profile.program).toBe('Residential')
    expect(profile.legal_probation_status).toBe('Active')
    expect(typeof profile.age).toBe('number')
  })

  it('builds a normalized shared profile from an existing client record', () => {
    const profile = buildSharedProfileFromClient({
      first_name: 'John',
      last_name: 'Smith',
      zip_code: '90021',
      program_type: 'PHP',
      intake_date: '2026-06-10',
    })

    expect(profile.full_name).toBe('John Smith')
    expect(profile.zip).toBe('90021')
    expect(profile.program).toBe('PHP')
    expect(profile.admission_date).toBe('2026-06-10')
  })

  it('fills repeated packet fields from the shared profile without overwriting manual edits', () => {
    const response = withProfileMeta(
      {
        client_name: 'Manual Alias',
        primary_member_id: 'KEEP-ME',
      },
      {
        client_name: true,
        primary_member_id: true,
      }
    )

    const applied = applySharedProfile(response, {
      full_name: 'Alice Walker',
      date_of_birth: '1988-03-01',
      insurance_member_id: 'ABC123',
      emergency_contact_name: 'Maria Walker',
    })

    expect(applied.client_name).toBe('Manual Alias')
    expect(applied.primary_member_id).toBe('KEEP-ME')
    expect(applied.date_of_birth).toBe('1988-03-01')
    expect(applied.emergency_contact_name).toBe('Maria Walker')
  })

  it('supports an explicit overwrite refresh from profile', () => {
    const response = withProfileMeta(
      {
        client_name: 'Manual Alias',
      },
      {
        client_name: true,
      }
    )

    const applied = applySharedProfile(
      response,
      {
        full_name: 'Alice Walker',
        legal_probation_status: 'On probation',
      },
      { overwrite: true }
    )

    expect(applied.client_name).toBe('Alice Walker')
    expect(applied.current_legal_involvement).toBe('On probation')
    expect(getTouchedFields(applied)).toEqual({})
  })

  it('stores and reads touched field metadata', () => {
    const response = withProfileMeta({ client_name: 'Alice Walker' }, { client_name: true })

    expect(response[PROFILE_META_KEY].touched_fields.client_name).toBe(true)
    expect(getTouchedFields(response)).toEqual({ client_name: true })
  })
})
