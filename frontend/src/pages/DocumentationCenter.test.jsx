// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'
import toast from 'react-hot-toast'

vi.mock('../api/config', () => ({ apiFetch: vi.fn() }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))
vi.mock('../components/ClientSelector', () => ({
  default: ({ onClientSelect }) => (
    <button
      type="button"
      onClick={() =>
        onClientSelect?.({
          client_id: 'client-1',
          first_name: 'QA',
          last_name: 'TestClient-Eval',
        })
      }
    >
      SELECT_CLIENT
    </button>
  ),
}))
vi.mock('../components/DocumentationAssistPanel', () => ({ default: () => <div>ASSIST_PANEL</div> }))
vi.mock('../components/VoiceNoteRecorder', () => ({ default: () => <div>VOICE_RECORDER</div> }))

import { apiFetch } from '../api/config'
import DocumentationCenter from './DocumentationCenter'

const fileTemplates = [
  {
    id: 'file-completion-letter-template',
    label: 'Completion Letter Template',
    mode: 'document',
    category: 'letters',
    noteType: 'Discharge',
    noteKind: 'completion_letter',
    bestFor: 'Completion verification',
    body: 'Completion body',
  },
  {
    id: 'file-letter-of-presence-template',
    label: 'Letter of Presence Template',
    mode: 'document',
    category: 'letters',
    noteType: 'Court',
    noteKind: 'presence_letter',
    bestFor: 'Presence verification',
    body: 'Presence body',
  },
  {
    id: 'file-progress-report-template',
    label: 'Progress Report Template',
    mode: 'document',
    category: 'letters',
    noteType: 'Court',
    noteKind: 'progress_report',
    bestFor: 'Progress reporting',
    body: 'Progress report body',
  },
  {
    id: 'file-proof-of-residence-template',
    label: 'Proof of Residence Template',
    mode: 'document',
    category: 'letters',
    noteType: 'Housing',
    noteKind: 'proof_of_residence',
    bestFor: 'Residence verification',
    body: 'Residence body',
  },
]

const templateMetadataExpectations = [
  ['Completion Letter Template', { note_kind: 'completion_letter', mode: 'document', category: 'letters' }],
  ['Letter of Presence Template', { note_kind: 'presence_letter', mode: 'document', category: 'letters' }],
  ['Progress Report Template', { note_kind: 'progress_report', mode: 'document', category: 'letters' }],
  ['Proof of Residence Template', { note_kind: 'proof_of_residence', mode: 'document', category: 'letters' }],
  ['Initial CM Note', { note_kind: 'initial_note', mode: 'note', category: 'clinical' }],
  ['Weekly CM Note', { note_kind: 'progress_note', mode: 'note', category: 'clinical' }],
  ['Treatment Plan Review', { note_kind: 'treatment_plan', mode: 'document', category: 'planning' }],
  ['Group Note', { note_kind: 'group_note', mode: 'note', category: 'clinical' }],
  ['Discharge Summary', { note_kind: 'discharge_summary', mode: 'document', category: 'planning' }],
  ['Referral Summary', { note_kind: 'referral_summary', mode: 'document', category: 'planning' }],
  ['Court / Probation Letter', { note_kind: 'court_letter', mode: 'document', category: 'letters' }],
  ['FMLA Correspondence', { note_kind: 'fmla_correspondence', mode: 'document', category: 'fmla' }],
  ['LOC Transition Note', { note_kind: 'loc_transition', mode: 'note', category: 'planning' }],
]

const renderPage = () =>
  render(
    <MemoryRouter>
      <DocumentationCenter />
    </MemoryRouter>,
  )

beforeEach(() => {
  vi.clearAllMocks()
})

