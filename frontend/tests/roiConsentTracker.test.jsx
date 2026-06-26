// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import RoiConsentTracker from '../src/components/RoiConsentTracker'

// Mock the API layer so the component renders against fixed packet data without
// touching firebase/network.
const apiFetch = vi.hoisted(() => vi.fn())

vi.mock('../src/api/config', () => ({
  apiFetch: (...args) => apiFetch(...args),
}))

// A future + past ISO date so expiration logic is deterministic.
const FUTURE = new Date(Date.now() + 1000 * 60 * 60 * 24 * 30).toISOString()
const PAST = new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString()

const PACKET = {
  id: 'packet-1',
  client_id: 'client-1',
  shared_profile: { roi_contact_name: 'County Probation Dept' },
  forms: [
    {
      form_key: 'roi',
      form_name: 'ROI — Consent to Release or Obtain Information',
      category: 'Legal / Consent',
      status: 'Completed',
      completed_at: '2026-06-02T12:00:00Z',
      expires_at: FUTURE,
      allow_revocation: true,
      attachment_count: 1,
    },
    {
      form_key: 'treatment_consent',
      form_name: 'Consent for Behavioral Health Treatment',
      category: 'Consent',
      status: 'Needs Signature',
      allow_revocation: true,
      attachment_count: 0,
    },
    {
      form_key: 'telehealth_consent',
      form_name: 'Telehealth, Electronic Services & Media Consent',
      category: 'Consent',
      status: 'Revoked',
      expires_at: PAST,
      allow_revocation: true,
      attachment_count: 0,
    },
    {
      form_key: 'hipaa_npp',
      form_name: 'HIPAA / 42 CFR Part 2 Notice of Privacy Practices',
      category: 'Consent',
      status: 'Not Started',
      allow_revocation: false,
      attachment_count: 0,
    },
    {
      // Non-consent form must be excluded from the tracker.
      form_key: 'bps_assessment',
      form_name: 'Biopsychosocial (BPS) Intake Assessment',
      category: 'Clinical',
      status: 'In Progress',
      attachment_count: 0,
    },
  ],
}

// Uploaded signed ROI documents (doc_type === 'roi' client documents), plus a
// non-ROI client document that must be excluded from the uploaded-ROI section.
const ROI_DOCS = [
  {
    doc_id: 'doc-1',
    title: 'ROI — County Probation Dept',
    doc_type: 'roi',
    file_name: 'probation_roi.pdf',
    file_mime: 'application/pdf',
    file_path: 'uploads/clients/client-1/abc_probation_roi.pdf',
    created_at: '2026-06-20T10:00:00Z',
  },
  {
    doc_id: 'doc-2',
    title: 'ROI — Mother (Jane Doe)',
    doc_type: 'roi',
    file_name: 'family_roi.jpg',
    file_mime: 'image/jpeg',
    file_path: 'uploads/clients/client-1/def_family_roi.jpg',
    created_at: '2026-06-21T10:00:00Z',
  },
  {
    doc_id: 'doc-9',
    title: 'Insurance card',
    doc_type: 'insurance',
    file_name: 'card.jpg',
    file_path: 'uploads/clients/client-1/ghi_card.jpg',
    created_at: '2026-06-19T10:00:00Z',
  },
]

function makeResponse(body, { ok = true, status = 200 } = {}) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) })
}

// Route apiFetch by URL: the tracker self-fetches both the admissions packet and
// the client-documents list. Tests can pass their own packet/documents.
function routedHandler({ packet = PACKET, documents = [] } = {}) {
  return (url) => {
    if (/\/api\/clients\/[^/]+\/documents$/.test(String(url))) {
      return makeResponse({ success: true, documents })
    }
    if (packet) return makeResponse({ packet })
    return makeResponse({ detail: 'not found' }, { ok: false, status: 404 })
  }
}

function renderTracker() {
  return render(
    <MemoryRouter>
      <RoiConsentTracker clientId="client-1" />
    </MemoryRouter>
  )
}

beforeEach(() => {
  apiFetch.mockReset()
  apiFetch.mockImplementation(() => makeResponse({ packet: PACKET }))
})

afterEach(cleanup)

