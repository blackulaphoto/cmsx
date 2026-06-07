// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import SoberLivingDirectory from '../src/pages/SoberLivingDirectory'
import SoberLivingDirectoryDiscovery, { DiscoveryPageErrorBoundary } from '../src/pages/SoberLivingDirectoryDiscovery'
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
  searchLive: vi.fn(),
  getReviewQueue: vi.fn(),
  createListing: vi.fn(),
  getListing: vi.fn(),
  updateListing: vi.fn(),
  verifyListing: vi.fn(),
  archiveListing: vi.fn(),
  createTask: vi.fn(),
  updateTask: vi.fn(),
  listSources: vi.fn(),
  createSource: vi.fn(),
  updateSource: vi.fn(),
  listDiscoveryJobs: vi.fn(),
  createDiscoveryJob: vi.fn(),
  updateDiscoveryJob: vi.fn(),
  updateDiscoveryJobSchedule: vi.fn(),
  listDiscoveryRuns: vi.fn(),
  getDiscoveryRun: vi.fn(),
  runDiscoveryJob: vi.fn(),
  listSchedulerPreview: vi.fn(),
  getSchedulerStatus: vi.fn(),
  startSchedulerWorker: vi.fn(),
  stopSchedulerWorker: vi.fn(),
  runSchedulerOnce: vi.fn(),
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

  it('renders a search-first directory page, shows saved results, and supports manual creation', async () => {
    api.listListings.mockResolvedValue({
      listings: [
        {
          listing_id: 'sld_1',
          name: 'Oak Recovery House',
          city: 'Los Angeles',
          state: 'CA',
          zip_code: '90012',
          phone: '555-111-2222',
          website: 'https://oak.example.com',
          population_served: 'Men',
          certification_status: 'Certified',
          certification_body: 'CCAPP',
          last_verified_date: null,
          status: 'pending_review',
          trust_score: 50,
          accepts_mat: true,
          accepts_insurance: true,
          deposit_required: true,
        },
        {
          listing_id: 'sld_2',
          name: 'Beacon Women House',
          city: 'Long Beach',
          state: 'CA',
          zip_code: '90802',
          phone: '555-333-4444',
          website: 'https://beacon.example.com',
          population_served: 'Women',
          certification_status: 'Listed',
          certification_body: 'Sober Living Network',
          last_verified_date: '2030-01-01T00:00:00',
          status: 'approved',
          trust_score: 70,
          accepts_mat: false,
          accepts_insurance: false,
          deposit_required: false,
        },
      ],
    })
    api.createListing.mockResolvedValue({ success: true, listing: { listing_id: 'sld_2' } })

    render(
      <MemoryRouter>
        <SoberLivingDirectory />
      </MemoryRouter>
    )

    expect(await screen.findByText('Oak Recovery House')).toBeTruthy()
    expect(screen.getByText('Search sober livings like a live research tool')).toBeTruthy()
    expect(screen.getByRole('link', { name: /Admin \/ Advanced/i }).getAttribute('href')).toBe('/sober-living-directory/discovery')
    expect(screen.getByRole('button', { name: /Search Directory \+ Web/i })).toBeTruthy()
    expect(screen.getByLabelText('City or location')).toBeTruthy()
    expect(screen.getByLabelText('Verification status')).toBeTruthy()

    fireEvent.change(screen.getByLabelText('Population'), { target: { value: 'Women' } })
    expect(await screen.findByText('Beacon Women House')).toBeTruthy()
    expect(screen.queryByText('Oak Recovery House')).toBeNull()

    fireEvent.change(screen.getByLabelText('Funding'), { target: { value: 'no_deposit' } })
    expect(screen.getByText('Beacon Women House')).toBeTruthy()

    fireEvent.change(screen.getByLabelText('Verification status'), { target: { value: 'use_caution' } })
    expect(await screen.findByText(/No saved directory listings match this search yet/i)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Add Listing/i }))
    const createHeading = screen.getByText('Add a sober living listing')
    const createSection = createHeading.closest('section')
    const createForm = createHeading.closest('section')?.querySelector('form')
    fireEvent.change(within(createSection).getByLabelText('Name'), { target: { value: 'Beacon Women House' } })
    fireEvent.change(within(createSection).getByLabelText('City'), { target: { value: 'Long Beach' } })
    fireEvent.submit(createForm)

    await waitFor(() => {
      expect(api.createListing).toHaveBeenCalled()
    })
  })

  it('shows live external results immediately and lets a case manager save one to the directory', async () => {
    api.listListings
      .mockResolvedValueOnce({ listings: [] })
      .mockResolvedValueOnce({
        listings: [
          {
            listing_id: 'sld_saved_ccapp',
            name: 'CCAPP Recovery Residence Alpha',
            city: 'Los Angeles',
            state: 'CA',
            phone: '555-900-1212',
            website: 'https://ccapp.example.com/alpha',
            status: 'pending_review',
            trust_score: 55,
            accepts_mat: true,
            accepts_insurance: false,
            deposit_required: true,
            certification_body: 'CCAPP',
            certification_status: 'Certified',
            notes: 'Saved from live search',
          },
        ],
      })
    api.searchLive.mockResolvedValue({
      external_results: [
        {
          result_id: 'live_ccapp_alpha',
          source_key: 'ccapp',
          source_label: 'CCAPP Result',
          source_name: 'CCAPP Recovery Residences',
          name: 'CCAPP Recovery Residence Alpha',
          city: 'Los Angeles',
          state: 'CA',
          phone: '555-900-1212',
          website: 'https://ccapp.example.com/alpha',
          source_url: 'https://ccapp.example.com/alpha',
          snippet: 'Certified recovery residence in Los Angeles.',
          certification_body: 'CCAPP',
          certification_status: 'Certified',
          verification_method: 'certification_directory',
          source_urls_json: ['https://ccapp.example.com/alpha'],
        },
        {
          result_id: 'live_oxford_beta',
          source_key: 'oxford',
          source_label: 'Oxford Result',
          source_name: 'Oxford House',
          name: 'Oxford House - Beta',
          city: 'Los Angeles',
          state: 'CA',
          phone: '555-777-3333',
          website: null,
          source_url: 'https://www.oxfordvacancies.com/',
          snippet: 'Public recovery housing listing with open vacancies.',
          verification_method: 'public_directory',
          source_urls_json: ['https://www.oxfordvacancies.com/'],
        },
      ],
    })
    api.createListing.mockResolvedValue({
      listing: { listing_id: 'sld_saved_ccapp' },
    })

    render(
      <MemoryRouter>
        <SoberLivingDirectory />
      </MemoryRouter>
    )

    expect(await screen.findByText('Run a search to pull live external results onto this page.')).toBeTruthy()

    fireEvent.change(screen.getByLabelText('City or location'), { target: { value: 'Los Angeles, CA' } })
    fireEvent.click(screen.getByRole('button', { name: /Search Directory \+ Web/i }))

    await waitFor(() => {
      expect(api.searchLive).toHaveBeenCalledWith({
        query: 'Los Angeles, CA',
        city: 'Los Angeles',
        state: 'CA',
        zip_code: '',
        sources: ['ccapp', 'oxford'],
      })
    })
    expect(await screen.findByText('CCAPP Recovery Residence Alpha')).toBeTruthy()
    expect(screen.getByText('Oxford House - Beta')).toBeTruthy()
    expect(screen.getAllByText(/CCAPP Result/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Oxford Result/i).length).toBeGreaterThan(0)

    const externalCards = screen.getAllByText('CCAPP Recovery Residence Alpha')
    const externalCard = externalCards[externalCards.length - 1].closest('article')
    fireEvent.click(within(externalCard).getByRole('button', { name: /Add Note/i }))
    fireEvent.change(within(externalCard).getByPlaceholderText(/Case manager note/i), { target: { value: 'Called and got a callback.' } })
    fireEvent.click(within(externalCard).getByRole('button', { name: /Save to Directory/i }))

    await waitFor(() => {
      expect(api.createListing).toHaveBeenCalledWith(expect.objectContaining({
        name: 'CCAPP Recovery Residence Alpha',
        city: 'Los Angeles',
        state: 'CA',
        notes: expect.stringContaining('Called and got a callback.'),
      }))
    })
    expect((await screen.findAllByText('CCAPP Recovery Residence Alpha')).length).toBeGreaterThan(0)
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

  it('renders discovery controls, creates source and job, runs discovery, and shows review links', async () => {
    api.listSources
      .mockResolvedValueOnce({
        sources: [
          {
            source_id: 'src_ccapp',
            source_name: 'CCAPP Recovery Residences',
            source_type: 'certification_directory',
            base_url: 'https://ccapprecoveryresidences.org/search/',
            trust_level: 'high',
            supports_api: false,
            supports_scraping: true,
            requires_manual_review: true,
            is_active: true,
            last_checked_at: '2030-01-01T00:00:00',
          },
        ],
      })
      .mockResolvedValue({
        sources: [
          {
            source_id: 'src_new',
            source_name: 'Manual Source',
            source_type: 'manual',
            base_url: 'https://example.com',
            trust_level: 'medium',
            supports_api: false,
            supports_scraping: false,
            requires_manual_review: true,
            is_active: true,
            last_checked_at: null,
          },
        ],
      })
      .mockResolvedValueOnce({
        sources: [
          {
            source_id: 'src_new',
            source_name: 'Manual Source',
            source_type: 'manual',
            base_url: 'https://example.com',
            trust_level: 'medium',
            supports_api: false,
            supports_scraping: false,
            requires_manual_review: true,
            is_active: true,
            last_checked_at: null,
          },
          {
            source_id: 'src_ccapp',
            source_name: 'CCAPP Recovery Residences',
            source_type: 'certification_directory',
            base_url: 'https://ccapprecoveryresidences.org/search/',
            trust_level: 'high',
            supports_api: false,
            supports_scraping: true,
            requires_manual_review: true,
            is_active: true,
            last_checked_at: '2030-01-01T00:00:00',
          },
        ],
      })
      .mockResolvedValueOnce({
        sources: [
          {
            source_id: 'src_new',
            source_name: 'Manual Source',
            source_type: 'manual',
            base_url: 'https://example.com',
            trust_level: 'medium',
            supports_api: false,
            supports_scraping: false,
            requires_manual_review: true,
            is_active: true,
            last_checked_at: null,
          },
        ],
      })
    api.listDiscoveryJobs
      .mockResolvedValueOnce({
        jobs: [
          {
            job_id: 'job_1',
            source_id: 'src_ccapp',
            source_name: 'CCAPP Recovery Residences',
            job_name: 'CCAPP Sacramento Run',
            job_type: 'scheduled_source_check',
            target_city: 'Sacramento',
            target_state: 'CA',
            query: 'recovery residence',
            is_active: true,
            last_run_at: null,
            next_run_at: null,
          },
        ],
      })
      .mockResolvedValue({
        jobs: [
          {
            job_id: 'job_new',
            source_id: 'src_new',
            source_name: 'Manual Source',
            job_name: 'Manual Discovery Job',
            job_type: 'manual_test',
            target_city: 'Los Angeles',
            target_state: 'CA',
            query: 'test',
            is_active: true,
            last_run_at: '2030-01-02T00:00:00',
            next_run_at: null,
          },
        ],
      })
      .mockResolvedValueOnce({
        jobs: [
          {
            job_id: 'job_new',
            source_id: 'src_new',
            source_name: 'Manual Source',
            job_name: 'Manual Discovery Job',
            job_type: 'manual_test',
            target_city: 'Los Angeles',
            target_state: 'CA',
            query: 'test',
            is_active: true,
            last_run_at: null,
            next_run_at: null,
          },
          {
            job_id: 'job_1',
            source_id: 'src_ccapp',
            source_name: 'CCAPP Recovery Residences',
            job_name: 'CCAPP Sacramento Run',
            job_type: 'scheduled_source_check',
            target_city: 'Sacramento',
            target_state: 'CA',
            query: 'recovery residence',
            is_active: true,
            last_run_at: null,
            next_run_at: null,
          },
        ],
      })
      .mockResolvedValueOnce({
        jobs: [
          {
            job_id: 'job_new',
            source_id: 'src_new',
            source_name: 'Manual Source',
            job_name: 'Manual Discovery Job',
            job_type: 'manual_test',
            target_city: 'Los Angeles',
            target_state: 'CA',
            query: 'test',
            is_active: true,
            last_run_at: '2030-01-02T00:00:00',
            next_run_at: null,
          },
        ],
      })
    api.listDiscoveryRuns
      .mockResolvedValueOnce({
        runs: [
          {
            run_id: 'run_1',
            job_id: 'job_1',
            job_name: 'CCAPP Sacramento Run',
            source_id: 'src_ccapp',
            source_name: 'CCAPP Recovery Residences',
            started_at: '2030-01-01T00:00:00',
            finished_at: '2030-01-01T00:01:00',
            status: 'completed',
            records_found: 6,
            raw_records_created: 6,
            duplicates_detected: 1,
            errors_count: 0,
            error_message: null,
            notes: 'Connector run completed.',
          },
        ],
      })
      .mockResolvedValue({
        runs: [
          {
            run_id: 'run_2',
            job_id: 'job_new',
            job_name: 'Manual Discovery Job',
            source_id: 'src_new',
            source_name: 'Manual Source',
            started_at: '2030-01-02T00:00:00',
            finished_at: '2030-01-02T00:01:00',
            status: 'completed',
            records_found: 2,
            raw_records_created: 2,
            duplicates_detected: 0,
            errors_count: 0,
            error_message: null,
            notes: 'Manual run completed.',
          },
        ],
      })
      .mockResolvedValueOnce({
        runs: [
          {
            run_id: 'run_1',
            job_id: 'job_1',
            job_name: 'CCAPP Sacramento Run',
            source_id: 'src_ccapp',
            source_name: 'CCAPP Recovery Residences',
            started_at: '2030-01-01T00:00:00',
            finished_at: '2030-01-01T00:01:00',
            status: 'completed',
            records_found: 6,
            raw_records_created: 6,
            duplicates_detected: 1,
            errors_count: 0,
            error_message: null,
            notes: 'Connector run completed.',
          },
        ],
      })
      .mockResolvedValueOnce({
        runs: [
          {
            run_id: 'run_2',
            job_id: 'job_new',
            job_name: 'Manual Discovery Job',
            source_id: 'src_new',
            source_name: 'Manual Source',
            started_at: '2030-01-02T00:00:00',
            finished_at: '2030-01-02T00:01:00',
            status: 'completed',
            records_found: 2,
            raw_records_created: 2,
            duplicates_detected: 0,
            errors_count: 0,
            error_message: null,
            notes: 'Manual run completed.',
          },
        ],
      })
    api.listSchedulerPreview
      .mockResolvedValueOnce({
        jobs: [
          {
            job_id: 'job_1',
            source_id: 'src_ccapp',
            source_name: 'CCAPP Recovery Residences',
            job_name: 'CCAPP Sacramento Run',
            schedule_enabled: false,
            schedule_frequency: 'manual_only',
            next_scheduled_run_at: null,
            last_scheduled_run_at: null,
            last_run_status: null,
            consecutive_failures: 0,
            due: false,
            can_run: false,
            blocked_reason: 'schedule_disabled',
            max_runs_per_day: 1,
            scheduled_runs_today: 0,
          },
        ],
      })
      .mockResolvedValue({
        jobs: [
          {
            job_id: 'job_new',
            source_id: 'src_new',
            source_name: 'Manual Source',
            job_name: 'Manual Discovery Job',
            schedule_enabled: true,
            schedule_frequency: 'daily',
            next_scheduled_run_at: '2030-01-03T00:00:00',
            last_scheduled_run_at: null,
            last_run_status: 'completed',
            consecutive_failures: 0,
            due: false,
            can_run: false,
            blocked_reason: 'not_due',
            max_runs_per_day: 1,
            scheduled_runs_today: 0,
          },
        ],
      })
      .mockResolvedValueOnce({
        jobs: [
          {
            job_id: 'job_1',
            source_id: 'src_ccapp',
            source_name: 'CCAPP Recovery Residences',
            job_name: 'CCAPP Sacramento Run',
            schedule_enabled: true,
            schedule_frequency: 'daily',
            next_scheduled_run_at: '2030-01-03T00:00:00',
            last_scheduled_run_at: null,
            last_run_status: null,
            consecutive_failures: 0,
            due: false,
            can_run: false,
            blocked_reason: 'not_due',
            max_runs_per_day: 1,
            scheduled_runs_today: 0,
          },
          {
            job_id: 'job_new',
            source_id: 'src_new',
            source_name: 'Manual Source',
            job_name: 'Manual Discovery Job',
            schedule_enabled: false,
            schedule_frequency: 'manual_only',
            next_scheduled_run_at: null,
            last_scheduled_run_at: null,
            last_run_status: null,
            consecutive_failures: 0,
            due: false,
            can_run: false,
            blocked_reason: 'schedule_disabled',
            max_runs_per_day: 1,
            scheduled_runs_today: 0,
          },
        ],
      })
      .mockResolvedValueOnce({
        jobs: [
          {
            job_id: 'job_new',
            source_id: 'src_new',
            source_name: 'Manual Source',
            job_name: 'Manual Discovery Job',
            schedule_enabled: true,
            schedule_frequency: 'daily',
            next_scheduled_run_at: '2030-01-03T00:00:00',
            last_scheduled_run_at: null,
            last_run_status: null,
            consecutive_failures: 0,
            due: false,
            can_run: false,
            blocked_reason: 'not_due',
            max_runs_per_day: 1,
            scheduled_runs_today: 0,
          },
        ],
      })
    api.createSource.mockResolvedValue({
      source: {
        source_id: 'src_new',
        source_name: 'Manual Source',
        source_type: 'manual',
        base_url: 'https://example.com',
        trust_level: 'medium',
        supports_api: false,
        supports_scraping: false,
        requires_manual_review: true,
        is_active: true,
        last_checked_at: null,
      },
    })
    api.createDiscoveryJob.mockResolvedValue({
      job: {
        job_id: 'job_new',
        source_id: 'src_new',
        source_name: 'Manual Source',
        job_name: 'Manual Discovery Job',
        job_type: 'manual_test',
        target_city: 'Los Angeles',
        target_state: 'CA',
        query: 'test',
        is_active: true,
        last_run_at: null,
        next_run_at: null,
      },
    })
    api.runDiscoveryJob.mockResolvedValue({
      run: {
        run_id: 'run_2',
        status: 'completed',
        records_found: 2,
        raw_records_created: 2,
        duplicates_detected: 0,
        errors_count: 0,
      },
    })
    api.updateDiscoveryJobSchedule.mockResolvedValue({
      job: {
        job_id: 'job_1',
        schedule_enabled: true,
      },
    })
    api.getSchedulerStatus.mockResolvedValue({
      scheduler: {
        running: false,
        autostart_enabled: false,
        poll_interval_seconds: 300,
        max_jobs_per_cycle: 3,
        started_at: null,
        stopped_at: null,
        last_poll_at: null,
        last_cycle_started_at: null,
        last_cycle_finished_at: null,
        current_job_id: null,
        current_job_name: null,
        last_cycle_summary: {
          checked_jobs: 0,
          due_jobs: 0,
          executed_jobs: 0,
          failed_jobs: 0,
          skipped_jobs: 0,
          trigger: null,
        },
        warning: 'Scheduler worker is disabled by default.',
      },
    })
    api.startSchedulerWorker.mockResolvedValue({
      scheduler: {
        running: true,
        autostart_enabled: false,
        poll_interval_seconds: 300,
        max_jobs_per_cycle: 3,
        last_cycle_summary: { checked_jobs: 0, due_jobs: 0, executed_jobs: 0, failed_jobs: 0, skipped_jobs: 0, trigger: null },
      },
    })
    api.runSchedulerOnce.mockResolvedValue({
      scheduler: {
        running: false,
        autostart_enabled: false,
        poll_interval_seconds: 300,
        max_jobs_per_cycle: 3,
        last_cycle_summary: { checked_jobs: 2, due_jobs: 1, executed_jobs: 1, failed_jobs: 0, skipped_jobs: 1, trigger: 'manual_tick' },
      },
    })

    render(
      <MemoryRouter>
        <SoberLivingDirectoryDiscovery />
      </MemoryRouter>
    )

    expect(await screen.findByText('Discovery Sources')).toBeTruthy()
    expect(screen.getByText(/Scheduling is configured here but no autonomous runner is active yet/i)).toBeTruthy()
    expect(screen.getByText('Scheduling Eligibility Preview')).toBeTruthy()
    expect(screen.getByText('Runtime Controls')).toBeTruthy()
    expect(screen.getAllByText('CCAPP Recovery Residences').length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: /Open Review Queue/i })[0].getAttribute('href')).toBe('/sober-living-directory/review')

    fireEvent.click(screen.getByRole('button', { name: /Start Worker/i }))
    await waitFor(() => {
      expect(api.startSchedulerWorker).toHaveBeenCalled()
    })

    fireEvent.click(screen.getByRole('button', { name: /Poll Once/i }))
    await waitFor(() => {
      expect(api.runSchedulerOnce).toHaveBeenCalled()
    })

    fireEvent.change(screen.getByLabelText('Source Name'), { target: { value: 'Manual Source' } })
    fireEvent.change(screen.getByLabelText('Base URL'), { target: { value: 'https://example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /Create Source/i }))

    await waitFor(() => {
      expect(api.createSource).toHaveBeenCalled()
    })

    const sourceSelects = screen.getAllByLabelText('Source')
    fireEvent.change(sourceSelects[0], { target: { value: 'src_new' } })
    fireEvent.change(screen.getByLabelText('Job Name'), { target: { value: 'Manual Discovery Job' } })
    fireEvent.change(screen.getByLabelText('Query'), { target: { value: 'test' } })
    fireEvent.change(screen.getByLabelText('Target City'), { target: { value: 'Los Angeles' } })
    fireEvent.click(screen.getByRole('button', { name: /Create Job/i }))

    await waitFor(() => {
      expect(api.createDiscoveryJob).toHaveBeenCalled()
    })

    expect((await screen.findAllByText('Manual Discovery Job')).length).toBeGreaterThan(0)
    const runButtons = await screen.findAllByRole('button', { name: /Run Discovery/i })
    const runButton = runButtons.find((button) => within(button.closest('article')).queryByText('Manual Discovery Job'))
    const newJobCard = runButton.closest('article')
    fireEvent.change(within(newJobCard).getByLabelText('Frequency'), { target: { value: 'daily' } })
    fireEvent.click(within(newJobCard).getByRole('button', { name: /Save Schedule Settings/i }))

    await waitFor(() => {
      expect(api.updateDiscoveryJobSchedule).toHaveBeenCalledWith('job_new', expect.objectContaining({
        schedule_enabled: false,
        schedule_frequency: 'daily',
      }))
    })

    expect((await screen.findAllByText('Manual Discovery Job')).length).toBeGreaterThan(0)
    const refreshedRunButtons = await screen.findAllByRole('button', { name: /Run Discovery/i })
    const refreshedRunButton = refreshedRunButtons.find((button) => within(button.closest('article')).queryByText('Manual Discovery Job'))
    fireEvent.click(refreshedRunButton)

    await waitFor(() => {
      expect(api.runDiscoveryJob).toHaveBeenCalledWith('job_new')
    })

    expect(await screen.findByText(/Records found: 2/i)).toBeTruthy()
  })

  it('blocks invalid custom-hours schedule settings on the discovery page', async () => {
    api.listSources.mockResolvedValue({ sources: [] })
    api.listDiscoveryJobs.mockResolvedValue({
      jobs: [
        {
          job_id: 'job_sched',
          source_id: 'src_sched',
          source_name: 'Schedule Source',
          job_name: 'Schedule Test Job',
          job_type: 'scheduled_source_check',
          target_city: 'Sacramento',
          target_state: 'CA',
          query: '',
          is_active: true,
          schedule_enabled: true,
          schedule_frequency: 'custom_hours',
          schedule_interval_hours: '',
          max_runs_per_day: 1,
          schedule_timezone: 'America/Los_Angeles',
          auto_disable_after_failures: 3,
          last_run_at: null,
          next_run_at: null,
        },
      ],
    })
    api.listDiscoveryRuns.mockResolvedValue({ runs: [] })
    api.listSchedulerPreview.mockResolvedValue({
      jobs: [
        {
          job_id: 'job_sched',
          source_id: 'src_sched',
          source_name: 'Schedule Source',
          job_name: 'Schedule Test Job',
          schedule_enabled: true,
          schedule_frequency: 'custom_hours',
          next_scheduled_run_at: null,
          last_scheduled_run_at: null,
          last_run_status: null,
          consecutive_failures: 0,
          due: false,
          can_run: false,
          blocked_reason: 'not_due',
          max_runs_per_day: 1,
          scheduled_runs_today: 0,
        },
      ],
    })
    api.getSchedulerStatus.mockResolvedValue({
      scheduler: {
        running: false,
        autostart_enabled: false,
        poll_interval_seconds: 300,
        max_jobs_per_cycle: 3,
        last_cycle_summary: { checked_jobs: 0, due_jobs: 0, executed_jobs: 0, failed_jobs: 0, skipped_jobs: 0, trigger: null },
      },
    })

    render(
      <MemoryRouter>
        <SoberLivingDirectoryDiscovery />
      </MemoryRouter>
    )

    expect((await screen.findAllByText('Schedule Test Job')).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: /Save Schedule Settings/i }))

    await waitFor(() => {
      expect(api.updateDiscoveryJobSchedule).not.toHaveBeenCalled()
    })
  })

  it('renders empty states on the discovery page when all collections are empty', async () => {
    api.listSources.mockResolvedValue({ sources: [] })
    api.listDiscoveryJobs.mockResolvedValue({ jobs: [] })
    api.listDiscoveryRuns.mockResolvedValue({ runs: [] })
    api.listSchedulerPreview.mockResolvedValue({ jobs: [] })
    api.getSchedulerStatus.mockResolvedValue({
      scheduler: {
        running: false,
        autostart_enabled: false,
        poll_interval_seconds: 300,
        max_jobs_per_cycle: 3,
        last_cycle_summary: { checked_jobs: 0, due_jobs: 0, executed_jobs: 0, failed_jobs: 0, skipped_jobs: 0, trigger: null },
      },
    })

    render(
      <MemoryRouter>
        <SoberLivingDirectoryDiscovery />
      </MemoryRouter>
    )

    expect(await screen.findByText('Sober Living Discovery Controls')).toBeTruthy()
    expect(await screen.findByText('No discovery sources configured yet.')).toBeTruthy()
    expect(screen.getByText('No discovery jobs configured yet.')).toBeTruthy()
    expect(screen.getByText('No discovery runs have been recorded yet.')).toBeTruthy()
    expect(screen.getByText('No discovery jobs are available for scheduler preview yet.')).toBeTruthy()
  })

  it('renders section-level errors without blanking the discovery page when one endpoint fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    api.listSources.mockResolvedValue({ sources: [] })
    api.listDiscoveryJobs.mockResolvedValue({ jobs: [] })
    api.listDiscoveryRuns.mockRejectedValue(new Error('HTTP 500'))
    api.listSchedulerPreview.mockResolvedValue({ jobs: [] })
    api.getSchedulerStatus.mockResolvedValue({
      scheduler: {
        running: false,
        autostart_enabled: false,
        poll_interval_seconds: 300,
        max_jobs_per_cycle: 3,
        last_cycle_summary: { checked_jobs: 0, due_jobs: 0, executed_jobs: 0, failed_jobs: 0, skipped_jobs: 0, trigger: null },
      },
    })

    render(
      <MemoryRouter>
        <SoberLivingDirectoryDiscovery />
      </MemoryRouter>
    )

    expect(await screen.findByText('Sober Living Discovery Controls')).toBeTruthy()
    expect(await screen.findByText('Some discovery sections could not load')).toBeTruthy()
    expect(screen.getByText('Run history unavailable')).toBeTruthy()
    expect(screen.getByText('HTTP 500')).toBeTruthy()
    expect(screen.getByText('No discovery sources configured yet.')).toBeTruthy()
    consoleErrorSpy.mockRestore()
  })

  it('renders visible auth or API errors when all discovery endpoints fail', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    api.listSources.mockRejectedValue(new Error('HTTP 401'))
    api.listDiscoveryJobs.mockRejectedValue(new Error('HTTP 401'))
    api.listDiscoveryRuns.mockRejectedValue(new Error('HTTP 401'))
    api.listSchedulerPreview.mockRejectedValue(new Error('HTTP 401'))
    api.getSchedulerStatus.mockRejectedValue(new Error('HTTP 401'))

    render(
      <MemoryRouter>
        <SoberLivingDirectoryDiscovery />
      </MemoryRouter>
    )

    expect(await screen.findByText('Sober Living Discovery Controls')).toBeTruthy()
    expect(await screen.findByText(/authentication or API access failure/i)).toBeTruthy()
    expect(screen.getByText('Source registry unavailable')).toBeTruthy()
    expect(screen.getByText('Discovery jobs unavailable')).toBeTruthy()
    expect(screen.getByText('Run history unavailable')).toBeTruthy()
    expect(screen.getByText('Scheduler preview unavailable')).toBeTruthy()
    expect(screen.getByText('Scheduler controls unavailable')).toBeTruthy()
    consoleErrorSpy.mockRestore()
  })

  it('shows the route-level discovery error boundary when a child render throws', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const ThrowingChild = () => {
      throw new Error('render explosion')
    }

    render(
      <MemoryRouter>
        <DiscoveryPageErrorBoundary>
          <ThrowingChild />
        </DiscoveryPageErrorBoundary>
      </MemoryRouter>
    )

    expect(await screen.findByText('Discovery page failed to render')).toBeTruthy()
    expect(screen.getByText('render explosion')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Reload/i })).toBeTruthy()
    consoleErrorSpy.mockRestore()
  })

  it('shows discovery run failures on the discovery page', async () => {
    api.listSources.mockResolvedValue({ sources: [] })
    api.listDiscoveryJobs.mockResolvedValue({
      jobs: [
        {
          job_id: 'job_fail',
          source_id: 'src_fail',
          source_name: 'Broken Source',
          job_name: 'Broken Run',
          job_type: 'scheduled_source_check',
          target_city: 'Los Angeles',
          target_state: 'CA',
          query: '',
          is_active: true,
          last_run_at: null,
          next_run_at: null,
        },
      ],
    })
    api.listDiscoveryRuns.mockResolvedValue({ runs: [] })
    api.listSchedulerPreview.mockResolvedValue({
      jobs: [
        {
          job_id: 'job_fail',
          source_id: 'src_fail',
          source_name: 'Broken Source',
          job_name: 'Broken Run',
          schedule_enabled: false,
          schedule_frequency: 'manual_only',
          next_scheduled_run_at: null,
          last_scheduled_run_at: null,
          last_run_status: null,
          consecutive_failures: 0,
          due: false,
          can_run: false,
          blocked_reason: 'schedule_disabled',
          max_runs_per_day: 1,
          scheduled_runs_today: 0,
        },
      ],
    })
    api.getSchedulerStatus.mockResolvedValue({
      scheduler: {
        running: false,
        autostart_enabled: false,
        poll_interval_seconds: 300,
        max_jobs_per_cycle: 3,
        last_cycle_summary: { checked_jobs: 0, due_jobs: 0, executed_jobs: 0, failed_jobs: 0, skipped_jobs: 0, trigger: null },
      },
    })
    api.runDiscoveryJob.mockRejectedValue(new Error('Connector failed'))

    render(
      <MemoryRouter>
        <SoberLivingDirectoryDiscovery />
      </MemoryRouter>
    )

    expect((await screen.findAllByText('Broken Run')).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: /Run Discovery/i }))

    expect(await screen.findByText('Connector failed')).toBeTruthy()
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
            normalized_preview: {
              notes: 'State set from the manual discovery job target because the visible Oxford grid row does not expose a state column: CA.',
            },
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
        notes: 'State set from the manual discovery job target because the visible Oxford grid row does not expose a state column: CA.',
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
    expect(screen.getByText(/State shown here was inferred from the manual discovery job target/i)).toBeTruthy()
    expect(screen.getByText(/1 duplicate candidate/i)).toBeTruthy()
    const rawRecordCard = screen.getByText('Raw Discovery Home').closest('article')
    fireEvent.click(within(rawRecordCard).getByRole('button', { name: /View Details/i }))

    await waitFor(() => {
      expect(api.getRawRecord).toHaveBeenCalledWith('raw_1')
    })

    expect(await screen.findByText('Normalized Preview')).toBeTruthy()
    expect(screen.getByText(/Source state was inferred from the manual job target/i)).toBeTruthy()
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
