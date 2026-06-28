// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
  default: function MockClientSelector({ onClientSelect, placeholder }) {
    return (
      <button
        type="button"
        onClick={() => onClientSelect({
          client_id: 'client_1',
          first_name: 'Jamie',
          last_name: 'Rivera',
          case_manager_id: 'cm_1',
        })}
      >
        {placeholder || 'Select client'}
      </button>
    )
  },
}))

vi.mock('../components/LocationSelector', () => ({
  default: function MockLocationSelector({ value, onChange, placeholder }) {
    return (
      <input
        aria-label="Location selector"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    )
  },
}))

vi.mock('../utils/clientOperationalContext', () => ({
  clientLocation: vi.fn(() => ''),
  fetchClientWithOperationalContext: vi.fn(),
  formatNeedSummary: vi.fn(() => ''),
  getIntakeContext: vi.fn(() => ({})),
  getNeedKeys: vi.fn(() => new Set()),
}))

import Medical from './Medical'

function makeProvider(index, overrides = {}) {
  return {
    provider_id: `provider_${index}`,
    category: 'medi-cal',
    provider_name: `Provider ${index}`,
    provider_type: 'Primary Care',
    address: `${index} Main St, Los Angeles, CA 9000${index}`,
    city: 'Los Angeles',
    phone: `555-000-00${String(index).padStart(2, '0')}`,
    website: index === 1 ? 'https://provider-one.example.com' : '',
    description: index === 1 ? 'Accepts Medi-Cal and coordinates complex care.' : `General provider ${index}`,
    extra: index === 1
      ? {
          verified: true,
          specialties: ['Cardiology', 'Family Medicine'],
          services: ['Walk-In Exams'],
          medical_groups: ['Sunrise Medical Group'],
        }
      : {
          specialties: index === 14 ? ['Cardiology'] : ['Family Medicine'],
        },
    ...overrides,
  }
}

function jsonResponse(data, ok = true) {
  return {
    ok,
    json: async () => data,
  }
}

function filterProviders(providers, params) {
  const category = params.get('category') || 'medi-cal'
  const search = (params.get('search') || '').toLowerCase()
  const specialty = (params.get('specialty') || '').toLowerCase()
  const city = (params.get('city') || '').toLowerCase()

  return providers.filter((provider) => {
    const matchesCategory = provider.category === category
    const matchesSearch = !search || [
      provider.provider_name,
      provider.description,
      provider.provider_type,
    ].some((value) => String(value || '').toLowerCase().includes(search))
    const matchesSpecialty = !specialty || [
      ...(provider.extra?.specialties || []),
      ...(provider.extra?.services || []),
      provider.description,
    ].some((value) => String(value || '').toLowerCase().includes(specialty))
    const matchesCity = !city || [provider.city, provider.address].some((value) => String(value || '').toLowerCase().includes(city))
    return matchesCategory && matchesSearch && matchesSpecialty && matchesCity
  })
}

function renderMedical() {
  return render(
    <MemoryRouter>
      <Medical />
    </MemoryRouter>
  )
}

