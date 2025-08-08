"""
SAMHSA Behavioral Health Treatment Locator scraper
Scrapes treatment facilities from findtreatment.samhsa.gov
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

class SAMHSATreatmentScraper(BaseScraper):
    """Scraper for SAMHSA Behavioral Health Treatment Locator"""
    
    def __init__(self, config: Dict[str, Any], ai_analyzer=None):
        super().__init__(config, ai_analyzer)
        self.base_url = "https://findtreatment.samhsa.gov"
        self.search_url = "https://findtreatment.samhsa.gov/locator"
        
    def scrape_jobs(self, keywords: str = '', location: str = 'Los Angeles, CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape jobs - Not applicable for SAMHSA Treatment Scraper
        This method is required by the abstract base class but not used for this scraper
        """
        return []

    def scrape_providers(self, location: str = 'Los Angeles, CA', treatment_type: str = '', distance: int = 25, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape SAMHSA treatment providers
        
        Args:
            location: Location to search (city, state or zip)
            treatment_type: Type of treatment (substance abuse, mental health, etc.)
            distance: Search radius in miles
            max_pages: Maximum pages to scrape
            
        Returns:
            List of provider dictionaries
        """
        providers = []
        max_pages = max_pages or self.max_pages
        
        logger.info(f"Starting SAMHSA scrape for {location}, treatment: {treatment_type}")
        
        for page in range(max_pages):
            try:
                # Build search URL with parameters
                params = {
                    'location': location,
                    'distance': distance
                }
                
                if treatment_type:
                    params['type'] = treatment_type
                
                if page > 0:
                    params['page'] = page + 1
                
                # Construct URL
                url = f"{self.search_url}?"
                url_params = []
                for key, value in params.items():
                    url_params.append(f"{key}={quote_plus(str(value))}")
                url += "&".join(url_params)
                
                logger.debug(f"Scraping SAMHSA page {page + 1}: {url}")
                
                response = self._make_request(url)
                if not response:
                    logger.warning(f"Failed to get response for SAMHSA page {page + 1}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_providers = self.parse_provider_cards(soup, location)
                
                if not page_providers:
                    logger.info(f"No providers found on SAMHSA page {page + 1}, stopping")
                    break
                
                providers.extend(page_providers)
                logger.info(f"Found {len(page_providers)} providers on SAMHSA page {page + 1}")
                
                # Rate limiting
                self._rate_limit_delay()
                
            except Exception as e:
                logger.error(f"Error scraping SAMHSA page {page + 1}: {e}")
                continue
        
        logger.info(f"Total providers scraped from SAMHSA: {len(providers)}")
        return providers
    
    def parse_provider_cards(self, soup: BeautifulSoup, location: str) -> List[Dict[str, Any]]:
        """Parse provider cards from the page"""
        providers = []
        
        # Look for provider listings in various container types
        provider_containers = soup.find_all(['div', 'article', 'section'], class_=re.compile(r'(result|provider|facility|listing|card)', re.I))
        
        # If no class-based containers found, look for structural patterns
        if not provider_containers:
            # Look for divs with provider-like content
            all_divs = soup.find_all('div')
            provider_containers = [div for div in all_divs if self._contains_provider_info(div)]
        
        # Also check for list items that might contain provider info
        if not provider_containers:
            provider_containers = soup.find_all('li')
            provider_containers = [li for li in provider_containers if self._contains_provider_info(li)]
        
        logger.info(f"Found {len(provider_containers)} potential provider containers")
        
        for container in provider_containers:
            try:
                provider_data = self.extract_provider_from_container(container, location)
                if provider_data and provider_data.get('name'):
                    providers.append(provider_data)
            except Exception as e:
                logger.warning(f"Error extracting provider from container: {e}")
                continue
        
        return providers
    
    def _contains_provider_info(self, element) -> bool:
        """Check if element contains provider information"""
        text = element.get_text().upper()
        provider_indicators = [
            'TREATMENT', 'THERAPY', 'COUNSELING', 'MENTAL HEALTH', 'SUBSTANCE ABUSE',
            'REHABILITATION', 'RECOVERY', 'CLINIC', 'CENTER', 'HOSPITAL',
            'PHONE:', 'ADDRESS:', 'SERVICES:', 'ACCEPTS:', 'INSURANCE'
        ]
        
        # Must have provider indicators and be substantial content
        has_indicators = any(indicator in text for indicator in provider_indicators)
        has_substantial_content = len(text.strip()) > 100
        
        return has_indicators and has_substantial_content
    
    def extract_provider_from_container(self, container, location: str) -> Dict[str, Any]:
        """Extract provider information from a container element"""
        try:
            provider_data = {
                'scraped_date': datetime.now().isoformat(),
                'source_site': 'samhsa_treatment_locator',
                'resource_type': 'Mental Health/Addiction Treatment',
                'location': location
            }
            
            text_content = container.get_text(separator=' ', strip=True)
            
            # Extract provider name
            name_element = container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'])
            if name_element:
                provider_data['name'] = name_element.get_text(strip=True)
            else:
                # Try to extract from first meaningful line
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                for line in lines:
                    if len(line) > 10 and not line.startswith(('Phone:', 'Address:', 'Distance:')):
                        provider_data['name'] = line
                        break
            
            # Extract phone number
            phone_patterns = [
                r'Phone[:\s]*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
                r'Tel[:\s]*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
                r'(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
            ]
            
            for pattern in phone_patterns:
                phone_match = re.search(pattern, text_content, re.IGNORECASE)
                if phone_match:
                    provider_data['phone'] = phone_match.group(1)
                    break
            
            # Extract address
            address_patterns = [
                r'Address[:\s]*([^,\n]+(?:,[^,\n]+)*)',
                r'Location[:\s]*([^,\n]+(?:,[^,\n]+)*)',
                r'(\d+\s+[^,\n]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)[^,\n]*)'
            ]
            
            for pattern in address_patterns:
                address_match = re.search(pattern, text_content, re.IGNORECASE)
                if address_match:
                    provider_data['address'] = address_match.group(1).strip()
                    break
            
            # Extract distance if available
            distance_match = re.search(r'Distance[:\s]*([0-9.]+)\s*miles?', text_content, re.IGNORECASE)
            if distance_match:
                provider_data['distance'] = f"{distance_match.group(1)} miles"
            
            # Extract services offered
            services = []
            service_patterns = [
                ('Substance Abuse Treatment', ['substance abuse', 'drug treatment', 'addiction', 'detox']),
                ('Mental Health Services', ['mental health', 'psychiatric', 'psychology', 'therapy']),
                ('Outpatient Treatment', ['outpatient', 'ambulatory']),
                ('Inpatient Treatment', ['inpatient', 'residential']),
                ('Group Therapy', ['group therapy', 'group counseling']),
                ('Individual Therapy', ['individual therapy', 'individual counseling']),
                ('Crisis Services', ['crisis', 'emergency']),
                ('Medication Management', ['medication', 'psychiatric medication']),
                ('Dual Diagnosis', ['dual diagnosis', 'co-occurring'])
            ]
            
            text_lower = text_content.lower()
            for service_name, keywords in service_patterns:
                if any(keyword in text_lower for keyword in keywords):
                    services.append(service_name)
            
            if services:
                provider_data['services'] = services
            
            # Extract payment/insurance information
            payment_info = []
            payment_patterns = [
                ('Medicaid', ['medicaid']),
                ('Medicare', ['medicare']),
                ('Private Insurance', ['private insurance', 'insurance accepted']),
                ('Self-Pay', ['self-pay', 'cash', 'sliding scale']),
                ('State Funded', ['state funded', 'government funded'])
            ]
            
            for payment_type, keywords in payment_patterns:
                if any(keyword in text_lower for keyword in keywords):
                    payment_info.append(payment_type)
            
            if payment_info:
                provider_data['payment_accepted'] = payment_info
            
            # Extract specialties
            specialties = []
            specialty_keywords = [
                ('Adolescent Treatment', ['adolescent', 'teen', 'youth']),
                ('Adult Treatment', ['adult']),
                ('Women\'s Services', ['women', 'female']),
                ('Men\'s Services', ['men', 'male']),
                ('LGBTQ+ Services', ['lgbtq', 'gay', 'lesbian', 'transgender']),
                ('Veterans Services', ['veteran', 'military']),
                ('Trauma Services', ['trauma', 'ptsd']),
                ('Family Services', ['family', 'couples'])
            ]
            
            for specialty_name, keywords in specialty_keywords:
                if any(keyword in text_lower for keyword in keywords):
                    specialties.append(specialty_name)
            
            if specialties:
                provider_data['specialties'] = specialties
            
            # Extract website if available
            links = container.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.startswith('http') and 'samhsa.gov' not in href:
                    provider_data['website'] = href
                    break
            
            # Extract description
            description_patterns = [
                r'Description[:\s]*(.+?)(?:Phone|Address|Services|$)',
                r'About[:\s]*(.+?)(?:Phone|Address|Services|$)',
                r'Services[:\s]*(.+?)(?:Phone|Address|Payment|$)'
            ]
            
            for pattern in description_patterns:
                desc_match = re.search(pattern, text_content, re.IGNORECASE | re.DOTALL)
                if desc_match:
                    provider_data['description'] = desc_match.group(1).strip()[:400]
                    break
            
            # Generate external ID
            if provider_data.get('name'):
                name_id = re.sub(r'[^a-zA-Z0-9]', '_', provider_data['name'].lower())
                provider_data['external_id'] = f"samhsa_{name_id}"
            
            # Add background-friendly indicators
            provider_data['background_friendly_score'] = 0.7  # Treatment centers may vary
            provider_data['background_friendly_reasons'] = [
                "SAMHSA-listed treatment provider",
                "Healthcare facility with patient confidentiality",
                "Focus on treatment and recovery"
            ]
            
            return provider_data
            
        except Exception as e:
            logger.error(f"Error extracting SAMHSA provider data: {e}")
            return {}

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    config = {
        "name": "SAMHSA Treatment Locator",
        "base_url": "https://findtreatment.samhsa.gov",
        "rate_limit": 2,
        "max_pages": 2
    }
    
    scraper = SAMHSATreatmentScraper(config)
    providers = scraper.scrape_providers("Los Angeles, CA", "mental health")
    
    print(f"Found {len(providers)} providers")
    for provider in providers[:3]:
        print(f"- {provider.get('name', 'N/A')}")
        print(f"  Phone: {provider.get('phone', 'N/A')}")
        print(f"  Services: {provider.get('services', 'N/A')}")
        print(f"  Payment: {provider.get('payment_accepted', 'N/A')}")
        print(f"  {provider.get('description', 'N/A')[:100]}...")
        print()
