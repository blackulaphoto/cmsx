// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'

let currentSearchParams = new URLSearchParams()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useSearchParams: () => [currentSearchParams, vi.fn()],
  }
})

vi.mock('../api/config', () => ({
  apiFetch: vi.fn(),
}))

vi.mock('react-hot-toast', () => {
  const toast = vi.fn()
  toast.success = vi.fn()
  toast.error = vi.fn()
  return { default: toast }
})

vi.mock('../services/pdfService', () => ({
  default: {
    healthCheck: vi.fn().mockResolvedValue({ success: true, details: { weasyprint_available: true } }),
    generateAndDownload: vi.fn(),
    downloadPDF: vi.fn(),
    formatFilename: vi.fn(() => 'resume.pdf'),
    getErrorMessage: vi.fn((e) => e?.message || 'PDF error'),
  },
}))

vi.mock('../components/ClientSelector', () => ({
  default: ({ onClientSelect }) => (
    <button
      data-testid="select-client"
      onClick={() =>
        onClientSelect({
          client_id: 'c1',
          first_name: 'Import',
          last_name: 'TestClient',
          phone: '555-0100',
          email: 'import.testclient@example.com',
        })
      }
    >
      Pick client
    </button>
  ),
}))

vi.mock('../components/WorkExperienceForm', () => ({ default: () => <div data-testid="work-form" /> }))
vi.mock('../components/LivePreview', () => ({ default: () => <div data-testid="live-preview" /> }))
vi.mock('../components/TemplateSelector', () => ({ default: () => <div data-testid="template-selector" /> }))
vi.mock('../components/ResumeModal', () => ({ default: () => <div data-testid="resume-modal" /> }))
vi.mock('../components/DebugPanel', () => ({ default: () => <div data-testid="debug-panel" /> }))
vi.mock('../utils/clientOperationalContext', () => ({
  getIntakeContext: () => ({}),
  getTreatmentPlanContext: () => ({}),
  mergeUnique: (a = [], b = []) => [...(a || []), ...(b || [])].filter(Boolean),
}))

import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'
import Resume from './Resume'

const IMPORTED_PROFILE = {
  career_objective: 'Dependable warehouse associate seeking full-time work',
  work_history: [
    {
      job_title: 'Warehouse Associate',
      company: 'Acme Logistics',
      start_date: '2021',
      end_date: '2023',
      description: 'Picked and packed orders',
      achievements: [],
    },
  ],
  skills: [{ category: 'Warehouse', skill_list: ['Forklift', 'Inventory'] }],
  education: [],
  certifications: [],
  preferred_industries: [],
  professional_references: [],
}

function okJson(payload) {
  return Promise.resolve({ ok: true, json: async () => payload })
}

function setupApi({ importResponse } = {}) {
  apiFetch.mockImplementation((url, options = {}) => {
    if (url.startsWith('/api/resume/import')) {
      if (importResponse) return Promise.resolve(importResponse)
      return okJson({
        success: true,
        profile: IMPORTED_PROFILE,
        raw_text: 'raw resume text',
        extraction_summary: { sections_found: 3, experience_entries: 1, skills_count: 2, education_entries: 0 },
        ai_rewrite_applied: false,
        client_id: 'c1',
      })
    }
    if (url.startsWith('/api/resume/rewrite-profile')) {
      return okJson({
        success: true,
        ai_rewrite_applied: true,
        profile: { ...IMPORTED_PROFILE, career_objective: 'AI rewritten objective' },
      })
    }
    if (url.startsWith('/api/resume/profile/')) return okJson({ success: true, profile: null })
    if (url.startsWith('/api/resume/profile')) return okJson({ success: true, profile_id: 'p1' })
    if (url.startsWith('/api/resume/list/')) return okJson({ resumes: [] })
    if (url.startsWith('/api/resume/applications/')) return okJson({ applications: [] })
    return okJson({})
  })
}

async function renderWithClientSelected() {
  const utils = render(<Resume />)
  fireEvent.click(screen.getByTestId('select-client'))
  await waitFor(() => expect(screen.getByText(/Import TestClient selected/i)).toBeInTheDocument())
  return utils
}

function pickFile(container, name = 'resume.docx') {
  const input = container.querySelector('input[type="file"]')
  const file = new File(['dummy'], name, {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  })
  fireEvent.change(input, { target: { files: [file] } })
  return file
}

beforeEach(() => {
  vi.clearAllMocks()
  currentSearchParams = new URLSearchParams()
})

