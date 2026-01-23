"""
Indeed job scraper using the new modular architecture
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

class IndeedScraper(HTMLScraper):
    """Indeed.com job scraper"""
    
    def __init__(self, config: Dict[str, Any], ai_analyzer=None):
        super().__init__(config, ai_analyzer)
        self.name = "Indeed"
    
    def scrape_jobs(self, keywords: str = '', location: str = 'Los Angeles, CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Indeed.com
        
        Args:
            keywords: Search keywords
            location: Job location
            max_pages: Maximum pages to scrape
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        max_pages = max_pages or self.max_pages
        
        logger.info(f"Starting Indeed scrape for '{keywords}' in {location}")
        
        for page in range(max_pages):
            try:
                start = page * 10
                url = self.search_url.format(
                    keywords=quote_plus(str(keywords)),
                    location=quote_plus(str(location)),
                    start=start
                )
                
                logger.debug(f"Scraping Indeed page {page + 1}: {url}")
                
                response = self._make_request(url)
                if not response:
                    logger.warning(f"Failed to get response for Indeed page {page + 1}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_jobs = self.parse_job_cards(soup)
                
                if not page_jobs:
                    logger.info(f"No jobs found on Indeed page {page + 1}, stopping")
                    break
                
                jobs.extend(page_jobs)
                logger.info(f"Found {len(page_jobs)} jobs on Indeed page {page + 1}")
                
                # Rate limiting
                self._rate_limit_delay()
                
            except Exception as e:
                logger.error(f"Error scraping Indeed page {page + 1}: {e}")
                continue
        
        logger.info(f"Total jobs scraped from Indeed: {len(jobs)}")
        return jobs
    
    def extract_job_from_card(self, card) -> Dict[str, Any]:
        """
        Extract job data from a single Indeed job card
        
        Args:
            card: BeautifulSoup element representing a job card
            
        Returns:
            Raw job dictionary
        """
        try:
            # Extract job title
            title_elem = (
                card.find('span', attrs={'title': True}) or
                card.find('h2', class_='jobTitle') or
                card.find('a', {'data-jk': True}) or
                card.find('h2')
            )
            title = ''
            if title_elem:
                title = title_elem.get('title') or title_elem.get_text(strip=True)
            
            # Extract company name
            company_elem = (
                card.find('span', class_='companyName') or
                card.find('a', {'data-testid': 'company-name'}) or
                card.find('span', class_='company')
            )
            company = company_elem.get_text(strip=True) if company_elem else 'Unknown Company'
            
            # Extract location
            location_elem = (
                card.find('div', class_='companyLocation') or
                card.find('div', {'data-testid': 'job-location'}) or
                card.find('span', class_='location')
            )
            location = location_elem.get_text(strip=True) if location_elem else ''
            
            # Extract job description/summary
            description_elem = (
                card.find('div', class_='summary') or
                card.find('div', class_='job-snippet') or
                card.find('div', class_='jobSnippet') or
                card.find('span', class_='summary')
            )
            description = description_elem.get_text(strip=True) if description_elem else ''
            
            # Extract salary if available
            salary_elem = (
                card.find('span', class_='salary') or
                card.find('div', class_='salary-snippet') or
                card.find('span', class_='estimated-salary')
            )
            salary = salary_elem.get_text(strip=True) if salary_elem else ''
            
            # Extract job type if available
            job_type_elem = card.find('span', class_='jobType')
            job_type = job_type_elem.get_text(strip=True) if job_type_elem else ''
            
            # Get job ID and construct URL
            job_id = card.get('data-jk', '')
            if not job_id:
                # Try to find job ID in link
                link_elem = card.find('a', {'data-jk': True})
                if link_elem:
                    job_id = link_elem.get('data-jk', '')
            
            source_url = f"https://www.indeed.com/viewjob?jk={job_id}" if job_id else ''
            external_id = f"indeed_{job_id}" if job_id else f"indeed_{hash(title + company)}"
            
            # Extract posted date if available
            date_elem = card.find('span', class_='date')
            posted_date = None
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                posted_date = self._parse_date(date_text)
            
            # Determine experience level from title and description
            experience_level = self._determine_experience_level(title, description)
            
            job_data = {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'salary_range': salary,
                'job_type': job_type,
                'experience_level': experience_level,
                'source_url': source_url,
                'external_id': external_id,
                'posted_date': posted_date,
                'scraped_date': datetime.utcnow()
            }
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error extracting job from Indeed card: {e}")
            return {}
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse Indeed date format"""
        try:
            date_text = date_text.lower().strip()
            
            if 'today' in date_text or 'just posted' in date_text:
                return datetime.utcnow()
            elif 'yesterday' in date_text:
                return datetime.utcnow() - timedelta(days=1)
            elif 'days ago' in date_text:
                days = int(re.search(r'(\d+)', date_text).group(1))
                return datetime.utcnow() - timedelta(days=days)
            elif 'hours ago' in date_text:
                return datetime.utcnow()
            
        except Exception:
            pass
        
        return None
    
    def _determine_experience_level(self, title: str, description: str) -> str:
        """Determine experience level from job title and description"""
        text = (title + ' ' + description).lower()
        
        entry_keywords = ['entry level', 'entry-level', 'no experience', 'trainee', 'intern', 'junior', 'assistant']
        senior_keywords = ['senior', 'lead', 'principal', 'director', 'manager', 'supervisor', 'head of']
        
        for keyword in entry_keywords:
            if keyword in text:
                return 'entry'
        
        for keyword in senior_keywords:
            if keyword in text:
                return 'senior'
        
        return 'mid'

