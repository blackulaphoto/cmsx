// @vitest-environment jsdom
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const toastMock = vi.hoisted(() => {
  const fn = vi.fn()
  fn.success = vi.fn()
  fn.error = vi.fn()
  return fn
})

const apiFetch = vi.hoisted(() => vi.fn())

vi.mock('react-hot-toast', () => ({
  default: toastMock,
}))

vi.mock('../api/config', () => ({
  apiFetch,
}))

vi.mock('../components/ClientSelector', () => ({
  default: function MockClientSelector({ onClientSelect }) {
    return (
      <button
        type="button"
        onClick={() =>
          onClientSelect({
            client_id: 'client-1',
            first_name: 'Casey',
            last_name: 'Jones',
          })}
      >
        Select client
      </button>
    )
  },
}))

import AIChat from './AIChat'

describe('AIChat', () => {
  beforeEach(() => {
    apiFetch.mockReset()
    toastMock.mockReset()
    toastMock.success.mockReset()
    toastMock.error.mockReset()
    window.localStorage.clear()
    HTMLElement.prototype.scrollTo = vi.fn()
  })

  it('sends selected-client context and current route to the live AI chat endpoint', async () => {
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ response: 'Client has 1 overdue task.' }),
    })

    render(
      <MemoryRouter initialEntries={['/ai-chat?client=client-1']}>
        <AIChat />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Select client' }))
    fireEvent.change(screen.getByPlaceholderText('Type your message to the AI assistant...'), {
      target: { value: 'Does this client have overdue tasks?' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))

    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1))

    const [, options] = apiFetch.mock.calls[0]
    const body = JSON.parse(options.body)

    expect(body.client_id).toBe('client-1')
    expect(body.client_name).toBe('Casey Jones')
    expect(body.current_route).toBe('/ai-chat')
    expect(body.message).toBe('Does this client have overdue tasks?')
    expect(await screen.findByText('Client has 1 overdue task.')).toBeInTheDocument()
    expect(screen.queryByText('AI is thinking...')).not.toBeInTheDocument()
  })

  it('clears loading and shows the backend error when the AI request fails', async () => {
    apiFetch.mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'AI provider is unavailable.' }),
    })

    render(
      <MemoryRouter initialEntries={['/ai-chat']}>
        <AIChat />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByPlaceholderText('Type your message to the AI assistant...'), {
      target: { value: 'What should I follow up on?' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))

    expect(await screen.findByText(/AI provider is unavailable/)).toBeInTheDocument()
    expect(screen.queryByText('AI is thinking...')).not.toBeInTheDocument()
    expect(screen.getByPlaceholderText('Type your message to the AI assistant...')).not.toBeDisabled()
  })

  it('stops loading and shows a friendly error when the response body never completes', async () => {
    vi.useFakeTimers()
    apiFetch.mockResolvedValue({
      ok: true,
      json: () => new Promise(() => {}),
    })

    render(
      <MemoryRouter initialEntries={['/ai-chat']}>
        <AIChat />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByPlaceholderText('Type your message to the AI assistant...'), {
      target: { value: 'What overdue reminders do I have?' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))

    await act(async () => {
      await vi.advanceTimersByTimeAsync(20000)
    })

    expect(screen.getByText(/AI response timed out/)).toBeInTheDocument()
    expect(screen.queryByText('AI is thinking...')).not.toBeInTheDocument()
    expect(screen.getByPlaceholderText('Type your message to the AI assistant...')).not.toBeDisabled()
    vi.useRealTimers()
  })
})
