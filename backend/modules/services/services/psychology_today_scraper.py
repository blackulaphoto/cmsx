"""
Psychology Today Therapist Finder scraper
Scrapes therapist listings from psychologytoday.com
"""

import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class PsychologyTodayScraper(BaseScraper):
    """Scraper for Psychology Today Therapist Finder"""
    
    def __init__(self, config: Dict[str, Any], ai_analyzer=None):
        super().__init__(config, ai_analyzer)
        self.base_url = "https://www.psychologytoday.com"
        self.search_url = "https://www.psychologytoday.com/us/therapists"
        
    def scrape_therapists(self, location: str = 'Los Angeles, CA', specialty: str = '', insurance: str = '', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape Psychology Today therapist listings
        
        Args:
            location: Location to search (city, state or zip)
            specialty: Treatment specialty (anxiety, depression, etc.)
            insurance: Insurance type accepted
            max_pages: Maximum pages to scrape
            
        Returns:
            List of therapist dictionaries
        """
        therapists = []
        max_pages = max_pages or self.max_pages
        
        logger.info(f"Starting Psychology Today scrape for {location}, specialty: {specialty}")
        
        for page in range(max_pages):
            try:
                # Build search URL
                if location:
                    # Extract city and state for URL building
                    location_parts = location.split(',')
                    if len(location_parts) >= 2:
                        city = location_parts[0].strip()
                        state = location_parts[1].strip()
                        url_location = f"{city.lower().replace(' ', '-')}-{state.lower()}"
                    else:
                        url_location = location.lower().replace(' ', '-').replace(',', '')
                    
                    url = f"{self.search_url}/{url_location}"
                else:
                    url = self.search_url
                
                # Add search parameters
                params = []
                if specialty:
                    params.append(f"category={quote_plus(specialty)}")
                if insurance:
                    params.append(f"insurance={quote_plus(insurance)}")
                if page > 0:
                    params.append(f"page={page + 1}")
                
                if params:
                    url += "?" + "&".join(params)
                
                logger.debug(f"Scraping Psychology Today page {page + 1}: {url}")
                
                response = self._make_request(url)
                if not response:
                    logger.warning(f"Failed to get response for Psychology Today page {page + 1}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_therapists = self.parse_therapist_cards(soup, location)
                
                if not page_therapists:
                    logger.info(f"No therapists found on Psychology Today page {page + 1}, stopping")
                    break
                
                therapists.extend(page_therapists)
                logger.info(f"Found {len(page_therapists)} therapists on Psychology Today page {page + 1}")
                
                # Rate limiting
                self._rate_limit_delay()
                
            except Exception as e:
                logger.error(f"Error scraping Psychology Today page {page + 1}: {e}")
                continue
        
        logger.info(f"Total therapists scraped from Psychology Today: {len(therapists)}")
        return therapists
    
    def parse_therapist_cards(self, soup: BeautifulSoup, location: str) -> List[Dict[str, Any]]:
        """Parse therapist cards from the page"""
        therapists = []
        
        # Look for therapist listings
        therapist_containers = soup.find_all(['div', 'article'], class_=re.compile(r'(result|profile|therapist|listing|card)', re.I))
        
        # If no class-based containers found, look for structural patterns
        if not therapist_containers:
            # Look for divs with therapist-like content
            all_divs = soup.find_all('div')
            therapist_containers = [div for div in all_divs if self._contains_therapist_info(div)]
        
        # Also check for article tags which often contain therapist profiles
        if not therapist_containers:
            therapist_containers = soup.find_all('article')
            therapist_containers = [article for article in therapist_containers if self._contains_therapist_info(article)]
        
        logger.info(f"Found {len(therapist_containers)} potential therapist containers")
        
        for container in therapist_containers:
            try:
                therapist_data = self.extract_therapist_from_container(container, location)
                if therapist_data and therapist_data.get('name'):
                    therapists.append(therapist_data)
            except Exception as e:
                logger.warning(f"Error extracting therapist from container: {e}")
                continue
        
        return therapists
    
    def _contains_therapist_info(self, element) -> bool:
        """Check if element contains therapist information"""
        text = element.get_text().upper()
        therapist_indicators = [
            'THERAPIST', 'PSYCHOLOGIST', 'COUNSELOR', 'LCSW', 'LMFT', 'PHD', 'PSYD',
            'THERAPY', 'COUNSELING', 'SPECIALIZES', 'TREATMENT', 'ISSUES',
            'ACCEPTS INSURANCE', 'SLIDING SCALE', 'TELEHEALTH'
        ]
        
        # Must have therapist indicators and substantial content
        has_indicators = any(indicator in text for indicator in therapist_indicators)
        has_substantial_content = len(text.strip()) > 100
        
        return has_indicators and has_substantial_content
    
    def extract_therapist_from_container(self, container, location: str) -> Dict[str, Any]:
        """Extract therapist information from a container element"""
        try:
            therapist_data = {
                'scraped_date': datetime.now().isoformat(),
                'source_site': 'psychology_today',
                'resource_type': 'Mental Health Therapy',
                'location': location
            }
            
            text_content = container.get_text(separator=' ', strip=True)
            
            # Extract therapist name
            name_element = container.find(['h1', 'h2', 'h3', 'h4', 'h5'])
            if name_element:
                # Clean up name (remove credentials)
                name_text = name_element.get_text(strip=True)
                name_clean = re.sub(r',\s*(LCSW|LMFT|PhD|PsyD|MA|MS|LPC|LPCC).*$', '', name_text)
                therapist_data['name'] = name_clean.strip()
                
                # Extract credentials separately
                cred_match = re.search(r'(LCSW|LMFT|PhD|PsyD|MA|MS|LPC|LPCC|LCPC)[^a-zA-Z]*', name_text)
                if cred_match:
                    therapist_data['credentials'] = cred_match.group(1)
            
            # Extract phone number
            phone_patterns = [
                r'Phone[:\s]*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
                r'Call[:\s]*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
                r'(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
            ]
            
            for pattern in phone_patterns:
                phone_match = re.search(pattern, text_content, re.IGNORECASE)
                if phone_match:
                    therapist_data['phone'] = phone_match.group(1)
                    break
            
            # Extract address/location
            address_patterns = [
                r'Office[:\s]*([^,\n]+(?:,[^,\n]+)*)',
                r'Location[:\s]*([^,\n]+(?:,[^,\n]+)*)',
                r'(\d+\s+[^,\n]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)[^,\n]*)'
            ]
            
            for pattern in address_patterns:
                address_match = re.search(pattern, text_content, re.IGNORECASE)
                if address_match:
                    therapist_data['address'] = address_match.group(1).strip()
                    break
            
            # Extract specialties
            specialties = []
            specialty_patterns = [
                ('Anxiety Disorders', ['anxiety', 'panic', 'phobias', 'GAD']),
                ('Depression', ['depression', 'mood disorders', 'bipolar']),
                ('Trauma & PTSD', ['trauma', 'ptsd', 'abuse', 'assault']),
                ('Relationships', ['couples', 'marriage', 'relationship', 'family']),
                ('Addiction', ['addiction', 'substance abuse', 'alcoholism']),
                ('ADHD', ['adhd', 'attention deficit']),
                ('Eating Disorders', ['eating disorders', 'anorexia', 'bulimia']),
                ('LGBTQ+ Issues', ['lgbtq', 'gay', 'lesbian', 'transgender', 'gender']),
                ('Grief & Loss', ['grief', 'bereavement', 'loss']),
                ('Life Transitions', ['life transitions', 'career', 'divorce'])
            ]
            
            text_lower = text_content.lower()
            for specialty_name, keywords in specialty_patterns:
                if any(keyword in text_lower for keyword in keywords):
                    specialties.append(specialty_name)
            
            if specialties:
                therapist_data['specialties'] = specialties
            
            # Extract therapy types
            therapy_types = []
            therapy_patterns = [
                ('Cognitive Behavioral (CBT)', ['cbt', 'cognitive behavioral']),
                ('Dialectical Behavior (DBT)', ['dbt', 'dialectical behavior']),
                ('Psychodynamic', ['psychodynamic', 'psychoanalytic']),
                ('Humanistic', ['humanistic', 'person-centered']),
                ('EMDR', ['emdr', 'eye movement']),
                ('Solution Focused', ['solution focused', 'brief therapy']),
                ('Family Systems', ['family systems', 'systemic']),
                ('Mindfulness-Based', ['mindfulness', 'meditation', 'mbsr'])
            ]
            
            for therapy_name, keywords in therapy_patterns:
                if any(keyword in text_lower for keyword in keywords):
                    therapy_types.append(therapy_name)
            
            if therapy_types:
                therapist_data['therapy_types'] = therapy_types
            
            # Extract session fee
            fee_patterns = [
                r'\$(\d+)(?:-\$?(\d+))?\s*(?:per\s*session|session|fee)',
                r'Fee[:\s]*\$(\d+)(?:-\$?(\d+))?',
                r'Session[:\s]*\$(\d+)(?:-\$?(\d+))?'
            ]
            
            for pattern in fee_patterns:
                fee_match = re.search(pattern, text_content, re.IGNORECASE)
                if fee_match:
                    if fee_match.group(2):
                        therapist_data['session_fee'] = f"${fee_match.group(1)}-${fee_match.group(2)}"
                    else:
                        therapist_data['session_fee'] = f"${fee_match.group(1)}"
                    break
            
            # Extract insurance information
            insurance_info = []
            insurance_patterns = [
                ('Aetna', ['aetna']),
                ('Blue Cross Blue Shield', ['blue cross', 'bcbs']),
                ('Cigna', ['cigna']),
                ('UnitedHealth', ['united health', 'unitedhealthcare']),
                ('Kaiser', ['kaiser']),
                ('Medicare', ['medicare']),
                ('Medicaid', ['medicaid', 'medi-cal']),
                ('Out of Network', ['out of network', 'out-of-network'])
            ]
            
            for insurance_name, keywords in insurance_patterns:
                if any(keyword in text_lower for keyword in keywords):
                    insurance_info.append(insurance_name)
            
            # Check for sliding scale
            if 'sliding scale' in text_lower:
                insurance_info.append('Sliding Scale')
            
            if insurance_info:
                therapist_data['insurance_accepted'] = insurance_info
            
            # Extract age groups served
            age_groups = []
            if 'children' in text_lower or 'child' in text_lower:
                age_groups.append('Children')
            if 'adolescent' in text_lower or 'teen' in text_lower:
                age_groups.append('Adolescents')
            if 'adult' in text_lower:
                age_groups.append('Adults')
            if 'elder' in text_lower or 'senior' in text_lower:
                age_groups.append('Seniors')
            
            if age_groups:
                therapist_data['age_groups'] = age_groups
            
            # Extract telehealth availability
            if any(term in text_lower for term in ['telehealth', 'online', 'video', 'remote']):
                therapist_data['telehealth'] = True
            
            # Extract website if available
            links = container.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.startswith('http') and 'psychologytoday.com' not in href:
                    therapist_data['website'] = href
                    break
            
            # Extract profile URL
            profile_links = container.find_all('a', href=True)
            for link in profile_links:
                href = link['href']
                if 'psychologytoday.com' in href and '/therapists/' in href:
                    therapist_data['profile_url'] = urljoin(self.base_url, href)
                    break
            
            # Extract description/bio
            bio_patterns = [
                r'I\s+(?:am|work|help|specialize|provide|offer)(.{100,500}?)(?:\.|$)',
                r'My\s+(?:approach|practice|goal|focus)(.{100,500}?)(?:\.|$)',
                r'As\s+a\s+(?:therapist|counselor)(.{100,500}?)(?:\.|$)'
            ]
            
            for pattern in bio_patterns:
                bio_match = re.search(pattern, text_content, re.IGNORECASE | re.DOTALL)
                if bio_match:
                    therapist_data['bio'] = bio_match.group(0)[:400]
                    break
            
            # Generate external ID
            if therapist_data.get('name'):
                name_id = re.sub(r'[^a-zA-Z0-9]', '_', therapist_data['name'].lower())
                therapist_data['external_id'] = f"pt_{name_id}"
            
            # Add background-friendly indicators
            therapist_data['background_friendly_score'] = 0.8  # Licensed therapists
            therapist_data['background_friendly_reasons'] = [
                "Licensed mental health professional",
                "Bound by confidentiality and professional ethics",
                "Regulated healthcare provider"
            ]
            
            return therapist_data
            
        except Exception as e:
            logger.error(f"Error extracting Psychology Today therapist data: {e}")
            return {}

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    config = {
        "name": "Psychology Today",
        "base_url": "https://www.psychologytoday.com",
        "rate_limit": 2,
        "max_pages": 2
    }
    
    scraper = PsychologyTodayScraper(config)
    therapists = scraper.scrape_therapists("Los Angeles, CA", "anxiety")
    
    print(f"Found {len(therapists)} therapists")
    for therapist in therapists[:3]:
        print(f"- {therapist.get('name', 'N/A')} {therapist.get('credentials', '')}")
        print(f"  Phone: {therapist.get('phone', 'N/A')}")
        print(f"  Specialties: {therapist.get('specialties', 'N/A')}")
        print(f"  Fee: {therapist.get('session_fee', 'N/A')}")
        print(f"  Insurance: {therapist.get('insurance_accepted', 'N/A')}")
        print()
