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
})
