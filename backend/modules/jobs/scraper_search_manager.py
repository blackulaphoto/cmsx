#!/usr/bin/env python3
"""
Scraper Search Manager - Coordinates multiple job scrapers for specific job listings
Provides secondary search functionality alongside GCSE search
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import threading

# Import available scrapers
from .scrapers.craigslist_scraper import CraigslistScraper
from .scrapers.builtinla_scraper import BuiltInLAScraper
from .scrapers.universal_job_scraper import UniversalJobScraper
from .scrapers.government_scraper import GovernmentScraper
from .scrapers.city_la_scraper import CityLAScraper

logger = logging.getLogger(__name__)

class ScraperSearchManager:
    """
    Manages scraper-based job searches with caching, deduplication, and background-friendly scoring
    """
    
    def __init__(self):
        self.cache_db_path = "databases/scraper_cache.db"
        self.cache_ttl_minutes = 30  # Cache results for 30 minutes
        self.max_workers = 3  # Limit concurrent scraper threads
        self.search_timeout = 120  # 2 minutes timeout for scraper searches
        
        # Initialize scrapers with configurations
        self.scrapers = self._initialize_scrapers()
        
        # Initialize cache database
        self._init_cache_db()
        
        logger.info(f"ScraperSearchManager initialized with {len(self.scrapers)} scrapers")
    
    def _initialize_scrapers(self) -> Dict[str, Any]:
        """Initialize all available scrapers with proper configurations"""
        scrapers = {}
        
        # Base configuration for all scrapers
        base_config = {
            'max_pages': 2,
            'rate_limit': 2,  # 2 seconds between requests
            'timeout': 30,
        }
        
        try:
            # Craigslist scraper - excellent for entry-level and background-friendly jobs
            craigslist_config = base_config.copy()
            craigslist_config.update({
                'search_url': 'https://losangeles.craigslist.org/search/{section}',
                'max_pages': 2
            })
            scrapers['craigslist'] = CraigslistScraper(craigslist_config)
            logger.info("Craigslist scraper initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Craigslist scraper: {e}")
        
        try:
            # BuiltInLA scraper - tech jobs in LA
            builtin_config = base_config.copy()
            builtin_config.update({
                'search_url': 'https://builtin.com/jobs/los-angeles?q={keywords}',
                'max_pages': 2
            })
            scrapers['builtinla'] = BuiltInLAScraper(builtin_config)
            logger.info("BuiltInLA scraper initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize BuiltInLA scraper: {e}")
        
        try:
            # Government jobs scraper
            gov_config = base_config.copy()
            gov_config.update({
                'search_url': 'https://www.usajobs.gov/Search/Results',
                'max_pages': 1
            })
            scrapers['government'] = GovernmentScraper(gov_config)
            logger.info("Government scraper initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Government scraper: {e}")
        
        try:
            # City of LA scraper
            city_config = base_config.copy()
            city_config.update({
                'search_url': 'https://www.governmentjobs.com/careers/lacity',
                'max_pages': 1
            })
            scrapers['city_la'] = CityLAScraper(city_config)
            logger.info("City of LA scraper initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize City of LA scraper: {e}")
        
        # Universal scraper for enhancing GCSE results
        try:
            scrapers['universal'] = UniversalJobScraper()
            logger.info("Universal scraper initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Universal scraper: {e}")
        
        return scrapers
    
    def _init_cache_db(self):
        """Initialize SQLite cache database"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraper_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_key TEXT UNIQUE NOT NULL,
                    keywords TEXT NOT NULL,
                    location TEXT NOT NULL,
                    sources TEXT NOT NULL,
                    results TEXT NOT NULL,
                    background_friendly_only BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL
                )
            """)
            
            # Index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_key ON scraper_cache(search_key)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON scraper_cache(expires_at)
            """)
            
            conn.commit()
            conn.close()
            logger.info("Scraper cache database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize scraper cache DB: {e}")
    
    def _generate_search_key(self, keywords: str, location: str, sources: List[str], background_friendly: bool) -> str:
        """Generate unique cache key for search parameters"""
        key_data = f"{keywords}|{location}|{sorted(sources)}|{background_friendly}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_results(self, search_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached results if they exist and are not expired"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT results FROM scraper_cache 
                WHERE search_key = ? AND expires_at > datetime('now')
            """, (search_key,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return json.loads(row[0])
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached results: {e}")
            return None
    
    def _cache_results(self, search_key: str, keywords: str, location: str, sources: List[str], 
                      results: List[Dict[str, Any]], background_friendly: bool):
        """Cache search results"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            expires_at = datetime.now() + timedelta(minutes=self.cache_ttl_minutes)
            
            cursor.execute("""
                INSERT OR REPLACE INTO scraper_cache 
                (search_key, keywords, location, sources, results, background_friendly_only, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                search_key, keywords, location, json.dumps(sources), 
                json.dumps(results), background_friendly, expires_at
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"Cached {len(results)} results for search key: {search_key}")
        except Exception as e:
            logger.error(f"Error caching results: {e}")
    
    def _cleanup_expired_cache(self):
        """Remove expired cache entries"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM scraper_cache WHERE expires_at < datetime('now')")
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired cache entries")
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
    
    def _filter_relevant_jobs(self, jobs: List[Dict], keywords: str) -> List[Dict]:
        """Filter jobs with FLEXIBLE relevance matching"""
        if not keywords:
            return jobs
        
        import re
        from difflib import SequenceMatcher
        
        keywords_clean = re.sub(r'[^\w\s]', '', keywords.lower())
        search_terms = keywords_clean.split()
        relevant_jobs = []
        
        for job in jobs:
            title = job.get('title', '').lower()
            description = job.get('description', '').lower()
            company = job.get('company', '').lower()
            full_text = f"{title} {description} {company}"
            
            relevance_score = 0
            
            for term in search_terms:
                # FLEXIBLE MATCHING STRATEGIES:
                
                # 1. Exact match (highest score)
                if term in full_text:
                    if term in title:
                        relevance_score += 10
                    elif term in description:
                        relevance_score += 5
                    else:
                        relevance_score += 2
                
                # 2. Partial/fuzzy matching for related terms
                elif len(term) >= 4:  # Only for longer terms
                    # Check for partial matches
                    for word in full_text.split():
                        similarity = SequenceMatcher(None, term, word).ratio()
                        if similarity >= 0.7:  # 70% similarity
                            relevance_score += int(similarity * 5)
                
                # 3. Common word variations/stems
                term_variations = self._get_word_variations(term)
                for variation in term_variations:
                    if variation in full_text:
                        relevance_score += 3
            
            # 4. Negative scoring for OBVIOUSLY wrong jobs (but less aggressive)
            wrong_job_terms = ['handyman construction', 'heavy labor', 'truck driver', 'warehouse worker']
            wrong_penalty = 0
            for wrong_term in wrong_job_terms:
                if wrong_term in title:
                    wrong_penalty += 5  # Reduced from 20
            
            final_score = relevance_score - wrong_penalty
            
            # MUCH MORE LENIENT THRESHOLD
            if final_score >= 0:  # Changed from > 0 to >= 0
                job['relevance_score'] = final_score
                relevant_jobs.append(job)
        
        return sorted(relevant_jobs, key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    def _get_word_variations(self, word: str) -> List[str]:
        """Get common variations of a word"""
        variations = {
            'photographer': ['photography', 'photo', 'pics', 'pictures', 'camera'],
            'graphic': ['design', 'designer', 'graphics', 'visual'],
            'marketing': ['promo', 'promotion', 'advertising', 'social media'],
            'teacher': ['teaching', 'education', 'instructor', 'tutor'],
            'nurse': ['nursing', 'healthcare', 'medical', 'care'],
            'driver': ['driving', 'delivery', 'transport'],
            'cook': ['cooking', 'chef', 'kitchen', 'food'],
            'creative': ['design', 'art', 'artist', 'visual', 'media'],
            'designer': ['design', 'creative', 'visual', 'graphics'],
            'writer': ['writing', 'content', 'copywriter', 'editor'],
            'developer': ['programming', 'coding', 'software', 'web'],
            'manager': ['management', 'supervisor', 'lead', 'coordinator']
        }
        
        return variations.get(word, [])
    
    def _lenient_filter(self, jobs: List[Dict], keywords: str, max_results: int = 30) -> List[Dict]:
        """Super lenient filter when strict filter fails"""
        if not keywords:
            return jobs[:max_results]
        
        search_terms = keywords.lower().split()
        lenient_jobs = []
        
        for job in jobs:
            title = job.get('title', '').lower()
            description = job.get('description', '').lower()
            full_text = f"{title} {description}"
            
            # Just check if ANY search term appears ANYWHERE
            for term in search_terms:
                if term in full_text or any(char in full_text for char in term if len(term) >= 3):
                    job['relevance_score'] = 1  # Minimal score
                    lenient_jobs.append(job)
                    break
        
        return lenient_jobs[:max_results]  # Limit results
    
    def _select_appropriate_scrapers(self, keywords: str) -> List[str]:
        """Select which scrapers to use based on keywords"""
        keywords_lower = keywords.lower()
        selected_scrapers = ['craigslist']  # Always include Craigslist
        
        # Tech keywords -> include BuiltInLA
        tech_keywords = ['developer', 'engineer', 'programmer', 'software', 'tech', 'it', 
                         'data', 'analyst', 'designer', 'frontend', 'backend', 'fullstack']
        
        if any(keyword in keywords_lower for keyword in tech_keywords):
            selected_scrapers.append('builtinla')
        
        # Always include universal for broad coverage
        if 'universal' in self.scrapers:
            selected_scrapers.append('universal')
        
        return selected_scrapers
    
    async def search_jobs(self, keywords: str, location: str = "Los Angeles, CA", 
                         sources: Optional[List[str]] = None, max_results: int = 30,
                         background_friendly_only: bool = False, page: int = 1, 
                         per_page: int = 10) -> Dict[str, Any]:
        """
        Main async search method that coordinates multiple scrapers
        
        Args:
            keywords: Search keywords
            location: Job location
            sources: List of scraper sources to use (None = all available)
            max_results: Maximum total results to return
            background_friendly_only: Filter for background-friendly jobs only
            page: Page number for pagination
            per_page: Results per page
            
        Returns:
            Standardized search results with pagination
        """
        try:
            # Default to smart scraper selection if none specified
            if sources is None:
                sources = self._select_appropriate_scrapers(keywords)
            else:
                # Filter to only available scrapers
                sources = [s for s in sources if s in self.scrapers]
            
            if not sources:
                return self._empty_result(page, per_page, "No valid scrapers available")
            
            logger.info(f"Scraper search: '{keywords}' in '{location}' using {sources}")
            
            # Generate cache key
            search_key = self._generate_search_key(keywords, location, sources, background_friendly_only)
            
            # Check cache first
            cached_results = self._get_cached_results(search_key)
            if cached_results:
                logger.info(f"Using cached results ({len(cached_results)} jobs)")
                return self._paginate_results(cached_results, page, per_page, "cached_scrapers")
            
            # Clean up expired cache entries
            self._cleanup_expired_cache()
            
            # Perform fresh scraping
            all_jobs = await self._scrape_from_sources(keywords, location, sources, max_results)
            
            # Apply relevance filtering to remove irrelevant jobs
            relevant_jobs = self._filter_relevant_jobs(all_jobs, keywords)
            logger.info(f"Relevance filtering: {len(all_jobs)} -> {len(relevant_jobs)} jobs")
            
            # FALLBACK: If filtering removed too many results, be more lenient
            if len(relevant_jobs) == 0 and len(all_jobs) > 0:
                logger.warning(f"Relevance filter removed all {len(all_jobs)} jobs for '{keywords}' - using lenient filter")
                relevant_jobs = self._lenient_filter(all_jobs, keywords, max_results)
            
            # Apply background-friendly filtering if requested
            if background_friendly_only:
                relevant_jobs = [job for job in relevant_jobs if job.get('background_friendly_score', 0) >= 60]
            
            # Deduplicate and sort results
            unique_jobs = self._deduplicate_jobs(relevant_jobs)
            # Sort by relevance score first, then background score
            sorted_jobs = sorted(unique_jobs, key=lambda x: (x.get('relevance_score', 0), x.get('background_friendly_score', 0)), reverse=True)
            
            # Cache the results
            self._cache_results(search_key, keywords, location, sources, sorted_jobs, background_friendly_only)
            
            logger.info(f"Scraper search completed: {len(sorted_jobs)} unique jobs found")
            
            return self._paginate_results(sorted_jobs, page, per_page, "fresh_scrapers")
            
        except Exception as e:
            logger.error(f"Scraper search error: {e}")
            return self._empty_result(page, per_page, f"Search failed: {str(e)}")
    
    async def _scrape_from_sources(self, keywords: str, location: str, sources: List[str], 
                                  max_results: int) -> List[Dict[str, Any]]:
        """Scrape jobs from specified sources using thread pool"""
        all_jobs = []
        
        # Use ThreadPoolExecutor for concurrent scraping
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit scraping tasks
            future_to_source = {}
            for source in sources:
                if source in self.scrapers:
                    future = executor.submit(self._scrape_single_source, source, keywords, location)
                    future_to_source[future] = source
            
            # Collect results with timeout
            for future in future_to_source:
                source = future_to_source[future]
                try:
                    # Wait for result with timeout
                    jobs = future.result(timeout=self.search_timeout)
                    if jobs:
                        logger.info(f"{source}: {len(jobs)} jobs scraped")
                        all_jobs.extend(jobs)
                    else:
                        logger.warning(f"{source}: No jobs found")
                except Exception as e:
                    logger.error(f"{source} scraping failed: {e}")
                    continue
        
        return all_jobs[:max_results]
    
    def _scrape_single_source(self, source: str, keywords: str, location: str) -> List[Dict[str, Any]]:
        """Scrape jobs from a single source (runs in thread)"""
        try:
            scraper = self.scrapers[source]
            logger.debug(f"Starting {source} scraper...")
            
            # Call the scraper's main method
            raw_jobs = scraper.scrape(keywords, location)
            
            # Standardize job format and add metadata
            standardized_jobs = []
            for job in raw_jobs:
                standardized_job = self._standardize_job_format(job, source)
                if standardized_job:
                    standardized_jobs.append(standardized_job)
            
            return standardized_jobs
            
        except Exception as e:
            logger.error(f"Error in {source} scraper: {e}")
            return []
    
    def _standardize_job_format(self, raw_job: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """Convert raw scraper output to standardized format"""
        try:
            # Calculate background-friendly score
            bg_score = self._calculate_background_score(raw_job, source)
            
            standardized = {
                'title': raw_job.get('title', 'Job Title Not Available'),
                'company': raw_job.get('company', 'Company Not Listed'),
                'location': raw_job.get('location', 'Location Not Specified'),
                'salary': raw_job.get('salary', 'Salary Not Listed'),
                'description': raw_job.get('description', 'Description not available'),
                'source_url': raw_job.get('url', ''),
                'external_id': raw_job.get('id', f"{source}_{hash(raw_job.get('title', ''))}"),
                'background_friendly_score': bg_score,
                'scraped_date': datetime.now().isoformat(),
                'source': source,
                'metadata': {
                    'scraped': True,
                    'scraper_source': source,
                    'requirements': raw_job.get('requirements', []),
                    'benefits': raw_job.get('benefits', []),
                    'employment_type': raw_job.get('type', 'Not specified'),
                    'posted_date': raw_job.get('posted', 'Not specified'),
                    'contact_info': raw_job.get('contact', {})
                }
            }
            
            return standardized
            
        except Exception as e:
            logger.error(f"Error standardizing job from {source}: {e}")
            return None
    
    def _calculate_background_score(self, job: Dict[str, Any], source: str) -> int:
        """Calculate background-friendly score (0-100) for a job"""
        score = 50  # Base score
        
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        company = job.get('company', '').lower()
        
        # Positive indicators for background-friendly jobs
        positive_terms = [
            'entry level', 'no experience', 'will train', 'training provided',
            'second chance', 'equal opportunity', 'background friendly',
            'warehouse', 'construction', 'manufacturing', 'delivery',
            'kitchen', 'cleaning', 'maintenance', 'security',
            'general labor', 'helper', 'assistant', 'driver',
            'food service', 'retail', 'customer service'
        ]
        
        # Negative indicators
        negative_terms = [
            'background check required', 'clean record', 'security clearance',
            'financial', 'banking', 'insurance', 'government',
            'childcare', 'elderly care', 'healthcare professional', 'education',
            'must pass background', 'clean driving record', 'bonded'
        ]
        
        # Check title and description
        text_to_check = f"{title} {description}"
        
        for term in positive_terms:
            if term in text_to_check:
                score += 8
        
        for term in negative_terms:
            if term in text_to_check:
                score -= 12
        
        # Source-based adjustments
        if source == 'craigslist':
            score += 15  # Craigslist often has background-friendly jobs
        elif source == 'government':
            score -= 20  # Government jobs typically require clean records
        elif source == 'city_la':
            score -= 15  # City jobs often have background requirements
        elif source == 'builtinla':
            score += 5   # Tech jobs can be more flexible
        
        return max(0, min(100, score))
    
    def _deduplicate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate jobs based on title and company"""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            # Create a key for deduplication
            title = job.get('title', '').lower().strip()
            company = job.get('company', '').lower().strip()
            key = f"{title}:{company}"
            
            if key not in seen and title and company:
                seen.add(key)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def _paginate_results(self, jobs: List[Dict[str, Any]], page: int, per_page: int, 
                         source: str) -> Dict[str, Any]:
        """Apply pagination to results and return standardized format"""
        total_results = len(jobs)
        total_pages = max(1, (total_results + per_page - 1) // per_page)
        
        # Calculate pagination bounds
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        
        # Get page results
        page_jobs = jobs[start_index:end_index]
        
        return {
            "success": True,
            "jobs": page_jobs,
            "source": source,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total_results": total_results,
                "total_pages": total_pages,
                "has_next_page": page < total_pages,
                "has_prev_page": page > 1,
                "start_index": start_index + 1 if page_jobs else 0,
                "end_index": min(end_index, total_results)
            },
            "search_metadata": {
                "search_type": "scrapers",
                "scrapers_used": list(self.scrapers.keys()),
                "cache_used": source == "cached_scrapers",
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def _empty_result(self, page: int, per_page: int, error_message: str = "") -> Dict[str, Any]:
        """Return empty result with proper pagination structure"""
        return {
            "success": False,
            "jobs": [],
            "source": "scrapers_error",
            "error": error_message,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total_results": 0,
                "total_pages": 0,
                "has_next_page": False,
                "has_prev_page": False,
                "start_index": 0,
                "end_index": 0
            },
            "search_metadata": {
                "search_type": "scrapers",
                "scrapers_used": [],
                "cache_used": False,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def get_available_scrapers(self) -> Dict[str, str]:
        """Get list of available scrapers with descriptions"""
        return {
            'craigslist': 'Craigslist LA - Entry-level and background-friendly jobs',
            'builtinla': 'BuiltInLA - Tech jobs in Los Angeles',
            'government': 'USAJobs - Federal government positions',
            'city_la': 'City of LA - Municipal government jobs',
            'universal': 'Universal - Enhances job details from other sources'
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of scraper system"""
        return {
            "scrapers_available": len(self.scrapers),
            "scrapers_list": list(self.scrapers.keys()),
            "cache_enabled": True,
            "cache_ttl_minutes": self.cache_ttl_minutes,
            "max_workers": self.max_workers,
            "search_timeout": self.search_timeout,
            "status": "healthy" if self.scrapers else "no_scrapers"
        }

# Global instance
scraper_search_manager = ScraperSearchManager()