describe('Resume Builder import workflow', () => {
  it('imports a resume for the selected client and populates the editor', async () => {
    setupApi()
    const { container } = await renderWithClientSelected()
    pickFile(container)

    fireEvent.click(screen.getByRole('button', { name: /Import Resume/i }))

    await waitFor(() => {
      const importCall = apiFetch.mock.calls.find(([url]) => url.startsWith('/api/resume/import'))
      expect(importCall).toBeTruthy()
      const [url, options] = importCall
      expect(url).toContain('client_id=c1')
      expect(url).toContain('ai_rewrite=true') // default mode is Import + AI rewrite
      expect(options.method).toBe('POST')
      expect(options.body).toBeInstanceOf(FormData)
    })

    // Extracted content lands in the editor form.
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(/Brief statement about career goals/i)
      ).toHaveValue(IMPORTED_PROFILE.career_objective)
    })

    // Honest toast: backend reported ai_rewrite_applied=false.
    expect(toast.success).toHaveBeenCalledWith('Resume imported successfully')
    // Selected client is preserved.
    expect(screen.getByText(/Import TestClient selected/i)).toBeInTheDocument()
  })

  it('imports without AI rewrite when "Import only" is chosen', async () => {
    setupApi()
    const { container } = await renderWithClientSelected()
    pickFile(container)

    fireEvent.change(container.querySelector('select'), { target: { value: 'populate' } })
    fireEvent.click(screen.getByRole('button', { name: /Import Resume/i }))

    await waitFor(() => {
      const importCall = apiFetch.mock.calls.find(([url]) => url.startsWith('/api/resume/import'))
      expect(importCall[0]).toContain('ai_rewrite=false')
    })
  })

  it('shows the backend detail as a friendly error when import fails', async () => {
    setupApi({
      importResponse: {
        ok: false,
        json: async () => ({ detail: 'Unsupported file format. Supported formats: .pdf, .doc, .docx' }),
      },
    })
    const { container } = await renderWithClientSelected()
    pickFile(container, 'resume.txt')

    fireEvent.click(screen.getByRole('button', { name: /Import Resume/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'Unsupported file format. Supported formats: .pdf, .doc, .docx'
      )
    })
    // Editor state is not wiped by a failed import.
    expect(screen.getByPlaceholderText(/Brief statement about career goals/i)).toHaveValue('')
  })

  it('requires a file before importing', async () => {
    setupApi()
    await renderWithClientSelected()
    const importButton = screen.getByRole('button', { name: /Import Resume/i })
    expect(importButton).toBeDisabled()
  })

  it('sends AI rewrite instructions with the current profile to the rewrite endpoint', async () => {
    setupApi()
    await renderWithClientSelected()

    const instructions = screen.getByPlaceholderText(/Example: Rewrite this for entry-level/i)
    fireEvent.change(instructions, { target: { value: 'Rewrite for warehouse jobs' } })
    fireEvent.click(screen.getByRole('button', { name: /Rewrite with AI/i }))

    await waitFor(() => {
      const call = apiFetch.mock.calls.find(([url]) => url.startsWith('/api/resume/rewrite-profile'))
      expect(call).toBeTruthy()
      const body = JSON.parse(call[1].body)
      expect(body.client_id).toBe('c1')
      expect(body.instructions).toBe('Rewrite for warehouse jobs')
      expect(body.profile).toBeTruthy()
    })

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(/Brief statement about career goals/i)
      ).toHaveValue('AI rewritten objective')
    })
    expect(toast.success).toHaveBeenCalledWith('Resume updated with AI changes')
  })

  it('surfaces the backend error when AI rewrite is unavailable', async () => {
    setupApi()
    // Override only the rewrite endpoint to fail like an unconfigured AI backend.
    const base = apiFetch.getMockImplementation()
    apiFetch.mockImplementation((url, options) => {
      if (url.startsWith('/api/resume/rewrite-profile')) {
        return Promise.resolve({
          ok: false,
          json: async () => ({
            detail:
              'AI rewrite is unavailable right now, so the resume was left unchanged. Check the AI configuration (OPENAI_API_KEY) or try again in a moment.',
          }),
        })
      }
      return base(url, options)
    })
    await renderWithClientSelected()

    const instructions = screen.getByPlaceholderText(/Example: Rewrite this for entry-level/i)
    fireEvent.change(instructions, { target: { value: 'Rewrite for warehouse jobs' } })
    fireEvent.click(screen.getByRole('button', { name: /Rewrite with AI/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('AI rewrite is unavailable'))
    })
  })

  it('saves the employment profile for the selected client', async () => {
    setupApi()
    await renderWithClientSelected()

    fireEvent.change(screen.getByPlaceholderText(/Brief statement about career goals/i), {
      target: { value: 'My objective' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save Profile/i }))

    await waitFor(() => {
      const call = apiFetch.mock.calls.find(
        ([url, options]) => url === '/api/resume/profile' && options?.method === 'POST'
      )
      expect(call).toBeTruthy()
      const body = JSON.parse(call[1].body)
      expect(body.client_id).toBe('c1')
      expect(body.career_objective).toBe('My objective')
    })
    expect(toast.success).toHaveBeenCalledWith('Employment profile saved successfully!')
  })

  it('blocks import when no client is selected', async () => {
    setupApi()
    const { container } = render(<Resume />)
    // Without a selected client the builder shows its empty state and the
    // import controls are not reachable, so no import request can be sent.
    expect(screen.getByText(/Select a Client to Begin/i)).toBeInTheDocument()
    expect(container.querySelector('input[type="file"]')).toBeNull()
    expect(apiFetch.mock.calls.find(([url]) => url.startsWith('/api/resume/import'))).toBeFalsy()
  })
})
