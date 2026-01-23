#!/usr/bin/env python3
"""
Job Search Manager - Coordinates multiple job scrapers and search sources
"""

import os
import sys
import asyncio
import threading
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

# Import scrapers - with error handling for missing dependencies
try:
    from backend.modules.jobs.scrapers.craigslist_scraper import CraigslistScraper
except ImportError as e:
    logger.warning(f"Failed to import CraigslistScraper: {e}")
    CraigslistScraper = None

try:
    from backend.modules.jobs.scrapers.builtinla_scraper import BuiltInLAScraper
except ImportError as e:
    logger.warning(f"Failed to import BuiltInLAScraper: {e}")
    BuiltInLAScraper = None

try:
    from backend.modules.jobs.scrapers.government_scraper import GovernmentScraper
except ImportError as e:
    logger.warning(f"Failed to import GovernmentScraper: {e}")
    GovernmentScraper = None
import requests

class JobSearchManager:
    """Manages job searches across multiple sources with progress tracking"""
    
    def __init__(self):
        self.search_status = {}
        self.search_results = {}
        self.search_threads = {}
        
        # Initialize scrapers
        self.scrapers = self._initialize_scrapers()
        
        # Google Custom Search configuration
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.custom_search_engine_id = (
            os.getenv('GOOGLE_JOBS_CSE_ID')
            or os.getenv('GOOGLE_CSE_ID')
            or os.getenv('CUSTOM_SEARCH_ENGINE_ID')
        )
    
    def _initialize_scrapers(self) -> Dict[str, Any]:
        """Initialize all available job scrapers"""
        scrapers = {}
        
        # Basic configuration for scrapers
        config = {
            'max_pages': 2,
            'rate_limit': 1,
            'timeout': 30,
            'search_url': ''
        }
        
        # Initialize scrapers only if classes are available
        if CraigslistScraper:
            try:
                # Craigslist scraper  
                craigslist_config = config.copy()
                craigslist_config.update({
                    'search_url': 'https://losangeles.craigslist.org/search/{section}',
                    'max_pages': 2
                })
                scrapers['craigslist'] = CraigslistScraper(craigslist_config)
                logger.info("Craigslist scraper initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Craigslist scraper: {e}")
        
        if BuiltInLAScraper:
            try:
                # BuiltIn LA scraper
                builtin_config = config.copy()
                builtin_config.update({
                    'search_url': 'https://builtin.com/jobs/{location}',
                    'max_pages': 2
                })
                scrapers['builtin'] = BuiltInLAScraper(builtin_config)
                logger.info("BuiltIn LA scraper initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize BuiltIn LA scraper: {e}")
        
        if GovernmentScraper:
            try:
                # Government jobs scraper
                gov_config = config.copy()
                gov_config.update({
                    'search_url': 'https://www.usajobs.gov/Search/Results',
                    'max_pages': 1
                })
                scrapers['government'] = GovernmentScraper(gov_config)
                logger.info("Government scraper initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Government scraper: {e}")
        
        # If no scrapers are available, log warning but continue with Google Custom Search
        if not scrapers:
            logger.warning("No scrapers initialized - job search will rely on Google Custom Search only")
        
        return scrapers
    
    def start_search(self, search_id: str, keywords: str, location: str = "Los Angeles", max_pages: int = 2) -> bool:
        """Start an asynchronous job search"""
        try:
            # Initialize search status
            self.search_status[search_id] = {
                'is_running': True,
                'progress': 0,
                'current_source': 'Initializing...',
                'start_time': datetime.now(),
                'total_sources': len(self.scrapers) + 1,  # +1 for Google Custom Search
                'completed_sources': 0,
                'total_jobs_found': 0,
                'errors': []
            }
            
            self.search_results[search_id] = []
            
            # Start search in background thread
            search_thread = threading.Thread(
                target=self._execute_search,
                args=(search_id, keywords, location, max_pages),
                daemon=True
            )
            search_thread.start()
            self.search_threads[search_id] = search_thread
            
            logger.info(f"Started job search {search_id} for '{keywords}' in {location}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start search {search_id}: {e}")
            return False
    
    def _execute_search(self, search_id: str, keywords: str, location: str, max_pages: int):
        """Execute the job search across all sources"""
        try:
            status = self.search_status[search_id]
            all_jobs = []
            
            # 1. Try scrapers first
            for i, (scraper_name, scraper) in enumerate(self.scrapers.items()):
                try:
                    status['current_source'] = scraper_name.title()
                    status['progress'] = int((i / status['total_sources']) * 100)
                    
                    logger.info(f"Search {search_id}: Starting {scraper_name} scraper")
                    
                    # Scrape jobs with rate limiting
                    jobs = scraper.scrape_jobs(keywords, location, max_pages)
                    
                    if jobs:
                        # Add source identifier
                        for job in jobs:
                            job['source'] = scraper_name
                            job['search_id'] = search_id
                            job['background_friendly_score'] = self._calculate_background_score(job)
                        
                        all_jobs.extend(jobs)
                        status['total_jobs_found'] += len(jobs)
                        logger.info(f"Search {search_id}: {scraper_name} found {len(jobs)} jobs")
                    else:
                        logger.warning(f"Search {search_id}: {scraper_name} returned no jobs")
                    
                    status['completed_sources'] += 1
                    
                    # Rate limiting between scrapers
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Search {search_id}: {scraper_name} scraper failed: {e}")
                    status['errors'].append(f"{scraper_name}: {str(e)}")
                    status['completed_sources'] += 1
            
            # 2. Google Custom Search as fallback/supplement
            try:
                status['current_source'] = 'Google Custom Search'
                status['progress'] = int((status['completed_sources'] / status['total_sources']) * 100)
                
                google_jobs = self._search_google_jobs(keywords, location)
                if google_jobs:
                    for job in google_jobs:
                        job['source'] = 'google_search'
                        job['search_id'] = search_id
                        job['background_friendly_score'] = self._calculate_background_score(job)
                    
                    all_jobs.extend(google_jobs)
                    status['total_jobs_found'] += len(google_jobs)
                    logger.info(f"Search {search_id}: Google Custom Search found {len(google_jobs)} jobs")
                
                status['completed_sources'] += 1
                
            except Exception as e:
                logger.error(f"Search {search_id}: Google Custom Search failed: {e}")
                status['errors'].append(f"Google Search: {str(e)}")
                status['completed_sources'] += 1
            
            # 3. Finalize search
            status['progress'] = 100
            status['is_running'] = False
            status['current_source'] = 'Complete'
            
            # Remove duplicates and sort by background-friendly score
            unique_jobs = self._deduplicate_jobs(all_jobs)
            sorted_jobs = sorted(unique_jobs, key=lambda x: x.get('background_friendly_score', 0), reverse=True)
            
            self.search_results[search_id] = sorted_jobs
            
            logger.info(f"Search {search_id} completed: {len(sorted_jobs)} unique jobs found")
            
        except Exception as e:
            logger.error(f"Search {search_id} failed: {e}")
            status['is_running'] = False
            status['progress'] = 100
            status['current_source'] = 'Failed'
            status['errors'].append(f"Search execution failed: {str(e)}")
    
    def _search_google_jobs(self, keywords: str, location: str) -> List[Dict[str, Any]]:
        """Search for jobs using Google Custom Search API"""
        if not self.google_api_key or not self.custom_search_engine_id:
            logger.warning("Google Custom Search not configured, skipping")
            return []
        
        try:
            # Search for job listings
            search_query = f"{keywords} jobs {location} hiring entry level"
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': self.custom_search_engine_id,
                'q': search_query,
                'num': 10
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                jobs = []
                
                for item in data.get('items', []):
                    job = {
                        'title': self._extract_job_title(item.get('title', '')),
                        'company': self._extract_company_name(item.get('snippet', '')),
                        'location': location,
                        'description': item.get('snippet', '')[:300] + '...',
                        'url': item.get('link', ''),
                        'date_posted': datetime.now().strftime('%Y-%m-%d'),
                        'source': 'google_search'
                    }
                    jobs.append(job)
                
                return jobs
            else:
                logger.warning(f"Google Custom Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Google Custom Search error: {e}")
            return []
    
    def _extract_job_title(self, title: str) -> str:
        """Extract clean job title from search result title"""
        # Remove common suffixes and clean up
        title = title.replace(' - Indeed.com', '').replace(' | Indeed', '')
        title = title.replace(' - Glassdoor', '').replace(' | Glassdoor', '')
        title = title.replace(' Jobs', '').strip()
        
        # If still too long, take first part
        if len(title) > 80:
            title = title.split(' - ')[0].strip()
        
        return title[:80]
    
    def _extract_company_name(self, snippet: str) -> str:
        """Extract company name from search result snippet"""
        # Look for common patterns
        snippet_lower = snippet.lower()
        
        if 'hiring' in snippet_lower:
            parts = snippet.split(' is hiring')
            if len(parts) > 1:
                return parts[0].strip()
        
        if 'company' in snippet_lower:
            parts = snippet.split('company')
            if len(parts) > 1:
                return parts[0].strip()
        
        # Default fallback
        words = snippet.split()[:3]
        return ' '.join(words) if words else 'Hiring Company'
    
    def _calculate_background_score(self, job: Dict[str, Any]) -> int:
        """Calculate background-friendly score for a job (0-100)"""
        score = 50  # Base score
        
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        company = job.get('company', '').lower()
        
        # Positive indicators
        positive_terms = [
            'entry level', 'no experience', 'will train', 'training provided',
            'second chance', 'equal opportunity', 'background friendly',
            'warehouse', 'construction', 'manufacturing', 'delivery',
            'kitchen', 'cleaning', 'maintenance', 'security',
            'general labor', 'helper', 'assistant'
        ]
        
        # Negative indicators  
        negative_terms = [
            'background check required', 'clean record', 'security clearance',
            'financial', 'banking', 'insurance', 'government',
            'childcare', 'elderly care', 'healthcare', 'education'
        ]
        
        # Check title and description
        text_to_check = f"{title} {description}"
        
        for term in positive_terms:
            if term in text_to_check:
                score += 10
        
        for term in negative_terms:
            if term in text_to_check:
                score -= 15
        
        # Source-based adjustments
        source = job.get('source', '')
        if source == 'craigslist':
            score += 15  # Craigslist often has background-friendly jobs
        elif source == 'government':
            score -= 20  # Government jobs typically require clean records
        
        return max(0, min(100, score))
    
    def _deduplicate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate jobs based on title and company"""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            title = job.get('title', '').lower().strip()
            company = job.get('company', '').lower().strip()
            key = f"{title}:{company}"
            
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def get_search_status(self, search_id: str) -> Dict[str, Any]:
        """Get current status of a job search"""
        return self.search_status.get(search_id, {
            'is_running': False,
            'progress': 0,
            'current_source': 'Not found',
            'total_jobs_found': 0,
            'errors': ['Search not found']
        })
    
    def get_search_results(self, search_id: str) -> List[Dict[str, Any]]:
        """Get results of a completed job search"""
        return self.search_results.get(search_id, [])
    
    def cleanup_old_searches(self, max_age_hours: int = 24):
        """Clean up old search data"""
        try:
            current_time = datetime.now()
            old_searches = []
            
            for search_id, status in self.search_status.items():
                start_time = status.get('start_time')
                if start_time:
                    age_hours = (current_time - start_time).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        old_searches.append(search_id)
            
            for search_id in old_searches:
                self.search_status.pop(search_id, None)
                self.search_results.pop(search_id, None)
                self.search_threads.pop(search_id, None)
                logger.info(f"Cleaned up old search: {search_id}")
                
        except Exception as e:
            logger.error(f"Error cleaning up old searches: {e}")

# Global instance
job_search_manager = JobSearchManager()