describe('RoiConsentTracker', () => {
  it('renders consent/ROI items from existing packet data and excludes non-consent forms', async () => {
    renderTracker()
    expect(await screen.findByText('ROI — Consent to Release or Obtain Information')).toBeTruthy()
    expect(screen.getByText('Consent for Behavioral Health Treatment')).toBeTruthy()
    expect(screen.getByText('HIPAA / 42 CFR Part 2 Notice of Privacy Practices')).toBeTruthy()
    // Clinical form is not a consent doc → excluded.
    expect(screen.queryByText('Biopsychosocial (BPS) Intake Assessment')).toBeNull()
  })

  it('maps stored statuses to active / pending signature / revoked / missing badges', async () => {
    renderTracker()
    await screen.findByText('ROI — Consent to Release or Obtain Information')
    expect(screen.getByText('Active')).toBeTruthy()
    expect(screen.getByText('Pending signature')).toBeTruthy()
    expect(screen.getByText('Revoked')).toBeTruthy()
    expect(screen.getByText('Missing')).toBeTruthy()
  })

  it('shows the structured authorized party only for the ROI record', async () => {
    renderTracker()
    await screen.findByText('ROI — Consent to Release or Obtain Information')
    expect(screen.getByText('County Probation Dept')).toBeTruthy()
  })

  it('wires the Open action to the existing admissions form route', async () => {
    renderTracker()
    await screen.findByText('ROI — Consent to Release or Obtain Information')
    const links = screen.getAllByRole('link')
    const hrefs = links.map((a) => a.getAttribute('href') || '')
    expect(hrefs).toContain('/admissions/client-1/forms/roi')
    expect(hrefs).toContain('/admissions/client-1/forms/treatment_consent')
  })

  it('renders the compliance helper copy', async () => {
    renderTracker()
    await screen.findByText('ROI — Consent to Release or Obtain Information')
    expect(
      screen.getByText(/Review active ROI\/consent status before disclosing client information/i)
    ).toBeTruthy()
    expect(screen.getByText(/not legal advice or a guarantee of HIPAA/i)).toBeTruthy()
  })

  it('renders a clear empty state when the client has no admissions packet', async () => {
    apiFetch.mockImplementation(() => makeResponse({ detail: 'not found' }, { ok: false, status: 404 }))
    renderTracker()
    expect(await screen.findByText('No ROI / consent records yet')).toBeTruthy()
  })

  // ── Uploaded signed ROIs (file-based, doc_type === 'roi') ────────────────────

  it('renders the Upload Signed ROI action', async () => {
    apiFetch.mockImplementation(routedHandler({ documents: [] }))
    renderTracker()
    await screen.findByText('ROI — Consent to Release or Obtain Information')
    expect(screen.getByRole('button', { name: /Upload Signed ROI/i })).toBeTruthy()
  })

  it('renders multiple uploaded ROI documents in a separate section and excludes non-ROI docs', async () => {
    apiFetch.mockImplementation(routedHandler({ documents: ROI_DOCS }))
    renderTracker()
    expect(await screen.findByText('Uploaded Signed ROIs')).toBeTruthy()
    expect(screen.getByText('ROI — County Probation Dept')).toBeTruthy()
    expect(screen.getByText('ROI — Mother (Jane Doe)')).toBeTruthy()
    // Non-ROI client document is excluded from the uploaded-ROI section.
    expect(screen.queryByText('Insurance card')).toBeNull()
    // Uploaded files surface their file name and an upload date.
    expect(screen.getByText('probation_roi.pdf')).toBeTruthy()
    expect(screen.getByText(/Uploaded: Jun 20, 2026/)).toBeTruthy()
  })

  it('wires Download Signed ROI to the existing client-documents view route', async () => {
    apiFetch.mockImplementation(routedHandler({ documents: ROI_DOCS }))
    renderTracker()
    await screen.findByText('Uploaded Signed ROIs')
    const links = screen.getAllByRole('link')
    const hrefs = links.map((a) => a.getAttribute('href') || '')
    expect(hrefs).toContain('/api/clients/client-1/documents/doc-1/view')
    expect(hrefs).toContain('/api/clients/client-1/documents/doc-2/view')
  })

  it('keeps packet-derived consent forms in their own section alongside uploaded ROIs', async () => {
    apiFetch.mockImplementation(routedHandler({ documents: ROI_DOCS }))
    renderTracker()
    await screen.findByText('Uploaded Signed ROIs')
    // Packet section + its forms still render separately.
    expect(screen.getByText('Packet consent forms')).toBeTruthy()
    expect(screen.getByText('ROI — Consent to Release or Obtain Information')).toBeTruthy()
    expect(screen.getByText('Consent for Behavioral Health Treatment')).toBeTruthy()
  })

  it('shows an uploaded-ROI empty state when there are no uploaded ROI files', async () => {
    apiFetch.mockImplementation(routedHandler({ documents: [] }))
    renderTracker()
    await screen.findByText('Uploaded Signed ROIs')
    expect(screen.getByText(/No uploaded signed ROIs yet/i)).toBeTruthy()
  })

  it('renders the uploaded-ROI helper/disclaimer copy', async () => {
    apiFetch.mockImplementation(routedHandler({ documents: ROI_DOCS }))
    renderTracker()
    await screen.findByText('Uploaded Signed ROIs')
    expect(
      screen.getByText(/Uploaded ROI files are stored as client documents/i)
    ).toBeTruthy()
    expect(screen.getByText(/does not guarantee HIPAA or 42 CFR Part 2 compliance/i)).toBeTruthy()
  })
})
