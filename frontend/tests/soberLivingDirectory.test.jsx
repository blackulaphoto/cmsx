// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import SoberLivingDirectory from '../src/pages/SoberLivingDirectory'
import SoberLivingDirectoryListing from '../src/pages/SoberLivingDirectoryListing'
import SoberLivingDirectoryReview from '../src/pages/SoberLivingDirectoryReview'

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const api = vi.hoisted(() => ({
  listListings: vi.fn(),
  getReviewQueue: vi.fn(),
  createListing: vi.fn(),
  getListing: vi.fn(),
  updateListing: vi.fn(),
  verifyListing: vi.fn(),
  archiveListing: vi.fn(),
  createTask: vi.fn(),
  updateTask: vi.fn(),
  getDuplicateCandidate: vi.fn(),
  mergeDuplicateCandidate: vi.fn(),
  keepDuplicateCandidateSeparate: vi.fn(),
  rejectDuplicateCandidate: vi.fn(),
}))

vi.mock('../src/utils/soberLivingDirectory', async () => {
  const actual = await vi.importActual('../src/utils/soberLivingDirectory')
  return {
    ...actual,
    soberLivingDirectoryApi: api,
  }
})

describe('Sober living directory pages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders populated and filtered directory states and supports manual creation', async () => {
    api.listListings
      .mockResolvedValueOnce({
        listings: [
          {
            listing_id: 'sld_1',
            name: 'Oak Recovery House',
            city: 'Los Angeles',
            state: 'CA',
            phone: '555-111-2222',
            population_served: 'Men',
            certification_status: 'Certified',
            certification_body: 'CCAPP',
            last_verified_date: null,
            status: 'pending_review',
            trust_score: 50,
            accepts_mat: true,
          },
        ],
      })
      .mockResolvedValueOnce({
        listings: [],
      })
      .mockResolvedValueOnce({
        listings: [
          {
            listing_id: 'sld_2',
            name: 'Beacon Women House',
            city: 'Long Beach',
            state: 'CA',
            phone: '555-333-4444',
            population_served: 'Women',
            certification_status: 'Listed',
            certification_body: 'Sober Living Network',
            last_verified_date: null,
            status: 'approved',
            trust_score: 35,
            accepts_mat: false,
          },
        ],
      })
    api.createListing.mockResolvedValue({ success: true, listing: { listing_id: 'sld_2' } })

    render(
      <MemoryRouter>
        <SoberLivingDirectory />
      </MemoryRouter>
    )

    expect(screen.getByText(/Loading sober living directory/i)).toBeTruthy()
    expect(await screen.findByText('Oak Recovery House')).toBeTruthy()
    expect(screen.getByRole('link', { name: /Open Review Queue/i }).getAttribute('href')).toBe('/sober-living-directory/review')

    fireEvent.change(screen.getByLabelText('City'), { target: { value: 'Los Angeles' } })
    fireEvent.click(screen.getByRole('button', { name: /Apply Filters/i }))

    await screen.findByText(/No sober living listings match the current filters/i)
    expect(api.listListings).toHaveBeenLastCalledWith(expect.objectContaining({ city: 'Los Angeles' }))

    fireEvent.click(screen.getByRole('button', { name: /Add Listing/i }))
    const createHeading = screen.getByText('New Sober Living Listing')
    const createSection = createHeading.closest('section')
    const createForm = createHeading.closest('section')?.querySelector('form')
    fireEvent.change(within(createSection).getByLabelText('Name'), { target: { value: 'Beacon Women House' } })
    fireEvent.change(within(createSection).getByLabelText('City'), { target: { value: 'Long Beach' } })
    fireEvent.submit(createForm)

    await waitFor(() => {
      expect(api.createListing).toHaveBeenCalled()
    })
    await screen.findByText('Beacon Women House')
  })

  it('loads listing detail, saves edits, verifies, creates tasks, and updates task status', async () => {
    const listing = {
      listing_id: 'sld_123',
      name: 'Harbor House',
      city: 'Torrance',
      state: 'CA',
      phone: '555-111-2222',
      notes: 'Original note',
      internal_referral_notes: 'Original internal note',
      verification_method: 'phone',
      status: 'approved',
      trust_score: 60,
      missing_verification_fields: [],
      is_stale: false,
      verification_tasks: [
        {
          task_id: 'task_1',
          task_type: 'call_to_verify',
          priority: 'medium',
          assigned_to: '',
          due_date: '',
          status: 'open',
          result_notes: '',
        },
      ],
      change_log: [],
    }

    api.getListing.mockResolvedValue({ listing })
    api.updateListing.mockResolvedValue({
      listing: {
        ...listing,
        phone: '555-999-0000',
        notes: 'Updated note',
        internal_referral_notes: 'Updated internal note',
      },
    })
    api.verifyListing.mockResolvedValue({
      listing: {
        ...listing,
        last_verified_date: '2030-01-01T00:00:00',
      },
    })
    api.createTask.mockResolvedValue({ task: { task_id: 'task_2' } })
    api.updateTask.mockResolvedValue({ task: { task_id: 'task_1', status: 'completed' } })

    render(
      <MemoryRouter initialEntries={['/sober-living-directory/sld_123']}>
        <Routes>
          <Route path="/sober-living-directory/:listingId" element={<SoberLivingDirectoryListing />} />
        </Routes>
      </MemoryRouter>
    )

    expect(await screen.findByText('Harbor House')).toBeTruthy()

    fireEvent.change(screen.getByLabelText('Phone'), { target: { value: '555-999-0000' } })
    fireEvent.change(screen.getByLabelText('Notes'), { target: { value: 'Updated note' } })
    fireEvent.change(screen.getByLabelText('Internal Referral Notes'), { target: { value: 'Updated internal note' } })
    fireEvent.click(screen.getByRole('button', { name: /Save Changes/i }))

    await waitFor(() => {
      expect(api.updateListing).toHaveBeenCalled()
    })

    fireEvent.click(screen.getByRole('button', { name: /Mark Verified/i }))
    await waitFor(() => {
      expect(api.verifyListing).toHaveBeenCalledWith('sld_123', expect.any(Object))
    })

    fireEvent.click(screen.getByRole('button', { name: /Create Task/i }))
    await waitFor(() => {
      expect(api.createTask).toHaveBeenCalledWith(expect.objectContaining({ listing_id: 'sld_123' }))
    })

    fireEvent.click(screen.getByRole('button', { name: /Mark Completed/i }))
    await waitFor(() => {
      expect(api.updateTask).toHaveBeenCalledWith('task_1', { status: 'completed' })
    })
  })

  it('renders duplicate diff details and merges selected imported fields from the review page', async () => {
    api.getReviewQueue
      .mockResolvedValueOnce({
        listings: [],
        raw_records: [
          {
            raw_id: 'raw_1',
            raw_name: 'Raw Discovery Home',
            raw_phone: '555-222-3333',
            raw_website: 'https://raw.example.com',
            review_status: 'new',
            discovered_at: '2030-01-01T00:00:00',
            source_name: 'Manual Test Source',
            extracted_json: { city: 'Los Angeles', state: 'CA' },
          },
        ],
        duplicate_candidates: [
          {
            candidate_id: 'dup_1',
            proposed_name: 'Oak Recovery Residence',
            existing_name: 'Oak Recovery House',
            confidence_score: 80,
            match_reasons_json: ['phone_match', 'city_match'],
            extracted_json: {
              name: 'Oak Recovery Residence',
              city: 'Los Angeles',
              phone: '555-111-2222',
              website: 'oak.example.com',
              population_served: 'Men',
            },
            existing_city: 'Los Angeles',
            existing_state: 'CA',
            existing_phone: '555-111-2222',
            existing_website: 'oak.example.com',
            existing_population_served: 'Men',
            existing_status: 'approved',
          },
        ],
      })
      .mockResolvedValueOnce({
        listings: [],
        raw_records: [],
        duplicate_candidates: [],
      })
    api.getDuplicateCandidate.mockResolvedValue({
      candidate: { candidate_id: 'dup_1' },
      existing_listing: { listing_id: 'sld_1', status: 'approved' },
      raw_record: { raw_id: 'raw_1' },
      normalized_imported_fields: {
        phone: '555-111-2222',
        notes: 'Imported note',
        source_urls_json: ['oak.example.com'],
      },
      match_reasons: ['phone_match', 'city_match'],
      confidence_score: 80,
      field_diff: [
        {
          field: 'phone',
          existing_value: '555-111-2222',
          imported_value: '555-111-2222',
          status: 'same',
          recommended_action: 'no_change',
        },
        {
          field: 'notes',
          existing_value: 'Existing note',
          imported_value: 'Imported note',
          status: 'conflict',
          recommended_action: 'manual_review',
        },
        {
          field: 'source_urls_json',
          existing_value: ['oak-house.example.com'],
          imported_value: ['oak.example.com'],
          status: 'conflict',
          recommended_action: 'manual_review',
        },
      ],
    })
    api.mergeDuplicateCandidate.mockResolvedValue({ success: true })

    render(
      <MemoryRouter>
        <SoberLivingDirectoryReview />
      </MemoryRouter>
    )

    expect(await screen.findByText('Possible Duplicate Candidates')).toBeTruthy()
    expect(await screen.findByText('Raw Discovery Records')).toBeTruthy()
    expect(screen.getByText('Raw Discovery Home')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Review Diff/i }))

    await waitFor(() => {
      expect(api.getDuplicateCandidate).toHaveBeenCalledWith('dup_1')
    })

    expect(await screen.findByText('Field-by-field comparison')).toBeTruthy()
    expect(screen.getAllByText(/Recommended: manual review/i).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByLabelText(/Apply imported value for notes/i))
    fireEvent.click(screen.getByRole('button', { name: /Merge Selected Fields/i }))

    await waitFor(() => {
      expect(api.mergeDuplicateCandidate).toHaveBeenCalledWith('dup_1', expect.objectContaining({
        selected_imported_fields: ['notes'],
      }))
    })

    await waitFor(() => {
      expect(screen.getByText(/No duplicate candidates are waiting for review/i)).toBeTruthy()
    })
  })

  it('supports a safe merge action from the duplicate review card', async () => {
    api.getReviewQueue.mockResolvedValue({
      listings: [],
      raw_records: [],
      duplicate_candidates: [
        {
          candidate_id: 'dup_1',
          proposed_name: 'Oak Recovery Residence',
          existing_name: 'Oak Recovery House',
          confidence_score: 80,
          match_reasons_json: ['phone_match', 'city_match'],
          extracted_json: {
            name: 'Oak Recovery Residence',
            city: 'Los Angeles',
            phone: '555-111-2222',
            website: 'oak.example.com',
            population_served: 'Men',
          },
          existing_city: 'Los Angeles',
          existing_state: 'CA',
          existing_phone: '555-111-2222',
          existing_website: 'oak.example.com',
          existing_population_served: 'Men',
          existing_status: 'approved',
        },
      ],
    })
    api.mergeDuplicateCandidate.mockResolvedValue({ success: true })

    render(
      <MemoryRouter>
        <SoberLivingDirectoryReview />
      </MemoryRouter>
    )

    expect(await screen.findByText('Possible Duplicate Candidates')).toBeTruthy()
    expect(await screen.findByText('Oak Recovery Residence')).toBeTruthy()
    fireEvent.click(screen.getAllByRole('button', { name: /Merge Safely/i })[0])

    await waitFor(() => {
      expect(api.mergeDuplicateCandidate).toHaveBeenCalledWith('dup_1', expect.any(Object))
    })
  })
})
