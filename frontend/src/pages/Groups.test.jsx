import '@testing-library/jest-dom/vitest'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Groups from './Groups'
import { apiCall, apiFetch } from '../api/config'

vi.mock('../api/config', () => ({
  apiCall: vi.fn(),
  apiFetch: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const TOPICS = [
  {
    topic_id: 'topic-1',
    title: 'Managing Cravings',
    category: 'Addiction Education',
    source: 'seeded',
    description: 'Understand cravings and build a response plan.',
    key_points_json: ['Know the cycle', 'Use your support plan'],
    discussion_questions_json: ['What triggers cravings?'],
    activity: 'Trigger mapping',
    writing_prompt: 'Describe your strongest trigger.',
    facilitator_tips: 'Keep the group practical.',
  },
  {
    topic_id: 'topic-2',
    title: 'Healthy Boundaries',
    category: 'Relationships',
    source: 'custom',
    description: 'Practice saying no without escalating conflict.',
    key_points_json: ['Boundaries are clear and kind'],
    discussion_questions_json: [],
    activity: '',
    writing_prompt: '',
    facilitator_tips: '',
  },
  {
    topic_id: 'topic-3',
    title: 'Grounding Skills',
    category: 'Coping Skills',
    source: 'ai_generated',
    description: 'Stabilize during stress with sensory grounding.',
    key_points_json: ['5-4-3-2-1 grounding'],
    discussion_questions_json: ['Which senses help most?'],
    activity: 'Practice the grounding sequence',
    writing_prompt: '',
    facilitator_tips: 'Model the exercise slowly.',
  },
]

function mockGroupsApi() {
  apiCall.mockImplementation((url) => {
    if (url === '/api/groups/topics') {
      return Promise.resolve({ topics: TOPICS })
    }
    if (url === '/api/groups/curriculum-packs') {
      return Promise.resolve({ packs: [] })
    }
    if (url === '/api/groups/sessions') {
      return Promise.resolve({ sessions: [] })
    }
    return Promise.resolve({})
  })
  apiFetch.mockResolvedValue({ ok: true, json: async () => ({}) })
}

function renderGroups() {
  return render(
    <MemoryRouter>
      <Groups />
    </MemoryRouter>,
  )
}

describe('Groups topics template layout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGroupsApi()
  })

  it('renders category filters and collapsible template groups', async () => {
    renderGroups()

    await screen.findByText('Managing Cravings')

    expect(screen.getByRole('button', { name: /Filter All Categories/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Filter Coping Skills/i })).toBeInTheDocument()

    const addictionSection = screen.getByRole('button', { name: /Collapse Addiction Education topics/i })
    fireEvent.click(addictionSection)

    expect(screen.getByRole('button', { name: /Expand Addiction Education topics/i })).toBeInTheDocument()
    expect(screen.queryByText('Managing Cravings')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Expand Addiction Education topics/i }))
    expect(await screen.findByText('Managing Cravings')).toBeInTheDocument()
  })

  it('lets the user switch category and expand a topic without changing template behavior', async () => {
    renderGroups()

    await screen.findByText('Managing Cravings')

    fireEvent.click(screen.getByRole('button', { name: /Filter Coping Skills/i }))

    await screen.findByText('Grounding Skills')
    expect(screen.queryByText('Managing Cravings')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Expand Grounding Skills/i }))
    expect(await screen.findByText('5-4-3-2-1 grounding')).toBeInTheDocument()
    expect(screen.getByText('Which senses help most?')).toBeInTheDocument()
  })

  it('keeps the existing sessions workflow available with the same topic library', async () => {
    renderGroups()

    await screen.findByText('Managing Cravings')
    fireEvent.click(screen.getByRole('button', { name: 'Sessions' }))

    await screen.findByRole('button', { name: /New Session/i })
    fireEvent.click(screen.getByRole('button', { name: /New Session/i }))

    expect(await screen.findByText('Create Group Session')).toBeInTheDocument()
    const topicSelect = screen.getAllByRole('combobox')[0]
    const options = within(topicSelect).getAllByRole('option').map((option) => option.textContent)

    expect(options).toContain('Managing Cravings')
    expect(options).toContain('Grounding Skills')
  })

  it('does not change backend API usage for topic and pack loading', async () => {
    renderGroups()

    await waitFor(() => {
      expect(apiCall).toHaveBeenCalledWith('/api/groups/topics')
      expect(apiCall).toHaveBeenCalledWith('/api/groups/curriculum-packs')
    })
    expect(apiCall).not.toHaveBeenCalledWith(expect.stringContaining('/api/groups/topics/categories'))
  })
})
