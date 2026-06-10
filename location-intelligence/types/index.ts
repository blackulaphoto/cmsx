/**
 * Normalized location object returned by the search module
 */
export interface Location {
  city: string;
  state: string;
  state_code: string;
  country: string;
  display: string;
  slug: string;
  lat: number;
  lng: number;
  population: number;
}

/**
 * Search result with match information
 */
export interface SearchResult {
  location: Location;
  matchType: "exact" | "prefix" | "fuzzy" | "alias";
  matchStrength: number; // 0-1
  score: number;
}

/**
 * Search response
 */
export interface SearchResponse {
  results: Location[];
  query: string;
  count: number;
}

/**
 * Configuration for the search engine
 */
export interface SearchEngineConfig {
  maxResults?: number;
  fuzzyThreshold?: number;
  populationWeight?: number;
}