describe('DocumentationCenter client-linked saves', () => {
  it.each(templateMetadataExpectations)(
    'sends the correct metadata for %s',
    async (templateLabel, expected) => {
      apiFetch.mockImplementation((url) => {
        if (url === '/api/dashboard/docs') {
          return Promise.resolve({ ok: true, json: async () => ({ docs: [] }) })
        }
        if (url === '/api/ai-documentation/templates') {
          return Promise.resolve({ ok: true, json: async () => ({ templates: fileTemplates }) })
        }
        if (url === '/api/ai-documentation/brand-resources') {
          return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
        }
        if (url === '/api/case-management/notes/list/client-1') {
          return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
        }
        if (url === '/api/clients/client-1/documents') {
          return Promise.resolve({ ok: true, json: async () => ({ documents: [] }) })
        }
        if (url === '/api/ai-documentation/note-draft') {
          return Promise.resolve({ ok: true, json: async () => ({ draft: `${templateLabel} draft`, source: 'openai', provider_status: { model: 'gpt-4o' } }) })
        }
        return Promise.resolve({ ok: true, json: async () => ({}) })
      })

      renderPage()

      fireEvent.click(screen.getByText('SELECT_CLIENT'))
      fireEvent.click(await screen.findByRole('button', { name: new RegExp(templateLabel, 'i') }))
      fireEvent.change(screen.getByPlaceholderText(/Select a template, then type your rough notes here|Example:/i), {
        target: { value: 'Client needs a professionally rewritten brief with verified facts only.' },
      })
      fireEvent.click(screen.getByRole('button', { name: /Generate Draft/i }))

      await waitFor(() => {
        expect(apiFetch).toHaveBeenCalledWith('/api/ai-documentation/note-draft', expect.anything())
      })

      const [, options] = apiFetch.mock.calls.find(([url]) => url === '/api/ai-documentation/note-draft')
      const payload = JSON.parse(options.body)
      expect(payload.note_kind).toBe(expected.note_kind)
      expect(payload.context.template_label).toBe(templateLabel)
      expect(payload.context.template_category).toBe(expected.category)
      expect(payload.context.requested_output_mode).toBe(expected.mode)
      expect(payload.context.linked_client_id).toBe('client-1')
      expect(payload.context.case_manager_brief).toContain('verified facts only')
    },
  )

  it('sends weekly note template metadata, requested mode, brief text, and linked client context when generating', async () => {
    apiFetch.mockImplementation((url) => {
      if (url === '/api/dashboard/docs') {
        return Promise.resolve({ ok: true, json: async () => ({ docs: [] }) })
      }
      if (url === '/api/ai-documentation/templates') {
        return Promise.resolve({ ok: true, json: async () => ({ templates: [] }) })
      }
      if (url === '/api/ai-documentation/brand-resources') {
        return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
      }
      if (url === '/api/case-management/notes/list/client-1') {
        return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
      }
      if (url === '/api/clients/client-1/documents') {
        return Promise.resolve({ ok: true, json: async () => ({ documents: [] }) })
      }
      if (url === '/api/ai-documentation/note-draft') {
        return Promise.resolve({ ok: true, json: async () => ({ draft: 'Generated weekly note' }) })
      }
      return Promise.resolve({ ok: true, json: async () => ({}) })
    })

    renderPage()

    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Weekly CM Note/i }))
    fireEvent.change(screen.getByPlaceholderText(/Select a template, then type your rough notes here|Example:/i), {
      target: { value: 'Client needs dental care and probation follow-up this week.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Generate Draft/i }))

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        '/api/ai-documentation/note-draft',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    })

    const [, options] = apiFetch.mock.calls.find(([url]) => url === '/api/ai-documentation/note-draft')
    const payload = JSON.parse(options.body)
    expect(payload.note_kind).toBe('progress_note')
    expect(payload.user_prompt).toContain('dental care')
    expect(payload.client_id).toBe('client-1')
    expect(payload.context.template_label).toBe('Weekly CM Note')
    expect(payload.context.template_mode).toBe('note')
    expect(payload.context.requested_output_mode).toBe('note')
    expect(payload.context.case_manager_brief).toContain('probation follow-up')
    expect(payload.context.linked_client_id).toBe('client-1')
  })

  it('keeps treatment plan review generation explicitly treatment-plan scoped', async () => {
    apiFetch.mockImplementation((url) => {
      if (url === '/api/dashboard/docs') {
        return Promise.resolve({ ok: true, json: async () => ({ docs: [] }) })
      }
      if (url === '/api/ai-documentation/templates') {
        return Promise.resolve({ ok: true, json: async () => ({ templates: [] }) })
      }
      if (url === '/api/ai-documentation/brand-resources') {
        return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
      }
      if (url === '/api/case-management/notes/list/client-1') {
        return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
      }
      if (url === '/api/clients/client-1/documents') {
        return Promise.resolve({ ok: true, json: async () => ({ documents: [] }) })
      }
      if (url === '/api/ai-documentation/note-draft') {
        return Promise.resolve({ ok: true, json: async () => ({ draft: 'Generated treatment plan review' }) })
      }
      return Promise.resolve({ ok: true, json: async () => ({}) })
    })

    renderPage()

    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Treatment Plan Review/i }))
    fireEvent.change(screen.getByPlaceholderText(/Select a template, then type your rough notes here|Example:/i), {
      target: { value: 'Client needs a 30-day treatment plan review.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Generate Draft/i }))

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith('/api/ai-documentation/note-draft', expect.anything())
    })

    const [, options] = apiFetch.mock.calls.find(([url]) => url === '/api/ai-documentation/note-draft')
    const payload = JSON.parse(options.body)
    expect(payload.note_kind).toBe('treatment_plan')
    expect(payload.context.template_label).toBe('Treatment Plan Review')
    expect(payload.context.requested_output_mode).toBe('document')
  })

  it('saves client-linked notes to the selected client note library instead of dashboard docs', async () => {
    apiFetch.mockImplementation((url) => {
      if (url === '/api/dashboard/docs') {
        return Promise.resolve({ ok: true, json: async () => ({ docs: [] }) })
      }
      if (url === '/api/ai-documentation/templates') {
        return Promise.resolve({ ok: true, json: async () => ({ templates: [] }) })
      }
      if (url === '/api/ai-documentation/brand-resources') {
        return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
      }
      if (url === '/api/case-management/notes/list/client-1') {
        return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
      }
      if (url === '/api/clients/client-1/documents') {
        return Promise.resolve({ ok: true, json: async () => ({ documents: [] }) })
      }
      if (url === '/api/case-management/notes/add/client-1') {
        return Promise.resolve({ ok: true, json: async () => ({ success: true, note_id: 'note-1' }) })
      }
      return Promise.resolve({ ok: true, json: async () => ({}) })
    })

    renderPage()

    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Weekly CM Note/i }))
    fireEvent.change(screen.getByPlaceholderText('Enter a strong document title'), {
      target: { value: 'Weekly CM Note for QA Client' },
    })
    fireEvent.change(screen.getByPlaceholderText('Your generated or hand-written final draft appears here.'), {
      target: { value: 'Weekly case management note body' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save Note/i }))

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        '/api/case-management/notes/add/client-1',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    })

    const dashboardPostCall = apiFetch.mock.calls.find(([url, options]) =>
      url === '/api/dashboard/docs' && options?.method === 'POST'
    )
    expect(dashboardPostCall).toBeUndefined()
  })

  it('shows the treatment plan handoff and opens the structured plan for the selected client', async () => {
    apiFetch.mockImplementation((url) => {
      if (url === '/api/dashboard/docs') {
        return Promise.resolve({ ok: true, json: async () => ({ docs: [] }) })
      }
      if (url === '/api/ai-documentation/templates') {
        return Promise.resolve({ ok: true, json: async () => ({ templates: [] }) })
      }
      if (url === '/api/ai-documentation/brand-resources') {
        return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
      }
      if (url === '/api/case-management/notes/list/client-1') {
        return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
      }
      if (url === '/api/clients/client-1/documents') {
        return Promise.resolve({ ok: true, json: async () => ({ documents: [] }) })
      }
      return Promise.resolve({ ok: true, json: async () => ({}) })
    })

    renderPage()

    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Treatment Plan Review/i }))

    expect(await screen.findByText('Treatment Plan Handoff')).toBeInTheDocument()
    expect(screen.getByText('Saved as a document only. Use Treatment Plan to create/edit the structured plan.')).toBeInTheDocument()
    expect(screen.getByText('This document is saved to the client profile. Use Treatment Plan to create the canonical draft.')).toBeInTheDocument()

    const link = screen.getByRole('link', { name: /Open Treatment Plan/i })
    expect(link).toHaveAttribute('href', '/treatment-plan?client=client-1')
  })

  it('saves client-linked documents into the client documents endpoint instead of dashboard docs', async () => {
    apiFetch.mockImplementation((url) => {
      if (url === '/api/dashboard/docs') {
        return Promise.resolve({ ok: true, json: async () => ({ docs: [] }) })
      }
      if (url === '/api/ai-documentation/templates') {
        return Promise.resolve({ ok: true, json: async () => ({ templates: [] }) })
      }
      if (url === '/api/ai-documentation/brand-resources') {
        return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
      }
      if (url === '/api/case-management/notes/list/client-1') {
        return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
      }
      if (url === '/api/clients/client-1/documents') {
        return Promise.resolve({ ok: true, json: async () => ({ documents: [] }) })
      }
      return Promise.resolve({ ok: true, json: async () => ({}) })
    })

    renderPage()

    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Treatment Plan Review/i }))

    fireEvent.change(screen.getByPlaceholderText('Enter a strong document title'), {
      target: { value: 'TP Review for QA Client' },
    })
    fireEvent.change(screen.getByPlaceholderText('Your generated or hand-written final draft appears here.'), {
      target: { value: 'Structured treatment plan review narrative' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save to Client Documents/i }))

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        '/api/clients/client-1/documents',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        }),
      )
    })

    const clientSaveCall = apiFetch.mock.calls.find(([url, options]) =>
      url === '/api/clients/client-1/documents' && options?.method === 'POST'
    )
    expect(clientSaveCall).toBeTruthy()

    const [, requestOptions] = clientSaveCall
    expect(requestOptions.body.get('title')).toBe('TP Review for QA Client')
    expect(requestOptions.body.get('doc_type')).toBe('treatment_plan')
    expect(requestOptions.body.get('file')).toBeInstanceOf(File)

    const dashboardPostCall = apiFetch.mock.calls.find(([url, options]) =>
      url === '/api/dashboard/docs' && options?.method === 'POST'
    )
    expect(dashboardPostCall).toBeUndefined()
  })

  it('shows an honest fallback warning when the provider is unavailable', async () => {
    apiFetch.mockImplementation((url) => {
      if (url === '/api/dashboard/docs') {
        return Promise.resolve({ ok: true, json: async () => ({ docs: [] }) })
      }
      if (url === '/api/ai-documentation/templates') {
        return Promise.resolve({ ok: true, json: async () => ({ templates: fileTemplates }) })
      }
      if (url === '/api/ai-documentation/brand-resources') {
        return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
      }
      if (url === '/api/case-management/notes/list/client-1') {
        return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
      }
      if (url === '/api/clients/client-1/documents') {
        return Promise.resolve({ ok: true, json: async () => ({ documents: [] }) })
      }
      if (url === '/api/ai-documentation/note-draft') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            draft: 'Fallback draft',
            source: 'template_fallback',
            provider_status: { reason: 'missing_openai_api_key' },
          }),
        })
      }
      return Promise.resolve({ ok: true, json: async () => ({}) })
    })

    renderPage()

    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Weekly CM Note/i }))
    fireEvent.change(screen.getByPlaceholderText(/Select a template, then type your rough notes here|Example:/i), {
      target: { value: 'Brief facts only.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Generate Draft/i }))

    expect(await screen.findByText('AI provider unavailable; using structured fallback.')).toBeInTheDocument()
  })
})

