/**
 * API Configuration for Case Management Suite
 * Updated for new 9-database architecture
 */

import { auth } from '../lib/firebase'

// Base API URL - on Vercel browser runtime prefer same-origin /api rewrite
const configuredApiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
const configuredRailwayPublicUrl = (import.meta.env.VITE_RAILWAY_PUBLIC_URL || 'https://cmsx-production-088d.up.railway.app')
  .trim()
  .replace(/\/+$/, '')
const isVercelBrowserHost =
  typeof window !== 'undefined' && window.location.hostname.endsWith('.vercel.app')
const useSameOriginProxyOnVercel = isVercelBrowserHost && import.meta.env.VITE_FORCE_DIRECT_API !== '1'
export const API_BASE_URL = useSameOriginProxyOnVercel ? '' : configuredApiBaseUrl
const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 8000)
const isAbsoluteUrl = (endpoint) => /^https?:\/\//i.test(String(endpoint || ''))
export const apiUrl = (endpoint) => isAbsoluteUrl(endpoint) ? endpoint : `${API_BASE_URL}${endpoint}`
const frontendEnvironment = (
  import.meta.env.VITE_APP_ENV ||
  import.meta.env.VITE_ENVIRONMENT ||
  import.meta.env.MODE ||
  ''
).toLowerCase()
const isProductionLikeFrontend =
  frontendEnvironment === 'production' ||
  (typeof window !== 'undefined' && !['localhost', '127.0.0.1'].includes(window.location.hostname))
export const isFrontendTestAuthEnabled =
  import.meta.env.VITE_ENABLE_TEST_AUTH === 'true' && !isProductionLikeFrontend

const getTestAuthHeaders = () => {
  if (!isFrontendTestAuthEnabled) return {}
  return {
    'X-Test-Auth-User': import.meta.env.VITE_TEST_AUTH_USER || 'uid-e2e',
    'X-Test-Auth-Email': import.meta.env.VITE_TEST_AUTH_EMAIL || 'e2e.case.manager@example.com',
    'X-Test-Auth-Name': import.meta.env.VITE_TEST_AUTH_NAME || 'E2E Case Manager',
    'X-Test-Auth-Role': import.meta.env.VITE_TEST_AUTH_ROLE || 'admin',
    'X-Test-Auth-Case-Manager-Id': import.meta.env.VITE_TEST_AUTH_CASE_MANAGER || 'cm_e2e'
  }
}

const GATEWAY_RETRY_STATUS = new Set([502, 503, 504])

const isSafeMethod = (method) => {
  const normalized = (method || 'GET').toUpperCase()
  return normalized === 'GET' || normalized === 'HEAD'
}

const getDirectFallbackBase = () => {
  if (configuredApiBaseUrl) return configuredApiBaseUrl
  if (configuredRailwayPublicUrl) return configuredRailwayPublicUrl
  return ''
}

const shouldRetryDirect = (response, method) => {
  return useSameOriginProxyOnVercel && isSafeMethod(method) && GATEWAY_RETRY_STATUS.has(response.status)
}

const buildFallbackUrl = (endpoint) => {
  if (isAbsoluteUrl(endpoint)) return ''
  const base = getDirectFallbackBase()
  return base ? `${base}${endpoint}` : ''
}

export class ApiError extends Error {
  constructor(message, { status = 0, endpoint = '', data = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.endpoint = endpoint
    this.data = data
  }
}

const shouldUseJsonContentType = (body, headers) => {
  if (!body) return false
  if (typeof FormData !== 'undefined' && body instanceof FormData) return false
  if (typeof Blob !== 'undefined' && body instanceof Blob) return false
  if (typeof URLSearchParams !== 'undefined' && body instanceof URLSearchParams) return false
  const headerKeys = Object.keys(headers || {}).map((key) => key.toLowerCase())
  return !headerKeys.includes('content-type')
}

export const getFirebaseBearerToken = async ({ authUser = null, forceRefresh = false } = {}) => {
  const user = authUser || auth?.currentUser
  if (!user) return null
  return user.getIdToken(forceRefresh)
}

const buildHeaders = async (options = {}) => {
  const {
    headers: providedHeaders = {},
    authRequired = true,
    authUser = null,
    forceRefreshToken = false,
    body,
  } = options
  const token = authRequired
    ? await getFirebaseBearerToken({ authUser, forceRefresh: forceRefreshToken })
    : null
  if (authRequired && !token && !isFrontendTestAuthEnabled) {
    throw new ApiError('No Firebase user is signed in; cannot call protected API without a bearer token', {
      status: 401,
    })
  }
  const headers = {
    ...getTestAuthHeaders(),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...providedHeaders,
  }
  if (shouldUseJsonContentType(body, headers)) {
    headers['Content-Type'] = 'application/json'
  }
  return headers
}

const parseResponseBody = async (response) => {
  if (response.status === 204) return null
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json()
  }
  if (contentType.includes('application/pdf') || contentType.includes('application/octet-stream')) {
    return response.blob()
  }
  const text = await response.text()
  return text || null
}

const handleAuthFailure = (response, endpoint) => {
  if (response.status !== 401 && response.status !== 403) return
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('cmsx:api-auth-error', {
      detail: { status: response.status, endpoint }
    }))
  }
}

