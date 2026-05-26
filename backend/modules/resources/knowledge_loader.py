"""
Knowledge Loader
Parses and indexes all curated knowledge files into structured provider data.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class Provider:
    """Structured provider information"""
    name: str
    service_type: str  # treatment, medical, food, housing, etc.
    service_subtypes: List[str] = field(default_factory=list)  # detox, residential, primary_care, etc.

    # Contact information
    phone: Optional[str] = None
    phone_secondary: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None

    # Location
    address: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Services
    services_offered: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)  # dual_diagnosis, lgbtq, veterans, etc.

    # Eligibility
    insurance_accepted: List[str] = field(default_factory=list)  # medi_cal, medicare, uninsured, etc.
    income_requirement: Optional[str] = None  # free, sliding_scale, low_cost, etc.
    demographics_served: List[str] = field(default_factory=list)  # women, men, youth, seniors, etc.
    languages: List[str] = field(default_factory=list)

    # Operational
    hours: Optional[str] = None
    availability: Optional[str] = None  # 24_7, emergency, appointment_only, etc.
    capacity: Optional[str] = None

    # Quality indicators
    internal_rating: float = 0.0  # Case manager trust score 0-1
    is_trusted: bool = False
    is_verified: bool = False
    notes: Optional[str] = None

    # Source tracking
    source_file: Optional[str] = None
    last_updated: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KnowledgeLoader:
    """Load and parse all knowledge files into structured provider index"""

    def __init__(self, knowledge_base_path: Optional[Path] = None):
        if knowledge_base_path is None:
            # Default to knowledge files directory
            self.knowledge_base_path = Path(__file__).resolve().parents[3] / "knowledge files"
        else:
            self.knowledge_base_path = Path(knowledge_base_path)

        self.providers: List[Provider] = []
        self.provider_index: Dict[str, List[Provider]] = {}  # service_type -> providers

    def load_all(self) -> List[Provider]:
        """Load all knowledge files and return structured provider list"""
        logger.info(f"Loading knowledge files from {self.knowledge_base_path}")

        if not self.knowledge_base_path.exists():
            logger.warning(f"Knowledge base path does not exist: {self.knowledge_base_path}")
            return []

        # Load each knowledge source
        self._load_sober_living_directory()
        self._load_food_programs()
        self._load_provider_text_files()
        self._load_markdown_guides()
        self._load_treatment_providers()

        # Build search index
        self._build_index()

        logger.info(f"Loaded {len(self.providers)} providers from knowledge base")
        return self.providers

    def _build_index(self):
        """Build searchable index by service type"""
        self.provider_index.clear()
        for provider in self.providers:
            if provider.service_type not in self.provider_index:
                self.provider_index[provider.service_type] = []
            self.provider_index[provider.service_type].append(provider)

    # ============================================================================
    # SOBER LIVING DIRECTORY
    # ============================================================================

    def _load_sober_living_directory(self):
        """Load CA_Sober_Living_Directory.xlsx"""
        file_path = self.knowledge_base_path / "CA_Sober_Living_Directory.xlsx"
        if not file_path.exists():
            logger.debug(f"Sober living directory not found: {file_path}")
            return

        try:
            # Note: Would need openpyxl or pandas to parse Excel
            # For now, log that we need to implement this
            logger.info(f"Sober living directory found: {file_path}")
            # TODO: Parse Excel file when openpyxl available
            # For now, we'll rely on other text-based sources
        except Exception as e:
            logger.error(f"Error loading sober living directory: {e}")

    # ============================================================================
    # FOOD PROGRAMS
    # ============================================================================

    def _load_food_programs(self):
        """Load LA_County_Food_Grocery_Programs_by_SPA.xlsx"""
        file_path = self.knowledge_base_path / "LA_County_Food_Grocery_Programs_by_SPA.xlsx"
        if not file_path.exists():
            logger.debug(f"Food programs file not found: {file_path}")
            return

        try:
            logger.info(f"Food programs file found: {file_path}")
            # TODO: Parse Excel file when openpyxl available
        except Exception as e:
            logger.error(f"Error loading food programs: {e}")

    # ============================================================================
    # TEXT FILES (Provider lists, clinics, etc.)
    # ============================================================================

    def _load_provider_text_files(self):
        """Load all .txt provider files"""
        text_files = {
            "suboxone clinics.txt": ("treatment", ["mat", "outpatient"]),
            "Urgent cares.txt": ("medical", ["urgent_care"]),
            "Los Angeles Free & Low-Cost Dental.txt": ("medical", ["dental"]),
            "TRANSPORTATION AND HOUSING OPTIONS.txt": ("housing", ["transportation"]),
            "Provider Search Results - Medi-cal.txt": ("medical", ["primary_care", "specialty"]),
        }

        for filename, (service_type, subtypes) in text_files.items():
            file_path = self.knowledge_base_path / filename
            if file_path.exists():
                self._parse_provider_text_file(file_path, service_type, subtypes)

    def _parse_provider_text_file(self, file_path: Path, service_type: str, subtypes: List[str]):
        """Parse unstructured provider text file"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            # Split by common delimiters (double newline, numbered lists, etc.)
            entries = self._split_provider_entries(content)

            for entry in entries:
                provider = self._extract_provider_from_text(entry, service_type, subtypes)
                if provider and provider.name:
                    provider.source_file = file_path.name
                    self.providers.append(provider)

            logger.info(f"Loaded {len(entries)} entries from {file_path.name}")
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")

    def _split_provider_entries(self, content: str) -> List[str]:
        """Split text content into individual provider entries"""
        # Common patterns: numbered lists, double newlines, section headers

        # Try numbered list first (1., 2., etc.)
        numbered_pattern = re.compile(r'\n\d+\.\s+', re.MULTILINE)
        if numbered_pattern.search(content):
            entries = numbered_pattern.split(content)
            return [e.strip() for e in entries if e.strip()]

        # Try double newlines
        entries = content.split('\n\n')
        if len(entries) > 1:
            return [e.strip() for e in entries if e.strip()]

        # Try section headers (ALL CAPS lines)
        section_pattern = re.compile(r'\n[A-Z\s]{10,}\n', re.MULTILINE)
        if section_pattern.search(content):
            entries = section_pattern.split(content)
            return [e.strip() for e in entries if e.strip()]

        # Fallback: treat entire file as one entry
        return [content.strip()]

    def _extract_provider_from_text(self, text: str, service_type: str, subtypes: List[str]) -> Optional[Provider]:
        """Extract structured provider data from unstructured text"""
        if not text or len(text) < 10:
            return None

        # Extract name (usually first line or before first phone/address)
        name = self._extract_name(text)
        if not name:
            return None

        # Extract contact info
        phone = self._extract_phone(text)
        website = self._extract_website(text)
        email = self._extract_email(text)

        # Extract location
        address = self._extract_address(text)
        city, zip_code = self._extract_city_zip(text)
        neighborhood = self._extract_neighborhood(text)

        # Extract insurance
        insurance = self._extract_insurance(text)

        # Extract services
        services = self._extract_services(text)

        # Extract specializations
        specializations = self._extract_specializations(text)

        return Provider(
            name=name,
            service_type=service_type,
            service_subtypes=subtypes,
            phone=phone,
            website=website,
            email=email,
            address=address,
            city=city,
            zip_code=zip_code,
            neighborhood=neighborhood,
            insurance_accepted=insurance,
            services_offered=services,
            specializations=specializations,
        )

    # ============================================================================
    # MARKDOWN GUIDES
    # ============================================================================

    def _load_markdown_guides(self):
        """Load structured markdown guides"""
        md_files = {
            "CA_Housing_Services_Directory_COMPLETE.md": "housing",
            "la_food_right_now.md": "food",
            "la_sleep_and_shelter_quickstart.md": "housing",
            "la_substance_use_treatment_access.md": "treatment",
            "la_crisis_and_24_7_help.md": "crisis",
            "ca_benefits_fast_start.md": "benefits",
            "ca_medical_access_scripts.md": "medical",
        }

        for filename, service_type in md_files.items():
            file_path = self.knowledge_base_path / filename
            if file_path.exists():
                self._parse_markdown_guide(file_path, service_type)

    def _parse_markdown_guide(self, file_path: Path, service_type: str):
        """Parse structured markdown guide"""
        try:
            content = file_path.read_text(encoding='utf-8')

            # These guides are structured with headers and contact blocks
            # Extract provider blocks between headers
            sections = self._split_markdown_sections(content)

            for section_title, section_content in sections:
                provider = self._extract_provider_from_markdown_section(
                    section_title, section_content, service_type
                )
                if provider and provider.name:
                    provider.source_file = file_path.name
                    self.providers.append(provider)

            logger.info(f"Loaded {len(sections)} sections from {file_path.name}")
        except Exception as e:
            logger.error(f"Error parsing markdown {file_path}: {e}")

    def _split_markdown_sections(self, content: str) -> List[tuple]:
        """Split markdown into sections by headers"""
        sections = []

        # Match headers (### Title)
        header_pattern = re.compile(r'^###\s+(.+)$', re.MULTILINE)
        matches = list(header_pattern.finditer(content))

        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_content = content[start:end].strip()

            sections.append((title, section_content))

        return sections

    def _extract_provider_from_markdown_section(self, title: str, content: str, service_type: str) -> Optional[Provider]:
        """Extract provider from markdown section"""
        # Title is often the provider name
        name = title

        # Skip generic sections
        if any(skip in name.lower() for skip in ['quick access', 'section', 'general information', 'overview']):
            return None

        phone = self._extract_phone(content)
        website = self._extract_website(content)
        email = self._extract_email(content)
        address = self._extract_address(content)
        city, zip_code = self._extract_city_zip(content)

        # Extract "What They Do" or service descriptions
        services = self._extract_services(content)

        return Provider(
            name=name,
            service_type=service_type,
            phone=phone,
            website=website,
            email=email,
            address=address,
            city=city,
            zip_code=zip_code,
            services_offered=services,
        )

    # ============================================================================
    # TREATMENT PROVIDERS (High-priority boosted providers)
    # ============================================================================

    def _load_treatment_providers(self):
        """Load known trusted treatment providers from unified_service.py config"""

        # These are the providers that should rank highest
        trusted_providers = [
            {
                "name": "Muse Treatment Center",
                "service_type": "treatment",
                "service_subtypes": ["detox", "residential"],
                "phone": "(800) 426-1818",
                "website": "https://musetreatment.com",
                "address": "4849 Van Nuys Blvd",
                "city": "Sherman Oaks",
                "neighborhood": "Sherman Oaks",
                "zip_code": "91403",
                "insurance_accepted": ["medi_cal", "medicare", "private"],
                "specializations": ["dual_diagnosis", "luxury"],
                "internal_rating": 0.95,
                "is_trusted": True,
                "is_verified": True,
                "notes": "Strong detox program, Sherman Oaks location, excellent Medi-Cal acceptance"
            },
            {
                "name": "CRI-Help, Inc.",
                "service_type": "treatment",
                "service_subtypes": ["mat", "outpatient"],
                "phone": "(818) 985-8323",
                "website": "https://cri-help.org",
                "address": "11027 Burbank Blvd",
                "city": "North Hollywood",
                "neighborhood": "North Hollywood",
                "zip_code": "91601",
                "insurance_accepted": ["medi_cal", "uninsured"],
                "specializations": ["mat", "outpatient", "counseling"],
                "internal_rating": 0.90,
                "is_trusted": True,
                "is_verified": True,
                "notes": "Excellent MAT program in North Hollywood, very accessible"
            },
            {
                "name": "Tarzana Treatment Centers",
                "service_type": "treatment",
                "service_subtypes": ["detox", "residential", "outpatient"],
                "phone": "(818) 996-1051",
                "website": "https://tarzanatc.org",
                "city": "Tarzana",
                "neighborhood": "Tarzana",
                "insurance_accepted": ["medi_cal", "medicare", "private"],
                "specializations": ["dual_diagnosis", "women", "lgbtq"],
                "internal_rating": 0.90,
                "is_trusted": True,
                "is_verified": True,
                "notes": "Comprehensive dual diagnosis, multiple service levels"
            },
            {
                "name": "Westwind Recovery",
                "service_type": "treatment",
                "service_subtypes": ["detox", "residential"],
                "phone": "(323) 747-4580",
                "website": "https://westwindrecovery.com",
                "city": "Los Angeles",
                "neighborhood": "West Los Angeles",
                "insurance_accepted": ["medi_cal", "private"],
                "specializations": ["detox", "residential"],
                "internal_rating": 0.85,
                "is_trusted": True,
                "is_verified": True,
                "notes": "Quality detox and residential, accepts Medi-Cal"
            },
            {
                "name": "Resurgence Behavioral Health",
                "service_type": "treatment",
                "service_subtypes": ["detox", "residential"],
                "phone": "(855) 458-0050",
                "website": "https://resurgencebehavioralhealth.com",
                "city": "Costa Mesa",
                "neighborhood": "Costa Mesa",
                "insurance_accepted": ["private", "medi_cal"],
                "specializations": ["luxury", "dual_diagnosis"],
                "internal_rating": 0.80,
                "is_trusted": True,
                "is_verified": True,
                "notes": "High quality but distant from LA (Orange County)"
            },
            {
                "name": "Hope of the Valley Rescue Mission",
                "service_type": "housing",
                "service_subtypes": ["emergency_shelter", "transitional"],
                "phone": "(818) 392-0020",
                "website": "https://www.hopeofthevalley.org",
                "city": "Los Angeles",
                "neighborhood": "San Fernando Valley",
                "insurance_accepted": ["free"],
                "income_requirement": "free",
                "specializations": ["emergency", "veterans", "families"],
                "internal_rating": 0.90,
                "is_trusted": True,
                "is_verified": True,
                "notes": "Major San Fernando Valley homeless services provider"
            },
            {
                "name": "San Fernando Valley Rescue Mission",
                "service_type": "housing",
                "service_subtypes": ["emergency_shelter", "meals"],
                "phone": "(818) 785-4476",
                "city": "Los Angeles",
                "neighborhood": "San Fernando Valley",
                "insurance_accepted": ["free"],
                "income_requirement": "free",
                "internal_rating": 0.85,
                "is_trusted": True,
                "is_verified": True,
            },
            {
                "name": "LA Family Housing",
                "service_type": "housing",
                "service_subtypes": ["transitional", "permanent_supportive"],
                "phone": "(818) 982-3895",
                "website": "https://lafh.org",
                "city": "Los Angeles",
                "neighborhood": "San Fernando Valley",
                "specializations": ["families", "veterans"],
                "internal_rating": 0.90,
                "is_trusted": True,
                "is_verified": True,
            },
        ]

        for data in trusted_providers:
            provider = Provider(**data)
            provider.source_file = "internal_trusted_providers"
            self.providers.append(provider)

        logger.info(f"Loaded {len(trusted_providers)} trusted providers")

    # ============================================================================
    # EXTRACTION UTILITIES
    # ============================================================================

    def _extract_name(self, text: str) -> Optional[str]:
        """Extract provider name from text"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            return None

        # First non-empty line is usually the name
        name = lines[0]

        # Clean up common prefixes
        name = re.sub(r'^\d+\.\s*', '', name)  # Remove "1. "
        name = re.sub(r'^-\s*', '', name)  # Remove "- "
        name = re.sub(r'^\*+\s*', '', name)  # Remove "**"

        # Stop at first colon or dash (usually means description follows)
        if ':' in name:
            name = name.split(':')[0]
        if ' - ' in name and len(name) > 50:
            name = name.split(' - ')[0]

        return name.strip() if len(name) < 200 else None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        # Common patterns: (818) 555-1234, 818-555-1234, 1-800-555-1234
        patterns = [
            r'\(\d{3}\)\s*\d{3}-\d{4}',  # (818) 555-1234
            r'\d{3}-\d{3}-\d{4}',  # 818-555-1234
            r'1-\d{3}-\d{3}-\d{4}',  # 1-800-555-1234
            r'\d{3}\.\d{3}\.\d{4}',  # 818.555.1234
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return None

    def _extract_website(self, text: str) -> Optional[str]:
        """Extract website URL from text"""
        # Match http(s)://... or www....
        pattern = r'https?://[^\s<>"\')]+|www\.[^\s<>"\')]+\.[a-z]{2,}'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0) if match else None

    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def _extract_address(self, text: str) -> Optional[str]:
        """Extract street address from text"""
        # Match patterns like "1234 Main St" or "1234 Main Street, Suite 100"
        pattern = r'\d{1,6}\s+[A-Za-z0-9\s,.-]+(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir|Plaza|Pl)\.?(?:,?\s*(?:Suite|Ste|Unit|#)\s*[A-Za-z0-9-]+)?'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0).strip() if match else None

    def _extract_city_zip(self, text: str) -> tuple:
        """Extract city and zip code from text"""
        # Match "Los Angeles, CA 90001" or "Los Angeles 90001"
        pattern = r'([A-Z][a-z\s]+),?\s*(?:CA|California)?\s*(\d{5})'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(), match.group(2)

        # Try just zip code
        zip_pattern = r'\b\d{5}\b'
        zip_match = re.search(zip_pattern, text)
        if zip_match:
            return None, zip_match.group(0)

        return None, None

    def _extract_neighborhood(self, text: str) -> Optional[str]:
        """Extract LA neighborhood from text"""
        # LA neighborhoods
        neighborhoods = [
            "North Hollywood", "Van Nuys", "Sherman Oaks", "Studio City",
            "Burbank", "Glendale", "Tarzana", "Encino", "Reseda",
            "Canoga Park", "West Hollywood", "Hollywood", "Downtown",
            "West LA", "Santa Monica", "Venice", "Culver City",
            "Pasadena", "Alhambra", "San Fernando Valley", "South LA",
        ]

        text_lower = text.lower()
        for neighborhood in neighborhoods:
            if neighborhood.lower() in text_lower:
                return neighborhood

        return None

    def _extract_insurance(self, text: str) -> List[str]:
        """Extract insurance types accepted"""
        insurance_types = []
        text_lower = text.lower()

        if any(term in text_lower for term in ['medi-cal', 'medicaid', 'medical']):
            insurance_types.append('medi_cal')
        if 'medicare' in text_lower:
            insurance_types.append('medicare')
        if any(term in text_lower for term in ['uninsured', 'no insurance', 'free']):
            insurance_types.append('uninsured')
        if any(term in text_lower for term in ['private', 'insurance', 'ppo', 'hmo']):
            insurance_types.append('private')
        if 'sliding scale' in text_lower:
            insurance_types.append('sliding_scale')

        return insurance_types

    def _extract_services(self, text: str) -> List[str]:
        """Extract services offered"""
        services = []
        text_lower = text.lower()

        service_keywords = {
            'detox': ['detox', 'detoxification'],
            'residential': ['residential', 'inpatient', 'rtc'],
            'outpatient': ['outpatient', 'iop', 'intensive outpatient'],
            'mat': ['mat', 'medication assisted', 'suboxone', 'methadone'],
            'counseling': ['counseling', 'therapy', 'individual therapy'],
            'group_therapy': ['group therapy', 'group counseling'],
            'case_management': ['case management', 'care coordination'],
            'shelter': ['shelter', 'emergency housing'],
            'meals': ['meals', 'food', 'dining'],
            'medical': ['medical', 'primary care', 'health'],
        }

        for service, keywords in service_keywords.items():
            if any(kw in text_lower for kw in keywords):
                services.append(service)

        return services

    def _extract_specializations(self, text: str) -> List[str]:
        """Extract population specializations"""
        specializations = []
        text_lower = text.lower()

        spec_keywords = {
            'dual_diagnosis': ['dual diagnosis', 'co-occurring'],
            'lgbtq': ['lgbtq', 'lgbt', 'gay', 'lesbian', 'transgender'],
            'veterans': ['veteran', 'military'],
            'women': ['women', 'female'],
            'men': ['men', 'male'],
            'youth': ['youth', 'adolescent', 'teen'],
            'seniors': ['senior', 'elder', 'older adult'],
            'families': ['family', 'families', 'children'],
            'pregnant': ['pregnant', 'prenatal', 'postpartum'],
        }

        for spec, keywords in spec_keywords.items():
            if any(kw in text_lower for kw in keywords):
                specializations.append(spec)

        return specializations

    # ============================================================================
    # SEARCH INTERFACE
    # ============================================================================

    def search(self, query: str, service_type: Optional[str] = None) -> List[Provider]:
        """Simple text search across all providers"""
        query_lower = query.lower()
        results = []

        # Filter by service type if specified
        candidates = self.providers
        if service_type and service_type in self.provider_index:
            candidates = self.provider_index[service_type]

        # Search in name, services, city, neighborhood
        for provider in candidates:
            score = 0

            if query_lower in provider.name.lower():
                score += 10
            if provider.city and query_lower in provider.city.lower():
                score += 5
            if provider.neighborhood and query_lower in provider.neighborhood.lower():
                score += 5
            if any(query_lower in s.lower() for s in provider.services_offered):
                score += 3
            if any(query_lower in s.lower() for s in provider.service_subtypes):
                score += 3

            if score > 0:
                results.append((provider, score))

        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in results]

    def get_by_service_type(self, service_type: str) -> List[Provider]:
        """Get all providers of a specific service type"""
        return self.provider_index.get(service_type, [])

    def get_trusted_providers(self) -> List[Provider]:
        """Get all trusted/verified providers"""
        return [p for p in self.providers if p.is_trusted]


# Singleton instance
_knowledge_loader = None

def get_knowledge_loader() -> KnowledgeLoader:
    """Get singleton knowledge loader instance"""
    global _knowledge_loader
    if _knowledge_loader is None:
        _knowledge_loader = KnowledgeLoader()
        _knowledge_loader.load_all()
    return _knowledge_loader
