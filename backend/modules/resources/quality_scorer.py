"""
Quality Scorer
Ranks providers based on internal trust ratings and relationship strength.
"""

import logging
from typing import Dict, List, Optional, Set
import re

logger = logging.getLogger(__name__)


# Trusted providers from case manager experience
# These get significant ranking boosts
TRUSTED_PROVIDERS = {
    # Treatment centers
    "muse": {
        "boost": 0.30,
        "keywords": ["muse treatment", "muse recovery"],
        "notes": "Strong detox program, Sherman Oaks, excellent Medi-Cal acceptance",
    },
    "cri-help": {
        "boost": 0.25,
        "keywords": ["cri-help", "cri help"],
        "notes": "Excellent MAT program in North Hollywood, very accessible",
    },
    "tarzana": {
        "boost": 0.25,
        "keywords": ["tarzana treatment"],
        "notes": "Comprehensive dual diagnosis, multiple service levels",
    },
    "westwind": {
        "boost": 0.20,
        "keywords": ["westwind recovery"],
        "notes": "Quality detox and residential, accepts Medi-Cal",
    },
    "resurgence": {
        "boost": 0.15,
        "keywords": ["resurgence behavioral", "resurgence health"],
        "notes": "High quality but distant from LA (Orange County)",
    },
    "clare foundation": {
        "boost": 0.20,
        "keywords": ["clare foundation"],
        "notes": "Excellent women's treatment and sober living",
    },
    "phoenix house": {
        "boost": 0.15,
        "keywords": ["phoenix house"],
        "notes": "Established provider, multiple locations",
    },

    # Housing/shelter
    "hope of the valley": {
        "boost": 0.25,
        "keywords": ["hope of the valley", "hope valley"],
        "notes": "Major San Fernando Valley homeless services provider",
    },
    "hope the mission": {
        "boost": 0.20,
        "keywords": ["hope the mission", "hope mission"],
        "notes": "Established LA homeless services",
    },
    "la family housing": {
        "boost": 0.25,
        "keywords": ["la family housing", "lafh"],
        "notes": "Excellent family and veteran services",
    },
    "san fernando valley rescue mission": {
        "boost": 0.20,
        "keywords": ["sfv rescue", "san fernando valley rescue"],
        "notes": "Reliable shelter and meals",
    },
    "midnight mission": {
        "boost": 0.20,
        "keywords": ["midnight mission"],
        "notes": "Downtown LA, comprehensive services",
    },
    "union rescue mission": {
        "boost": 0.20,
        "keywords": ["union rescue"],
        "notes": "Large downtown shelter, established",
    },
}

# Providers to avoid or de-prioritize
# These are aggregators, directories, or low-quality providers
AVOID_PROVIDERS = {
    "211": {
        "penalty": -0.50,
        "keywords": ["211", "dial 211", "call 211"],
        "reason": "Referral service, not actual provider - only use if no direct providers available",
    },
    "findhelp": {
        "penalty": -0.40,
        "keywords": ["findhelp.org", "find help"],
        "reason": "Directory aggregator, not direct service",
    },
    "psychologytoday": {
        "penalty": -0.40,
        "keywords": ["psychology today"],
        "reason": "Therapist directory, not vetted providers",
    },
    "recovery.com": {
        "penalty": -0.35,
        "keywords": ["recovery.com"],
        "reason": "Commercial aggregator with paid listings",
    },
    "rehabs.com": {
        "penalty": -0.35,
        "keywords": ["rehabs.com"],
        "reason": "Commercial aggregator",
    },
    "addiction.com": {
        "penalty": -0.35,
        "keywords": ["addiction.com", "addictions.com"],
        "reason": "Commercial aggregator",
    },
    "samhsa": {
        "penalty": -0.20,
        "keywords": ["samhsa", "treatment locator"],
        "reason": "Federal directory, not direct provider",
    },
}

# Domain-based filtering (from unified_service.py)
AGGREGATOR_DOMAINS = {
    "recovery.com",
    "rehabs.com",
    "addictions.com",
    "psychologytoday.com",
    "yelp.com",
    "findhelp.org",
    "roomies.com",
    "craigslist.org",
    "roomster.com",
    "rehabnet.com",
    "drugrehabus.org",
    "alcohol.org",
}


