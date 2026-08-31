// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../api/config', () => ({ apiFetch: vi.fn() }))

import { apiFetch } from '../api/config'
import RoiConsentTracker from './RoiConsentTracker'

// Regression coverage for the production P1: "Generate Printable ROI Form"
// succeeded (200, real document created), but "View linked document"
// reported "Could not open document. Please try again." even though its own
// GET .../documents/{doc_id}/view also returned 200. Root cause lived in the
// shared clientDocuments.js openClientDocument() helper (fixed there, with
// its own dedicated unit tests) - this test exercises the actual reported
// repro path (this component's "View linked document" button) end to end to
// confirm the fix reaches it.

const ROI_RECORD = {
  roi_id: 'roi-1',
  client_id: 'client-1',
  authorized_party: 'QA Smoke Test Party',
  relationship_type: 'Other',
  purpose: 'Other',
  release_method: 'Verbal',
  effective_date: '2026-08-31',
  revocable: true,
  revoked: false,
  status: 'draft',
  linked_document_id: 'doc-roi-generated-1',
}

const routeFetch = () => (url) => {
  if (url.includes('/roi-records')) {
    return Promise.resolve({ ok: true, json: async () => ({ roi_records: [ROI_RECORD] }) })
  }
  if (url.includes('/admissions/packets/')) {
    return Promise.resolve({ ok: false, status: 404 })
  }
  if (url.endsWith('/documents')) {
    return Promise.resolve({ ok: true, json: async () => ({ success: true, documents: [] }) })
  }
  if (url.includes('/documents/doc-roi-generated-1/view')) {
    return Promise.resolve({
      ok: true,
      status: 200,
      headers: { get: () => null },
      blob: async () => new Blob(['<html>ROI form</html>'], { type: 'text/html' }),
    })
  }
  return Promise.resolve({ ok: true, json: async () => ({}) })
}

beforeEach(() => {
  vi.clearAllMocks()
  global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
  global.URL.revokeObjectURL = vi.fn()
})

describe('RoiConsentTracker - View linked document', () => {
  it('opens a generated ROI document via View linked document instead of showing "Could not open document"', async () => {
    apiFetch.mockImplementation(routeFetch())
    const fakeWindow = { closed: false, location: { href: '' } }
    vi.spyOn(window, 'open').mockReturnValue(fakeWindow)

    render(
      <MemoryRouter>
        <RoiConsentTracker clientId="client-1" />
      </MemoryRouter>,
    )

    const viewButton = await screen.findByRole('button', { name: /view linked document/i })
    fireEvent.click(viewButton)

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith('/api/clients/client-1/documents/doc-roi-generated-1/view'),
    )
    await waitFor(() => expect(fakeWindow.location.href).toBe('blob:mock-url'))

    // The bug's exact symptom - this error text must not appear once the
    // document actually opens.
    expect(screen.queryByText('Could not open document. Please try again.')).not.toBeInTheDocument()
  })

  it('still shows the friendly error text when the browser genuinely blocks the popup', async () => {
    apiFetch.mockImplementation(routeFetch())
    vi.spyOn(window, 'open').mockReturnValue(null)

    render(
      <MemoryRouter>
        <RoiConsentTracker clientId="client-1" />
      </MemoryRouter>,
    )

    const viewButton = await screen.findByRole('button', { name: /view linked document/i })
    fireEvent.click(viewButton)

    expect(await screen.findByText('Could not open document. Please try again.')).toBeInTheDocument()
  })
})
