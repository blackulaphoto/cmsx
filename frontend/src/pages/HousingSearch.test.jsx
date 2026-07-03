// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'

const toastMock = vi.hoisted(() => {
  const t = vi.fn()
  t.success = vi.fn()
  t.error = vi.fn()
  return t
})

vi.mock('react-hot-toast', () => ({ default: toastMock }))
vi.mock('../api/config', () => ({ apiFetch: vi.fn() }))
vi.mock('../components/ClientSelector', () => ({
  default: ({ onClientSelect }) => (
    <button
      data-testid="pick-client"
      onClick={() => onClientSelect({ client_id: 'client-1', first_name: 'Casey', last_name: 'Jones' })}
    >
      pick client
    </button>
  ),
}))
vi.mock('../components/LocationSelector', () => ({
  default: ({ value, onChange }) => (
    <input
      data-testid="location-input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}))
vi.mock('../components/HousingSitesIframe', () => ({ default: () => <div>SITES</div> }))
vi.mock('../utils/clientOperationalContext', () => ({
  clientLocation: vi.fn(() => ''),
  fetchClientWithOperationalContext: vi.fn(),
  getNeedKeys: vi.fn(() => new Set()),
}))

import { apiFetch } from '../api/config'
import HousingSearch from './HousingSearch'

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/housing']}>
      <HousingSearch />
    </MemoryRouter>,
  )

const listing = {
  title: 'Sunset Rooms NoHo - $1,400/mo',
  description: 'Room for rent in North Hollywood, CA near the metro.',
  url: 'https://example.com/listing/1',
  source: 'google_housing_cse',
  background_friendly: false,
}

const searchResponse = (listings, extra = {}) => ({
  ok: true,
  json: async () => ({
    success: true,
    housing_listings: listings,
    total_count: listings.length,
    search_sources: ['google_housing_cse'],
    filters_applied: { query: 'apartments for rent in North Hollywood, CA' },
    ...extra,
  }),
})

const setLocation = (value) => {
  const inputs = screen.getAllByTestId('location-input')
  fireEvent.change(inputs[0], { target: { value } })
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('HousingSearch query construction', () => {
  it('calls /api/housing/search with a sane, non-stuffed query and structured params', async () => {
    apiFetch.mockResolvedValue(searchResponse([listing]))

    renderPage()
    setLocation('North Hollywood, CA')
    fireEvent.change(screen.getByPlaceholderText('Monthly rent'), { target: { value: '1400' } })
    fireEvent.click(screen.getByLabelText(/background-friendly only/i))
    fireEvent.click(screen.getByRole('button', { name: /^search housing$/i }))

    await waitFor(() => expect(apiFetch).toHaveBeenCalled())
    const url = apiFetch.mock.calls[0][0]
    const params = new URLSearchParams(url.split('?')[1])

    // Broad query: location + housing type only.
    expect(params.get('query')).toBe('apartments for rent in North Hollywood, CA')
    // Budget and background-friendly travel as structured params, not query stuffing.
    expect(params.get('max_cost')).toBe('1400')
    expect(params.get('background_friendly')).toBe('true')
    expect(params.get('query')).not.toMatch(/under \$/i)
    expect(params.get('query')).not.toMatch(/background friendly/i)
    expect(params.get('query')).not.toMatch(/second chance/i)
    expect(url).toMatch(/^\/api\/housing\/search\?/)
  })

  it('requires a city before searching', () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: /^search housing$/i }))
    expect(toastMock.error).toHaveBeenCalledWith('Please select a city')
    expect(apiFetch).not.toHaveBeenCalled()
  })
})

describe('HousingSearch truthful states', () => {
  it('shows a truthful empty state (no crash) when zero listings come back', async () => {
    apiFetch.mockResolvedValue(searchResponse([]))

    renderPage()
    setLocation('North Hollywood, CA')
    fireEvent.click(screen.getByRole('button', { name: /^search housing$/i }))

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.stringMatching(/no housing options found/i),
        expect.anything(),
      )
    })
    expect(await screen.findByText('No housing options found')).toBeInTheDocument()
    // Regression guard: the old code called toast.info (undefined in
    // react-hot-toast) which threw and surfaced a fake "Search failed".
    expect(toastMock.error).not.toHaveBeenCalled()
  })

  it('surfaces backend errors as a friendly error message', async () => {
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: false, housing_listings: [], error: 'Google API key or Housing CSE ID not configured' }),
    })

    renderPage()
    setLocation('North Hollywood, CA')
    fireEvent.click(screen.getByRole('button', { name: /^search housing$/i }))

    await waitFor(() => {
      expect(toastMock.error).toHaveBeenCalledWith(
        expect.stringContaining('Google API key or Housing CSE ID not configured'),
      )
    })
    expect(screen.getByText('No housing options found')).toBeInTheDocument()
  })
})

