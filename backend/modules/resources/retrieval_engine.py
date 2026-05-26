"""
Resource Retrieval Engine
Main orchestrator for full-spectrum social services resource retrieval.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from .knowledge_loader import KnowledgeLoader, Provider, get_knowledge_loader
from .location_intelligence import LocationIntelligence, LocationContext, get_location_intelligence
from .service_matcher import ServiceMatcher, get_service_matcher
from .quality_scorer import QualityScorer, get_quality_scorer

logger = logging.getLogger(__name__)


@dataclass
class ResourceQuery:
    """Structured resource query"""
    query_text: str
    service_type: Optional[str] = None
    service_subtypes: List[str] = None
    location_context: Optional[LocationContext] = None
    insurance: Optional[str] = None
    urgency: str = "routine"
    limit: int = 10


@dataclass
class ScoredProvider:
    """Provider with retrieval score and breakdown"""
    provider: Provider
    total_score: float
    location_score: float
    service_score: float
    quality_score: float
    eligibility_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            **self.provider.to_dict(),
            "retrieval_score": {
                "total": round(self.total_score, 3),
                "location": round(self.location_score, 3),
                "service_match": round(self.service_score, 3),
                "quality": round(self.quality_score, 3),
                "eligibility": round(self.eligibility_score, 3),
            }
        }


class ResourceRetrievalEngine:
    """
    Full-spectrum resource retrieval system.

    Combines:
    - Knowledge base loading (curated files)
    - Location-aware ranking
    - Service hierarchy matching
    - Quality/trust scoring
    - Eligibility filtering
    """

    def __init__(self):
        self.knowledge_loader = get_knowledge_loader()
        self.location_intelligence = get_location_intelligence()
        self.service_matcher = get_service_matcher()
        self.quality_scorer = get_quality_scorer()

        logger.info("Resource Retrieval Engine initialized")

    def search(
        self,
        query: str,
        client_context: Optional[Dict] = None,
        service_type: Optional[str] = None,
        limit: int = 10
    ) -> List[ScoredProvider]:
        """
        Main search interface.

        Args:
            query: User's natural language query
            client_context: Optional client demographic/eligibility info
            service_type: Optional explicit service type override
            limit: Max number of results to return

        Returns:
            List of scored providers, ranked by relevance
        """

        logger.info(f"Resource search: '{query[:100]}'")

        # Build structured query
        resource_query = self._build_query(query, client_context, service_type)

        # Get candidate providers
        candidates = self._get_candidates(resource_query)

        if not candidates:
            logger.warning(f"No candidates found for query: {query}")
            return []

        # Score and rank providers
        scored_providers = self._score_providers(candidates, resource_query)

        # Filter by minimum score threshold
        min_score = 0.2  # Only return providers with reasonable match
        scored_providers = [sp for sp in scored_providers if sp.total_score >= min_score]

        # Sort by total score
        scored_providers.sort(key=lambda sp: sp.total_score, reverse=True)

        # Apply limit
        results = scored_providers[:limit]

        logger.info(f"Returning {len(results)} providers (from {len(scored_providers)} scored)")

        return results

    def _build_query(
        self,
        query_text: str,
        client_context: Optional[Dict],
        service_type_override: Optional[str]
    ) -> ResourceQuery:
        """Build structured query from inputs"""

        # Identify service type
        if service_type_override:
            service_type = service_type_override
        else:
            service_type = self.service_matcher.identify_service_type_from_query(query_text)

        # Identify service subtypes
        service_subtypes = self.service_matcher.identify_service_subtypes_from_query(
            query_text, service_type
        )

        # Extract location context
        location_context = self.location_intelligence.extract_location_from_query(query_text)

        # Determine urgency
        urgency = self.location_intelligence.determine_service_urgency(query_text, service_type)
        location_context.service_urgency = urgency

        # Extract insurance from client context
        insurance = None
        if client_context:
            insurance = client_context.get('insurance')

        # Check for insurance in query
        if not insurance:
            query_lower = query_text.lower()
            if 'medi-cal' in query_lower or 'medicaid' in query_lower:
                insurance = 'medi_cal'
            elif 'medicare' in query_lower:
                insurance = 'medicare'
            elif 'uninsured' in query_lower or 'no insurance' in query_lower:
                insurance = 'uninsured'

        return ResourceQuery(
            query_text=query_text,
            service_type=service_type,
            service_subtypes=service_subtypes or [],
            location_context=location_context,
            insurance=insurance,
            urgency=urgency,
        )

    def _get_candidates(self, resource_query: ResourceQuery) -> List[Provider]:
        """Get candidate providers from knowledge base"""

        # Get providers by service type
        if resource_query.service_type:
            candidates = self.knowledge_loader.get_by_service_type(resource_query.service_type)
        else:
            candidates = self.knowledge_loader.providers

        # Filter aggregators (unless no direct providers available)
        non_aggregator_candidates = [
            p for p in candidates
            if not self.quality_scorer.is_aggregator(p.to_dict())
        ]

        # If we have direct providers, use those
        if non_aggregator_candidates:
            candidates = non_aggregator_candidates
        else:
            logger.warning("No direct providers found, including aggregators as fallback")

        return candidates

    def _score_providers(
        self,
        candidates: List[Provider],
        resource_query: ResourceQuery
    ) -> List[ScoredProvider]:
        """Score all candidate providers"""

        scored = []

        for provider in candidates:
            provider_dict = provider.to_dict()

            # Location score
            location_score = self.location_intelligence.score_location(
                provider_dict,
                resource_query.location_context
            )

            # Service match score
            service_score = self.service_matcher.score_service_match(
                provider_dict,
                resource_query.service_type,
                resource_query.service_subtypes,
                resource_query.query_text
            )

            # Quality score
            quality_score = self.quality_scorer.score_quality(provider_dict)

            # Eligibility score
            eligibility_score = self._score_eligibility(provider_dict, resource_query)

            # Calculate weighted total score
            total_score = (
                location_score * 0.35 +      # Location is most important
                service_score * 0.30 +       # Service match second
                quality_score * 0.25 +       # Quality/trust third
                eligibility_score * 0.10     # Eligibility bonus
            )

            scored.append(ScoredProvider(
                provider=provider,
                total_score=total_score,
                location_score=location_score,
                service_score=service_score,
                quality_score=quality_score,
                eligibility_score=eligibility_score,
            ))

        return scored

    def _score_eligibility(self, provider: Dict, resource_query: ResourceQuery) -> float:
        """Score provider eligibility match"""

        score = 0.5  # Base neutral score

        # Check insurance match
        if resource_query.insurance:
            insurance_accepted = provider.get('insurance_accepted', [])
            if resource_query.insurance in insurance_accepted:
                score += 0.3
            elif 'all' in insurance_accepted or 'any' in insurance_accepted:
                score += 0.2
            elif not insurance_accepted:
                # Unknown insurance - neutral
                score += 0.0
            else:
                # Insurance not accepted
                score -= 0.2

        # Free/low-cost is always a bonus
        income_requirement = provider.get('income_requirement', '')
        if income_requirement in ['free', 'sliding_scale', 'low_cost']:
            score += 0.2

        # Ensure score is within bounds
        return max(0.0, min(1.0, score))

    def format_for_ai_context(self, scored_providers: List[ScoredProvider], limit: int = 5) -> str:
        """
        Format providers for AI assistant context.

        Returns markdown-formatted provider list.
        """

        if not scored_providers:
            return "No relevant providers found in our curated database."

        top_providers = scored_providers[:limit]

        lines = ["# RELEVANT RESOURCES FROM CURATED DATABASE\n"]

        for i, sp in enumerate(top_providers, 1):
            p = sp.provider

            # Header with name and service type
            lines.append(f"## {i}. {p.name}")
            if p.service_subtypes:
                lines.append(f"**Service Type:** {', '.join(p.service_subtypes).replace('_', ' ').title()}")

            # Contact info
            if p.phone:
                lines.append(f"**Phone:** {p.phone}")
            if p.website:
                lines.append(f"**Website:** {p.website}")

            # Location
            location_parts = []
            if p.address:
                location_parts.append(p.address)
            if p.neighborhood:
                location_parts.append(p.neighborhood)
            elif p.city:
                location_parts.append(p.city)
            if location_parts:
                lines.append(f"**Location:** {', '.join(location_parts)}")

            # Insurance
            if p.insurance_accepted:
                insurance_display = ', '.join(p.insurance_accepted).replace('_', '-').upper()
                lines.append(f"**Insurance:** {insurance_display}")

            # Services
            if p.services_offered:
                services_display = ', '.join(p.services_offered[:5]).replace('_', ' ').title()
                lines.append(f"**Services:** {services_display}")

            # Specializations
            if p.specializations:
                spec_display = ', '.join(p.specializations).replace('_', ' ').title()
                lines.append(f"**Specializations:** {spec_display}")

            # Internal notes
            if p.notes and p.is_trusted:
                lines.append(f"**Notes:** {p.notes}")

            # Hours/availability
            if p.hours:
                lines.append(f"**Hours:** {p.hours}")

            # Relevance score (for debugging)
            lines.append(f"*Relevance: {sp.total_score:.0%}*")

            lines.append("")  # Blank line between providers

        # Add usage instruction
        lines.append("\n**INSTRUCTION:** Use these curated providers in your response. Prioritize the top-ranked providers.\n")

        return "\n".join(lines)

    def get_provider_by_name(self, name: str) -> Optional[Provider]:
        """Get specific provider by name"""
        name_lower = name.lower()
        for provider in self.knowledge_loader.providers:
            if name_lower in provider.name.lower():
                return provider
        return None

    def get_trusted_providers(self, service_type: Optional[str] = None) -> List[Provider]:
        """Get all trusted providers, optionally filtered by service type"""
        trusted = self.knowledge_loader.get_trusted_providers()

        if service_type:
            trusted = [p for p in trusted if p.service_type == service_type]

        return trusted


# Singleton instance
_resource_engine = None

def get_resource_engine() -> ResourceRetrievalEngine:
    """Get singleton resource retrieval engine instance"""
    global _resource_engine
    if _resource_engine is None:
        _resource_engine = ResourceRetrievalEngine()
    return _resource_engine
