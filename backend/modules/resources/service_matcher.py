"""
Service Matcher
Ranks providers by service type hierarchy and specialization matching.
"""

import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# Treatment Placement Continuum
TREATMENT_CONTINUUM = {
    "detox": {
        "priority": 1,
        "urgency": "immediate",
        "typical_duration": "3-7 days",
        "next_steps": ["residential", "sober_living", "outpatient"],
        "insurance_critical": True,
        "keywords": ["detox", "detoxification", "withdrawal", "medical detox"],
    },
    "residential": {
        "priority": 2,
        "urgency": "urgent",
        "typical_duration": "30-90 days",
        "next_steps": ["sober_living", "outpatient", "iop"],
        "insurance_critical": True,
        "keywords": ["residential", "inpatient", "rtc", "residential treatment"],
    },
    "sober_living": {
        "priority": 3,
        "urgency": "planning",
        "typical_duration": "90+ days",
        "next_steps": ["independent_living"],
        "insurance_critical": False,
        "keywords": ["sober living", "recovery housing", "oxford house", "transitional living"],
    },
    "outpatient": {
        "priority": 4,
        "urgency": "routine",
        "typical_duration": "ongoing",
        "next_steps": ["aftercare", "alumni"],
        "insurance_critical": True,
        "keywords": ["outpatient", "iop", "intensive outpatient", "php"],
    },
    "mat": {
        "priority": 2,
        "urgency": "urgent",
        "typical_duration": "ongoing",
        "next_steps": ["outpatient", "counseling"],
        "insurance_critical": True,
        "keywords": ["mat", "medication assisted", "suboxone", "methadone", "buprenorphine"],
    },
}

# Medical Service Priority
MEDICAL_SERVICE_PRIORITY = {
    "emergency": {
        "priority": 1,
        "services": ["emergency_room", "urgent_care", "crisis_clinic"],
        "keywords": ["emergency", "urgent care", "er", "crisis"],
    },
    "acute": {
        "priority": 2,
        "services": ["primary_care", "specialist", "urgent_care"],
        "keywords": ["primary care", "doctor", "physician", "clinic"],
    },
    "preventive": {
        "priority": 3,
        "services": ["community_health_center", "primary_care", "wellness"],
        "keywords": ["preventive", "wellness", "checkup", "screening"],
    },
    "specialty": {
        "priority": 4,
        "services": ["specialist", "clinic"],
        "keywords": ["specialist", "cardiologist", "psychiatrist", "neurologist"],
    },
}

# Housing Service Hierarchy
HOUSING_CONTINUUM = {
    "emergency_shelter": {
        "priority": 1,
        "urgency": "immediate",
        "keywords": ["emergency shelter", "shelter", "homeless", "street"],
    },
    "bridge_housing": {
        "priority": 2,
        "urgency": "urgent",
        "keywords": ["bridge housing", "interim housing", "transitional"],
    },
    "transitional": {
        "priority": 3,
        "urgency": "planning",
        "keywords": ["transitional housing", "supportive housing"],
    },
    "permanent_supportive": {
        "priority": 4,
        "urgency": "planning",
        "keywords": ["permanent supportive housing", "psh", "housing first"],
    },
}

# Food Service Types
FOOD_SERVICE_TYPES = {
    "emergency_food": {
        "priority": 1,
        "keywords": ["food bank", "emergency food", "food pantry", "free food"],
    },
    "meal_program": {
        "priority": 2,
        "keywords": ["meal program", "soup kitchen", "free meals", "hot meals"],
    },
    "groceries": {
        "priority": 3,
        "keywords": ["groceries", "food distribution", "calfresh"],
    },
}