describe('HousingSearch save lead', () => {
  it('POSTs the lead to /api/housing/leads linked to the selected client', async () => {
    apiFetch.mockImplementation((url) => {
      if (url.startsWith('/api/housing/search')) {
        return Promise.resolve(searchResponse([listing]))
      }
      if (url === '/api/housing/leads') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, application_id: 'housing_app_1', housing_resource_id: 1 }),
        })
      }
      return Promise.resolve({ ok: true, json: async () => ({ success: true }) })
    })

    renderPage()
    fireEvent.click(screen.getByTestId('pick-client'))
    setLocation('North Hollywood, CA')
    fireEvent.click(screen.getByRole('button', { name: /^search housing$/i }))
    await screen.findByText('Sunset Rooms NoHo - $1,400/mo')

    fireEvent.click(screen.getByRole('button', { name: /save for client/i }))

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith('/api/housing/leads', expect.objectContaining({ method: 'POST' }))
    })
    const saveCall = apiFetch.mock.calls.find(([u]) => u === '/api/housing/leads')
    const body = JSON.parse(saveCall[1].body)
    expect(body.client_id).toBe('client-1')
    expect(body.title).toBe('Sunset Rooms NoHo - $1,400/mo')
    expect(body.url).toBe('https://example.com/listing/1')
    await waitFor(() => {
      expect(toastMock.success).toHaveBeenCalledWith(expect.stringContaining('Saved housing lead for Casey'))
    })
  })

  it('refuses to save without a selected client', async () => {
    apiFetch.mockResolvedValue(searchResponse([listing]))

    renderPage()
    setLocation('North Hollywood, CA')
    fireEvent.click(screen.getByRole('button', { name: /^search housing$/i }))
    await screen.findByText('Sunset Rooms NoHo - $1,400/mo')

    fireEvent.click(screen.getByRole('button', { name: /save for client/i }))

    expect(toastMock.error).toHaveBeenCalledWith('Please select a client first')
    const saveCalls = apiFetch.mock.calls.filter(([u]) => u === '/api/housing/leads')
    expect(saveCalls).toHaveLength(0)
  })

  it('reports a save failure truthfully instead of faking success', async () => {
    apiFetch.mockImplementation((url) => {
      if (url.startsWith('/api/housing/search')) {
        return Promise.resolve(searchResponse([listing]))
      }
      if (url === '/api/housing/leads') {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: async () => ({ detail: 'Failed to persist housing lead' }),
        })
      }
      return Promise.resolve({ ok: true, json: async () => ({ success: true }) })
    })

    renderPage()
    fireEvent.click(screen.getByTestId('pick-client'))
    setLocation('North Hollywood, CA')
    fireEvent.click(screen.getByRole('button', { name: /^search housing$/i }))
    await screen.findByText('Sunset Rooms NoHo - $1,400/mo')

    fireEvent.click(screen.getByRole('button', { name: /save for client/i }))

    await waitFor(() => {
      expect(toastMock.error).toHaveBeenCalledWith(expect.stringContaining('Could not save lead'))
    })
    expect(toastMock.success).not.toHaveBeenCalledWith(expect.stringContaining('Saved housing lead'))
  })
})

describe('HousingSearch Craigslist handoff', () => {
  let openSpy
  beforeEach(() => {
    openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
  })

  it('opens a broad Craigslist query with structured filters, not stacked terms', () => {
    renderPage()
    setLocation('North Hollywood, CA')
    fireEvent.change(screen.getByPlaceholderText('Monthly rent'), { target: { value: '1400' } })
    fireEvent.click(screen.getByRole('button', { name: /search craigslist housing/i }))

    expect(openSpy).toHaveBeenCalledTimes(1)
    const openedUrl = openSpy.mock.calls[0][0]
    const params = new URLSearchParams(openedUrl.split('?')[1])
    expect(openedUrl).toContain('losangeles.craigslist.org/search/apa')
    expect(params.get('query')).toBe('North Hollywood')
    expect(params.get('max_price')).toBe('1400')
    expect(params.get('query')).not.toMatch(/owner|private landlord|second chance/i)
    // Plain-language description of what was searched.
    expect(toastMock).toHaveBeenCalledWith(expect.stringMatching(/searching craigslist/i), expect.anything())
  })
})
