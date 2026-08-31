/**
 * Authenticated client-document file access.
 *
 * Protected document routes (e.g. `/api/clients/{id}/documents/{doc_id}/view`)
 * require the Firebase bearer token. A raw `<a href>`, `<img src>`, `<iframe src>`,
 * or `window.open(url)` performs a plain browser navigation that does NOT carry
 * that header, so the backend responds with `{"detail":"Missing Firebase bearer
 * token"}`. These helpers fetch the file through the authenticated `apiFetch`
 * (which attaches the token), turn the response into a blob object URL, and let
 * the caller preview, open, or download it from the authenticated session.
 */
import { apiFetch } from '../api/config'

const FILENAME_RE = /filename\*?=(?:UTF-8'')?["']?([^"';]+)/i
const EXTERNAL_URL_RE = /^https?:\/\//i

const filenameFromResponse = (response) => {
  const disposition = (response?.headers?.get?.('content-disposition')) || ''
  const match = FILENAME_RE.exec(disposition)
  if (match && match[1]) {
    try {
      return decodeURIComponent(match[1])
    } catch {
      return match[1]
    }
  }
  return ''
}

/**
 * Fetch a protected document and return a blob object URL plus a best-effort
 * filename. The caller owns the returned `objectUrl` and must revoke it with
 * `URL.revokeObjectURL` once it is no longer needed.
 */
export const fetchClientDocumentObjectUrl = async (endpoint) => {
  const response = await apiFetch(endpoint)
  if (!response || !response.ok) {
    const status = response?.status || 0
    throw new Error(`Failed to load document (HTTP ${status})`)
  }
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  return { objectUrl, blob, filename: filenameFromResponse(response) }
}

export const isExternalClientDocumentUrl = (url) => EXTERNAL_URL_RE.test(String(url || '').trim())

export const isProtectedClientDocument = (doc) =>
  Boolean(doc?.doc_id) && !isExternalClientDocumentUrl(doc?.url)

/**
 * Open a protected document in a new tab using an authenticated blob URL.
 * Returns true when a window was opened. The object URL is revoked after a
 * delay so the new tab has time to load it.
 *
 * Browsers only honor `window.open()` as a direct result of a user gesture
 * (a click) when it runs *before* the call stack yields - once an `await`
 * happens first, the browser can no longer tell the popup was requested by
 * the click that's still on screen, and silently blocks it (`window.open`
 * then returns `null`). This function used to `await` the document fetch
 * before calling `window.open(objectUrl, ...)`, so real browsers blocked
 * every call - the fetch itself succeeded (200), which is why this looked
 * like generation/persistence/auth all working while "View" still failed.
 * Opening a blank tab synchronously first, then navigating it once the
 * fetch resolves, keeps the call inside the user-gesture window.
 */
export const openClientDocument = async (endpoint) => {
  const canOpenWindow = typeof window !== 'undefined' && typeof window.open === 'function'
  // Must happen before the first `await` below - see note above.
  const pendingWindow = canOpenWindow ? window.open('', '_blank', 'noopener,noreferrer') : null

  let objectUrl
  try {
    ;({ objectUrl } = await fetchClientDocumentObjectUrl(endpoint))
  } catch (error) {
    if (pendingWindow && !pendingWindow.closed) pendingWindow.close()
    throw error
  }

  if (pendingWindow && !pendingWindow.closed) {
    pendingWindow.location.href = objectUrl
  }
  if (typeof URL !== 'undefined' && URL.revokeObjectURL) {
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60000)
  }
  return Boolean(pendingWindow)
}

/**
 * Download a protected document with the correct filename (when the server
 * provides one) via an authenticated blob URL.
 */
export const downloadClientDocument = async (endpoint, fallbackName = 'document') => {
  const { objectUrl, filename } = await fetchClientDocumentObjectUrl(endpoint)
  const name = filename || fallbackName
  if (typeof document !== 'undefined') {
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = name
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
  }
  if (typeof URL !== 'undefined' && URL.revokeObjectURL) {
    setTimeout(() => URL.revokeObjectURL(objectUrl), 10000)
  }
  return name
}