class QualityScorer:
    """Score providers based on quality indicators and trust ratings"""

    def __init__(self):
        self.trusted_providers = TRUSTED_PROVIDERS
        self.avoid_providers = AVOID_PROVIDERS
        self.aggregator_domains = AGGREGATOR_DOMAINS

    def score_quality(self, provider: Dict) -> float:
        """
        Score provider quality and trustworthiness.

        Returns score from 0.0 (avoid) to 1.0 (highly trusted)
        Base score is 0.5 (neutral/unknown)
        """

        # Start with base score
        score = 0.5

        # Check if provider is in our trusted list
        trust_boost = self._check_trusted_provider(provider)
        score += trust_boost

        # Check if provider should be avoided
        avoid_penalty = self._check_avoid_provider(provider)
        score += avoid_penalty

        # Check for aggregator domain
        aggregator_penalty = self._check_aggregator_domain(provider)
        score += aggregator_penalty

        # Use provider's internal rating if available
        internal_rating = provider.get('internal_rating', 0.0)
        if internal_rating > 0:
            score = max(score, internal_rating)

        # Verified providers get bonus
        if provider.get('is_verified'):
            score += 0.10

        # Ensure score is within bounds
        score = max(0.0, min(1.0, score))

        logger.debug(
            f"Quality score for {provider.get('name', 'Unknown')}: {score:.2f} "
            f"(trust_boost: {trust_boost:+.2f}, avoid: {avoid_penalty:+.2f})"
        )

        return score

    def _check_trusted_provider(self, provider: Dict) -> float:
        """Check if provider is in trusted list and return boost"""
        name = provider.get('name', '')
        if not name or not isinstance(name, str):
            return 0.0
        name_lower = name.lower()

        website = provider.get('website')
        website_lower = website.lower() if website and isinstance(website, str) else ''

        for provider_key, config in self.trusted_providers.items():
            # Check name match
            if provider_key in name_lower:
                logger.info(f"Trusted provider match: {name} ({config['notes']})")
                return config['boost']

            # Check keyword match
            keywords = config.get('keywords', [])
            if any(kw in name_lower for kw in keywords):
                logger.info(f"Trusted provider keyword match: {name}")
                return config['boost']

            # Check website match
            if website_lower and any(kw in website_lower for kw in keywords):
                return config['boost']

        return 0.0

    def _check_avoid_provider(self, provider: Dict) -> float:
        """Check if provider should be avoided and return penalty"""
        name = provider.get('name', '')
        if not name or not isinstance(name, str):
            return 0.0
        name_lower = name.lower()

        website = provider.get('website')
        website_lower = website.lower() if website and isinstance(website, str) else ''

        for provider_key, config in self.avoid_providers.items():
            # Check name match
            if provider_key in name_lower:
                logger.warning(f"Avoid provider match: {name} ({config['reason']})")
                return config['penalty']

            # Check keyword match
            keywords = config.get('keywords', [])
            if any(kw in name_lower for kw in keywords):
                logger.warning(f"Avoid provider keyword match: {name}")
                return config['penalty']

            # Check website match
            if website_lower and any(kw in website_lower for kw in keywords):
                return config['penalty']

        return 0.0

    def _check_aggregator_domain(self, provider: Dict) -> float:
        """Check if provider website is an aggregator domain"""
        website = provider.get('website')
        if not website or not isinstance(website, str):
            return 0.0

        # Extract domain
        domain = self._extract_domain(website.lower())
        if domain in self.aggregator_domains:
            logger.warning(f"Aggregator domain detected: {domain} for {provider.get('name', 'Unknown')}")
            return -0.30

        return 0.0

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        # Remove protocol
        url = re.sub(r'^https?://', '', url)
        # Remove www
        url = re.sub(r'^www\.', '', url)
        # Get domain (first part before /)
        domain = url.split('/')[0]
        return domain.lower()

    def is_aggregator(self, provider: Dict) -> bool:
        """Check if provider is an aggregator (directory, not direct service)"""
        # Check domain
        website = provider.get('website')
        if website and isinstance(website, str):
            domain = self._extract_domain(website.lower())
            if domain in self.aggregator_domains:
                return True

        # Check name
        name = provider.get('name', '')
        if name and isinstance(name, str):
            name_lower = name.lower()
            aggregator_keywords = ['211', 'findhelp', 'directory', 'locator', 'referral service']
            if any(kw in name_lower for kw in aggregator_keywords):
                return True

        return False

    def filter_aggregators(self, providers: List[Dict]) -> List[Dict]:
        """Remove aggregator providers from list"""
        return [p for p in providers if not self.is_aggregator(p)]

    def add_trusted_provider(self, name: str, boost: float, notes: str = ""):
        """Dynamically add a trusted provider"""
        key = name.lower().replace(' ', '_')
        self.trusted_providers[key] = {
            "boost": boost,
            "keywords": [name.lower()],
            "notes": notes,
        }
        logger.info(f"Added trusted provider: {name} (boost: {boost})")

    def add_avoid_provider(self, name: str, penalty: float, reason: str = ""):
        """Dynamically add a provider to avoid"""
        key = name.lower().replace(' ', '_')
        self.avoid_providers[key] = {
            "penalty": penalty,
            "keywords": [name.lower()],
            "reason": reason,
        }
        logger.info(f"Added avoid provider: {name} (penalty: {penalty})")


# Singleton instance
_quality_scorer = None

def get_quality_scorer() -> QualityScorer:
    """Get singleton quality scorer instance"""
    global _quality_scorer
    if _quality_scorer is None:
        _quality_scorer = QualityScorer()
    return _quality_scorer
