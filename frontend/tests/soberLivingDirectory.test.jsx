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
  getRawRecord: vi.fn(),
  approveRawRecord: vi.fn(),
  rejectRawRecord: vi.fn(),
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
    vi.resetAllMocks()
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

  it('renders raw record review details and approves a raw record from the review page', async () => {
    api.getReviewQueue
      .mockResolvedValueOnce({
        listings: [],
        raw_records: [
          {
            raw_id: 'raw_1',
            raw_name: 'Raw Discovery Home',
            raw_address: '101 Main St',
            raw_phone: '555-222-3333',
            raw_website: 'https://raw.example.com',
            review_status: 'new',
            discovered_at: '2030-01-01T00:00:00',
            source_name: 'Manual Test Source',
            duplicate_candidate_count: 0,
            missing_required_fields: [],
            extracted_json: { city: 'Los Angeles', state: 'CA', address: '101 Main St' },
          },
          {
            raw_id: 'raw_2',
            raw_name: 'Blocked Duplicate Raw',
            raw_phone: '555-888-9999',
            raw_website: 'https://duplicate.example.com',
            review_status: 'possible_duplicate',
            discovered_at: '2030-01-02T00:00:00',
            source_name: 'Manual Test Source',
            duplicate_candidate_count: 1,
            missing_required_fields: [],
            extracted_json: { city: 'Long Beach', state: 'CA' },
          },
        ],
        duplicate_candidates: [
          {
            candidate_id: 'dup_1',
            raw_id: 'raw_2',
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
    api.getRawRecord.mockResolvedValue({
      raw_record: {
        raw_id: 'raw_1',
        review_notes: '',
        run_id: 'run_1',
      },
      source: {
        source_name: 'Manual Test Source',
        source_type: 'manual',
      },
      discovery_run: {
        run_id: 'run_1',
        status: 'completed',
      },
      original_raw_fields: {
        raw_name: 'Raw Discovery Home',
        raw_address: '101 Main St',
        raw_phone: '555-222-3333',
        raw_email: null,
        raw_website: 'https://raw.example.com',
      },
      normalized_preview_fields: {
        name: 'Raw Discovery Home',
        city: 'Los Angeles',
        state: 'CA',
        phone: '555-222-3333',
        website: 'https://raw.example.com',
        population_served: null,
      },
      duplicate_candidates: [],
      missing_required_fields: [],
    })
    api.approveRawRecord.mockResolvedValue({
      listing: { listing_id: 'sld_raw_1', name: 'Raw Discovery Home' },
      raw_record: { raw_id: 'raw_1', review_status: 'approved' },
    })
    render(
      <MemoryRouter>
        <SoberLivingDirectoryReview />
      </MemoryRouter>
    )

    expect(await screen.findByText('Possible Duplicate Candidates')).toBeTruthy()
    expect(await screen.findByText('Raw Discovery Records')).toBeTruthy()
    expect(screen.getByText('Raw Discovery Home')).toBeTruthy()
    expect(screen.getByText(/1 duplicate candidate/i)).toBeTruthy()
    const rawRecordCard = screen.getByText('Raw Discovery Home').closest('article')
    fireEvent.click(within(rawRecordCard).getByRole('button', { name: /View Details/i }))

    await waitFor(() => {
      expect(api.getRawRecord).toHaveBeenCalledWith('raw_1')
    })

    expect(await screen.findByText('Normalized Preview')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Approve Into Pending Review/i }))
    await waitFor(() => {
      expect(api.approveRawRecord).toHaveBeenCalledWith('raw_1', expect.objectContaining({
        force: false,
      }))
    })
  })

  it('supports a safe merge action from the duplicate review card', async () => {
    api.getReviewQueue.mockResolvedValue({
      listings: [],
      raw_records: [],
      duplicate_candidates: [
        {
          candidate_id: 'dup_1',
          raw_id: 'raw_2',
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

  it('rejects a raw record from the review page', async () => {
    api.getReviewQueue
      .mockResolvedValueOnce({
        listings: [],
        raw_records: [
          {
            raw_id: 'raw_9',
            raw_name: 'Rejectable Raw',
            raw_phone: '555-123-9999',
            raw_website: 'https://reject.example.com',
            review_status: 'new',
            discovered_at: '2030-01-01T00:00:00',
            source_name: 'Manual Test Source',
            duplicate_candidate_count: 0,
            missing_required_fields: [],
            extracted_json: { city: 'Los Angeles', state: 'CA' },
          },
        ],
        duplicate_candidates: [],
      })
      .mockResolvedValueOnce({
        listings: [],
        raw_records: [],
        duplicate_candidates: [],
      })
    api.rejectRawRecord.mockResolvedValue({ raw_record: { raw_id: 'raw_9', review_status: 'rejected' } })

    render(
      <MemoryRouter>
        <SoberLivingDirectoryReview />
      </MemoryRouter>
    )

    expect(await screen.findByText('Rejectable Raw')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Reject/i }))

    await waitFor(() => {
      expect(api.rejectRawRecord).toHaveBeenCalledWith('raw_9', expect.any(Object))
    })
  })
})
