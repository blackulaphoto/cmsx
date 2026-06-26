// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AdmissionsPacket from '../src/pages/AdmissionsPacket'

// ── Mocks ─────────────────────────────────────────────────────────────────────
// Mock the API layer so the component renders against fixed packet data without
// touching firebase/network. The Financial Coordination panel makes its own
// fetches and is unrelated to packet/status behavior under test — stub it out.

const apiFetch = vi.hoisted(() => vi.fn())

vi.mock('../src/api/config', () => ({
  apiFetch: (...args) => apiFetch(...args),
}))

vi.mock('../src/components/admissions/FinancialCoordinationPanel', () => ({
  default: () => null,
}))

// ── Fixtures ────────────────────────────────────────────────────────────────

const PACKET = {
  id: 'packet-1',
  client_id: 'client-1',
  client_name: 'Jordan Rivers',
  status: 'In Progress',
  case_manager_id: 'cm-1',
  created_at: '2026-06-01T10:00:00Z',
  forms: [
    {
      form_key: 'consent_treatment',
      form_name: 'Consent to Treatment',
      timing_group: 'admission',
      category: 'Consent & Compliance',
      required: true,
      status: 'Completed',
      completed_at: '2026-06-02T12:00:00Z',
      requires_signature: true,
      signatures_required: ['Client'],
      review_status: 'Not Reviewed',
    },
    {
      form_key: 'roi_form',
      form_name: 'Release of Information',
      timing_group: 'admission',
      category: 'Consent & Compliance',
      required: true,
      status: 'Not Started',
      requires_signature: true,
      signatures_required: ['Client'],
      allow_revocation: true,
      review_status: 'Not Reviewed',
    },
    {
      form_key: 'bio_psych',
      form_name: 'Biopsychosocial Assessment',
      timing_group: '72_hours',
      category: 'Clinical',
      required: false,
      status: 'In Progress',
      review_status: 'Not Reviewed',
    },
  ],
}

function makeResponse(body, { ok = true, status = 200 } = {}) {
  return Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(body),
  })
}

// Route apiFetch calls by URL so the page (and its operational-summary fetch)
// both resolve. Operational summary returns has_packet:false → panel renders null.
function defaultApiHandler(url, opts) {
  if (url.endsWith('/operational-summary')) {
    return makeResponse({ summary: { has_packet: false } })
  }
  if (/\/forms\/.+\/status$/.test(url)) {
    return makeResponse({ ok: true })
  }
  if (/\/api\/admissions\/packets\/[^/]+$/.test(url)) {
    return makeResponse({ packet: PACKET })
  }
  return makeResponse({})
}

function renderPacket() {
  return render(
    <MemoryRouter initialEntries={['/admissions/client-1']}>
      <Routes>
        <Route path="/admissions/:client_id" element={<AdmissionsPacket />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  apiFetch.mockReset()
  apiFetch.mockImplementation((url, opts) => defaultApiHandler(url, opts))
})

afterEach(cleanup)

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AdmissionsPacket professional polish', () => {
  it('renders the client header and all existing forms', async () => {
    renderPacket()
    expect(await screen.findByText('Jordan Rivers')).toBeTruthy()
    expect(screen.getByText('Clinical Assessment Packet')).toBeTruthy()
    expect(screen.getByText('Consent to Treatment')).toBeTruthy()
    expect(screen.getByText('Release of Information')).toBeTruthy()
    expect(screen.getByText('Biopsychosocial Assessment')).toBeTruthy()
  })

  it('renders total / missing-required counters from the existing stats logic', async () => {
    renderPacket()
    await screen.findByText('Jordan Rivers')

    // Total Forms stat card = 3
    const totalCard = screen.getByText('Total Forms').closest('div').parentElement
    expect(within(totalCard).getByText('3')).toBeTruthy()

    // Missing Required stat card label still present
    expect(screen.getByText('Missing Required')).toBeTruthy()
    // Missing-required alert still surfaces (ROI not started)
    expect(screen.getByText(/1 required form not started/i)).toBeTruthy()
    // Section completion summary still rendered
    expect(screen.getByText('1/3 complete')).toBeTruthy()
  })

  it('keeps Open buttons wired to the existing form route', async () => {
    renderPacket()
    await screen.findByText('Jordan Rivers')
    const openLinks = screen.getAllByRole('link', { name: /^Open$/ })
    expect(openLinks.length).toBe(3)
    expect(openLinks.some((a) => a.getAttribute('href') === '/admissions/client-1/forms/roi_form')).toBe(true)
  })

  it('shows a Next Best Action pointing at the next required incomplete form', async () => {
    renderPacket()
    await screen.findByText('Jordan Rivers')
    expect(screen.getByText('Next Best Action')).toBeTruthy()
    expect(screen.getByText(/Continue packet — Release of Information/)).toBeTruthy()
    const cta = screen.getByRole('link', { name: /Open next required form/i })
    expect(cta.getAttribute('href')).toBe('/admissions/client-1/forms/roi_form')
  })

  it('surfaces the completion date on completed forms without changing status', async () => {
    renderPacket()
    await screen.findByText('Jordan Rivers')
    expect(screen.getByText(/Completed Jun 2, 2026/)).toBeTruthy()
  })

  it('preserves the status dropdown open + PATCH behavior', async () => {
    renderPacket()
    await screen.findByText('Jordan Rivers')

    // Open the status dropdown on the ROI (Not Started) row by clicking its badge.
    // Row order is consent (Completed), roi (Not Started), bio (In Progress).
    const statusButtons = screen.getAllByTitle('Change status')
    fireEvent.click(statusButtons[1])

    // Choose "Expired" — a status no form currently has, so the text is unique
    // to the open dropdown menu.
    const option = await screen.findByText('Expired')
    fireEvent.click(option)

    await waitFor(() => {
      const patchCall = apiFetch.mock.calls.find(
        ([url, opts]) => /\/forms\/roi_form\/status$/.test(url) && opts?.method === 'PATCH'
      )
      expect(patchCall).toBeTruthy()
    })
  })
})
