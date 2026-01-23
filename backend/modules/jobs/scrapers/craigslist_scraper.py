"""
Craigslist job scraper - excellent source for entry-level and background-friendly jobs
"""

import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.base_scraper import HTMLScraper

logger = logging.getLogger(__name__)

class CraigslistScraper(HTMLScraper):
    """Craigslist Los Angeles job scraper"""
    
    def __init__(self, config: Dict[str, Any], ai_analyzer=None):
        super().__init__(config)
        self.name = "Craigslist"
        # Craigslist has different sections for different job types
        self.job_sections = {
            'general': 'jjj',  # general labor
            'admin': 'ofc',    # admin/office
            'customer_service': 'csr',  # customer service
            'food': 'fbh',     # food/beverage/hospitality
            'retail': 'ret',   # retail/wholesale
            'transport': 'trp', # transport
            'skilled': 'trd',  # skilled trade/craft
            'security': 'sec', # security
            'healthcare': 'hea', # healthcare
            # NEW SECTIONS FOR BETTER TARGETING:
            'creative': 'crg',  # creative gigs (photography, design, etc.)
            'gigs': 'ggg',      # general gigs (includes photography, creative work)
            'education': 'edu', # education
            'legal': 'lgl',     # legal/paralegal
            'accounting': 'acc', # accounting/finance
            'nonprofit': 'npo', # nonprofit
            'event': 'evg',     # event/wedding
            'beauty': 'bty',    # beauty/salon
            'real_estate': 'rej' # real estate
        }
    
    def scrape(self, keywords: str = '', location: str = 'Los Angeles, CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Main scraping method - required by base class"""
        return self.scrape_jobs(keywords, location, max_pages)
    
    def scrape_jobs(self, keywords: str = '', location: str = 'Los Angeles, CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Craigslist Los Angeles
        
        Args:
            keywords: Search keywords
            location: Job location (ignored for Craigslist as it's location-specific)
            max_pages: Maximum pages to scrape
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        max_pages = max_pages or self.max_pages
        
        logger.info(f"Starting Craigslist scrape for '{keywords}'")
        
        # If keywords suggest a specific category, focus on that
        target_sections = self._determine_sections(keywords)
        
        for section_name, section_code in target_sections.items():
            try:
                section_jobs = self._scrape_section(section_code, keywords, max_pages)
                jobs.extend(section_jobs)
                logger.info(f"Found {len(section_jobs)} jobs in Craigslist {section_name} section")
                
                # Rate limiting between sections
                self._rate_limit_delay()
                
            except Exception as e:
                logger.error(f"Error scraping Craigslist {section_name} section: {e}")
                continue
        
        logger.info(f"Total jobs scraped from Craigslist: {len(jobs)}")
        return jobs
    
    def _determine_sections(self, keywords: str) -> Dict[str, str]:
        """Determine which Craigslist sections to search based on keywords"""
        keywords_lower = keywords.lower()
        
        # EXPANDED section mapping with comprehensive job categories
        section_mapping = {
            'general': ['general', 'labor', 'warehouse', 'entry level', 'no experience'],
            'admin': ['admin', 'office', 'clerk', 'receptionist', 'data entry'],
            'customer_service': ['customer service', 'call center', 'support', 'representative'],
            'food': ['restaurant', 'server', 'cook', 'kitchen', 'food', 'barista', 'cashier'],
            'retail': ['retail', 'sales', 'store', 'cashier', 'merchandise'],
            'transport': ['driver', 'delivery', 'transport', 'logistics', 'trucking'],
            'skilled': ['maintenance', 'repair', 'construction', 'electrician', 'plumber'],
            'security': ['security', 'guard', 'patrol'],
            'healthcare': ['healthcare', 'medical', 'nurse', 'caregiver', 'assistant'],
            # NEW CATEGORIES FOR BETTER TARGETING:
            'creative': ['photographer', 'photography', 'graphic design', 'designer', 'artist', 'creative', 'video', 'marketing', 'social media'],
            'gigs': ['photographer', 'photography', 'freelance', 'gig', 'project', 'contract'],
            'education': ['teacher', 'tutor', 'instructor', 'education', 'training'],
            'legal': ['legal', 'paralegal', 'attorney', 'law'],
            'accounting': ['accounting', 'bookkeeper', 'finance', 'accountant'],
            'nonprofit': ['nonprofit', 'volunteer', 'social work', 'community'],
            'event': ['event', 'wedding', 'party', 'coordinator', 'planning'],
            'beauty': ['beauty', 'salon', 'spa', 'massage', 'hair', 'nail'],
            'real_estate': ['real estate', 'property', 'leasing', 'realtor']
        }
        
        target_sections = {}
        
        # If no specific keywords, search general labor and a few key sections
        if not keywords or len(keywords.strip()) < 3:
            target_sections = {
                'general': 'jjj',
                'admin': 'ofc',
                'food': 'fbh',
                'retail': 'ret'
            }
        else:
            # Find matching sections
            for section, section_keywords in section_mapping.items():
                if any(kw in keywords_lower for kw in section_keywords):
                    target_sections[section] = self.job_sections[section]
                    logger.info(f"Photographer search: matched section '{section}' -> '{self.job_sections[section]}'")
            
            # If no specific matches, search general
            if not target_sections:
                logger.warning(f"No section match found for '{keywords}', using general section")
                target_sections['general'] = 'jjj'
        
        return target_sections
    
    def _enhance_search_query(self, keywords: str, section: str) -> str:
        """Enhance search query with relevant synonyms"""
        enhanced_terms = []
        keywords_lower = keywords.lower()
        
        # Add synonyms based on job type
        job_synonyms = {
            'photographer': ['photographer', 'photography', 'photo', 'wedding photographer', 'portrait photographer'],
            'graphic designer': ['graphic designer', 'graphic design', 'designer', 'visual designer'],
            'marketing': ['marketing', 'social media', 'digital marketing', 'marketing coordinator'],
            'teacher': ['teacher', 'tutor', 'instructor', 'educator'],
            'nurse': ['nurse', 'nursing', 'healthcare', 'medical assistant'],
            'driver': ['driver', 'delivery driver', 'truck driver', 'rideshare'],
            'cook': ['cook', 'chef', 'kitchen', 'prep cook', 'line cook'],
            'designer': ['designer', 'graphic designer', 'web designer', 'ui designer'],
            'artist': ['artist', 'creative', 'illustrator', 'painter'],
            'video': ['video', 'videographer', 'video editor', 'filmmaker']
        }
        
        # Find matching synonyms
        for job_type, synonyms in job_synonyms.items():
            if job_type in keywords_lower:
                enhanced_terms.extend(synonyms)
                break
        
        # If no synonyms found, use original keywords
        if not enhanced_terms:
            enhanced_terms = [keywords]
        
        return ' OR '.join(f'"{term}"' for term in enhanced_terms)
    
    def _scrape_section(self, section_code: str, keywords: str, max_pages: int) -> List[Dict[str, Any]]:
        """Scrape a specific Craigslist section"""
        jobs = []
        
        for page in range(max_pages):
            try:
                # Craigslist pagination uses 's' parameter (start index)
                start = page * 120  # Craigslist shows ~120 results per page
                
                if keywords:
                    # Use enhanced query for better targeting
                    enhanced_query = self._enhance_search_query(keywords, section_code)
                    url = f"https://losangeles.craigslist.org/search/{section_code}?query={quote_plus(enhanced_query)}&sort=date&s={start}"
                else:
                    url = f"https://losangeles.craigslist.org/search/{section_code}?sort=date&s={start}"
                
                logger.debug(f"Scraping Craigslist section {section_code}, page {page + 1}: {url}")
                
                response = self._make_request(url)
                if not response:
                    logger.warning(f"Failed to get response for Craigslist section {section_code}, page {page + 1}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_jobs = self.parse_job_cards(soup)
                
                if not page_jobs:
                    logger.info(f"No jobs found on Craigslist section {section_code}, page {page + 1}, stopping")
                    break
                
                jobs.extend(page_jobs)
                
                # Rate limiting
                self._rate_limit_delay()
                
            except Exception as e:
                logger.error(f"Error scraping Craigslist section {section_code}, page {page + 1}: {e}")
                continue
        
        return jobs
    
    def parse_job_cards(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse job cards from Craigslist HTML with updated selectors"""
        jobs = []
        
        # Craigslist updated their structure - now uses cl-static-search-result
        job_cards = soup.find_all('li', class_='cl-static-search-result')
        
        for card in job_cards:
            try:
                job_data = self.extract_job_from_card(card)
                if job_data and job_data.get('title'):
                    jobs.append(job_data)
            except Exception as e:
                logger.warning(f"Error parsing Craigslist job card: {e}")
                continue
        
        return jobs
    
    def extract_job_from_card(self, card) -> Dict[str, Any]:
        """
        Extract job data from a single Craigslist job listing
        
        Args:
            card: BeautifulSoup element representing a job listing
            
        Returns:
            Raw job dictionary
        """
        try:
            # Extract job title and link - try multiple selectors
            title_elem = card.find('div', class_='title')
            if not title_elem:
                title_elem = card.find('a', class_='cl-app-anchor')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Get the job URL - try multiple approaches
            job_url = ''
            
            # Method 1: Look for anchor tag with href
            link_elem = card.find('a')
            if link_elem and link_elem.get('href'):
                job_url = link_elem.get('href')
            
            # Method 2: Look for specific Craigslist anchor class
            if not job_url:
                link_elem = card.find('a', class_='cl-app-anchor')
                if link_elem and link_elem.get('href'):
                    job_url = link_elem.get('href')
            
            # Method 3: Look in title div for nested anchor
            if not job_url and title_elem:
                nested_link = title_elem.find('a')
                if nested_link and nested_link.get('href'):
                    job_url = nested_link.get('href')
            
            # Make URL absolute if it's relative
            if job_url and job_url.startswith('/'):
                job_url = f"https://losangeles.craigslist.org{job_url}"
            
            # Extract location from div.location
            location_elem = card.find('div', class_='location')
            location = location_elem.get_text(strip=True) if location_elem else 'Los Angeles, CA'
            if location and not location.endswith('CA'):
                location = f"{location}, CA"
            
            # Extract price/salary from div.price
            price_elem = card.find('div', class_='price')
            salary = price_elem.get_text(strip=True) if price_elem else ''
            
            # Extract job ID from URL
            job_id = ''
            if job_url:
                # Craigslist URLs typically end with the job ID
                match = re.search(r'/(\d+)\.html', job_url)
                if match:
                    job_id = match.group(1)
            
            # Debug logging for URL extraction
            if not job_url:
                logger.warning(f"No URL found for Craigslist job: {title}")
            else:
                logger.debug(f"Found URL for '{title}': {job_url}")
            
            # Create standardized job dictionary
            job_data = {
                'title': title,
                'company': 'Various Employers',  # Craigslist doesn't always show company
                'location': location,
                'description': title,  # We'll get full description if we fetch the job page
                'salary': salary if salary and salary != '$0' else '',
                'job_type': 'various',
                'experience_level': 'various',
                'source_url': job_url,
                'external_id': f"craigslist_{job_id}" if job_id else f"craigslist_{hash(job_url)}",
                'scraped_date': datetime.now()
            }
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error extracting Craigslist job data: {e}")
            return {}