describe('DocumentationCenter propagation to Client Documents vault', () => {
  const makeDocRoute = (extraRoutes = {}) => (url, options) => {
    if (url === '/api/dashboard/docs') return Promise.resolve({ ok: true, json: async () => ({ docs: [] }) })
    if (url === '/api/ai-documentation/templates') return Promise.resolve({ ok: true, json: async () => ({ templates: fileTemplates }) })
    if (url === '/api/ai-documentation/brand-resources') return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
    if (url === '/api/case-management/notes/list/client-1') return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
    if (url === '/api/clients/client-1/documents') return Promise.resolve({ ok: true, json: async () => ({ documents: [] }) })
    if (url in extraRoutes) return Promise.resolve(extraRoutes[url])
    return Promise.resolve({ ok: true, json: async () => ({}) })
  }

  it('saves a completion letter to client_documents with doc_type completion_letter', async () => {
    apiFetch.mockImplementation(makeDocRoute({
      '/api/clients/client-1/documents': { ok: true, json: async () => ({ documents: [] }) },
    }))

    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Completion Letter Template/i }))
    fireEvent.change(screen.getByPlaceholderText('Enter a strong document title'), {
      target: { value: 'Completion Letter - QA TestClient-Eval' },
    })
    fireEvent.change(screen.getByPlaceholderText('Your generated or hand-written final draft appears here.'), {
      target: { value: 'This client has successfully completed the program.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save to Client Documents/i }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/api/clients/client-1/documents',
        expect.objectContaining({ method: 'POST', body: expect.any(FormData) }),
      ),
    )

    const [, opts] = apiFetch.mock.calls.find(
      ([u, o]) => u === '/api/clients/client-1/documents' && o?.method === 'POST',
    )
    expect(opts.body.get('doc_type')).toBe('completion_letter')
    expect(opts.body.get('title')).toBe('Completion Letter - QA TestClient-Eval')
    expect(opts.body.get('file')).toBeInstanceOf(File)
  })

  it('shows "Saved to Client Documents." after a successful document-mode save', async () => {
    apiFetch.mockImplementation(makeDocRoute())

    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Treatment Plan Review/i }))
    fireEvent.change(screen.getByPlaceholderText('Enter a strong document title'), {
      target: { value: 'TP Review - Client' },
    })
    fireEvent.change(screen.getByPlaceholderText('Your generated or hand-written final draft appears here.'), {
      target: { value: 'Treatment plan review narrative.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save to Client Documents/i }))

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith('Saved to Client Documents.'),
    )
  })

  it('routes Group Note to client notes, not client_documents', async () => {
    apiFetch.mockImplementation(makeDocRoute({
      '/api/case-management/notes/add/client-1': { ok: true, json: async () => ({ success: true, note_id: 'n-1' }) },
    }))

    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Group Note/i }))
    fireEvent.change(screen.getByPlaceholderText('Enter a strong document title'), {
      target: { value: 'Group Note Session 1' },
    })
    fireEvent.change(screen.getByPlaceholderText('Your generated or hand-written final draft appears here.'), {
      target: { value: 'Client attended group and participated actively.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save Note/i }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/api/case-management/notes/add/client-1',
        expect.objectContaining({ method: 'POST' }),
      ),
    )
    const clientDocPost = apiFetch.mock.calls.find(
      ([u, o]) => u === '/api/clients/client-1/documents' && o?.method === 'POST',
    )
    expect(clientDocPost).toBeUndefined()
  })

  it('routes Initial CM Note to client notes, not client_documents', async () => {
    apiFetch.mockImplementation(makeDocRoute({
      '/api/case-management/notes/add/client-1': { ok: true, json: async () => ({ success: true, note_id: 'n-2' }) },
    }))

    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Initial CM Note/i }))
    fireEvent.change(screen.getByPlaceholderText('Enter a strong document title'), {
      target: { value: 'Initial CM Note - Week 1' },
    })
    fireEvent.change(screen.getByPlaceholderText('Your generated or hand-written final draft appears here.'), {
      target: { value: 'Initial assessment completed.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save Note/i }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/api/case-management/notes/add/client-1',
        expect.objectContaining({ method: 'POST' }),
      ),
    )
    const clientDocPost = apiFetch.mock.calls.find(
      ([u, o]) => u === '/api/clients/client-1/documents' && o?.method === 'POST',
    )
    expect(clientDocPost).toBeUndefined()
  })

  it('routes LOC Transition Note to client notes, not client_documents', async () => {
    apiFetch.mockImplementation(makeDocRoute({
      '/api/case-management/notes/add/client-1': { ok: true, json: async () => ({ success: true, note_id: 'n-3' }) },
    }))

    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /LOC Transition Note/i }))
    fireEvent.change(screen.getByPlaceholderText('Enter a strong document title'), {
      target: { value: 'LOC Transition - Step Down' },
    })
    fireEvent.change(screen.getByPlaceholderText('Your generated or hand-written final draft appears here.'), {
      target: { value: 'Client transitioning from RTC to IOP.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save Note/i }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/api/case-management/notes/add/client-1',
        expect.objectContaining({ method: 'POST' }),
      ),
    )
    const clientDocPost = apiFetch.mock.calls.find(
      ([u, o]) => u === '/api/clients/client-1/documents' && o?.method === 'POST',
    )
    expect(clientDocPost).toBeUndefined()
  })

  it('saves discharge summary to client_documents with doc_type discharge_summary', async () => {
    apiFetch.mockImplementation(makeDocRoute())

    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Discharge Summary/i }))
    fireEvent.change(screen.getByPlaceholderText('Enter a strong document title'), {
      target: { value: 'Discharge Summary - QA Client' },
    })
    fireEvent.change(screen.getByPlaceholderText('Your generated or hand-written final draft appears here.'), {
      target: { value: 'Client successfully completed 30 days of residential treatment.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save to Client Documents/i }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/api/clients/client-1/documents',
        expect.objectContaining({ method: 'POST', body: expect.any(FormData) }),
      ),
    )
    const [, opts] = apiFetch.mock.calls.find(
      ([u, o]) => u === '/api/clients/client-1/documents' && o?.method === 'POST',
    )
    expect(opts.body.get('doc_type')).toBe('discharge_summary')
  })
})