// API Endpoints for new 9-database architecture
export const API_ENDPOINTS = {
  // Core Clients (Master Database)
  clients: {
    getAll: '/api/clients',
    getById: (id) => `/api/clients/${id}`,
    create: '/api/clients',
    update: (id) => `/api/clients/${id}`,
    delete: (id) => `/api/clients/${id}`,
    addNote: (id) => `/api/clients/${id}/notes`
  },
  
  // AI Assistant (Full CRUD Access)
  ai: {
    getCompleteProfile: (clientId) => `/api/ai/clients/${clientId}/complete-profile`,
    createClient: '/api/ai/clients',
    updateAnyRecord: (database, table, recordId) => `/api/ai/${database}/${table}/${recordId}`,
    saveConversation: '/api/ai/conversations',
    updateAnalytics: (clientId) => `/api/ai/clients/${clientId}/analytics`
  },
  
  // Module-Specific Endpoints
  housing: {
    getClientData: (clientId) => `/api/housing/clients/${clientId}`,
    getInventory: '/api/housing/inventory',
    createApplication: '/api/housing/applications'
  },
  
  benefits: {
    getClientData: (clientId) => `/api/benefits/clients/${clientId}`,
    createApplication: '/api/benefits/applications',
    getAssessment: (clientId) => `/api/benefits/clients/${clientId}/assessment`
  },
  
  legal: {
    getClientData: (clientId) => `/api/legal/clients/${clientId}`,
    createCase: '/api/legal/cases',
    getExpungementEligibility: (clientId) => `/api/legal/clients/${clientId}/expungement`
  },
  
  employment: {
    getClientData: (clientId) => `/api/employment/clients/${clientId}`,
    createResume: '/api/employment/resumes',
    createJobApplication: '/api/employment/applications'
  },
  
  services: {
    getClientData: (clientId) => `/api/services/clients/${clientId}`,
    getProviders: '/api/services/providers',
    createReferral: '/api/services/referrals'
  },
  
  reminders: {
    getClientReminders: (clientId) => `/api/reminders/clients/${clientId}`,
    createReminder: '/api/reminders',
    updateReminder: (id) => `/api/reminders/${id}`
  },
  
  // System Endpoints
  system: {
    health: '/health',
    databaseStatus: '/api/system/database-status',
    accessMatrix: '/api/system/access-matrix'
  }
}

export const apiFetch = async (endpoint, options = {}) => {
  const {
    timeoutMs,
    authRequired,
    authUser,
    forceRefreshToken,
    ...fetchOptions
  } = options
  const effectiveTimeoutMs = Number(timeoutMs || API_TIMEOUT_MS)
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), effectiveTimeoutMs)
  try {
    const primaryUrl = apiUrl(endpoint)
    const headers = await buildHeaders({
      headers: fetchOptions.headers,
      authRequired,
      authUser,
      forceRefreshToken,
      body: fetchOptions.body,
    })
    let response = await fetch(primaryUrl, { ...fetchOptions, headers, signal: controller.signal })

    if (shouldRetryDirect(response, fetchOptions.method)) {
      const fallbackUrl = buildFallbackUrl(endpoint)
      if (fallbackUrl && fallbackUrl !== primaryUrl) {
        response = await fetch(fallbackUrl, { ...fetchOptions, headers, signal: controller.signal })
      }
    }

    handleAuthFailure(response, endpoint)
    return response
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new ApiError(`Request timeout after ${effectiveTimeoutMs}ms`, { endpoint })
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

// Helper function to make authenticated API calls and return parsed response bodies.
export const apiCall = async (endpoint, options = {}) => {
  try {
    const response = await apiFetch(endpoint, options)
    const data = await parseResponseBody(response)

    if (!response.ok) {
      const message = data?.detail || data?.message || data?.error || `HTTP ${response.status}`
      throw new ApiError(message, { status: response.status, endpoint, data })
    }

    return data
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    console.error(`API call failed: ${endpoint}`, error)
    throw new ApiError(error?.message || 'API request failed', { endpoint, data: error })
  }
}

export const apiRequest = apiCall

// Specific API functions for common operations
export const clientsAPI = {
  getAll: (module = 'case_management') => 
    apiCall(`${API_ENDPOINTS.clients.getAll}?module=${module}`),
    
  getById: (id, module = 'case_management') => 
    apiCall(`${API_ENDPOINTS.clients.getById(id)}?module=${module}`),
    
  create: (clientData, module = 'case_management') => 
    apiCall(`${API_ENDPOINTS.clients.create}?module=${module}`, {
      method: 'POST',
      body: JSON.stringify(clientData)
    }),
    
  update: (id, updates, module = 'case_management') => 
    apiCall(`${API_ENDPOINTS.clients.update(id)}?module=${module}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    }),
    
  addNote: (id, noteData, module = 'case_management') => 
    apiCall(`${API_ENDPOINTS.clients.addNote(id)}?module=${module}`, {
      method: 'POST',
      body: JSON.stringify(noteData)
    })
}

export const aiAPI = {
  getCompleteProfile: (clientId) => 
    apiCall(API_ENDPOINTS.ai.getCompleteProfile(clientId)),
    
  createClient: (clientData) => 
    apiCall(API_ENDPOINTS.ai.createClient, {
      method: 'POST',
      body: JSON.stringify(clientData)
    }),
    
  saveConversation: (conversationData) => 
    apiCall(API_ENDPOINTS.ai.saveConversation, {
      method: 'POST',
      body: JSON.stringify(conversationData)
    }),
    
  updateAnalytics: (clientId, analyticsData) => 
    apiCall(API_ENDPOINTS.ai.updateAnalytics(clientId), {
      method: 'PUT',
      body: JSON.stringify(analyticsData)
    })
}

export default {
  API_BASE_URL,
  API_ENDPOINTS,
  apiUrl,
  apiCall,
  apiFetch,
  clientsAPI,
  aiAPI
}
