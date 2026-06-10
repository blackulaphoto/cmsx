import type { Location, SearchResult } from "../types/index";

/**
 * Levenshtein distance algorithm for fuzzy matching
 * Calculates the minimum number of edits (insertions, deletions, substitutions)
 * needed to transform one string into another
 */
function levenshteinDistance(a: string, b: string): number {
  const matrix: number[][] = [];

  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i];
  }

  for (let j = 0; j <= a.length; j++) {
    matrix[0][j] = j;
  }

  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1, // substitution
          matrix[i][j - 1] + 1, // insertion
          matrix[i - 1][j] + 1 // deletion
        );
      }
    }
  }

  return matrix[b.length][a.length];
}

/**
 * Calculate similarity score based on Levenshtein distance
 * Returns value between 0 and 1, where 1 is perfect match
 */
function calculateSimilarity(a: string, b: string): number {
  const distance = levenshteinDistance(a.toLowerCase(), b.toLowerCase());
  const maxLength = Math.max(a.length, b.length);
  return 1 - distance / maxLength;
}

/**
 * Standalone location search module
 * No external dependencies, can be used in any JavaScript/Node.js environment
 */
export class LocationSearch {
  private locations: Location[] = [];
  private aliasMap: Map<string, Location> = new Map();
  private config: {
    maxResults: number;
    fuzzyThreshold: number;
    populationWeight: number;
  };

  constructor(config: {
    maxResults?: number;
    fuzzyThreshold?: number;
    populationWeight?: number;
  } = {}) {
    this.config = {
      maxResults: config.maxResults ?? 10,
      fuzzyThreshold: config.fuzzyThreshold ?? 0.6,
      populationWeight: config.populationWeight ?? 0.3,
    };
  }

  /**
   * Initialize the search engine with locations and aliases
   * Call this once with your data
   */
  initialize(locations: Location[], aliases: Record<string, string> = {}): void {
    this.locations = locations;

    // Build alias map: alias -> location
    Object.entries(aliases).forEach(([alias, slug]) => {
      const location = locations.find((loc) => loc.slug === slug);
      if (location) {
        this.aliasMap.set(alias.toLowerCase(), location);
      }
    });
  }

  /**
   * Search for locations by query
   * Supports exact matching, prefix matching, fuzzy matching, and aliases
   */
  search(query: string): Location[] {
    if (!query || !query.trim()) {
      return [];
    }

    const trimmedQuery = query.trim();
    const results: SearchResult[] = [];

    // 1. Check for exact alias match (highest priority)
    const aliasMatch = this.aliasMap.get(trimmedQuery.toLowerCase());
    if (aliasMatch) {
      return [aliasMatch];
    }

    // 2. Check for exact city name match
    const exactMatches = this.locations.filter(
      (loc) =>
        loc.city.toLowerCase() === trimmedQuery.toLowerCase() ||
        loc.state.toLowerCase() === trimmedQuery.toLowerCase() ||
        loc.state_code.toLowerCase() === trimmedQuery.toLowerCase()
    );

    if (exactMatches.length > 0) {
      return exactMatches.sort((a, b) => b.population - a.population);
    }

    // 3. Prefix matching (cities starting with query)
    const prefixMatches = this.locations.filter(
      (loc) =>
        loc.city.toLowerCase().startsWith(trimmedQuery.toLowerCase()) ||
        loc.state.toLowerCase().startsWith(trimmedQuery.toLowerCase())
    );

    prefixMatches.forEach((loc) => {
      results.push({
        location: loc,
        matchType: "prefix",
        matchStrength: 0.8,
        score: 0.8 + (loc.population / 10000000) * this.config.populationWeight,
      });
    });

    // 4. Fuzzy matching (for misspellings and typos)
    const fuzzyMatches = this.locations.filter((loc) => {
      const citySimilarity = calculateSimilarity(loc.city, trimmedQuery);
      const stateSimilarity = calculateSimilarity(loc.state, trimmedQuery);
      return (
        (citySimilarity >= this.config.fuzzyThreshold ||
          stateSimilarity >= this.config.fuzzyThreshold) &&
        !prefixMatches.includes(loc)
      );
    });

    fuzzyMatches.forEach((loc) => {
      const citySimilarity = calculateSimilarity(loc.city, trimmedQuery);
      const stateSimilarity = calculateSimilarity(loc.state, trimmedQuery);
      const matchStrength = Math.max(citySimilarity, stateSimilarity);

      results.push({
        location: loc,
        matchType: "fuzzy",
        matchStrength,
        score: matchStrength * 0.7 + (loc.population / 10000000) * this.config.populationWeight,
      });
    });

    // Sort by score (descending) and limit results
    return results
      .sort((a, b) => b.score - a.score)
      .slice(0, this.config.maxResults)
      .map((r) => r.location);
  }

  /**
   * Get all locations
   */
  getAll(): Location[] {
    return this.locations;
  }

  /**
   * Get a location by slug
   */
  getBySlug(slug: string): Location | undefined {
    return this.locations.find((loc) => loc.slug === slug);
  }

  /**
   * Get all locations in a state
   */
  getByState(stateCode: string): Location[] {
    return this.locations.filter(
      (loc) => loc.state_code.toUpperCase() === stateCode.toUpperCase()
    );
  }

  /**
   * Get locations within a radius (in kilometers)
   */
  getWithinRadius(lat: number, lng: number, radiusKm: number): Location[] {
    const toRad = (deg: number) => (deg * Math.PI) / 180;
    const earthRadiusKm = 6371;

    return this.locations.filter((loc) => {
      const dLat = toRad(loc.lat - lat);
      const dLng = toRad(loc.lng - lng);
      const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(toRad(lat)) *
          Math.cos(toRad(loc.lat)) *
          Math.sin(dLng / 2) *
          Math.sin(dLng / 2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      const distance = earthRadiusKm * c;
      return distance <= radiusKm;
    });
  }
}

/**
 * Create and initialize a search instance with default locations and aliases
 * Pass your own locations and aliases to customize
 */
export function createLocationSearch(
  locations: Location[],
  aliases?: Record<string, string>,
  config?: {
    maxResults?: number;
    fuzzyThreshold?: number;
    populationWeight?: number;
  }
): LocationSearch {
  const search = new LocationSearch(config);
  search.initialize(locations, aliases);
  return search;
}
