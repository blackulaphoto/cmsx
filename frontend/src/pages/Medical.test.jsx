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

// Treatment center fixtures used by geography filter tests.
const GEO_TREATMENT_FIXTURES = [
  {
    provider_id: 'geo_tc_1', category: 'treatment-centers',
    provider_name: 'Sunrise Recovery LA', city: 'Los Angeles',
    address: '100 Sunset Blvd, Los Angeles, CA 90028',
    provider_type: 'Outpatient', phone: '213-555-0001',
    description: 'Outpatient recovery center', website: '',
    extra: { services: ['Group Therapy', 'Counseling'] },
  },
  {
    provider_id: 'geo_tc_2', category: 'treatment-centers',
    provider_name: 'Hollywood Recovery Center', city: 'Hollywood',
    address: '200 Hollywood Blvd, Hollywood, CA 90038',
    provider_type: 'Residential', phone: '323-555-0002',
    description: 'Residential treatment in Hollywood', website: '',
    extra: { services: ['Counseling', 'Detox'] },
  },
  {
    provider_id: 'geo_tc_3', category: 'treatment-centers',
    provider_name: 'Valley Detox Van Nuys', city: 'Van Nuys',
    address: '300 Van Nuys Blvd, Van Nuys, CA 91401',
    provider_type: 'Detox', phone: '818-555-0003',
    description: 'Detox facility in Van Nuys', website: '',
    extra: { services: ['Detox'] },
  },
  {
    provider_id: 'geo_tc_4', category: 'treatment-centers',
    provider_name: 'Sherman Oaks Wellness', city: 'Sherman Oaks',
    address: '400 Ventura Blvd, Sherman Oaks, CA 91403',
    provider_type: 'IOP', phone: '818-555-0004',
    description: 'Intensive outpatient in Sherman Oaks', website: '',
    extra: { services: ['Group Therapy'] },
  },
  {
    provider_id: 'geo_tc_5', category: 'treatment-centers',
    provider_name: 'Sacramento Behavioral Health', city: 'Sacramento',
    address: '500 K Street, Sacramento, CA 95814',
    provider_type: 'Residential', phone: '916-555-0005',
    description: 'Behavioral health in Sacramento', website: '',
    extra: { services: ['Counseling', 'Group Therapy'] },
  },
]

function makeGeoMockFetch(fixtures, extraFixtures = []) {
  const all = [...fixtures, ...extraFixtures]
  return async (endpoint) => {
    if (endpoint.startsWith('/api/medical/providers?')) {
      const url = new URL(`http://localhost${endpoint}`)
      const category = url.searchParams.get('category') || 'medi-cal'
      const city = (url.searchParams.get('city') || '').toLowerCase()
      const search = (url.searchParams.get('search') || '').toLowerCase()

      const providers = all.filter((p) => {
        if (p.category !== category) return false
        // Backend only city-filters when a city value is actually sent (medi-cal path).
        // treatment-centers receives city="" so this clause is a no-op for them.
        if (city && ![p.city, p.address].some((v) => String(v || '').toLowerCase().includes(city))) return false
        if (search && ![p.provider_name, p.description].some((v) => String(v || '').toLowerCase().includes(search))) return false
        return true
      })
      return jsonResponse({ success: true, providers, total_count: providers.length, category, category_label: 'Treatment Centers' })
    }
    if (endpoint.startsWith('/api/medical/appointments?')) return jsonResponse({ success: true, appointments: [], total_count: 0 })
    if (endpoint.startsWith('/api/medical/referrals?')) return jsonResponse({ success: true, referrals: [], total_count: 0 })
    throw new Error(`Unhandled apiFetch call: ${endpoint}`)
  }
}