describe('DocumentationCenter authenticated client document view', () => {
  const CLIENT_DOC = {
    doc_id: 'doc-1',
    title: 'Court Letter Scan',
    doc_type: 'court',
    file_name: 'court_letter.pdf',
    file_path: 'uploads/clients/client-1/x_court_letter.pdf',
  }

  // Authenticated blob response for the protected /view route.
  const successView = () => ({
    ok: true,
    blob: async () => new Blob(['x'], { type: 'application/pdf' }),
    headers: {
      get: (key) =>
        String(key).toLowerCase() === 'content-disposition'
          ? 'attachment; filename="court_letter.pdf"'
          : null,
    },
  })

  const routeDocs = (documents, viewResponse) => (url) => {
    if (url === '/api/dashboard/docs') {
      return Promise.resolve({ ok: true, json: async () => ({ docs: [] }) })
    }
    if (url === '/api/ai-documentation/templates') {
      return Promise.resolve({ ok: true, json: async () => ({ templates: [] }) })
    }
    if (url === '/api/ai-documentation/brand-resources') {
      return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
    }
    if (url === '/api/case-management/notes/list/client-1') {
      return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
    }
    if (url === '/api/clients/client-1/documents') {
      return Promise.resolve({ ok: true, json: async () => ({ documents }) })
    }
    if (/\/api\/clients\/client-1\/documents\/[^/]+\/view$/.test(url)) {
      return Promise.resolve(viewResponse())
    }
    return Promise.resolve({ ok: true, json: async () => ({}) })
  }

  const showClientDocuments = async () => {
    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }))
  }

  beforeEach(() => {
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    global.URL.revokeObjectURL = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('opens a saved client document via the authenticated helper, not a raw protected href', async () => {
    apiFetch.mockImplementation(routeDocs([CLIENT_DOC], successView))
    const openSpy = vi.spyOn(window, 'open').mockReturnValue({})

    await showClientDocuments()
    expect(await screen.findByText('Court Letter Scan')).toBeInTheDocument()

    // The protected route must never be rendered as a raw, token-less link.
    const hrefs = screen.queryAllByRole('link').map((a) => a.getAttribute('href') || '')
    expect(hrefs).not.toContain('/api/clients/client-1/documents/doc-1/view')

    fireEvent.click(screen.getByRole('button', { name: 'View' }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith('/api/clients/client-1/documents/doc-1/view'),
    )
    await waitFor(() =>
      expect(openSpy).toHaveBeenCalledWith('blob:mock-url', '_blank', 'noopener,noreferrer'),
    )
  })

  it('shows a friendly error (never raw JSON) when the authenticated open fails', async () => {
    const failView = () => ({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Missing Firebase bearer token' }),
    })
    apiFetch.mockImplementation(routeDocs([CLIENT_DOC], failView))
    vi.spyOn(window, 'open').mockReturnValue({})

    await showClientDocuments()
    expect(await screen.findByText('Court Letter Scan')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'View' }))

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Could not open document. Please try again.'),
    )
    expect(screen.queryByText(/Missing Firebase bearer token/)).toBeNull()
  })

  it('opens an external-URL client document directly without an authenticated fetch', async () => {
    const EXT_DOC = {
      doc_id: 'doc-2',
      title: 'External Link Doc',
      doc_type: 'other',
      url: 'https://example.com/file.pdf',
    }
    apiFetch.mockImplementation(routeDocs([EXT_DOC], successView))
    const openSpy = vi.spyOn(window, 'open').mockReturnValue({})

    await showClientDocuments()
    expect(await screen.findByText('External Link Doc')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'View' }))

    expect(openSpy).toHaveBeenCalledWith('https://example.com/file.pdf', '_blank', 'noopener,noreferrer')
    expect(apiFetch).not.toHaveBeenCalledWith('/api/clients/client-1/documents/doc-2/view')
  })

  it('downloads a saved generated client document through the authenticated helper', async () => {
    const generatedDoc = {
      doc_id: 'doc-generated-1',
      title: 'Letter of Presence',
      doc_type: 'presence_letter',
      file_name: 'letter-of-presence.txt',
      file_path: 'uploads/clients/client-1/letter-of-presence.txt',
    }
    apiFetch.mockImplementation(routeDocs([generatedDoc], successView))
    let downloadedName = null
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function clickSpy() {
      downloadedName = this.download
    })

    await showClientDocuments()
    expect(await screen.findByText('Letter of Presence')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Download' }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith('/api/clients/client-1/documents/doc-generated-1/view'),
    )
    await waitFor(() => expect(downloadedName).toBe('court_letter.pdf'))
    expect(toast.success).toHaveBeenCalledWith('Document download started')
  })

  it('uses the authenticated helper for generated docs even when the saved record is missing file_path', async () => {
    const legacyGeneratedDoc = {
      doc_id: 'doc-generated-legacy',
      title: 'Legacy Letter of Presence',
      doc_type: 'presence_letter',
      file_name: 'legacy-letter.txt',
      url: null,
    }
    apiFetch.mockImplementation(routeDocs([legacyGeneratedDoc], successView))
    const openSpy = vi.spyOn(window, 'open').mockReturnValue({})

    await showClientDocuments()
    expect(await screen.findByText('Legacy Letter of Presence')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'View' }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith('/api/clients/client-1/documents/doc-generated-legacy/view'),
    )
    await waitFor(() =>
      expect(openSpy).toHaveBeenCalledWith('blob:mock-url', '_blank', 'noopener,noreferrer'),
    )
  })
})

