"""
Location Intelligence Engine
Geographic scoring for neighborhood-aware provider ranking.
"""

import logging
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LocationContext:
    """User location context for proximity scoring"""
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    service_urgency: str = "routine"  # immediate, urgent, routine


# Los Angeles County Neighborhood Coordinates
LA_NEIGHBORHOODS = {
    # San Fernando Valley - North
    "north hollywood": (34.1719, -118.3798),
    "van nuys": (34.1894, -118.4514),
    "sherman oaks": (34.1508, -118.4490),
    "studio city": (34.1408, -118.3965),
    "encino": (34.1591, -118.5012),
    "tarzana": (34.1686, -118.5456),
    "reseda": (34.1994, -118.5362),
    "canoga park": (34.2014, -118.5979),
    "woodland hills": (34.1683, -118.6059),
    "sun valley": (34.2198, -118.3901),
    "pacoima": (34.2778, -118.4090),

    # Adjacent Cities
    "burbank": (34.1808, -118.3090),
    "glendale": (34.1425, -118.2551),
    "pasadena": (34.1478, -118.1445),

    # Central LA
    "hollywood": (34.0928, -118.3287),
    "west hollywood": (34.0900, -118.3617),
    "downtown": (34.0407, -118.2468),
    "los feliz": (34.1069, -118.2884),
    "silver lake": (34.0870, -118.2704),
    "echo park": (34.0780, -118.2607),

    # Westside
    "west la": (34.0522, -118.4437),
    "west los angeles": (34.0522, -118.4437),
    "santa monica": (34.0195, -118.4912),
    "venice": (33.9850, -118.4695),
    "culver city": (34.0211, -118.3964),
    "beverly hills": (34.0736, -118.4004),
    "westwood": (34.0633, -118.4456),

    # South LA
    "south la": (33.9731, -118.2479),
    "south los angeles": (33.9731, -118.2479),
    "inglewood": (33.9617, -118.3531),
    "hawthorne": (33.9164, -118.3526),

    # East LA
    "east la": (34.0239, -118.1720),
    "east los angeles": (34.0239, -118.1720),
    "boyle heights": (34.0333, -118.2067),
    "alhambra": (34.0953, -118.1270),

    # Orange County (for reference - distant)
    "costa mesa": (33.6411, -117.9187),
    "santa ana": (33.7455, -117.8677),
}

# Service urgency affects acceptable distance
SERVICE_URGENCY_WEIGHTS = {
    "immediate": 0.5,  # Detox, emergency - short radius preferred
    "urgent": 0.7,  # Residential, shelter - medium radius ok
    "routine": 1.0,  # Outpatient, ongoing care - wider radius acceptable
}


