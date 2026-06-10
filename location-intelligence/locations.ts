import { LocationSearch } from "./search/LocationSearch";
import type { Location as SearchLocation } from "./types";
import locations from "./data/locations-extended.json";
import aliases from "./data/aliases.json";

export type LocationOption = {
  city: string;
  region: string;
  regionCode: string;
  label: string;
  slug: string;
  lat?: number;
  lng?: number;
  population?: number;
};

const locationSearch = new LocationSearch({
  maxResults: 8,
  fuzzyThreshold: 0.72,
  populationWeight: 0.2,
});

locationSearch.initialize(locations as SearchLocation[], aliases as Record<string, string>);

function toOption(location: SearchLocation): LocationOption {
  return {
    city: location.city,
    region: location.state,
    regionCode: location.state_code,
    label: `${location.city}, ${location.state}`,
    slug: location.slug,
    lat: location.lat,
    lng: location.lng,
    population: location.population,
  };
}

export function formatCityRegion(city?: string | null, region?: string | null) {
  return [city?.trim(), region?.trim()].filter(Boolean).join(", ");
}

export function parseCityRegion(value: string) {
  const trimmed = value.trim();
  const exact = searchLocationOptions(trimmed, 1)[0];
  if (exact && exact.label.toLowerCase() === trimmed.toLowerCase()) {
    return {
      city: exact.city,
      region: exact.region,
    };
  }

  const [city, ...rest] = trimmed.split(",").map((part) => part.trim()).filter(Boolean);
  return {
    city: city || "",
    region: rest.join(", "),
  };
}

export function searchLocationOptions(query: string, limit = 8) {
  const trimmed = query.trim();
  if (!trimmed) {
    return (locations as SearchLocation[])
      .slice(0, limit)
      .map(toOption);
  }

  return locationSearch
    .search(trimmed)
    .slice(0, limit)
    .map(toOption);
}
