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
  it('preserves assistant whitespace and wrapping for markdown-style responses', async () => {
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        response: [
          '### Immediate Next Steps',
          '',
          '1. **Prepare Documentation:** Use the initial note.',
          '2. **Client Information Gathering:** Verify demographics.',
          '',
          '- Verify insurance',
          '- Create reminder',
          '',
          'Final paragraph.',
        ].join('\n'),
      }),
    })

    render(<AIAssistantPopup />)

    fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }))
    fireEvent.change(screen.getByPlaceholderText(/ask me anything/i), {
      target: { value: 'Help me with intake' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send message/i }))

    const assistantMessage = await screen.findByTestId('assistant-message')
    expect(assistantMessage).toHaveTextContent('### Immediate Next Steps')
    expect(assistantMessage).toHaveTextContent('1. **Prepare Documentation:** Use the initial note.')
    expect(assistantMessage).toHaveClass('whitespace-pre-wrap')
    expect(assistantMessage).toHaveClass('break-words')
    expect(assistantMessage).toHaveClass('leading-7')
  })
})