class ServiceMatcher:
    """Match and rank providers by service type and specialization"""

    def __init__(self):
        self.treatment_continuum = TREATMENT_CONTINUUM
        self.medical_priority = MEDICAL_SERVICE_PRIORITY
        self.housing_continuum = HOUSING_CONTINUUM
        self.food_services = FOOD_SERVICE_TYPES

    def score_service_match(
        self,
        provider: Dict,
        requested_service_type: str,
        requested_subtypes: List[str],
        query: str = ""
    ) -> float:
        """
        Score provider's service match to user request.

        Returns score from 0.0 (no match) to 1.0 (perfect match)
        """

        # Check service type match
        if provider.get('service_type') != requested_service_type:
            return 0.0

        query_lower = query.lower()
        provider_subtypes = provider.get('service_subtypes', [])
        provider_services = provider.get('services_offered', [])

        # Exact subtype match
        exact_match_score = self._score_exact_match(provider_subtypes, requested_subtypes)

        # Hierarchy match (for treatment continuum)
        hierarchy_score = self._score_hierarchy_match(
            requested_service_type,
            requested_subtypes,
            provider_subtypes,
            query_lower
        )

        # Specialization match
        specialization_score = self._score_specializations(provider, query_lower)

        # Service offering match
        service_offering_score = self._score_service_offerings(provider_services, query_lower)

        # Weighted combination
        final_score = (
            exact_match_score * 0.4 +
            hierarchy_score * 0.3 +
            specialization_score * 0.2 +
            service_offering_score * 0.1
        )

        logger.debug(
            f"Service match score for {provider.get('name', 'Unknown')}: {final_score:.2f} "
            f"(exact: {exact_match_score:.2f}, hierarchy: {hierarchy_score:.2f})"
        )

        return final_score

    def _score_exact_match(self, provider_subtypes: List[str], requested_subtypes: List[str]) -> float:
        """Score exact subtype match"""
        if not requested_subtypes or not provider_subtypes:
            return 0.5  # Neutral if no subtypes specified

        matches = set(provider_subtypes) & set(requested_subtypes)
        if matches:
            return 1.0  # Perfect match

        return 0.0

    def _score_hierarchy_match(
        self,
        service_type: str,
        requested_subtypes: List[str],
        provider_subtypes: List[str],
        query: str
    ) -> float:
        """Score based on service hierarchy (treatment continuum, etc.)"""

        # Treatment continuum logic
        if service_type == "treatment":
            return self._score_treatment_continuum(requested_subtypes, provider_subtypes, query)

        # Medical service priority
        if service_type == "medical":
            return self._score_medical_priority(requested_subtypes, provider_subtypes, query)

        # Housing continuum
        if service_type == "housing":
            return self._score_housing_continuum(requested_subtypes, provider_subtypes, query)

        # Default: check if provider offers any requested subtype
        if set(provider_subtypes) & set(requested_subtypes):
            return 0.8

        return 0.5

    def _score_treatment_continuum(
        self,
        requested_subtypes: List[str],
        provider_subtypes: List[str],
        query: str
    ) -> float:
        """Score treatment providers by placement continuum"""

        # Identify what's being requested
        requested_level = None
        for subtype in requested_subtypes:
            if subtype in self.treatment_continuum:
                requested_level = subtype
                break

        # If no specific level requested, infer from query
        if not requested_level:
            for level, config in self.treatment_continuum.items():
                if any(kw in query for kw in config['keywords']):
                    requested_level = level
                    break

        if not requested_level:
            return 0.5  # Can't determine level

        # Exact match is best
        if requested_level in provider_subtypes:
            return 1.0

        # Next steps in continuum are good
        next_steps = self.treatment_continuum[requested_level].get('next_steps', [])
        if any(step in provider_subtypes for step in next_steps):
            return 0.7

        # Provider offers different level
        return 0.3

    def _score_medical_priority(
        self,
        requested_subtypes: List[str],
        provider_subtypes: List[str],
        query: str
    ) -> float:
        """Score medical providers by priority level"""

        # Check for emergency keywords
        emergency_keywords = ['emergency', 'urgent', 'now', 'today', 'asap']
        is_emergency = any(kw in query for kw in emergency_keywords)

        if is_emergency:
            # Urgent care or ER is best for emergencies
            if any(s in provider_subtypes for s in ['urgent_care', 'emergency_room']):
                return 1.0
            return 0.4  # Other medical not ideal for emergency

        # Otherwise, exact match
        if set(provider_subtypes) & set(requested_subtypes):
            return 1.0

        return 0.5

    def _score_housing_continuum(
        self,
        requested_subtypes: List[str],
        provider_subtypes: List[str],
        query: str
    ) -> float:
        """Score housing providers by continuum"""

        # Emergency housing is highest priority
        emergency_keywords = ['tonight', 'now', 'street', 'homeless', 'emergency']
        is_emergency = any(kw in query for kw in emergency_keywords)

        if is_emergency:
            if 'emergency_shelter' in provider_subtypes:
                return 1.0
            if 'bridge_housing' in provider_subtypes:
                return 0.7
            return 0.4

        # Otherwise exact match
        if set(provider_subtypes) & set(requested_subtypes):
            return 1.0

        return 0.6

    def _score_specializations(self, provider: Dict, query: str) -> float:
        """Score based on population specializations"""
        specializations = provider.get('specializations', [])
        if not specializations:
            return 0.5  # Neutral if no specializations

        # Check for specialization keywords in query
        specialization_keywords = {
            'dual_diagnosis': ['dual diagnosis', 'co-occurring', 'mental health'],
            'lgbtq': ['lgbtq', 'lgbt', 'gay', 'lesbian', 'transgender', 'queer'],
            'veterans': ['veteran', 'military', 'va'],
            'women': ['women', 'female'],
            'men': ['men', 'male'],
            'youth': ['youth', 'adolescent', 'teen', 'young adult'],
            'seniors': ['senior', 'elder', 'older adult'],
            'families': ['family', 'children', 'kids'],
            'pregnant': ['pregnant', 'prenatal', 'postpartum'],
        }

        for spec in specializations:
            keywords = specialization_keywords.get(spec, [])
            if any(kw in query for kw in keywords):
                return 1.0  # Perfect match

        return 0.5  # No specific specialization requested

    def _score_service_offerings(self, services_offered: List[str], query: str) -> float:
        """Score based on specific service offerings"""
        if not services_offered:
            return 0.5

        # Check if query mentions any offered services
        for service in services_offered:
            if service.lower() in query:
                return 1.0

        return 0.5

    def identify_service_type_from_query(self, query: str) -> str:
        """Identify primary service type from query"""
        query_lower = query.lower()

        # Treatment/recovery keywords
        treatment_keywords = ['detox', 'rehab', 'treatment', 'recovery', 'sober', 'addiction', 'substance', 'mat']
        if any(kw in query_lower for kw in treatment_keywords):
            return "treatment"

        # Housing keywords
        housing_keywords = ['shelter', 'housing', 'homeless', 'street', 'eviction', 'sober living']
        if any(kw in query_lower for kw in housing_keywords):
            return "housing"

        # Medical keywords
        medical_keywords = ['doctor', 'medical', 'clinic', 'primary care', 'urgent care', 'hospital', 'dentist']
        if any(kw in query_lower for kw in medical_keywords):
            return "medical"

        # Food keywords
        food_keywords = ['food', 'hungry', 'pantry', 'meals', 'groceries', 'calfresh']
        if any(kw in query_lower for kw in food_keywords):
            return "food"

        # Benefits keywords
        benefits_keywords = ['benefits', 'medi-cal', 'medicaid', 'insurance', 'ssi', 'ssdi', 'calfresh']
        if any(kw in query_lower for kw in benefits_keywords):
            return "benefits"

        # Legal keywords
        legal_keywords = ['legal', 'expungement', 'court', 'lawyer', 'attorney']
        if any(kw in query_lower for kw in legal_keywords):
            return "legal"

        # Employment keywords
        employment_keywords = ['job', 'employment', 'work', 'resume', 'hiring']
        if any(kw in query_lower for kw in employment_keywords):
            return "employment"

        # Default: general services
        return "services"

    def identify_service_subtypes_from_query(self, query: str, service_type: str) -> List[str]:
        """Identify specific service subtypes from query"""
        query_lower = query.lower()
        subtypes = []

        if service_type == "treatment":
            if any(kw in query_lower for kw in ['detox', 'detoxification', 'withdrawal']):
                subtypes.append('detox')
            if any(kw in query_lower for kw in ['residential', 'inpatient', 'rtc']):
                subtypes.append('residential')
            if any(kw in query_lower for kw in ['sober living', 'recovery housing']):
                subtypes.append('sober_living')
            if any(kw in query_lower for kw in ['outpatient', 'iop', 'php']):
                subtypes.append('outpatient')
            if any(kw in query_lower for kw in ['mat', 'suboxone', 'methadone', 'medication']):
                subtypes.append('mat')

        elif service_type == "housing":
            if any(kw in query_lower for kw in ['emergency', 'shelter', 'tonight', 'street']):
                subtypes.append('emergency_shelter')
            if any(kw in query_lower for kw in ['bridge', 'interim']):
                subtypes.append('bridge_housing')
            if 'transitional' in query_lower:
                subtypes.append('transitional')

        elif service_type == "medical":
            if any(kw in query_lower for kw in ['urgent care', 'urgent', 'emergency']):
                subtypes.append('urgent_care')
            if any(kw in query_lower for kw in ['primary care', 'doctor', 'physician']):
                subtypes.append('primary_care')
            if 'dental' in query_lower or 'dentist' in query_lower:
                subtypes.append('dental')

        return subtypes


# Singleton instance
_service_matcher = None

def get_service_matcher() -> ServiceMatcher:
    """Get singleton service matcher instance"""
    global _service_matcher
    if _service_matcher is None:
        _service_matcher = ServiceMatcher()
    return _service_matcher
