// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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
  })
})
