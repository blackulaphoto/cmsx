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
 */
export const openClientDocument = async (endpoint) => {
  const { objectUrl } = await fetchClientDocumentObjectUrl(endpoint)
  let opened = null
  if (typeof window !== 'undefined' && typeof window.open === 'function') {
    opened = window.open(objectUrl, '_blank', 'noopener,noreferrer')
  }
  if (typeof URL !== 'undefined' && URL.revokeObjectURL) {
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60000)
  }
  return Boolean(opened)
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
