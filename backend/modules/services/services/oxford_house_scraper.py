"""
Oxford House Sober Living scraper
Scrapes sober living homes from oxfordhouse.org
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

class OxfordHouseScraper(BaseScraper):
    """Scraper for Oxford House Sober Living Directory"""
    
    def __init__(self, config: Dict[str, Any], ai_analyzer=None):
        super().__init__(config, ai_analyzer)
        self.base_url = "https://www.oxfordhouse.org"
        self.search_url = "https://www.oxfordhouse.org/userfiles/file/doc/directory.php"
        
    def scrape_houses(self, state: str = 'CA', city: str = 'Los Angeles', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape Oxford House sober living homes
        
        Args:
            state: State abbreviation to search
            city: City to search (optional)
            max_pages: Maximum pages to scrape
            
        Returns:
            List of house dictionaries
        """
        houses = []
        max_pages = max_pages or self.max_pages
        
        logger.info(f"Starting Oxford House scrape for {city}, {state}")
        
        for page in range(max_pages):
            try:
                # Build search URL
                params = {
                    'state': state
                }
                
                if city:
                    params['city'] = city
                
                if page > 0:
                    params['page'] = page + 1
                
                # Construct URL
                url = f"{self.search_url}?"
                url_params = []
                for key, value in params.items():
                    url_params.append(f"{key}={quote_plus(str(value))}")
                url += "&".join(url_params)
                
                logger.debug(f"Scraping Oxford House page {page + 1}: {url}")
                
                response = self._make_request(url)
                if not response:
                    logger.warning(f"Failed to get response for Oxford House page {page + 1}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_houses = self.parse_house_cards(soup, city, state)
                
                if not page_houses:
                    logger.info(f"No houses found on Oxford House page {page + 1}, stopping")
                    break
                
                houses.extend(page_houses)
                logger.info(f"Found {len(page_houses)} houses on Oxford House page {page + 1}")
                
                # Rate limiting
                self._rate_limit_delay()
                
            except Exception as e:
                logger.error(f"Error scraping Oxford House page {page + 1}: {e}")
                continue
        
        logger.info(f"Total houses scraped from Oxford House: {len(houses)}")
        return houses
    
    def parse_house_cards(self, soup: BeautifulSoup, city: str, state: str) -> List[Dict[str, Any]]:
        """Parse house cards from the page"""
        houses = []
        
        # Look for house listings in various formats
        house_containers = soup.find_all(['div', 'tr', 'li'], class_=re.compile(r'(house|listing|directory|result)', re.I))
        
        # If no class-based containers, look for table rows (common format)
        if not house_containers:
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                # Skip header rows
                house_containers.extend([row for row in rows if self._is_house_row(row)])
        
        # Also look for div containers with house info
        if not house_containers:
            all_divs = soup.find_all('div')
            house_containers = [div for div in all_divs if self._contains_house_info(div)]
        
        logger.info(f"Found {len(house_containers)} potential house containers")
        
        for container in house_containers:
            try:
                house_data = self.extract_house_from_container(container, city, state)
                if house_data and house_data.get('name'):
                    houses.append(house_data)
            except Exception as e:
                logger.warning(f"Error extracting house from container: {e}")
                continue
        
        return houses
    
    def _is_house_row(self, row) -> bool:
        """Check if table row contains house information"""
        text = row.get_text().upper()
        cells = row.find_all(['td', 'th'])
        
        # Must have multiple cells and house-like content
        has_cells = len(cells) >= 3
        has_house_info = any(keyword in text for keyword in ['HOUSE', 'MEN', 'WOMEN', 'PHONE', 'ADDRESS'])
        
        return has_cells and has_house_info
    
    def _contains_house_info(self, element) -> bool:
        """Check if element contains house information"""
        text = element.get_text().upper()
        house_indicators = [
            'OXFORD HOUSE', 'SOBER LIVING', 'MEN\'S HOUSE', 'WOMEN\'S HOUSE',
            'RECOVERY HOUSE', 'PHONE:', 'ADDRESS:', 'CONTACT:'
        ]
        
        return any(indicator in text for indicator in house_indicators)
    
    def extract_house_from_container(self, container, city: str, state: str) -> Dict[str, Any]:
        """Extract house information from a container element"""
        try:
            house_data = {
                'scraped_date': datetime.now().isoformat(),
                'source_site': 'oxford_house',
                'resource_type': 'Sober Living',
                'location': f"{city}, {state}",
                'organization': 'Oxford House'
            }
            
            text_content = container.get_text(separator=' ', strip=True)
            
            # Extract house name
            name_element = container.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
            if name_element:
                house_data['name'] = name_element.get_text(strip=True)
            else:
                # Try to extract from table cells or first meaningful line
                cells = container.find_all(['td', 'th'])
                if cells and len(cells) > 0:
                    # First cell is usually the house name
                    house_data['name'] = cells[0].get_text(strip=True)
                else:
                    # Extract from first line that looks like a house name
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    for line in lines:
                        if 'house' in line.lower() or 'oxford' in line.lower():
                            house_data['name'] = line
                            break
            
            # Extract phone number
            phone_patterns = [
                r'Phone[:\s]*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
                r'Contact[:\s]*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
                r'(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
            ]
            
            for pattern in phone_patterns:
                phone_match = re.search(pattern, text_content, re.IGNORECASE)
                if phone_match:
                    house_data['phone'] = phone_match.group(1)
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
                    house_data['address'] = address_match.group(1).strip()
                    break
            
            # If table format, try to extract from cells
            cells = container.find_all(['td', 'th'])
            if len(cells) >= 3:
                # Common format: Name, Address, Phone
                if not house_data.get('name') and cells[0].get_text(strip=True):
                    house_data['name'] = cells[0].get_text(strip=True)
                
                if not house_data.get('address') and cells[1].get_text(strip=True):
                    house_data['address'] = cells[1].get_text(strip=True)
                
                if not house_data.get('phone') and cells[2].get_text(strip=True):
                    phone_text = cells[2].get_text(strip=True)
                    phone_match = re.search(r'(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})', phone_text)
                    if phone_match:
                        house_data['phone'] = phone_match.group(1)
            
            # Extract gender served
            gender_info = []
            text_lower = text_content.lower()
            if 'men' in text_lower and 'women' not in text_lower:
                gender_info.append('Men')
            elif 'women' in text_lower and 'men' not in text_lower:
                gender_info.append('Women')
            elif 'men' in text_lower and 'women' in text_lower:
                gender_info.extend(['Men', 'Women'])
            
            if gender_info:
                house_data['serves'] = gender_info
            
            # Extract capacity if mentioned
            capacity_match = re.search(r'(\d+)\s*(?:bed|resident|capacity)', text_content, re.IGNORECASE)
            if capacity_match:
                house_data['capacity'] = f"{capacity_match.group(1)} residents"
            
            # Extract contact person if mentioned
            contact_patterns = [
                r'Contact[:\s]*([A-Za-z\s]+)(?:\s|Phone|$)',
                r'Manager[:\s]*([A-Za-z\s]+)(?:\s|Phone|$)',
                r'Director[:\s]*([A-Za-z\s]+)(?:\s|Phone|$)'
            ]
            
            for pattern in contact_patterns:
                contact_match = re.search(pattern, text_content, re.IGNORECASE)
                if contact_match:
                    contact_name = contact_match.group(1).strip()
                    if len(contact_name) > 2 and len(contact_name) < 50:
                        house_data['contact_person'] = contact_name
                    break
            
            # Set Oxford House specific details
            house_data['program_type'] = 'Peer-Run Sober Living'
            house_data['requirements'] = [
                'Minimum 30 days sobriety',
                'Commitment to recovery',
                'Willingness to follow house rules',
                'Employment or income source'
            ]
            
            house_data['services'] = [
                'Peer support',
                'Sober living environment',
                'Group meetings',
                'Accountability system'
            ]
            
            # Extract website or email if available
            links = container.find_all('a', href=True)
            for link in links:
                href = link['href']
                if '@' in href and href.startswith('mailto:'):
                    house_data['email'] = href.replace('mailto:', '')
                elif href.startswith('http') and 'oxfordhouse.org' not in href:
                    house_data['website'] = href
            
            # Generate external ID
            if house_data.get('name'):
                name_id = re.sub(r'[^a-zA-Z0-9]', '_', house_data['name'].lower())
                house_data['external_id'] = f"oxford_{state.lower()}_{name_id}"
            
            # Add background-friendly indicators
            house_data['background_friendly_score'] = 0.6  # Oxford Houses have structured requirements
            house_data['background_friendly_reasons'] = [
                "Peer-run recovery community",
                "Focus on sobriety and mutual support",
                "Structured program with clear guidelines"
            ]
            
            return house_data
            
        except Exception as e:
            logger.error(f"Error extracting Oxford House data: {e}")
            return {}

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    config = {
        "name": "Oxford House",
        "base_url": "https://www.oxfordhouse.org",
        "rate_limit": 2,
        "max_pages": 2
    }
    
    scraper = OxfordHouseScraper(config)
    houses = scraper.scrape_houses("CA", "Los Angeles")
    
    print(f"Found {len(houses)} houses")
    for house in houses[:3]:
        print(f"- {house.get('name', 'N/A')}")
        print(f"  Address: {house.get('address', 'N/A')}")
        print(f"  Phone: {house.get('phone', 'N/A')}")
        print(f"  Serves: {house.get('serves', 'N/A')}")
        print(f"  Requirements: {house.get('requirements', 'N/A')}")
        print()
