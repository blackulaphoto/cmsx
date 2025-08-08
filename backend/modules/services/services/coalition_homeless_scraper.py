"""
Coalition for the Homeless Directory scraper
Scrapes homeless shelter directory from homelessshelterdirectory.org
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

class CoalitionHomelessScraper(BaseScraper):
    """Scraper for Coalition for the Homeless Directory"""
    
    def __init__(self, config: Dict[str, Any], ai_analyzer=None):
        super().__init__(config, ai_analyzer)
        self.base_url = "https://www.homelessshelterdirectory.org"
        self.search_url = "https://www.homelessshelterdirectory.org/cgi-bin/id/city.cgi"
        
    def scrape_jobs(self, keywords: str = '', location: str = 'Los Angeles, CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape jobs - Not applicable for Coalition Homeless Scraper
        This method is required by the abstract base class but not used for this scraper
        """
        return []

    def scrape_resources(self, location: str = 'Los Angeles', state: str = 'CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape homeless shelter directory resources
        
        Args:
            location: City to search
            state: State abbreviation
            max_pages: Maximum pages to scrape
            
        Returns:
            List of resource dictionaries
        """
        resources = []
        max_pages = max_pages or self.max_pages
        
        logger.info(f"Starting Coalition for the Homeless scrape for {location}, {state}")
        
        for page in range(max_pages):
            try:
                # Build search URL
                if page == 0:
                    url = f"{self.search_url}?city={quote_plus(location)}&state={state}"
                else:
                    url = f"{self.search_url}?city={quote_plus(location)}&state={state}&page={page + 1}"
                
                logger.debug(f"Scraping Coalition page {page + 1}: {url}")
                
                response = self._make_request(url)
                if not response:
                    logger.warning(f"Failed to get response for Coalition page {page + 1}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_resources = self.parse_resource_cards(soup, location, state)
                
                if not page_resources:
                    logger.info(f"No resources found on Coalition page {page + 1}, stopping")
                    break
                
                resources.extend(page_resources)
                logger.info(f"Found {len(page_resources)} resources on Coalition page {page + 1}")
                
                # Rate limiting
                self._rate_limit_delay()
                
            except Exception as e:
                logger.error(f"Error scraping Coalition page {page + 1}: {e}")
                continue
        
        logger.info(f"Total resources scraped from Coalition: {len(resources)}")
        return resources
    
    def parse_resource_cards(self, soup: BeautifulSoup, location: str, state: str) -> List[Dict[str, Any]]:
        """Parse resource cards from the page"""
        resources = []
        
        # Look for resource listings - typically in divs or table rows
        resource_containers = soup.find_all(['div', 'tr', 'li'], class_=re.compile(r'(listing|shelter|resource|result)', re.I))
        
        # If no class-based containers found, look for structural patterns
        if not resource_containers:
            # Look for tables with shelter data
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                resource_containers.extend(rows)
        
        # Also look for div containers with contact info patterns
        if not resource_containers:
            resource_containers = soup.find_all('div')
            resource_containers = [div for div in resource_containers if self._contains_shelter_info(div)]
        
        logger.info(f"Found {len(resource_containers)} potential resource containers")
        
        for container in resource_containers:
            try:
                resource_data = self.extract_resource_from_container(container, location, state)
                if resource_data and resource_data.get('name'):
                    resources.append(resource_data)
            except Exception as e:
                logger.warning(f"Error extracting resource from container: {e}")
                continue
        
        return resources
    
    def _contains_shelter_info(self, element) -> bool:
        """Check if element contains shelter/resource information"""
        text = element.get_text().upper()
        shelter_indicators = [
            'SHELTER', 'HOUSING', 'TRANSITIONAL', 'EMERGENCY', 'HOMELESS',
            'MISSION', 'SALVATION ARMY', 'CATHOLIC CHARITIES', 'RESCUE',
            'FOOD BANK', 'SOUP KITCHEN', 'PHONE:', 'ADDRESS:', 'HOURS:'
        ]
        
        return any(indicator in text for indicator in shelter_indicators)
    
    def extract_resource_from_container(self, container, location: str, state: str) -> Dict[str, Any]:
        """Extract resource information from a container element"""
        try:
            resource_data = {
                'scraped_date': datetime.now().isoformat(),
                'source_site': 'coalition_homeless_directory',
                'resource_type': 'Housing/Shelter',
                'location': f"{location}, {state}"
            }
            
            text_content = container.get_text(separator=' ', strip=True)
            
            # Extract name - usually the first line or in a header tag
            name_element = container.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
            if name_element:
                resource_data['name'] = name_element.get_text(strip=True)
            else:
                # Try to extract from first line of text
                lines = text_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 5 and not line.startswith(('Phone:', 'Address:', 'Hours:')):
                        resource_data['name'] = line
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
                    resource_data['phone'] = phone_match.group(1)
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
                    resource_data['address'] = address_match.group(1).strip()
                    break
            
            # Extract hours
            hours_patterns = [
                r'Hours[:\s]*([^,\n]+)',
                r'Open[:\s]*([^,\n]+)',
                r'Available[:\s]*([^,\n]+)'
            ]
            
            for pattern in hours_patterns:
                hours_match = re.search(pattern, text_content, re.IGNORECASE)
                if hours_match:
                    resource_data['hours'] = hours_match.group(1).strip()
                    break
            
            # Extract services offered
            services = []
            service_indicators = [
                ('Emergency Shelter', ['emergency', 'overnight', '24-hour']),
                ('Transitional Housing', ['transitional', 'temporary housing']),
                ('Food Services', ['meals', 'food', 'soup kitchen', 'food bank']),
                ('Case Management', ['case management', 'social services']),
                ('Job Training', ['job training', 'employment', 'vocational']),
                ('Mental Health', ['mental health', 'counseling', 'therapy']),
                ('Substance Abuse', ['substance abuse', 'addiction', 'recovery'])
            ]
            
            text_lower = text_content.lower()
            for service_name, keywords in service_indicators:
                if any(keyword in text_lower for keyword in keywords):
                    services.append(service_name)
            
            if services:
                resource_data['services'] = services
            
            # Extract description
            description_parts = []
            
            # Look for description sections
            desc_patterns = [
                r'Description[:\s]*(.+?)(?:Phone|Address|Hours|$)',
                r'Services[:\s]*(.+?)(?:Phone|Address|Hours|$)',
                r'About[:\s]*(.+?)(?:Phone|Address|Hours|$)'
            ]
            
            for pattern in desc_patterns:
                desc_match = re.search(pattern, text_content, re.IGNORECASE | re.DOTALL)
                if desc_match:
                    description_parts.append(desc_match.group(1).strip())
                    break
            
            if description_parts:
                resource_data['description'] = description_parts[0][:500]  # Limit length
            else:
                # Use cleaned text content as description
                clean_text = re.sub(r'(Phone|Address|Hours)[:\s]*[^\n]*', '', text_content)
                if len(clean_text.strip()) > 20:
                    resource_data['description'] = clean_text.strip()[:300]
            
            # Extract website if available
            links = container.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.startswith('http') and 'homelessshelterdirectory.org' not in href:
                    resource_data['website'] = href
                    break
            
            # Set eligibility and requirements
            eligibility_keywords = ['men', 'women', 'families', 'children', 'veterans', 'disabled']
            eligibility = []
            for keyword in eligibility_keywords:
                if keyword in text_lower:
                    eligibility.append(keyword.title())
            
            if eligibility:
                resource_data['eligibility'] = eligibility
            
            # Generate external ID
            if resource_data.get('name'):
                name_id = re.sub(r'[^a-zA-Z0-9]', '_', resource_data['name'].lower())
                resource_data['external_id'] = f"coalition_{name_id}"
            
            # Add background-friendly indicators
            resource_data['background_friendly_score'] = 0.9  # Homeless resources typically very accessible
            resource_data['background_friendly_reasons'] = [
                "Emergency housing service with minimal barriers",
                "Serves vulnerable populations",
                "No background check typically required for emergency services"
            ]
            
            return resource_data
            
        except Exception as e:
            logger.error(f"Error extracting Coalition resource data: {e}")
            return {}

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    config = {
        "name": "Coalition for the Homeless",
        "base_url": "https://www.homelessshelterdirectory.org",
        "rate_limit": 2,
        "max_pages": 2
    }
    
    scraper = CoalitionHomelessScraper(config)
    resources = scraper.scrape_resources("Los Angeles", "CA")
    
    print(f"Found {len(resources)} resources")
    for resource in resources[:3]:
        print(f"- {resource.get('name', 'N/A')}")
        print(f"  Phone: {resource.get('phone', 'N/A')}")
        print(f"  Services: {resource.get('services', 'N/A')}")
        print(f"  {resource.get('description', 'N/A')[:100]}...")
        print()