class LocationIntelligence:
    """Geographic scoring for provider proximity"""

    def __init__(self):
        self.neighborhoods = LA_NEIGHBORHOODS

    def score_location(
        self,
        provider_location: Dict,
        user_context: LocationContext
    ) -> float:
        """
        Score provider location based on proximity to user.

        Returns score from 0.0 (very far) to 1.0 (very close)
        """

        # If no location data, return neutral score
        if not self._has_location_data(provider_location) or not self._has_user_location(user_context):
            return 0.5

        # Get coordinates
        provider_coords = self._get_coordinates(provider_location)
        user_coords = self._get_user_coordinates(user_context)

        if not provider_coords or not user_coords:
            # Try neighborhood-based scoring
            return self._score_by_neighborhood(provider_location, user_context)

        # Calculate distance
        distance_miles = self._calculate_distance(provider_coords, user_coords)

        # Apply distance decay with urgency weighting
        urgency_weight = SERVICE_URGENCY_WEIGHTS.get(user_context.service_urgency, 1.0)
        base_score = self._distance_to_score(distance_miles, urgency_weight)

        # Bonus for same neighborhood
        neighborhood_bonus = self._neighborhood_match_bonus(provider_location, user_context)

        # Bonus for metro/transit accessibility
        transit_bonus = self._transit_accessibility_bonus(provider_location)

        final_score = min(1.0, base_score + neighborhood_bonus + transit_bonus)

        logger.debug(
            f"Location score for {provider_location.get('name', 'Unknown')}: "
            f"{final_score:.2f} (distance: {distance_miles:.1f} mi, urgency: {user_context.service_urgency})"
        )

        return final_score

    def _has_location_data(self, provider_location: Dict) -> bool:
        """Check if provider has usable location data"""
        return bool(
            provider_location.get('latitude') and provider_location.get('longitude')
            or provider_location.get('neighborhood')
            or provider_location.get('city')
        )

    def _has_user_location(self, user_context: LocationContext) -> bool:
        """Check if user context has location"""
        return bool(
            user_context.latitude and user_context.longitude
            or user_context.neighborhood
            or user_context.city
        )

    def _get_coordinates(self, provider_location: Dict) -> Optional[Tuple[float, float]]:
        """Get provider coordinates (lat, lon)"""
        # Direct coordinates
        if provider_location.get('latitude') and provider_location.get('longitude'):
            return (provider_location['latitude'], provider_location['longitude'])

        # Lookup by neighborhood
        neighborhood = provider_location.get('neighborhood')
        if neighborhood and isinstance(neighborhood, str):
            neighborhood_lower = neighborhood.lower()
            if neighborhood_lower in self.neighborhoods:
                return self.neighborhoods[neighborhood_lower]

        # Lookup by city
        city = provider_location.get('city')
        if city and isinstance(city, str):
            city_lower = city.lower()
            if city_lower in self.neighborhoods:
                return self.neighborhoods[city_lower]

        return None

    def _get_user_coordinates(self, user_context: LocationContext) -> Optional[Tuple[float, float]]:
        """Get user coordinates (lat, lon)"""
        # Direct coordinates
        if user_context.latitude and user_context.longitude:
            return (user_context.latitude, user_context.longitude)

        # Lookup by neighborhood
        if user_context.neighborhood:
            neighborhood = user_context.neighborhood.lower()
            if neighborhood in self.neighborhoods:
                return self.neighborhoods[neighborhood]

        # Lookup by city
        if user_context.city:
            city = user_context.city.lower()
            if city in self.neighborhoods:
                return self.neighborhoods[city]

        return None

    def _calculate_distance(self, coords1: Tuple[float, float], coords2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates in miles (haversine formula)"""
        lat1, lon1 = coords1
        lat2, lon2 = coords2

        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Radius of earth in miles
        r = 3956

        return c * r

    def _distance_to_score(self, distance_miles: float, urgency_weight: float) -> float:
        """
        Convert distance to score with exponential decay.

        Urgency weight affects acceptable radius:
        - immediate (0.5): 5 miles = 0.5 score
        - urgent (0.7): 7 miles = 0.5 score
        - routine (1.0): 10 miles = 0.5 score
        """
        # Adjust effective distance by urgency
        effective_distance = distance_miles / urgency_weight

        # Exponential decay: score = e^(-distance/scale)
        # Scale of 10 means 10 miles ~= 0.37 score, 5 miles ~= 0.61 score
        scale = 10.0
        score = math.exp(-effective_distance / scale)

        return score

    def _score_by_neighborhood(self, provider_location: Dict, user_context: LocationContext) -> float:
        """Fallback: score by neighborhood name matching"""
        provider_neighborhood = provider_location.get('neighborhood') or ''
        provider_neighborhood = provider_neighborhood.lower() if isinstance(provider_neighborhood, str) else ''

        provider_city = provider_location.get('city') or ''
        provider_city = provider_city.lower() if isinstance(provider_city, str) else ''

        user_neighborhood = user_context.neighborhood or ''
        user_neighborhood = user_neighborhood.lower() if isinstance(user_neighborhood, str) else ''

        user_city = user_context.city or ''
        user_city = user_city.lower() if isinstance(user_city, str) else ''

        # Exact neighborhood match
        if provider_neighborhood and provider_neighborhood == user_neighborhood:
            return 0.9

        # Same city
        if provider_city and provider_city == user_city:
            return 0.6

        # San Fernando Valley region match
        sfv_neighborhoods = {
            'north hollywood', 'van nuys', 'sherman oaks', 'studio city',
            'encino', 'tarzana', 'reseda', 'canoga park', 'woodland hills',
            'sun valley', 'pacoima'
        }

        if provider_neighborhood in sfv_neighborhoods and user_neighborhood in sfv_neighborhoods:
            return 0.7

        # Adjacent to SFV
        sfv_adjacent = {'burbank', 'glendale'}
        if (provider_neighborhood in sfv_adjacent and user_neighborhood in sfv_neighborhoods) or \
           (provider_neighborhood in sfv_neighborhoods and user_neighborhood in sfv_adjacent):
            return 0.5

        # Default: unknown proximity
        return 0.3

    def _neighborhood_match_bonus(self, provider_location: Dict, user_context: LocationContext) -> float:
        """Bonus for exact neighborhood match"""
        provider_neighborhood = provider_location.get('neighborhood') or ''
        provider_neighborhood = provider_neighborhood.lower() if isinstance(provider_neighborhood, str) else ''

        user_neighborhood = user_context.neighborhood or ''
        user_neighborhood = user_neighborhood.lower() if isinstance(user_neighborhood, str) else ''

        if provider_neighborhood and provider_neighborhood == user_neighborhood:
            return 0.1  # 10% bonus for same neighborhood

        return 0.0

    def _transit_accessibility_bonus(self, provider_location: Dict) -> float:
        """Bonus for metro/transit proximity"""
        # Metro Red Line neighborhoods (North Hollywood, Universal City, Hollywood)
        red_line_neighborhoods = {
            'north hollywood', 'universal city', 'hollywood',
            'downtown', 'union station'
        }

        # Metro Orange Line (Van Nuys, Sherman Oaks, etc.)
        orange_line_neighborhoods = {
            'van nuys', 'sherman oaks', 'reseda', 'canoga park',
            'woodland hills', 'north hollywood'
        }

        neighborhood = provider_location.get('neighborhood') or ''
        neighborhood_lower = neighborhood.lower() if isinstance(neighborhood, str) else ''

        if neighborhood_lower in red_line_neighborhoods or neighborhood_lower in orange_line_neighborhoods:
            return 0.05  # 5% bonus for metro access

        return 0.0

    def extract_location_from_query(self, query: str) -> LocationContext:
        """Extract location context from user query"""
        query_lower = query.lower()

        # Look for neighborhood mentions
        for neighborhood, coords in self.neighborhoods.items():
            if neighborhood in query_lower:
                return LocationContext(
                    neighborhood=neighborhood.title(),
                    latitude=coords[0],
                    longitude=coords[1]
                )

        # Look for zip codes
        import re
        zip_pattern = r'\b9\d{4}\b'  # LA zip codes start with 9
        zip_match = re.search(zip_pattern, query)
        if zip_match:
            return LocationContext(zip_code=zip_match.group(0))

        # Default: no location context
        return LocationContext()

    def determine_service_urgency(self, query: str, service_type: str) -> str:
        """Determine urgency level from query and service type"""
        query_lower = query.lower()

        # Immediate keywords
        immediate_keywords = ['tonight', 'today', 'now', 'emergency', 'urgent', 'asap', 'immediate']
        if any(kw in query_lower for kw in immediate_keywords):
            return "immediate"

        # Detox is usually urgent
        if service_type == "treatment" and any(kw in query_lower for kw in ['detox', 'withdrawal']):
            return "urgent"

        # Emergency shelter is immediate
        if service_type == "housing" and any(kw in query_lower for kw in ['shelter', 'homeless', 'street']):
            return "immediate"

        # Default: routine
        return "routine"


# Singleton instance
_location_intelligence = None

def get_location_intelligence() -> LocationIntelligence:
    """Get singleton location intelligence instance"""
    global _location_intelligence
    if _location_intelligence is None:
        _location_intelligence = LocationIntelligence()
    return _location_intelligence