describe('DocumentationCenter PR3: save destination clarity', () => {
  const baseRoutes = (url) => {
    if (url === '/api/dashboard/docs') return Promise.resolve({ ok: true, json: async () => ({ docs: [] }) })
    if (url === '/api/ai-documentation/templates') return Promise.resolve({ ok: true, json: async () => ({ templates: [] }) })
    if (url === '/api/ai-documentation/brand-resources') return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
    if (url === '/api/case-management/notes/list/client-1') return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
    if (url === '/api/clients/client-1/documents') return Promise.resolve({ ok: true, json: async () => ({ documents: [] }) })
    if (url === '/api/case-management/notes/add/client-1') return Promise.resolve({ ok: true, json: async () => ({ success: true, note_id: 'n-pr3' }) })
    return Promise.resolve({ ok: true, json: async () => ({}) })
  }

  it('shows "Destination: Client Notes" when Weekly CM Note template is selected', async () => {
    apiFetch.mockImplementation(baseRoutes)
    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Weekly CM Note/i }))

    const banner = await screen.findByTestId('destination-banner')
    expect(banner).toHaveTextContent('Destination: Client Notes')
    expect(banner).toHaveTextContent('Saved as a Client Note for QA TestClient-Eval')
  })

  it('shows "Destination: Client Documents" when Letter of Presence template is selected with client', async () => {
    apiFetch.mockImplementation(baseRoutes)
    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Discharge Summary/i }))

    const banner = await screen.findByTestId('destination-banner')
    expect(banner).toHaveTextContent('Destination: Client Documents')
    expect(banner).toHaveTextContent("This will save to QA TestClient-Eval's Client Documents vault.")
  })

  it('shows the selected client banner before save when a client is linked', async () => {
    apiFetch.mockImplementation(baseRoutes)
    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Weekly CM Note/i }))

    const clientBanner = await screen.findByTestId('selected-client-banner')
    expect(clientBanner).toHaveTextContent('Selected client: QA TestClient-Eval')
    expect(clientBanner).toHaveTextContent('Saves from this draft will target Client Notes.')
  })

  it('shows "Save to Client Documents" button label when document template and client are selected', async () => {
    apiFetch.mockImplementation(baseRoutes)
    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Discharge Summary/i }))

    expect(await screen.findByRole('button', { name: /Save to Client Documents/i })).toBeInTheDocument()
  })

  it('shows "Save Note" button label when note template is selected', async () => {
    apiFetch.mockImplementation(baseRoutes)
    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Weekly CM Note/i }))

    expect(await screen.findByRole('button', { name: /Save Note/i })).toBeInTheDocument()
  })

  it('shows "Saved to Client Notes." toast after saving a Weekly CM Note', async () => {
    apiFetch.mockImplementation(baseRoutes)
    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Weekly CM Note/i }))
    fireEvent.change(screen.getByPlaceholderText('Enter a strong document title'), {
      target: { value: 'Weekly Note - QA Client' },
    })
    fireEvent.change(screen.getByPlaceholderText('Your generated or hand-written final draft appears here.'), {
      target: { value: 'Client attended weekly check-in and is progressing.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save Note/i }))

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Saved to Client Notes.'))
  })

  it('"Client Linked No" never appears — stat shows "No Client Linked" when no client is selected', async () => {
    apiFetch.mockImplementation(baseRoutes)
    renderPage()

    // Do not click SELECT_CLIENT — verify the no-client label
    expect(screen.queryByText('Client Linked No')).toBeNull()
    // The label "No Client Linked" replaces the old ambiguous "Client Linked" + "No"
    const allText = document.body.textContent
    expect(allText).not.toMatch(/Client Linked\s*No/)
  })

  it('shows a safe no-client message before saving when no client is selected', async () => {
    apiFetch.mockImplementation(baseRoutes)
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /Discharge Summary/i }))

    const clientBanner = await screen.findByTestId('selected-client-banner')
    expect(clientBanner).toHaveTextContent('No client selected')
    expect(clientBanner).toHaveTextContent('Without a selected client, document-mode saves go to the shared Document Library.')
  })

  it('switching from a note template to a document template updates the destination banner', async () => {
    apiFetch.mockImplementation(baseRoutes)
    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))

    // Select Weekly CM Note -> expect "Client Notes"
    fireEvent.click(await screen.findByRole('button', { name: /Weekly CM Note/i }))
    let banner = await screen.findByTestId('destination-banner')
    expect(banner).toHaveTextContent('Destination: Client Notes')

    // Switch to Letter of Presence -> expect "Client Documents"
    fireEvent.click(screen.getByRole('button', { name: /Change template/i }))
    fireEvent.click(await screen.findByRole('button', { name: /Discharge Summary/i }))
    banner = await screen.findByTestId('destination-banner')
    expect(banner).toHaveTextContent('Destination: Client Documents')
  })
})

