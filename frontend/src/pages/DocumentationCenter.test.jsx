// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

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
    fireEvent.click(screen.getByRole('button', { name: /Save Document/i }))

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
