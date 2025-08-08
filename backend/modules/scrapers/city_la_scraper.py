"""
City of LA Personnel Department job scraper
Scrapes government jobs from governmentjobs.com/careers/lacity
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
from backend.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class CityLAScraper(BaseScraper):
    """Scraper for City of LA Personnel Department jobs"""
    
    def __init__(self, config: Dict[str, Any], ai_analyzer=None):
        super().__init__(config, ai_analyzer)
        self.base_url = "https://www.governmentjobs.com"
        self.search_url = "https://www.governmentjobs.com/careers/lacity"
        
    def scrape_jobs(self, keywords: str = '', location: str = 'Los Angeles, CA', max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape City of LA Personnel jobs
        
        Args:
            keywords: Search keywords (optional for government jobs)
            location: Not used (always Los Angeles)
            max_pages: Maximum pages to scrape
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        max_pages = max_pages or self.max_pages
        
        logger.info(f"Starting City of LA Personnel scrape for '{keywords}'")
        
        for page in range(max_pages):
            try:
                # Build URL with search if keywords provided
                if keywords and page == 0:
                    # Use search functionality
                    url = f"{self.search_url}?q={quote_plus(str(keywords))}"
                elif page > 0:
                    # Handle pagination if available
                    url = f"{self.search_url}?page={page + 1}"
                else:
                    # Default listing
                    url = self.search_url
                
                logger.debug(f"Scraping City of LA page {page + 1}: {url}")
                
                response = self._make_request(url)
                if not response:
                    logger.warning(f"Failed to get response for City of LA page {page + 1}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_jobs = self.parse_job_cards(soup)
                
                if not page_jobs:
                    logger.info(f"No jobs found on City of LA page {page + 1}, stopping")
                    break
                
                jobs.extend(page_jobs)
                logger.info(f"Found {len(page_jobs)} jobs on City of LA page {page + 1}")
                
                # Rate limiting
                self._rate_limit_delay()
                
            except Exception as e:
                logger.error(f"Error scraping City of LA page {page + 1}: {e}")
                continue
        
        logger.info(f"Total jobs scraped from City of LA Personnel: {len(jobs)}")
        return jobs
    
    def parse_job_cards(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse job cards from the page"""
        jobs = []
        
        # Look for job listings in list items - they contain the job information
        job_cards = soup.find_all('li')
        
        # Filter to only job listing items (they contain job title links)
        valid_job_cards = []
        for card in job_cards:
            # Check if this list item contains a job title link
            job_link = card.find('a', href=True)
            if job_link and self._is_job_link(job_link):
                valid_job_cards.append(card)
        
        logger.info(f"Found {len(valid_job_cards)} potential job cards")
        
        for card in valid_job_cards:
            try:
                job_data = self.extract_job_from_card(card)
                if job_data and job_data.get('title'):
                    jobs.append(job_data)
            except Exception as e:
                logger.warning(f"Error extracting job from card: {e}")
                continue
        
        return jobs
    
    def _is_job_link(self, link) -> bool:
        """Check if a link appears to be a job listing"""
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Check for job-like patterns in the text
        job_indicators = [
            'CLERK', 'OFFICER', 'INSPECTOR', 'ANALYST', 'SPECIALIST', 'ENGINEER', 
            'MANAGER', 'SUPERVISOR', 'ASSISTANT', 'COORDINATOR', 'TECHNICIAN',
            'INVESTIGATOR', 'PROVIDER', 'OPERATOR'
        ]
        
        # Check if text contains job indicators and classification numbers
        has_job_title = any(indicator in text.upper() for indicator in job_indicators)
        has_classification = bool(re.search(r'\d{4}', text))
        
        # Also check for typical government job patterns
        has_revision = 'REVISED' in text.upper() or 'REVISED:' in text.upper()
        
        # Must have either job title indicators or classification numbers
        is_job = has_job_title or has_classification or has_revision
        
        # Exclude obvious non-job links
        exclude_terms = ['MENU', 'SIGN IN', 'SEARCH', 'FILTER', 'SORT', 'VIEW', 'SHARE', 'SUPPORT']
        is_excluded = any(term in text.upper() for term in exclude_terms)
        
        return is_job and not is_excluded and len(text) > 10
    
    def extract_job_from_card(self, card) -> Dict[str, Any]:
        """Extract job information from a job card"""
        try:
            job_data = {
                'scraped_date': datetime.now().isoformat(),
                'source_site': 'city_la_personnel',
                'job_type': 'Government',
                'location': 'Los Angeles, CA'
            }
            
            # Find job title link
            title_link = card.find('a', href=True)
            if title_link:
                job_data['title'] = title_link.get_text(strip=True)
                job_data['source_url'] = urljoin(self.base_url, title_link['href'])
                
                # Extract job classification number from title
                title_text = job_data['title']
                class_match = re.search(r'(\d{4})', title_text)
                if class_match:
                    job_data['external_id'] = f"lacity_{class_match.group(1)}"
            
            # Extract company (always City of Los Angeles)
            job_data['company'] = 'City of Los Angeles'
            
            # Look for salary information
            salary_text = card.get_text()
            salary_patterns = [
                r'\$[\d,]+\.?\d*\s*-\s*\$[\d,]+\.?\d*\s*Annually',
                r'\$[\d,]+\.?\d*\s*\(flat-rated\)',
                r'ANNUAL SALARY[:\s]*\$[\d,]+\.?\d*\s*to\s*\$[\d,]+\.?\d*'
            ]
            
            for pattern in salary_patterns:
                salary_match = re.search(pattern, salary_text, re.IGNORECASE)
                if salary_match:
                    job_data['salary_range'] = salary_match.group(0)
                    break
            
            # Extract category/department
            category_patterns = [
                r'Category:\s*([^•\n]+)',
                r'Department:\s*([^•\n]+)'
            ]
            
            for pattern in category_patterns:
                match = re.search(pattern, salary_text, re.IGNORECASE)
                if match:
                    if 'Category:' in pattern:
                        job_data['category'] = match.group(1).strip()
                    else:
                        job_data['department'] = match.group(1).strip()
            
            # Extract job description
            description_parts = []
            
            # Look for description text
            text_content = card.get_text(separator=' ', strip=True)
            
            # Extract the main description (usually after salary info)
            desc_match = re.search(r'DUTIES?\s+(.+?)(?:Posted|$)', text_content, re.IGNORECASE | re.DOTALL)
            if desc_match:
                description_parts.append(desc_match.group(1).strip())
            else:
                # Fallback: take text after salary
                salary_end = text_content.find('Annually')
                if salary_end > 0:
                    remaining_text = text_content[salary_end + 8:].strip()
                    if len(remaining_text) > 50:  # Only if substantial content
                        description_parts.append(remaining_text[:500])  # Limit length
            
            if description_parts:
                job_data['description'] = ' '.join(description_parts)
            
            # Extract posted date
            posted_match = re.search(r'Posted\s+(.+?)(?:\s*\||\s*$)', text_content, re.IGNORECASE)
            if posted_match:
                job_data['posted_date'] = posted_match.group(1).strip()
            
            # Set experience level based on job title
            title_lower = job_data.get('title', '').lower()
            if any(term in title_lower for term in ['senior', 'principal', 'manager', 'supervisor']):
                job_data['experience_level'] = 'Senior'
            elif any(term in title_lower for term in ['assistant', 'clerk', 'aide']):
                job_data['experience_level'] = 'Entry Level'
            else:
                job_data['experience_level'] = 'Mid Level'
            
            # Add background-friendly indicators
            job_data['background_friendly_score'] = 0.8  # Government jobs often more background-friendly
            job_data['background_friendly_reasons'] = [
                "Government position with structured hiring process",
                "Equal opportunity employer",
                "Clear qualification requirements"
            ]
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error extracting City of LA job data: {e}")
            return {}

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    config = {
        "name": "City of LA Personnel",
        "base_url": "https://www.governmentjobs.com",
        "rate_limit": 2,
        "max_pages": 2
    }
    
    scraper = CityLAScraper(config)
    jobs = scraper.scrape_jobs("clerk")
    
    print(f"Found {len(jobs)} jobs")
    for job in jobs[:3]:
        print(f"- {job.get('title', 'N/A')} | {job.get('salary_range', 'N/A')}")
        print(f"  {job.get('description', 'N/A')[:100]}...")
        print()

