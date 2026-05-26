"""
Knowledge Enrichment Service
Enriches Virgil DB results with detailed notes from knowledge files
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class KnowledgeEnrichment:
    """Enriches provider results with knowledge file data"""

    def __init__(self, knowledge_dir: Optional[Path] = None):
        """Initialize enrichment service"""
        if knowledge_dir is None:
            # Default to knowledge files directory
            knowledge_dir = Path(__file__).parent.parent.parent.parent / "knowledge files"

        self.knowledge_dir = knowledge_dir
        self.provider_index: Dict[str, Dict[str, Any]] = {}
        self._load_knowledge_files()

    def _load_knowledge_files(self):
        """Load and index provider data from knowledge files"""
        logger.info(f"Loading knowledge files from {self.knowledge_dir}")

        if not self.knowledge_dir.exists():
            logger.warning(f"Knowledge directory not found: {self.knowledge_dir}")
            return

        # Load provider-specific files
        provider_files = [
            "suboxone clinics.txt",
            "Urgent cares.txt",
            "Los Angeles Free & Low-Cost Dental.txt",
        ]

        for filename in provider_files:
            filepath = self.knowledge_dir / filename
            if filepath.exists():
                try:
                    self._parse_provider_file(filepath)
                except Exception as e:
                    logger.error(f"Error parsing {filename}: {e}")

        logger.info(f"Indexed {len(self.provider_index)} providers from knowledge files")

    def _parse_provider_file(self, filepath: Path):
        """Parse a knowledge file and extract provider entries"""
        content = filepath.read_text(encoding='utf-8', errors='ignore')

        # Split content into provider entries by looking for numbered items
        # Pattern: digit(s). **Name**
        pattern = r'(\d+)\.\s*\*\*(.+?)\*\*'

        matches = list(re.finditer(pattern, content))

        for i, match in enumerate(matches):
            number = match.group(1)
            name = match.group(2).strip()

            # Get details block (everything from after this match to before next match)
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)

            details_block = content[start_pos:end_pos]

            # Extract structured details
            provider_data = self._extract_provider_details(name, details_block)
            provider_data['source_file'] = filepath.name
            provider_data['raw_name'] = name

            # Index by clean name and variations
            clean_name = self._clean_provider_name(name)
            self.provider_index[clean_name] = provider_data

            # Also index by key phrases in name
            key_phrases = self._extract_key_phrases(name)
            for phrase in key_phrases:
                if phrase not in self.provider_index:
                    self.provider_index[phrase] = provider_data

        logger.info(f"Parsed {len(matches)} providers from {filepath.name}")

    def _extract_provider_details(self, name: str, details_block: str) -> Dict[str, Any]:
        """Extract structured details from provider details block"""
        details = {
            'enriched_description': '',
            'website': None,
            'services_detail': '',
            'payment_detail': '',
            'hours_detail': '',
            'notes': '',
        }

        lines = details_block.strip().split('\n')
        current_field = None

        for line in lines:
            line = line.strip()
            if not line or not line.startswith('-'):
                continue

            # Remove leading dash and clean
            line = line.lstrip('-').strip()

            # Identify field type
            if line.lower().startswith('website:'):
                details['website'] = self._extract_url(line)
            elif line.lower().startswith('services:'):
                details['services_detail'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('payment:'):
                details['payment_detail'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('phone:'):
                # Already have phone in Virgil DB
                pass
            elif line.lower().startswith('details:'):
                details['notes'] = line.split(':', 1)[1].strip()
            else:
                # Add to general notes
                if details['notes']:
                    details['notes'] += ' ' + line
                else:
                    details['notes'] = line

        # Build enriched description
        desc_parts = []
        if details['services_detail']:
            desc_parts.append(f"Services: {details['services_detail']}")
        if details['payment_detail']:
            desc_parts.append(f"Payment: {details['payment_detail']}")
        if details['notes']:
            desc_parts.append(details['notes'])

        details['enriched_description'] = '. '.join(desc_parts)

        return details

    def _extract_url(self, text: str) -> Optional[str]:
        """Extract URL from text"""
        # Match http://... or https://...
        url_match = re.search(r'(https?://[^\s\)]+)', text)
        if url_match:
            return url_match.group(1).rstrip('.,;')
        return None

    def _clean_provider_name(self, name: str) -> str:
        """Clean provider name for matching"""
        # Remove special characters, extra spaces
        name = name.lower()
        # Remove parenthetical info
        name = re.sub(r'\([^)]*\)', '', name)
        # Remove dashes and extra spaces
        name = re.sub(r'[-–—]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        return name.strip()

    def _extract_key_phrases(self, name: str) -> List[str]:
        """Extract key identifying phrases from provider name"""
        clean = self._clean_provider_name(name)
        phrases = []

        # Split by common separators
        parts = re.split(r'\s*[-–—/]\s*', clean)
        for part in parts:
            if len(part) > 3:  # Skip very short phrases
                phrases.append(part.strip())

        # Also add full clean name
        phrases.append(clean)

        return list(set(phrases))

    def enrich_provider(self, provider: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single provider with knowledge file data"""
        provider_name = provider.get('name', '')
        if not provider_name:
            return provider

        # Try to find match in knowledge index
        enrichment = self._find_enrichment(provider_name)

        if enrichment:
            # Merge enrichment data
            enriched = provider.copy()

            # Add enriched description if better than current
            if enrichment.get('enriched_description'):
                current_desc = enriched.get('description', '')
                enriched_desc = enrichment['enriched_description']

                # If current description is generic, replace it
                if len(current_desc) < 100 or 'service' in current_desc.lower():
                    enriched['description'] = enriched_desc
                else:
                    # Append enrichment
                    enriched['description'] = f"{current_desc}. {enriched_desc}"

            # Add website if missing
            if not enriched.get('website') and enrichment.get('website'):
                enriched['website'] = enrichment['website']
                enriched['url'] = enrichment['website']

            # Add enrichment metadata
            enriched['enriched'] = True
            enriched['enrichment_source'] = enrichment.get('source_file', '')
            enriched['payment_details'] = enrichment.get('payment_detail', '')
            enriched['services_details'] = enrichment.get('services_detail', '')
            enriched['provider_notes'] = enrichment.get('notes', '')

            logger.info(f"Enriched provider: {provider_name} from {enrichment.get('source_file')}")
            return enriched

        return provider

    def _find_enrichment(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Find enrichment data for a provider name"""
        clean_name = self._clean_provider_name(provider_name)

        # Try exact match first
        if clean_name in self.provider_index:
            return self.provider_index[clean_name]

        # Try fuzzy matching
        best_match = None
        best_score = 0.0

        for indexed_name, enrichment in self.provider_index.items():
            # Calculate similarity
            score = self._similarity_score(clean_name, indexed_name)

            if score > best_score and score > 0.75:  # 75% similarity threshold
                best_score = score
                best_match = enrichment

        if best_match:
            logger.debug(f"Fuzzy matched '{provider_name}' with score {best_score:.2f}")

        return best_match

    def _similarity_score(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two names"""
        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

    def enrich_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich a list of provider results"""
        enriched_results = []

        for provider in results:
            enriched = self.enrich_provider(provider)
            enriched_results.append(enriched)

        enriched_count = sum(1 for r in enriched_results if r.get('enriched'))
        if enriched_count > 0:
            logger.info(f"Enriched {enriched_count}/{len(results)} providers with knowledge file data")

        return enriched_results


# Singleton instance
_knowledge_enrichment = None

def get_knowledge_enrichment() -> KnowledgeEnrichment:
    """Get singleton knowledge enrichment instance"""
    global _knowledge_enrichment
    if _knowledge_enrichment is None:
        _knowledge_enrichment = KnowledgeEnrichment()
    return _knowledge_enrichment
