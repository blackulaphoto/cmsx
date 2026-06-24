// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'

vi.mock('../../api/config', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../api/config'
import AIAssistantPopup from './AIAssistantPopup'

beforeEach(() => {
  vi.clearAllMocks()
  window.history.replaceState({}, '', '/case-management')
  window.HTMLElement.prototype.scrollTo = vi.fn()
})

describe('AIAssistantPopup', () => {
  it('renders assistant markdown as formatted HTML without raw markers', async () => {
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        response: [
          '### Morning Steps',
          '',
          'Click **Dashboard** to see your caseload overview.',
          '',
          '- Open Smart Daily for your work queue.',
          '- Check Messages for team updates.',
          '',
          'Best next step: start with Dashboard.',
        ].join('\n'),
      }),
    })

    render(<AIAssistantPopup />)

    fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }))
    fireEvent.change(screen.getByPlaceholderText(/ask me anything/i), {
      target: { value: 'What should I check every morning?' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send message/i }))

    const assistantMessage = await screen.findByTestId('assistant-message')

    // Heading renders as readable text — raw '###' markers must not appear
    expect(assistantMessage).toHaveTextContent('Morning Steps')
    expect(assistantMessage).not.toHaveTextContent('### Morning Steps')

    // Bold renders as text — raw '**' markers must not appear
    expect(assistantMessage).toHaveTextContent('Dashboard')
    expect(assistantMessage).not.toHaveTextContent('**Dashboard**')

    // List items appear in readable form
    expect(assistantMessage).toHaveTextContent('Open Smart Daily for your work queue.')
    expect(assistantMessage).toHaveTextContent('Check Messages for team updates.')

    // Best-next-step guidance appears
    expect(assistantMessage).toHaveTextContent('Best next step: start with Dashboard.')

    // Wrapper carries readable styling classes
    expect(assistantMessage).toHaveClass('break-words')
    expect(assistantMessage).toHaveClass('leading-relaxed')
  })

  it('renders user messages as plain text without markdown processing', async () => {
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ response: 'Got it.' }),
    })

    render(<AIAssistantPopup />)

    fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }))
    fireEvent.change(screen.getByPlaceholderText(/ask me anything/i), {
      target: { value: 'Help me with **bold** text' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send message/i }))

    // The user bubble should show the raw text exactly as typed
    const userBubbles = await screen.findAllByText('Help me with **bold** text')
    expect(userBubbles.length).toBeGreaterThan(0)
  })

  it('shows assistant error message when API fails', async () => {
    apiFetch.mockResolvedValue({ ok: false })

    render(<AIAssistantPopup />)

    fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }))
    fireEvent.change(screen.getByPlaceholderText(/ask me anything/i), {
      target: { value: 'Any question' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send message/i }))

    const assistantMessage = await screen.findByTestId('assistant-message')
    expect(assistantMessage).toHaveTextContent('Error')
  })
})
