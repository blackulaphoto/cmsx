"""
BuiltInLA job scraper using the new modular architecture
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
from backend.base_scraper import HTMLScraper

logger = logging.getLogger(__name__)

class BuiltInLAScraper(HTMLScraper):
    """BuiltInLA.com job scraper for tech jobs in Los Angeles"""
    
    def __init__(self, config: Dict[str, Any], ai_analyzer=None):
        super().__init__(config)
        self.name = "BuiltInLA"
    
    def scrape(self, keywords: str = '', location: str = 'Los Angeles, CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Main scraping method - required by base class"""
        return self.scrape_jobs(keywords, location, max_pages)
    
    def scrape_jobs(self, keywords: str = '', location: str = 'Los Angeles, CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape jobs from BuiltInLA.com
        
        Args:
            keywords: Search keywords
            location: Job location (ignored as BuiltInLA is LA-specific)
            max_pages: Maximum pages to scrape
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        max_pages = max_pages or self.max_pages
        
        logger.info(f"Starting BuiltInLA scrape for '{keywords}'")
        
        for page in range(max_pages):
            try:
                # Use search URL from configuration
                url = self.search_url.format(keywords=quote_plus(str(keywords)))
                if page > 1:
                    # Add pagination if needed
                    url += f"&page={page}"
                
                logger.debug(f"Scraping BuiltInLA page {page + 1}: {url}")
                
                response = self._make_request(url)
                if not response:
                    logger.warning(f"Failed to get response for BuiltInLA page {page + 1}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_jobs = self.parse_job_cards(soup)
                
                if not page_jobs:
                    logger.info(f"No jobs found on BuiltInLA page {page + 1}, stopping")
                    break
                
                jobs.extend(page_jobs)
                logger.info(f"Found {len(page_jobs)} jobs on BuiltInLA page {page + 1}")
                
                # Rate limiting
                self._rate_limit_delay()
                
            except Exception as e:
                logger.error(f"Error scraping BuiltInLA page {page + 1}: {e}")
                continue
        
        logger.info(f"Total jobs scraped from BuiltInLA: {len(jobs)}")
        return jobs
    
    def extract_job_from_card(self, card) -> Dict[str, Any]:
        """
        Extract job data from a single BuiltInLA job card
        
        Args:
            card: BeautifulSoup element representing a job card
            
        Returns:
            Raw job dictionary
        """
        try:
            # BuiltInLA has multiple possible selectors for job cards
            # Try different selectors for title
            title_elem = (
                card.find('h2', class_='job-title') or
                card.find('h3', class_='job-title') or
                card.find('a', class_='job-title') or
                card.find('h2') or
                card.find('h3') or
                card.select_one('[data-id] h2') or
                card.select_one('[data-id] h3')
            )
            
            title = ''
            job_url = ''
            
            if title_elem:
                title = title_elem.get_text(strip=True)
                # Try to find the link
                link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
                if link_elem and link_elem.get('href'):
                    job_url = urljoin('https://builtin.com', link_elem['href'])
            
            # Extract company name
            company_elem = (
                card.find('div', class_='company-name') or
                card.find('span', class_='company-name') or
                card.find('a', class_='company-name') or
                card.find('div', class_='company') or
                card.select_one('.job-company') or
                card.select_one('[data-company]')
            )
            
            company = company_elem.get_text(strip=True) if company_elem else 'Unknown Company'
            
            # Extract location (usually Los Angeles area)
            location_elem = (
                card.find('div', class_='job-location') or
                card.find('span', class_='location') or
                card.select_one('.location')
            )
            location = location_elem.get_text(strip=True) if location_elem else 'Los Angeles, CA'
            
            # Extract job description/summary
            description_elem = (
                card.find('div', class_='job-description') or
                card.find('div', class_='description') or
                card.find('p', class_='job-summary') or
                card.find('p') or
                card.select_one('.job-snippet')
            )
            description = description_elem.get_text(strip=True) if description_elem else ''
            
            # Extract salary if available
            salary_elem = (
                card.find('div', class_='salary') or
                card.find('span', class_='salary') or
                card.select_one('.compensation')
            )
            salary = salary_elem.get_text(strip=True) if salary_elem else ''
            
            # Extract job type and experience level
            job_type_elem = card.find('span', class_='job-type')
            job_type = job_type_elem.get_text(strip=True) if job_type_elem else 'full-time'
            
            # Generate external ID
            job_id = ''
            if job_url:
                # Extract ID from URL
                match = re.search(r'/jobs/(\d+)', job_url)
                if match:
                    job_id = match.group(1)
            
            external_id = f"builtinla_{job_id}" if job_id else f"builtinla_{hash(title + company)}"
            
            # Determine experience level
            experience_level = self._determine_experience_level(title, description)
            
            # Extract additional details if available
            tags_elem = card.find('div', class_='job-tags')
            tags = []
            if tags_elem:
                tag_elements = tags_elem.find_all('span', class_='tag')
                tags = [tag.get_text(strip=True) for tag in tag_elements]
            
            job_data = {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'salary_range': salary,
                'job_type': job_type,
                'experience_level': experience_level,
                'source_url': job_url,
                'external_id': external_id,
                'tags': tags,
                'scraped_date': datetime.utcnow()
            }
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error extracting job from BuiltInLA card: {e}")
            return {}
    
    def _determine_experience_level(self, title: str, description: str) -> str:
        """Determine experience level from job title and description"""
        text = (title + ' ' + description).lower()
        
        # Tech-specific keywords
        entry_keywords = [
            'entry level', 'entry-level', 'junior', 'associate', 'trainee',
            'new grad', 'recent graduate', 'intern', 'level i', 'level 1'
        ]
        senior_keywords = [
            'senior', 'sr.', 'lead', 'principal', 'staff', 'architect',
            'director', 'manager', 'head of', 'vp', 'vice president',
            'level iii', 'level 3', 'level iv', 'level 4'
        ]
        mid_keywords = [
            'mid level', 'mid-level', 'level ii', 'level 2', 'experienced'
        ]
        
        for keyword in senior_keywords:
            if keyword in text:
                return 'senior'
        
        for keyword in entry_keywords:
            if keyword in text:
                return 'entry'
        
        for keyword in mid_keywords:
            if keyword in text:
                return 'mid'
        
        # Default to mid for tech jobs if unclear
        return 'mid'
    
    def parse_job_cards(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Parse job cards from BuiltInLA HTML
        Override to handle BuiltInLA's specific structure
        """
        jobs = []
        
        # Try multiple selectors for job cards
        job_cards = (
            soup.find_all('div', class_='company-job-item') or
            soup.find_all('div', class_='job-item') or
            soup.find_all('article', class_='job') or
            soup.find_all('div', {'data-id': True}) or
            soup.select('.job-list .job') or
            soup.select('[data-testid="job-card"]')
        )
        
        logger.debug(f"Found {len(job_cards)} job cards on BuiltInLA page")
        
        for card in job_cards:
            try:
                job = self.extract_job_from_card(card)
                if job and job.get('title'):
                    jobs.append(job)
            except Exception as e:
                logger.error(f"Error parsing BuiltInLA job card: {e}")
                continue
        
        return jobs

