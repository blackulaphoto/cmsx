#!/usr/bin/env python3
"""
Universal Job Scraper - Scrapes job details from URLs returned by Google Custom Search
Handles Indeed, ZipRecruiter, Glassdoor, and other major job sites
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, urljoin
import json

logger = logging.getLogger(__name__)

class UniversalJobScraper:
    """Scrapes job details from various job sites"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.delay = 2  # Delay between requests
        
    def scrape_job_details(self, url: str, title: str = "", description: str = "") -> Optional[Dict[str, Any]]:
        """
        Scrape job details from a URL
        Returns structured job data or None if scraping fails
        """
        try:
            domain = urlparse(url).netloc.lower()
            
            # Route to appropriate scraper based on domain
            if 'indeed.com' in domain:
                return self._scrape_indeed(url, title, description)
            elif 'ziprecruiter.com' in domain:
                return self._scrape_ziprecruiter(url, title, description)
            elif 'glassdoor.com' in domain:
                return self._scrape_glassdoor(url, title, description)
            elif 'linkedin.com' in domain:
                return self._scrape_linkedin(url, title, description)
            elif 'craigslist.org' in domain:
                return self._scrape_craigslist(url, title, description)
            else:
                # Generic scraper for unknown sites
                return self._scrape_generic(url, title, description)
                
        except Exception as e:
            logger.error(f"Error scraping job from {url}: {e}")
            return None
    
    def _scrape_indeed(self, url: str, title: str, description: str) -> Optional[Dict[str, Any]]:
        """Scrape Indeed job listings"""
        try:
            # Indeed search pages are different from individual job pages
            if '/jobs?' in url or '/q-' in url:
                # This is a search results page, extract individual job URLs
                return self._scrape_indeed_search_page(url, title, description)
            else:
                # This is an individual job page
                return self._scrape_indeed_job_page(url, title, description)
                
        except Exception as e:
            logger.error(f"Error scraping Indeed job {url}: {e}")
            return None
    
    def _scrape_indeed_search_page(self, url: str, title: str, description: str) -> Dict[str, Any]:
        """Scrape Indeed search results page to get individual jobs"""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for job cards on Indeed search page
            job_cards = soup.find_all(['div', 'article'], class_=re.compile(r'job|result|card', re.I))
            
            if job_cards:
                # Extract first job from search results
                first_job = job_cards[0]
                
                # Extract job details from the card
                job_title = self._extract_text(first_job, ['h2', 'h3', 'a'], ['title', 'jobTitle'])
                company = self._extract_text(first_job, ['span', 'div', 'a'], ['company', 'companyName'])
                location = self._extract_text(first_job, ['div', 'span'], ['location', 'companyLocation'])
                salary = self._extract_text(first_job, ['span', 'div'], ['salary', 'salaryText'])
                job_desc = self._extract_text(first_job, ['div', 'span'], ['summary', 'description'])
                
                return {
                    'title': job_title or title,
                    'company': company or 'See job posting',
                    'location': location or 'See job posting',
                    'salary': salary or 'See job posting',
                    'description': job_desc or description,
                    'employment_type': 'See job posting',
                    'posted_date': 'See job posting',
                    'source_url': url,
                    'source': 'Indeed',
                    'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'requirements': ['Visit Indeed for full requirements'],
                    'benefits': ['Visit Indeed for benefits information'],
                    'contact_info': {
                        'phone': 'Apply through Indeed',
                        'email': 'Apply through Indeed'
                    }
                }
            else:
                # Fallback to basic info
                return self._create_basic_job_data(url, title, description, 'Indeed')
                
        except Exception as e:
            logger.error(f"Error scraping Indeed search page {url}: {e}")
            return self._create_basic_job_data(url, title, description, 'Indeed')
    
    def _scrape_indeed_job_page(self, url: str, title: str, description: str) -> Dict[str, Any]:
        """Scrape individual Indeed job page"""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract job details from Indeed job page
            job_title = self._extract_text(soup, ['h1'], ['jobsearch-JobInfoHeader-title'])
            company = self._extract_text(soup, ['a', 'span'], ['companyName'])
            location = self._extract_text(soup, ['div'], ['companyLocation'])
            salary = self._extract_text(soup, ['span'], ['salary'])
            job_desc = self._extract_text(soup, ['div'], ['jobsearch-jobDescriptionText'])
            
            return {
                'title': job_title or title,
                'company': company or 'See job posting',
                'location': location or 'See job posting',
                'salary': salary or 'See job posting',
                'description': job_desc or description,
                'employment_type': 'See job posting',
                'posted_date': 'See job posting',
                'source_url': url,
                'source': 'Indeed',
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'requirements': ['Visit Indeed for full requirements'],
                'benefits': ['Visit Indeed for benefits information'],
                'contact_info': {
                    'phone': 'Apply through Indeed',
                    'email': 'Apply through Indeed'
                }
            }
            
        except Exception as e:
            logger.error(f"Error scraping Indeed job page {url}: {e}")
            return self._create_basic_job_data(url, title, description, 'Indeed')
    
    def _scrape_ziprecruiter(self, url: str, title: str, description: str) -> Dict[str, Any]:
        """Scrape ZipRecruiter job listings"""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract job details from ZipRecruiter
            job_title = self._extract_text(soup, ['h1'], ['job_title'])
            company = self._extract_text(soup, ['a', 'span'], ['company'])
            location = self._extract_text(soup, ['span', 'div'], ['location'])
            salary = self._extract_text(soup, ['span'], ['salary'])
            job_desc = self._extract_text(soup, ['div'], ['job_description'])
            
            return {
                'title': job_title or title,
                'company': company or 'See job posting',
                'location': location or 'See job posting',
                'salary': salary or 'See job posting',
                'description': job_desc or description,
                'employment_type': 'See job posting',
                'posted_date': 'See job posting',
                'source_url': url,
                'source': 'ZipRecruiter',
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'requirements': ['Visit ZipRecruiter for full requirements'],
                'benefits': ['Visit ZipRecruiter for benefits information'],
                'contact_info': {
                    'phone': 'Apply through ZipRecruiter',
                    'email': 'Apply through ZipRecruiter'
                }
            }
            
        except Exception as e:
            logger.error(f"Error scraping ZipRecruiter {url}: {e}")
            return self._create_basic_job_data(url, title, description, 'ZipRecruiter')
    
    def _scrape_glassdoor(self, url: str, title: str, description: str) -> Dict[str, Any]:
        """Scrape Glassdoor job listings"""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract job details from Glassdoor
            job_title = self._extract_text(soup, ['h1'], ['job-title'])
            company = self._extract_text(soup, ['span', 'div'], ['employer'])
            location = self._extract_text(soup, ['span'], ['location'])
            salary = self._extract_text(soup, ['span'], ['salary'])
            job_desc = self._extract_text(soup, ['div'], ['desc'])
            
            return {
                'title': job_title or title,
                'company': company or 'See job posting',
                'location': location or 'See job posting',
                'salary': salary or 'See job posting',
                'description': job_desc or description,
                'employment_type': 'See job posting',
                'posted_date': 'See job posting',
                'source_url': url,
                'source': 'Glassdoor',
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'requirements': ['Visit Glassdoor for full requirements'],
                'benefits': ['Visit Glassdoor for benefits information'],
                'contact_info': {
                    'phone': 'Apply through Glassdoor',
                    'email': 'Apply through Glassdoor'
                }
            }
            
        except Exception as e:
            logger.error(f"Error scraping Glassdoor {url}: {e}")
            return self._create_basic_job_data(url, title, description, 'Glassdoor')
    
    def _scrape_linkedin(self, url: str, title: str, description: str) -> Dict[str, Any]:
        """Scrape LinkedIn job listings"""
        # LinkedIn is heavily protected, return basic info
        return self._create_basic_job_data(url, title, description, 'LinkedIn')
    
    def _scrape_craigslist(self, url: str, title: str, description: str) -> Dict[str, Any]:
        """Scrape Craigslist job listings"""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract job details from Craigslist
            job_title = self._extract_text(soup, ['span'], ['titletextonly'])
            location = self._extract_text(soup, ['small'], [])
            job_desc = self._extract_text(soup, ['section'], ['postingbody'])
            compensation = self._extract_text(soup, ['span'], ['compensation'])
            
            return {
                'title': job_title or title,
                'company': 'See Craigslist posting',
                'location': location or 'See job posting',
                'salary': compensation or 'See job posting',
                'description': job_desc or description,
                'employment_type': 'See job posting',
                'posted_date': 'See job posting',
                'source_url': url,
                'source': 'Craigslist',
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'requirements': ['Visit Craigslist for full requirements'],
                'benefits': ['Contact employer for benefits'],
                'contact_info': {
                    'phone': 'See Craigslist posting',
                    'email': 'See Craigslist posting'
                }
            }
            
        except Exception as e:
            logger.error(f"Error scraping Craigslist {url}: {e}")
            return self._create_basic_job_data(url, title, description, 'Craigslist')
    
    def _scrape_generic(self, url: str, title: str, description: str) -> Dict[str, Any]:
        """Generic scraper for unknown job sites"""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            domain = urlparse(url).netloc
            
            # Try to extract basic job info using common patterns
            job_title = self._extract_text(soup, ['h1', 'h2'], ['title', 'job', 'position'])
            company = self._extract_text(soup, ['span', 'div', 'a'], ['company', 'employer'])
            location = self._extract_text(soup, ['span', 'div'], ['location', 'city'])
            
            return {
                'title': job_title or title,
                'company': company or 'See job posting',
                'location': location or 'See job posting',
                'salary': 'See job posting',
                'description': description,
                'employment_type': 'See job posting',
                'posted_date': 'See job posting',
                'source_url': url,
                'source': domain,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'requirements': ['Visit job posting for requirements'],
                'benefits': ['Visit job posting for benefits'],
                'contact_info': {
                    'phone': 'See job posting',
                    'email': 'See job posting'
                }
            }
            
        except Exception as e:
            logger.error(f"Error scraping generic job site {url}: {e}")
            return self._create_basic_job_data(url, title, description, urlparse(url).netloc)
    
    def _extract_text(self, soup, tags: List[str], classes: List[str] = None) -> str:
        """Extract text from soup using various selectors"""
        try:
            # Try with classes first
            if classes:
                for class_name in classes:
                    for tag in tags:
                        element = soup.find(tag, class_=re.compile(class_name, re.I))
                        if element:
                            return element.get_text(strip=True)
            
            # Try without classes
            for tag in tags:
                element = soup.find(tag)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 3:  # Avoid empty or very short text
                        return text
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""
    
    def _create_basic_job_data(self, url: str, title: str, description: str, source: str) -> Dict[str, Any]:
        """Create basic job data structure when scraping fails"""
        return {
            'title': title or 'Job Opportunity',
            'company': 'See job posting',
            'location': 'See job posting',
            'salary': 'See job posting',
            'description': description or 'Visit job posting for details',
            'employment_type': 'See job posting',
            'posted_date': 'See job posting',
            'source_url': url,
            'source': source,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'requirements': ['Visit job posting for requirements'],
            'benefits': ['Visit job posting for benefits'],
            'contact_info': {
                'phone': 'See job posting',
                'email': 'See job posting'
            }
        }
    
    def scrape_multiple_jobs(self, job_urls: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Scrape multiple job URLs
        job_urls should be list of dicts with 'url', 'title', 'description' keys
        """
        scraped_jobs = []
        
        for job_info in job_urls:
            url = job_info.get('url', '')
            title = job_info.get('title', '')
            description = job_info.get('description', '')
            
            if url:
                logger.info(f"Scraping job: {title[:50]}...")
                job_data = self.scrape_job_details(url, title, description)
                if job_data:
                    scraped_jobs.append(job_data)
                    logger.info(f"✅ Successfully scraped: {job_data['title']}")
                else:
                    logger.warning(f"❌ Failed to scrape: {url}")
        
        return scraped_jobs

# Create global instance
universal_scraper = UniversalJobScraper()