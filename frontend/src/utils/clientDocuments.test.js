// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../api/config', () => ({ apiFetch: vi.fn() }))

import { apiFetch } from '../api/config'
import { openClientDocument, downloadClientDocument, fetchClientDocumentObjectUrl } from './clientDocuments'

// Regression coverage for the production P1 where "View linked document" on
// a freshly-generated ROI form (and the equivalent actions in Documentation
// Center) failed with "Could not open document. Please try again." even
// though generation, persistence, auth, and the /view endpoint all returned
// 200. Root cause: openClientDocument awaited the authenticated document
// fetch *before* calling window.open(objectUrl, ...) - real browsers only
// honor window.open() as a direct result of a user gesture when it runs
// before the call stack yields, so by the time the fetch resolved the
// browser no longer associated the call with the click and silently
// blocked it (window.open returned null). A test double that makes
// window.open unconditionally "succeed" (e.g. `mockReturnValue({})`)
// can't detect this class of bug at all, so these tests assert the actual
// call order, not just the eventual outcome.

const buildResponse = (overrides = {}) => ({
  ok: true,
  status: 200,
  headers: { get: () => null },
  blob: async () => new Blob(['<html>hi</html>'], { type: 'text/html' }),
  ...overrides,
})

beforeEach(() => {
  vi.clearAllMocks()
  global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
  global.URL.revokeObjectURL = vi.fn()
})

describe('openClientDocument', () => {
  it('opens the tab synchronously, before the document fetch resolves (not after)', async () => {
    const callOrder = []
    let resolveFetch
    apiFetch.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = () => {
            callOrder.push('fetch-resolved')
            resolve(buildResponse())
          }
        }),
    )
    const fakeWindow = { closed: false, location: { href: '' } }
    const openSpy = vi.spyOn(window, 'open').mockImplementation((...args) => {
      callOrder.push('window-open')
      return fakeWindow
    })

    const openPromise = openClientDocument('/api/clients/c1/documents/d1/view')

    // window.open must already have been called before the fetch even
    // resolves - i.e. synchronously, in the same tick as the call.
    expect(openSpy).toHaveBeenCalledWith('', '_blank', 'noopener,noreferrer')
    expect(callOrder).toEqual(['window-open'])

    resolveFetch()
    const opened = await openPromise

    expect(callOrder).toEqual(['window-open', 'fetch-resolved'])
    expect(opened).toBe(true)
    expect(fakeWindow.location.href).toBe('blob:mock-url')
    // Only ever one window.open call - navigation happens via .location.href,
    // never a second window.open(url, ...) call after the fetch.
    expect(openSpy).toHaveBeenCalledTimes(1)
  })

  it('returns false and does not throw when the browser blocks the popup outright', async () => {
    apiFetch.mockResolvedValue(buildResponse())
    vi.spyOn(window, 'open').mockReturnValue(null)

    const opened = await openClientDocument('/api/clients/c1/documents/d1/view')

    expect(opened).toBe(false)
  })

  it('closes the pending blank tab and rethrows when the authenticated fetch fails', async () => {
    apiFetch.mockResolvedValue({ ok: false, status: 404 })
    const fakeWindow = { closed: false, location: { href: '' }, close: vi.fn() }
    vi.spyOn(window, 'open').mockReturnValue(fakeWindow)

    await expect(openClientDocument('/api/clients/c1/documents/d1/view')).rejects.toThrow()
    expect(fakeWindow.close).toHaveBeenCalled()
  })

  it('works the same way for a generated text/html document as for an uploaded file', async () => {
    // The bug reproduced regardless of file_mime - it was about gesture
    // timing, not content type. This just confirms the html-fallback case
    // (the actual document type from the production ROI repro) also opens.
    apiFetch.mockResolvedValue(
      buildResponse({ blob: async () => new Blob(['<html>ROI</html>'], { type: 'text/html' }) }),
    )
    const fakeWindow = { closed: false, location: { href: '' } }
    vi.spyOn(window, 'open').mockReturnValue(fakeWindow)

    const opened = await openClientDocument('/api/clients/c1/documents/roi-doc/view')

    expect(opened).toBe(true)
    expect(fakeWindow.location.href).toBe('blob:mock-url')
  })
})

describe('downloadClientDocument (unaffected by the window.open fix)', () => {
  it('still downloads via an anchor click, not window.open', async () => {
    apiFetch.mockResolvedValue(buildResponse())
    const openSpy = vi.spyOn(window, 'open')
    let downloadedName = null
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      downloadedName = this.download
    })

    await downloadClientDocument('/api/clients/c1/documents/d1/view', 'fallback.txt')

    expect(downloadedName).toBe('fallback.txt')
    expect(openSpy).not.toHaveBeenCalled()
  })
})

describe('fetchClientDocumentObjectUrl', () => {
  it('sends the request through the authenticated apiFetch helper, not a raw fetch', async () => {
    apiFetch.mockResolvedValue(buildResponse())

    await fetchClientDocumentObjectUrl('/api/clients/c1/documents/d1/view')

    expect(apiFetch).toHaveBeenCalledWith('/api/clients/c1/documents/d1/view')
  })

  it('throws a descriptive error on a non-ok response instead of returning a broken blob', async () => {
    apiFetch.mockResolvedValue({ ok: false, status: 401 })

    await expect(fetchClientDocumentObjectUrl('/api/clients/c1/documents/d1/view')).rejects.toThrow(/401/)
  })
})