describe('Medical geography filter', () => {
  beforeEach(() => {
    apiFetch.mockReset()
    toastMock.mockReset()
    toastMock.success.mockReset()
    toastMock.error.mockReset()
    apiFetch.mockImplementation(makeGeoMockFetch(GEO_TREATMENT_FIXTURES))
  })

  it('blank city shows all treatment center records regardless of location', async () => {
    renderMedical()

    // Switch to treatment-centers (backend receives city="", returns all 5 fixtures)
    fireEvent.click(screen.getByRole('button', { name: /^Treatment Centers/ }))

    // Default city is "Los Angeles" — LA-area records visible after initial load
    expect(await screen.findByText('Sunrise Recovery LA')).toBeInTheDocument()

    // Clear city → all 5 records including Sacramento become visible
    fireEvent.change(screen.getByLabelText('Location selector'), { target: { value: '' } })

    expect(screen.getByText('Sunrise Recovery LA')).toBeInTheDocument()
    expect(screen.getByText('Hollywood Recovery Center')).toBeInTheDocument()
    expect(screen.getByText('Valley Detox Van Nuys')).toBeInTheDocument()
    expect(screen.getByText('Sherman Oaks Wellness')).toBeInTheDocument()
    expect(screen.getByText('Sacramento Behavioral Health')).toBeInTheDocument()
    expect(screen.getByText(/^5 results/)).toBeInTheDocument()
  })

  it('Los Angeles city filter includes LA-area neighborhood records', async () => {
    renderMedical()

    // Switch to treatment-centers; city state defaults to "Los Angeles"
    fireEvent.click(screen.getByRole('button', { name: /^Treatment Centers/ }))

    // All LA-area records (Los Angeles, Hollywood, Van Nuys, Sherman Oaks) should appear
    expect(await screen.findByText('Sunrise Recovery LA')).toBeInTheDocument()
    expect(screen.getByText('Hollywood Recovery Center')).toBeInTheDocument()
    expect(screen.getByText('Valley Detox Van Nuys')).toBeInTheDocument()
    expect(screen.getByText('Sherman Oaks Wellness')).toBeInTheDocument()

    // Sacramento is outside the LA area and must be excluded
    expect(screen.queryByText('Sacramento Behavioral Health')).toBeNull()
    expect(screen.getByText(/^4 results/)).toBeInTheDocument()
  })

  it('Sherman Oaks city filter shows only Sherman Oaks records', async () => {
    renderMedical()

    fireEvent.click(screen.getByRole('button', { name: /^Treatment Centers/ }))
    expect(await screen.findByText('Sunrise Recovery LA')).toBeInTheDocument()

    // Narrow city to Sherman Oaks (a specific neighborhood, not an LA alias)
    fireEvent.change(screen.getByLabelText('Location selector'), { target: { value: 'Sherman Oaks' } })

    expect(screen.getByText('Sherman Oaks Wellness')).toBeInTheDocument()
    expect(screen.queryByText('Sunrise Recovery LA')).toBeNull()
    expect(screen.queryByText('Hollywood Recovery Center')).toBeNull()
    expect(screen.queryByText('Valley Detox Van Nuys')).toBeNull()
    expect(screen.queryByText('Sacramento Behavioral Health')).toBeNull()
    expect(screen.getByText(/^1 results/)).toBeInTheDocument()
  })

  it('resets to page 1 when city filter changes', async () => {
    // 25 treatment-center records all in Los Angeles so they all pass the LA alias filter
    const manyFixtures = Array.from({ length: 25 }, (_, i) => ({
      provider_id: `tc_many_${i}`,
      category: 'treatment-centers',
      city: 'Los Angeles',
      provider_name: `TC Many ${i + 1}`,
      provider_type: 'Outpatient',
      address: `${(i + 1) * 10} Main St, Los Angeles, CA 90001`,
      phone: '', website: '', description: 'Treatment center', extra: {},
    }))
    apiFetch.mockImplementation(makeGeoMockFetch(manyFixtures))

    renderMedical()
    fireEvent.click(screen.getByRole('button', { name: /^Treatment Centers/ }))

    // All 25 match "Los Angeles" → 3 pages
    expect(await screen.findByText('TC Many 1')).toBeInTheDocument()
    // Page indicator appears in two places (stats chip + nav pagination)
    expect(screen.getAllByText(/Page 1 of 3/).length).toBeGreaterThan(0)

    // Navigate to page 2
    fireEvent.click(screen.getByRole('button', { name: /Next/i }))
    await waitFor(() => {
      expect(screen.getAllByText(/Page 2 of 3/).length).toBeGreaterThan(0)
    })

    // Change city — all 25 still match (empty string passes all), but page must reset to 1
    fireEvent.change(screen.getByLabelText('Location selector'), { target: { value: '' } })

    await waitFor(() => {
      expect(screen.getAllByText(/Page 1 of 3/).length).toBeGreaterThan(0)
    })
    // Confirm we are NOT still on page 2
    expect(screen.queryAllByText(/Page 2 of 3/).length).toBe(0)
  })

  it('search and city filters compose correctly for treatment centers', async () => {
    renderMedical()

    fireEvent.click(screen.getByRole('button', { name: /^Treatment Centers/ }))
    expect(await screen.findByText('Sunrise Recovery LA')).toBeInTheDocument()

    // Search keyword "Hollywood" — narrows to Hollywood Recovery Center at backend level
    fireEvent.change(screen.getByPlaceholderText('Provider name or keyword'), {
      target: { value: 'Hollywood' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Search Providers/i }))

    // Only Hollywood Recovery Center matches search and is in LA area
    expect(await screen.findByText('Hollywood Recovery Center')).toBeInTheDocument()
    expect(screen.queryByText('Sunrise Recovery LA')).toBeNull()
    expect(screen.queryByText('Valley Detox Van Nuys')).toBeNull()
    expect(screen.queryByText('Sacramento Behavioral Health')).toBeNull()
    expect(screen.getByText(/^1 results/)).toBeInTheDocument()
  })
})