describe('Medical page', () => {
  let providerFixtures
  let referralPosts
  let appointmentPosts

  beforeEach(() => {
    providerFixtures = Array.from({ length: 14 }, (_, index) => makeProvider(index + 1))
    referralPosts = []
    appointmentPosts = []

    apiFetch.mockReset()
    toastMock.mockReset()
    toastMock.success.mockReset()
    toastMock.error.mockReset()

    apiFetch.mockImplementation(async (endpoint, options = {}) => {
      if (endpoint.startsWith('/api/medical/providers?')) {
        const url = new URL(`http://localhost${endpoint}`)
        const providers = filterProviders(providerFixtures, url.searchParams)
        return jsonResponse({
          success: true,
          providers,
          total_count: providers.length,
          category: url.searchParams.get('category') || 'medi-cal',
          category_label: 'Medi-Cal Providers',
        })
      }

      if (endpoint.startsWith('/api/medical/appointments?')) {
        return jsonResponse({ success: true, appointments: [], total_count: 0 })
      }

      if (endpoint.startsWith('/api/medical/referrals?')) {
        return jsonResponse({ success: true, referrals: [], total_count: 0 })
      }

      if (endpoint === '/api/medical/referrals' && options.method === 'POST') {
        referralPosts.push(JSON.parse(options.body))
        return jsonResponse({ success: true, referral_id: 'ref_1' })
      }

      if (endpoint === '/api/medical/appointments' && options.method === 'POST') {
        appointmentPosts.push(JSON.parse(options.body))
        return jsonResponse({ success: true, appointment_id: 'apt_1' })
      }

      if (endpoint.startsWith('/api/medical/appointments/') && options.method === 'PATCH') {
        return jsonResponse({ success: true })
      }

      if (endpoint.startsWith('/api/medical/referrals/') && options.method === 'PATCH') {
        return jsonResponse({ success: true })
      }

      throw new Error(`Unhandled apiFetch call: ${endpoint}`)
    })
  })

  it('paginates provider results with previous and next controls', async () => {
    renderMedical()

    expect(await screen.findByText('Provider 1')).toBeInTheDocument()
    expect(screen.queryByText('Provider 13')).toBeNull()
    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Next/i }))

    expect(await screen.findByText('Provider 13')).toBeInTheDocument()
    expect(screen.queryByText('Provider 1')).toBeNull()
    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument()
  })

  it('shows the result count summary', async () => {
    renderMedical()

    expect(await screen.findByText('14 results · Showing 1-12 · Page 1 of 2')).toBeInTheDocument()
    expect(screen.getByText('Showing 1-12 of 14 results')).toBeInTheDocument()
  })

  it('renders rich provider card fields when available', async () => {
    renderMedical()

    const card = await screen.findByTestId('provider-card-provider_1')
    expect(within(card).getByText('Medi-Cal dataset')).toBeInTheDocument()
    expect(within(card).getByText('Verified')).toBeInTheDocument()
    expect(within(card).getByText('Cardiology')).toBeInTheDocument()
    expect(within(card).getByText('Walk-In Exams')).toBeInTheDocument()
    expect(within(card).getByText(/1 Main St/i)).toBeInTheDocument()
    expect(within(card).getByText('555-000-0001')).toBeInTheDocument()
    expect(within(card).getByRole('button', { name: /Visit Website/i })).toBeInTheDocument()
  })

  it('renders a fallback category icon when no logo exists', async () => {
    renderMedical()

    expect(await screen.findByTestId('provider-fallback-icon-provider_1')).toBeInTheDocument()
  })

  it('keeps search and specialty filtering working', async () => {
    renderMedical()

    await screen.findByText('Provider 1')
    fireEvent.change(screen.getByPlaceholderText('Psychiatry, detox, family medicine...'), {
      target: { value: 'Cardiology' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Search Providers/i }))

    expect(await screen.findByText(/2 results/)).toBeInTheDocument()
    expect(screen.getByText('Provider 1')).toBeInTheDocument()
    expect(screen.getByText('Provider 14')).toBeInTheDocument()
    expect(screen.queryByText('Provider 2')).toBeNull()
  })

  it('preserves the save referral and book appointment flow', async () => {
    renderMedical()

    await screen.findByText('Provider 1')
    fireEvent.click(screen.getByRole('button', { name: /Select a client to coordinate healthcare for/i }))

    const providerCard = screen.getByTestId('provider-card-provider_1')
    fireEvent.click(within(providerCard).getByRole('button', { name: 'Save Referral' }))

    await waitFor(() => {
      expect(referralPosts).toHaveLength(1)
    })
    expect(referralPosts[0].provider_name).toBe('Provider 1')

    fireEvent.click(within(providerCard).getByRole('button', { name: 'Book Appointment' }))
    expect(await screen.findByDisplayValue('Medical - Primary Care')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2030-01-15' } })
    fireEvent.click(screen.getByRole('button', { name: 'Schedule' }))

    await waitFor(() => {
      expect(appointmentPosts).toHaveLength(1)
    })
    expect(appointmentPosts[0]).toEqual(expect.objectContaining({
      client_id: 'client_1',
      provider_name: 'Provider 1',
      appointment_date: '2030-01-15',
    }))
  })

  it('prefers a better organization name over generic junk labels', async () => {
    providerFixtures[0] = makeProvider(1, {
      provider_name: 'PHYSICIAN',
      extra: {
        verified: true,
        specialties: ['Cardiology'],
        medical_groups: ['Better Health Clinic'],
      },
    })

    renderMedical()

    expect(await screen.findByText('Better Health Clinic')).toBeInTheDocument()
    expect(screen.queryByText(/^PHYSICIAN$/)).toBeNull()
  })
})
