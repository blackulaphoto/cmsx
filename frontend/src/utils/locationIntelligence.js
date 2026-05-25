let cachedLocations = null
let cachedAliases = null
let cachedTopLocations = null
let cachedStateOptions = null
let dataLoadPromise = null

const levenshteinDistance = (a, b) => {
  const matrix = []

  for (let i = 0; i <= b.length; i += 1) {
    matrix[i] = [i]
  }

  for (let j = 0; j <= a.length; j += 1) {
    matrix[0][j] = j
  }

  for (let i = 1; i <= b.length; i += 1) {
    for (let j = 1; j <= a.length; j += 1) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1]
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1,
          matrix[i][j - 1] + 1,
          matrix[i - 1][j] + 1
        )
      }
    }
  }

  return matrix[b.length][a.length]
}

const similarity = (a, b) => {
  const left = (a || '').toLowerCase()
  const right = (b || '').toLowerCase()
  if (!left || !right) return 0
  const distance = levenshteinDistance(left, right)
  const maxLength = Math.max(left.length, right.length)
  return maxLength ? 1 - distance / maxLength : 0
}

const toOption = (location) => ({
  city: location.city,
  region: location.state,
  regionCode: location.state_code,
  label: `${location.city}, ${location.state_code}`,
  slug: location.slug,
  lat: location.lat,
  lng: location.lng,
  population: location.population,
})

const loadLocationData = async () => {
  if (cachedLocations && cachedAliases) {
    return { locations: cachedLocations, aliases: cachedAliases }
  }

  if (!dataLoadPromise) {
    dataLoadPromise = Promise.all([
      import('../data/location-intelligence/locations-extended.json'),
      import('../data/location-intelligence/aliases.json'),
    ]).then(([locationsModule, aliasesModule]) => {
      cachedLocations = locationsModule.default || []
      cachedAliases = aliasesModule.default || {}
      cachedTopLocations = [...cachedLocations].sort((a, b) => (b.population || 0) - (a.population || 0))
      cachedStateOptions = Array.from(
        new Map(
          cachedLocations.map((location) => [
            location.state_code,
            { code: location.state_code, name: location.state }
          ])
        ).values()
      ).sort((a, b) => a.name.localeCompare(b.name))

      return { locations: cachedLocations, aliases: cachedAliases }
    })
  }

  return dataLoadPromise
}

export const getStateOptions = async () => {
  await loadLocationData()
  return cachedStateOptions || []
}

export const searchLocationOptions = async (query, limit = 8) => {
  const { locations, aliases } = await loadLocationData()
  const trimmed = (query || '').trim()
  const aliasMap = new Map()

  for (const [alias, slug] of Object.entries(aliases)) {
    const location = locations.find((item) => item.slug === slug)
    if (location) {
      aliasMap.set(alias.toLowerCase(), location)
    }
  }

  if (!trimmed) {
    return (cachedTopLocations || locations).slice(0, limit).map(toOption)
  }

  const normalizedQuery = trimmed.toLowerCase()
  const exactAlias = aliasMap.get(normalizedQuery)
  if (exactAlias) {
    return [toOption(exactAlias)]
  }

  const exactMatches = locations.filter((location) => (
    location.city.toLowerCase() === normalizedQuery ||
    location.state.toLowerCase() === normalizedQuery ||
    location.state_code.toLowerCase() === normalizedQuery ||
    `${location.city}, ${location.state_code}`.toLowerCase() === normalizedQuery
  ))
  if (exactMatches.length > 0) {
    return exactMatches
      .sort((a, b) => (b.population || 0) - (a.population || 0))
      .slice(0, limit)
      .map(toOption)
  }

  const prefixMatches = locations.filter((location) => (
    location.city.toLowerCase().startsWith(normalizedQuery) ||
    location.state.toLowerCase().startsWith(normalizedQuery) ||
    location.state_code.toLowerCase().startsWith(normalizedQuery)
  ))
  if (prefixMatches.length > 0) {
    return prefixMatches
      .sort((a, b) => (b.population || 0) - (a.population || 0))
      .slice(0, limit)
      .map(toOption)
  }

  const containsMatches = locations.filter((location) => {
    const city = location.city.toLowerCase()
    const state = location.state.toLowerCase()
    const stateCode = location.state_code.toLowerCase()
    const composite = `${city}, ${stateCode}`
    return (
      city.includes(normalizedQuery) ||
      state.includes(normalizedQuery) ||
      stateCode.includes(normalizedQuery) ||
      composite.includes(normalizedQuery)
    )
  })
  if (containsMatches.length > 0) {
    return containsMatches
      .sort((a, b) => (b.population || 0) - (a.population || 0))
      .slice(0, limit)
      .map(toOption)
  }

  const firstLetter = normalizedQuery.charAt(0)
  const fuzzyCandidates = locations.filter((location) => (
    location.city.toLowerCase().startsWith(firstLetter) ||
    location.state.toLowerCase().startsWith(firstLetter)
  ))

  return fuzzyCandidates
    .map((location) => ({
      location,
      score: Math.max(
        similarity(location.city, trimmed),
        similarity(location.state, trimmed),
        similarity(`${location.city}, ${location.state_code}`, trimmed)
      ),
    }))
    .filter((item) => item.score >= 0.72)
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score
      return (b.location.population || 0) - (a.location.population || 0)
    })
    .slice(0, limit)
    .map((item) => toOption(item.location))
}
