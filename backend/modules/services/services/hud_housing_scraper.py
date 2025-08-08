"""
HUD Housing Resources scraper
Scrapes housing assistance programs from hud.gov
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

class HUDHousingScraper(BaseScraper):
    """Scraper for HUD Housing Resources"""
    
    def __init__(self, config: Dict[str, Any], ai_analyzer=None):
        super().__init__(config, ai_analyzer)
        self.base_url = "https://www.hud.gov"
        self.search_url = "https://www.hud.gov/findhomes"
        self.pha_search_url = "https://www.hud.gov/program_offices/public_indian_housing/pha/contacts"
        
    def scrape_housing_resources(self, location: str = 'Los Angeles, CA', program_type: str = '', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape HUD housing resources
        
        Args:
            location: Location to search
            program_type: Type of housing program (section8, public_housing, etc.)
            max_pages: Maximum pages to scrape
            
        Returns:
            List of housing resource dictionaries
        """
        resources = []
        max_pages = max_pages or self.max_pages
        
        logger.info(f"Starting HUD housing scrape for {location}, program: {program_type}")
        
        # Search multiple HUD resources
        search_urls = [
            (self.search_url, "Housing Search"),
            (self.pha_search_url, "Public Housing Authorities")
        ]
        
        for base_url, search_type in search_urls:
            for page in range(max_pages):
                try:
                    # Build search URL
                    if location:
                        location_parts = location.split(',')
                        if len(location_parts) >= 2:
                            city = location_parts[0].strip()
                            state = location_parts[1].strip()
                        else:
                            city = location
                            state = ''
                        
                        params = []
                        if city:
                            params.append(f"city={quote_plus(city)}")
                        if state:
                            params.append(f"state={quote_plus(state)}")
                        if program_type:
                            params.append(f"program={quote_plus(program_type)}")
                        if page > 0:
                            params.append(f"page={page + 1}")
                        
                        if params:
                            url = f"{base_url}?" + "&".join(params)
                        else:
                            url = base_url
                    else:
                        url = base_url
                    
                    logger.debug(f"Scraping HUD {search_type} page {page + 1}: {url}")
                    
                    response = self._make_request(url)
                    if not response:
                        logger.warning(f"Failed to get response for HUD {search_type} page {page + 1}")
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_resources = self.parse_housing_cards(soup, location, search_type)
                    
                    if not page_resources:
                        logger.info(f"No resources found on HUD {search_type} page {page + 1}, stopping")
                        break
                    
                    resources.extend(page_resources)
                    logger.info(f"Found {len(page_resources)} resources on HUD {search_type} page {page + 1}")
                    
                    # Rate limiting
                    self._rate_limit_delay()
                    
                except Exception as e:
                    logger.error(f"Error scraping HUD {search_type} page {page + 1}: {e}")
                    continue
        
        logger.info(f"Total housing resources scraped from HUD: {len(resources)}")
        return resources
    
    def parse_housing_cards(self, soup: BeautifulSoup, location: str, search_type: str) -> List[Dict[str, Any]]:
        """Parse housing resource cards from the page"""
        resources = []
        
        # Look for housing listings
        resource_containers = soup.find_all(['div', 'tr', 'li'], class_=re.compile(r'(result|listing|pha|housing|property)', re.I))
        
        # If no class-based containers found, look for structural patterns
        if not resource_containers:
            # Look for tables with housing data
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                resource_containers.extend([row for row in rows if self._is_housing_row(row)])
        
        # Also look for div containers with housing info
        if not resource_containers:
            all_divs = soup.find_all('div')
            resource_containers = [div for div in all_divs if self._contains_housing_info(div)]
        
        logger.info(f"Found {len(resource_containers)} potential housing containers")
        
        for container in resource_containers:
            try:
                resource_data = self.extract_housing_from_container(container, location, search_type)
                if resource_data and (resource_data.get('name') or resource_data.get('property_name')):
                    resources.append(resource_data)
            except Exception as e:
                logger.warning(f"Error extracting housing resource from container: {e}")
                continue
        
        return resources
    
    def _is_housing_row(self, row) -> bool:
        """Check if table row contains housing information"""
        text = row.get_text().upper()
        cells = row.find_all(['td', 'th'])
        
        # Must have multiple cells and housing-related content
        has_cells = len(cells) >= 2
        has_housing_info = any(keyword in text for keyword in [
            'HOUSING', 'AUTHORITY', 'SECTION 8', 'VOUCHER', 'PUBLIC HOUSING',
            'PHONE', 'ADDRESS', 'CONTACT', 'WAITING LIST'
        ])
        
        return has_cells and has_housing_info
    
    def _contains_housing_info(self, element) -> bool:
        """Check if element contains housing information"""
        text = element.get_text().upper()
        housing_indicators = [
            'HOUSING AUTHORITY', 'PUBLIC HOUSING', 'SECTION 8', 'HOUSING VOUCHER',
            'AFFORDABLE HOUSING', 'HUD', 'WAITING LIST', 'RENTAL ASSISTANCE',
            'TRANSITIONAL HOUSING', 'SUPPORTIVE HOUSING'
        ]
        
        return any(indicator in text for indicator in housing_indicators)
    
    def extract_housing_from_container(self, container, location: str, search_type: str) -> Dict[str, Any]:
        """Extract housing resource information from a container element"""
        try:
            resource_data = {
                'scraped_date': datetime.now().isoformat(),
                'source_site': 'hud_housing',
                'resource_type': 'Housing Assistance',
                'location': location,
                'search_type': search_type
            }
            
            text_content = container.get_text(separator=' ', strip=True)
            
            # Extract organization/property name
            name_element = container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'])
            if name_element:
                resource_data['name'] = name_element.get_text(strip=True)
            else:
                # Try to extract from table cells or first meaningful line
                cells = container.find_all(['td', 'th'])
                if cells and len(cells) > 0:
                    resource_data['name'] = cells[0].get_text(strip=True)
                else:
                    # Extract from first line that looks like an organization name
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    for line in lines:
                        if len(line) > 10 and not line.startswith(('Phone:', 'Address:', 'Contact:')):
                            resource_data['name'] = line
                            break
            
            # Extract phone number
            phone_patterns = [
                r'Phone[:\s]*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
                r'Contact[:\s]*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
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
            
            # If table format, try to extract from cells
            cells = container.find_all(['td', 'th'])
            if len(cells) >= 3:
                # Common format: Name, Address, Phone
                if not resource_data.get('name') and cells[0].get_text(strip=True):
                    resource_data['name'] = cells[0].get_text(strip=True)
                
                if not resource_data.get('address') and len(cells) > 1:
                    addr_text = cells[1].get_text(strip=True)
                    if any(keyword in addr_text.lower() for keyword in ['street', 'avenue', 'road', 'drive']):
                        resource_data['address'] = addr_text
                
                if not resource_data.get('phone') and len(cells) > 2:
                    phone_text = cells[2].get_text(strip=True)
                    phone_match = re.search(r'(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})', phone_text)
                    if phone_match:
                        resource_data['phone'] = phone_match.group(1)
            
            # Extract program types
            programs = []
            program_patterns = [
                ('Section 8 Housing Voucher', ['section 8', 'voucher', 'rental assistance']),
                ('Public Housing', ['public housing']),
                ('Transitional Housing', ['transitional', 'temporary']),
                ('Supportive Housing', ['supportive housing', 'permanent supportive']),
                ('Emergency Housing', ['emergency', 'homeless', 'shelter']),
                ('Senior Housing', ['senior', 'elderly', '62+']),
                ('Family Housing', ['family', 'families']),
                ('Disabled Housing', ['disabled', 'accessibility', 'handicapped'])
            ]
            
            text_lower = text_content.lower()
            for program_name, keywords in program_patterns:
                if any(keyword in text_lower for keyword in keywords):
                    programs.append(program_name)
            
            if programs:
                resource_data['programs'] = programs
            
            # Extract waiting list information
            waiting_list_patterns = [
                r'waiting\s+list[:\s]*([^,\n.]+)',
                r'waitlist[:\s]*([^,\n.]+)',
                r'applications[:\s]*([^,\n.]+)'
            ]
            
            for pattern in waiting_list_patterns:
                wait_match = re.search(pattern, text_content, re.IGNORECASE)
                if wait_match:
                    resource_data['waiting_list_status'] = wait_match.group(1).strip()
                    break
            
            # Check for waiting list keywords
            if any(term in text_lower for term in ['waiting list open', 'accepting applications']):
                resource_data['waiting_list_status'] = 'Open'
            elif any(term in text_lower for term in ['waiting list closed', 'not accepting']):
                resource_data['waiting_list_status'] = 'Closed'
            
            # Extract income requirements
            income_patterns = [
                r'income[:\s]*(\d+%?\s*(?:ami|area median|poverty))',
                r'(\d+%)\s*(?:ami|area median)',
                r'extremely low income',
                r'very low income',
                r'low income'
            ]
            
            income_requirements = []
            for pattern in income_patterns:
                income_match = re.search(pattern, text_content, re.IGNORECASE)
                if income_match:
                    income_requirements.append(income_match.group(0))
            
            if income_requirements:
                resource_data['income_requirements'] = income_requirements
            
            # Extract eligibility criteria
            eligibility = []
            eligibility_keywords = [
                ('Families with Children', ['families', 'children']),
                ('Elderly (62+)', ['elderly', 'senior', '62+']),
                ('Disabled', ['disabled', 'disability']),
                ('Veterans', ['veteran', 'military']),
                ('Homeless', ['homeless', 'chronically homeless']),
                ('Single Adults', ['single', 'individual'])
            ]
            
            for eligibility_type, keywords in eligibility_keywords:
                if any(keyword in text_lower for keyword in keywords):
                    eligibility.append(eligibility_type)
            
            if eligibility:
                resource_data['eligibility'] = eligibility
            
            # Extract website if available
            links = container.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.startswith('http') and 'hud.gov' not in href:
                    resource_data['website'] = href
                    break
            
            # Extract email if available
            email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            email_match = re.search(email_pattern, text_content)
            if email_match:
                resource_data['email'] = email_match.group(1)
            
            # Generate external ID
            if resource_data.get('name'):
                name_id = re.sub(r'[^a-zA-Z0-9]', '_', resource_data['name'].lower())
                resource_data['external_id'] = f"hud_{name_id}"
            
            # Add HUD-specific information
            resource_data['organization_type'] = 'Government Housing Agency'
            resource_data['funding_source'] = 'HUD/Federal'
            
            # Add background-friendly indicators
            resource_data['background_friendly_score'] = 0.7  # Government programs have requirements
            resource_data['background_friendly_reasons'] = [
                "HUD-funded housing program",
                "Government oversight and regulations",
                "Equal housing opportunity provider"
            ]
            
            return resource_data
            
        except Exception as e:
            logger.error(f"Error extracting HUD housing data: {e}")
            return {}

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    config = {
        "name": "HUD Housing",
        "base_url": "https://www.hud.gov",
        "rate_limit": 2,
        "max_pages": 2
    }
    
    scraper = HUDHousingScraper(config)
    resources = scraper.scrape_housing_resources("Los Angeles, CA", "section8")
    
    print(f"Found {len(resources)} housing resources")
    for resource in resources[:3]:
        print(f"- {resource.get('name', 'N/A')}")
        print(f"  Phone: {resource.get('phone', 'N/A')}")
        print(f"  Programs: {resource.get('programs', 'N/A')}")
        print(f"  Waiting List: {resource.get('waiting_list_status', 'N/A')}")
        print(f"  Eligibility: {resource.get('eligibility', 'N/A')}")
        print()