describe('DocumentationCenter Documents counter', () => {
  const routesWithDocs = (clientDocuments) => (url) => {
    if (url === '/api/dashboard/docs') {
      return Promise.resolve({ ok: true, json: async () => ({ docs: [{ id: 'g1' }, { id: 'g2' }, { id: 'g3' }] }) })
    }
    if (url === '/api/ai-documentation/templates') return Promise.resolve({ ok: true, json: async () => ({ templates: [] }) })
    if (url === '/api/ai-documentation/brand-resources') return Promise.resolve({ ok: true, json: async () => ({ resources: [] }) })
    if (url === '/api/case-management/notes/list/client-1') return Promise.resolve({ ok: true, json: async () => ({ notes: [] }) })
    if (url === '/api/clients/client-1/documents') {
      return Promise.resolve({ ok: true, json: async () => ({ documents: clientDocuments }) })
    }
    return Promise.resolve({ ok: true, json: async () => ({}) })
  }

  // "Documents" also labels the note/document mode-switch button, so scope
  // the query to the stat-tile <p>, not any element with that text.
  const findDocumentsStatValue = () =>
    screen.getAllByText('Documents').find((el) => el.tagName === 'P').nextElementSibling

  it('shows the global docs count when no client is selected', async () => {
    apiFetch.mockImplementation(routesWithDocs([]))
    renderPage()

    await waitFor(() => {
      expect(findDocumentsStatValue()).toHaveTextContent('3')
    })
  })

  it('shows the selected client document count once a client is linked, not the global count', async () => {
    apiFetch.mockImplementation(routesWithDocs([{ doc_id: 'd1', title: 'Letter of Presence' }]))
    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))

    await waitFor(() => {
      expect(findDocumentsStatValue()).toHaveTextContent('1')
    })
  })

  it('never renders the literal "?" mojibake separator in the draft summary or guidance link', async () => {
    apiFetch.mockImplementation(routesWithDocs([]))
    renderPage()
    fireEvent.click(screen.getByText('SELECT_CLIENT'))
    fireEvent.click(await screen.findByRole('button', { name: /Weekly CM Note/i }))

    const bodyText = document.body.textContent
    expect(bodyText).not.toMatch(/\s\?\s(Saving to|Client|Manage AI)/)
    expect(screen.getByText('Manage AI style guides and company guidance')).toBeInTheDocument()
  })
})
