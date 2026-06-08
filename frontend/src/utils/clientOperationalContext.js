export const getOperationalContext = (client) => client?.operational_context || null

export const getIntakeContext = (client) => getOperationalContext(client)?.intake || {}

export const getTreatmentPlanContext = (client) => getOperationalContext(client)?.treatment_plan || {}

export const getModuleContext = (client, moduleName) =>
  getOperationalContext(client)?.module_context?.[moduleName] || {}

export const getActiveNeeds = (client, moduleName = null) => {
  if (moduleName) {
    const moduleContext = getModuleContext(client, moduleName)
    return moduleContext.active_needs || moduleContext.needs || []
  }
  return getOperationalContext(client)?.operational_needs || []
}

export const getNeedKeys = (client, moduleName = null) =>
  new Set(getActiveNeeds(client, moduleName).map((need) => need.need_key).filter(Boolean))

export const splitContextText = (value) =>
  String(value || '')
    .split(/[\n;,]+/)
    .map((item) => item.trim())
    .filter(Boolean)

export const mergeUnique = (...lists) => {
  const seen = new Set()
  const merged = []
  lists.flat().forEach((item) => {
    const text = String(item || '').trim()
    const key = text.toLowerCase()
    if (!text || seen.has(key)) return
    seen.add(key)
    merged.push(text)
  })
  return merged
}

export const clientLocation = (client, fallback = 'Los Angeles, CA') => {
  const contextClient = getOperationalContext(client)?.client || {}
  const city = client?.city || contextClient.city
  const state = client?.state || contextClient.state
  if (city && state) return `${city}, ${state}`
  return city || state || fallback
}

export const formatNeedSummary = (client, moduleName = null) =>
  getActiveNeeds(client, moduleName)
    .map((need) => need.reason || need.need_key?.replaceAll('_', ' '))
    .filter(Boolean)
    .join('; ')

export const fetchClientWithOperationalContext = async (apiFetch, clientId) => {
  const response = await apiFetch(`/api/clients/${encodeURIComponent(clientId)}/operational-context`)
  if (!response.ok) {
    throw new Error('Client not found')
  }
  const data = await response.json()
  const operationalContext = data?.operational_context
  return {
    ...(operationalContext?.client || {}),
    ...(data?.client || {}),
    client_id: clientId,
    operational_context: operationalContext,
  }
}
