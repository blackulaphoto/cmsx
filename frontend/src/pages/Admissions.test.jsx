// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

// Mock the manifest JSON import
vi.mock('../data/admissionsManifest.json', () => ({
  default: {
    version: '1.0',
    forms: [
      {
        form_key: 'consent_to_treat',
        form_name: 'Consent to Treatment',
        category: 'Consent',
        timing_group: 'admission',
        required: true,
        requires_signature: true,
        expires_in_days: null,
        sort_order: 1,
      },
      {
        form_key: 'financial_agreement',
        form_name: 'Financial Agreement',
        category: 'Financial',
        timing_group: '72_hours',
        required: true,
        requires_signature: false,
        expires_in_days: null,
        sort_order: 2,
      },
    ],
  },
}))

import Admissions from './Admissions'

function renderAdmissions() {
  return render(
    <MemoryRouter>
      <Admissions />
    </MemoryRouter>
  )
}

describe('Admissions page — dev-facing copy removed', () => {
  it('does NOT render the Admissions Module Roadmap heading', () => {
    renderAdmissions()
    expect(screen.queryByText(/Admissions Module Roadmap/i)).toBeNull()
  })

  it('does NOT render Phase roadmap cards (Phase 1 – Phase 6)', () => {
    renderAdmissions()
    expect(screen.queryByText(/Phase 1/i)).toBeNull()
    expect(screen.queryByText(/Phase 2/i)).toBeNull()
    expect(screen.queryByText(/Phase 3/i)).toBeNull()
    expect(screen.queryByText(/Phase 4/i)).toBeNull()
    expect(screen.queryByText(/Phase 5/i)).toBeNull()
    expect(screen.queryByText(/Phase 6/i)).toBeNull()
  })

  it('does NOT render the manifest JSON path footer', () => {
    renderAdmissions()
    expect(screen.queryByText(/manifest\.json/i)).toBeNull()
    expect(screen.queryByText(/Phase 2\u20133/i)).toBeNull()
    expect(screen.queryByText(/Forms rendered and persistence added/i)).toBeNull()
  })

  it('DOES render the Quick Intake action', () => {
    renderAdmissions()
    expect(screen.getAllByText(/Quick Intake/i).length).toBeGreaterThan(0)
  })

  it('DOES render the Full Admission Packet action', () => {
    renderAdmissions()
    expect(screen.getAllByText(/Full Admission Packet/i).length).toBeGreaterThan(0)
  })

  it('DOES render the form template list header', () => {
    renderAdmissions()
    expect(screen.getByText(/Admission Packet.*Form Templates/i)).toBeInTheDocument()
  })
})
