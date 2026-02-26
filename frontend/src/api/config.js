/**
 * API Configuration for Case Management Suite
 * Updated for new 9-database architecture
 */

// Base API URL - matches our new backend
const configuredApiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim()
const vercelFallbackApiBaseUrl = 'https://cmsx-production-088d.up.railway.app'
const isVercelBrowserHost =
  typeof window !== 'undefined' && window.location.hostname.endsWith('.vercel.app')
export const API_BASE_URL = configuredApiBaseUrl || (isVercelBrowserHost ? vercelFallbackApiBaseUrl : '')
const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 8000)
export const apiUrl = (endpoint) => `${API_BASE_URL}${endpoint}`

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

// Helper function to make API calls
export const apiCall = async (endpoint, options = {}) => {
  const url = apiUrl(endpoint)
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    }
  }
  
  const config = { ...defaultOptions, ...options }
  
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS)
  try {
    const response = await fetch(url, { ...config, signal: controller.signal })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error(`Request timeout after ${API_TIMEOUT_MS}ms`)
    }
    console.error(`API call failed: ${endpoint}`, error)
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

export const apiFetch = async (endpoint, options = {}) => {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS)
  try {
    return await fetch(apiUrl(endpoint), { ...options, signal: controller.signal })
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error(`Request timeout after ${API_TIMEOUT_MS}ms`)
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

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
