"""
Government job scraper for LA Local Hire Portal and City of LA Personnel
These sites are excellent for background-friendly opportunities
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
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.base_scraper import BrowserScraper

logger = logging.getLogger(__name__)

class GovernmentScraper(BrowserScraper):
    """Scraper for government job portals (LA Local Hire, City Personnel, etc.)"""
    
    def __init__(self, config: Dict[str, Any], ai_analyzer=None):
        super().__init__(config)
        self.site_type = self._determine_site_type()
    
    def scrape(self, keywords: str = '', location: str = 'Los Angeles, CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Main scraping method - required by base class"""
        return self.scrape_jobs(keywords, location, max_pages)
    
    def _determine_site_type(self) -> str:
        """Determine which government site this is based on URL"""
        base_url = self.search_url.lower()
        
        if 'lalocalhire' in base_url:
            return 'la_local_hire'
        elif 'personnel.lacity' in base_url:
            return 'city_personnel'
        elif 'hr.lacounty' in base_url:
            return 'county_hr'
        elif 'caljobs' in base_url:
            return 'caljobs'
        elif 'usajobs' in base_url:
            return 'usajobs'
        else:
            return 'generic_government'
    
    def scrape_jobs(self, keywords: str = '', location: str = 'Los Angeles, CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape jobs from government portals
        
        Args:
            keywords: Search keywords
            location: Job location
            max_pages: Maximum pages to scrape
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        max_pages = max_pages or min(self.max_pages, 2)  # Government sites are slower
        
        logger.info(f"Starting {self.name} government scrape for '{keywords}'")
        
        if self.site_type == 'la_local_hire':
            jobs = self._scrape_la_local_hire(keywords, max_pages)
        elif self.site_type == 'city_personnel':
            jobs = self._scrape_city_personnel(keywords, max_pages)
        elif self.site_type == 'county_hr':
            jobs = self._scrape_county_hr(keywords, max_pages)
        else:
            jobs = self._scrape_generic_government(keywords, max_pages)
        
        logger.info(f"Total jobs scraped from {self.name}: {len(jobs)}")
        return jobs
    
    def _scrape_la_local_hire(self, keywords: str, max_pages: int) -> List[Dict[str, Any]]:
        """Scrape LA Local Hire Portal"""
        jobs = []
        
        try:
            # LA Local Hire has a specific structure
            url = "https://lalocalhire.lacity.gov/target-local-hire"
            
            logger.debug(f"Scraping LA Local Hire: {url}")
            
            response = self._make_request(url)
            if not response:
                logger.warning("Failed to get response from LA Local Hire")
                return jobs
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for job listings or opportunities
            job_elements = (
                soup.find_all('div', class_='opportunity') or
                soup.find_all('div', class_='job-listing') or
                soup.find_all('div', class_='position') or
                soup.find_all('tr') or  # Table rows
                soup.find_all('li')     # List items
            )
            
            for element in job_elements:
                try:
                    job = self._extract_government_job(element, 'la_local_hire')
                    if job and job.get('title'):
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing LA Local Hire job: {e}")
                    continue
            
            # If no specific jobs found, create general information entry
            if not jobs:
                jobs.append({
                    'title': 'LA Local Hire Program Opportunities',
                    'company': 'City of Los Angeles',
                    'location': 'Los Angeles, CA',
                    'description': 'The LA Local Hire program provides pathways into civil service careers for local residents. Visit the portal for current opportunities and application information.',
                    'job_type': 'various',
                    'experience_level': 'entry',
                    'source_url': url,
                    'external_id': 'la_local_hire_general',
                    'scraped_date': datetime.utcnow()
                })
            
        except Exception as e:
            logger.error(f"Error scraping LA Local Hire: {e}")
        
        return jobs
    
    def _scrape_city_personnel(self, keywords: str, max_pages: int) -> List[Dict[str, Any]]:
        """Scrape City of LA Personnel Jobs Portal"""
        jobs = []
        
        try:
            # City Personnel portal
            base_url = "https://personnel.lacity.gov/jobs"
            
            if keywords:
                url = f"{base_url}?search={quote_plus(keywords)}"
            else:
                url = base_url
            
            logger.debug(f"Scraping City Personnel: {url}")
            
            response = self._make_request(url)
            if not response:
                logger.warning("Failed to get response from City Personnel")
                return jobs
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for job listings
            job_elements = (
                soup.find_all('div', class_='job-item') or
                soup.find_all('div', class_='position') or
                soup.find_all('tr', class_='job-row') or
                soup.find_all('li', class_='job') or
                soup.select('.job-listing') or
                soup.select('table tr')[1:]  # Skip header row
            )
            
            for element in job_elements:
                try:
                    job = self._extract_government_job(element, 'city_personnel')
                    if job and job.get('title'):
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing City Personnel job: {e}")
                    continue
            
            # If no specific jobs found, create general information entry
            if not jobs:
                jobs.append({
                    'title': 'City of Los Angeles Civil Service Positions',
                    'company': 'City of Los Angeles',
                    'location': 'Los Angeles, CA',
                    'description': 'The City of Los Angeles offers over 1,200 job classifications across 44 departments. Many positions offer excellent benefits and career advancement opportunities.',
                    'job_type': 'full-time',
                    'experience_level': 'various',
                    'source_url': url,
                    'external_id': 'city_personnel_general',
                    'scraped_date': datetime.utcnow()
                })
            
        except Exception as e:
            logger.error(f"Error scraping City Personnel: {e}")
        
        return jobs
    
    def _scrape_county_hr(self, keywords: str, max_pages: int) -> List[Dict[str, Any]]:
        """Scrape LA County HR"""
        jobs = []
        
        try:
            url = "https://hr.lacounty.gov/careers"
            
            response = self._make_request(url)
            if not response:
                return jobs
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Create general entry for LA County
            jobs.append({
                'title': 'LA County Employment Opportunities',
                'company': 'Los Angeles County',
                'location': 'Los Angeles County, CA',
                'description': 'LA County serves 100,000+ employees across 36+ departments with 2,300+ job classifications. Excellent benefits and diverse opportunities available.',
                'job_type': 'full-time',
                'experience_level': 'various',
                'source_url': url,
                'external_id': 'la_county_general',
                'scraped_date': datetime.utcnow()
            })
            
        except Exception as e:
            logger.error(f"Error scraping LA County HR: {e}")
        
        return jobs
    
    def _scrape_generic_government(self, keywords: str, max_pages: int) -> List[Dict[str, Any]]:
        """Generic government site scraper"""
        jobs = []
        
        try:
            url = self.search_url.format(
                keywords=quote_plus(keywords),
                location=quote_plus('Los Angeles, CA')
            ) if self.search_url else self.base_url
            
            response = self._make_request(url)
            if not response:
                return jobs
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Generic job extraction
            job_elements = soup.find_all(['div', 'li', 'tr'], class_=re.compile(r'job|position|listing'))
            
            for element in job_elements:
                try:
                    job = self._extract_government_job(element, 'generic')
                    if job and job.get('title'):
                        jobs.append(job)
                except Exception as e:
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping generic government site: {e}")
        
        return jobs
    
    def _extract_government_job(self, element, site_type: str) -> Dict[str, Any]:
        """Extract job data from government job element"""
        try:
            # Extract title
            title_elem = (
                element.find('h1') or element.find('h2') or element.find('h3') or
                element.find('a') or element.find('strong') or
                element.find('td')  # For table-based layouts
            )
            
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Skip if title is too short or generic
            if len(title) < 5 or title.lower() in ['job', 'position', 'opportunity']:
                return {}
            
            # Extract link if available
            link_elem = element.find('a')
            job_url = ''
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                if href.startswith('http'):
                    job_url = href
                else:
                    job_url = urljoin(self.base_url, href)
            
            # Extract description
            desc_elem = element.find('p') or element.find('div', class_='description')
            description = desc_elem.get_text(strip=True) if desc_elem else title
            
            # Government jobs are typically full-time and background-friendly
            company = self._get_company_name(site_type)
            
            external_id = f"{site_type}_{hash(title)}"
            
            job_data = {
                'title': title,
                'company': company,
                'location': 'Los Angeles, CA',
                'description': description,
                'job_type': 'full-time',
                'experience_level': 'various',
                'source_url': job_url or self.base_url,
                'external_id': external_id,
                'scraped_date': datetime.utcnow()
            }
            
            return job_data
            
        except Exception as e:
            logger.debug(f"Error extracting government job: {e}")
            return {}
    
    def _get_company_name(self, site_type: str) -> str:
        """Get appropriate company name for government site"""
        company_map = {
            'la_local_hire': 'City of Los Angeles - Local Hire',
            'city_personnel': 'City of Los Angeles',
            'county_hr': 'Los Angeles County',
            'caljobs': 'State of California',
            'usajobs': 'Federal Government',
            'generic': 'Government Agency'
        }
        return company_map.get(site_type, 'Government Agency')

