// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import RoiConsentTracker from '../src/components/RoiConsentTracker'

// Mock the API layer so the component renders against fixed data without
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

// Structured client ROI records (the real ongoing system).
const ROI_RECORDS = [
  {
    roi_id: 'roi-1',
    client_id: 'client-1',
    authorized_party: 'County Probation',
    relationship_type: 'Probation/parole',
    purpose: 'Court/legal',
    info_to_release: ['Attendance', 'Drug test results'],
    release_method: 'Secure email/portal',
    effective_date: '2026-06-01',
    expiration_date: FUTURE.slice(0, 10),
    revocable: true,
    revoked: false,
    status: 'active',
    linked_document_id: 'doc-signed-1',
    source: 'created_in_ember',
  },
  {
    roi_id: 'roi-2',
    client_id: 'client-1',
    authorized_party: 'Mother (Jane Doe)',
    relationship_type: 'Family',
    purpose: 'Family involvement',
    info_to_release: ['Attendance'],
    revocable: true,
    revoked: false,
    status: 'needs_signature',
    linked_document_id: null,
    source: 'created_in_ember',
  },
  {
    roi_id: 'roi-3',
    client_id: 'client-1',
    authorized_party: 'Former Employer',
    relationship_type: 'Employer',
    info_to_release: [],
    revocable: true,
    revoked: true,
    status: 'revoked',
    linked_document_id: null,
    source: 'created_in_ember',
  },
]

function makeResponse(body, { ok = true, status = 200 } = {}) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) })
}

// Route apiFetch by URL: the tracker self-fetches the admissions packet, the
// client-documents list, and the structured roi-records list.
function routedHandler({ packet = PACKET, documents = [], roiRecords = [] } = {}) {
  return (url) => {
    const str = String(url)
    if (/\/api\/clients\/[^/]+\/roi-records$/.test(str)) {
      return makeResponse({ success: true, roi_records: roiRecords })
    }
    if (/\/api\/clients\/[^/]+\/documents$/.test(str)) {
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
  apiFetch.mockImplementation(routedHandler({ packet: PACKET, documents: [], roiRecords: [] }))
})

afterEach(cleanup)

describe('RoiConsentTracker — packet consent forms', () => {
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

  it('keeps Packet consent forms as their own clearly separate section', async () => {
    renderTracker()
    expect(await screen.findByText('Packet consent forms')).toBeTruthy()
    expect(screen.getByText('From the Admissions packet')).toBeTruthy()
  })
})

describe('RoiConsentTracker — compliance', () => {
  it('renders the workflow-review compliance disclaimer', async () => {
    renderTracker()
    await screen.findByText('Client ROI Records')
    expect(
      screen.getByText(
        /This tool supports workflow review only\. It does not guarantee HIPAA or 42 CFR Part 2/i
      )
    ).toBeTruthy()
  })

  it('still renders the disclosure-review helper copy', async () => {
    renderTracker()
    await screen.findByText('Client ROI Records')
    expect(
      screen.getByText(/Review active ROI\/consent status before disclosing client information/i)
    ).toBeTruthy()
    expect(screen.getByText(/not legal advice or a guarantee of HIPAA/i)).toBeTruthy()
  })
})

describe('RoiConsentTracker — structured ROI records', () => {
  it('renders the Create New ROI action', async () => {
    renderTracker()
    await screen.findByText('Client ROI Records')
    expect(screen.getByRole('button', { name: /Create New ROI/i })).toBeTruthy()
  })

  it('renders multiple structured ROI records with authorized party prominent', async () => {
    apiFetch.mockImplementation(routedHandler({ packet: null, roiRecords: ROI_RECORDS }))
    renderTracker()
    expect(await screen.findByText('County Probation')).toBeTruthy()
    expect(screen.getByText('Mother (Jane Doe)')).toBeTruthy()
    expect(screen.getByText('Former Employer')).toBeTruthy()
    // Information scope renders for the records that carry it.
    expect(screen.getByText(/Attendance, Drug test results/)).toBeTruthy()
  })

  it('renders structured status badges (active / needs signature / revoked)', async () => {
    apiFetch.mockImplementation(routedHandler({ packet: null, roiRecords: ROI_RECORDS }))
    renderTracker()
    await screen.findByText('County Probation')
    expect(screen.getByText('Needs signature')).toBeTruthy()
    expect(screen.getAllByText('Active').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Revoked').length).toBeGreaterThanOrEqual(1)
  })

  it('renders Generate Printable ROI Form and Upload Signed Copy actions per record', async () => {
    apiFetch.mockImplementation(routedHandler({ packet: null, roiRecords: ROI_RECORDS }))
    renderTracker()
    await screen.findByText('County Probation')
    expect(screen.getAllByText(/Generate Printable ROI Form/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Upload Signed Copy/i).length).toBeGreaterThanOrEqual(1)
  })

  it('shows a linked-document view link when linked_document_id exists', async () => {
    apiFetch.mockImplementation(routedHandler({ packet: null, roiRecords: ROI_RECORDS }))
    renderTracker()
    await screen.findByText('County Probation')
    const links = screen.getAllByRole('link')
    const hrefs = links.map((a) => a.getAttribute('href') || '')
    expect(hrefs).toContain('/api/clients/client-1/documents/doc-signed-1/view')
  })

  it('shows an empty state when there are no structured ROI records', async () => {
    apiFetch.mockImplementation(routedHandler({ packet: null, roiRecords: [] }))
    renderTracker()
    await screen.findByText('Client ROI Records')
    expect(screen.getByText(/No structured ROI records yet/i)).toBeTruthy()
  })
})

describe('RoiConsentTracker — uploaded signed ROIs (fallback)', () => {
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

  it('keeps uploaded ROIs separate from structured records and packet forms', async () => {
    apiFetch.mockImplementation(
      routedHandler({ documents: ROI_DOCS, roiRecords: ROI_RECORDS })
    )
    renderTracker()
    await screen.findByText('Uploaded Signed ROIs')
    // All three layers render as distinct sections.
    expect(screen.getByText('Client ROI Records')).toBeTruthy()
    expect(screen.getByText('Packet consent forms')).toBeTruthy()
    expect(screen.getByText('ROI — Consent to Release or Obtain Information')).toBeTruthy()
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
    // The uploaded-section disclaimer is its own wording ("This tracker does
    // not guarantee…"), distinct from the top-level compliance notice.
    expect(screen.getByText(/This tracker does not guarantee HIPAA or 42 CFR Part 2 compliance/i)).toBeTruthy()
  })
})
