#!/usr/bin/env python3
"""
Simple Search Coordinator - Bullet-proof unified search layer
Unifies Jobs | Housing | Services | General Web search behind ONE coordinator
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import sqlite3
from dataclasses import dataclass
from enum import Enum

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, will use system environment variables

logger = logging.getLogger(__name__)

class SearchType(Enum):
    JOBS = "jobs"
    HOUSING = "housing"
    SERVICES = "services"
    GENERAL = "general"

@dataclass
class SearchResult:
    """Standard result schema for all search types"""
    title: str
    description: str
    url: str
    source: str
    type: SearchType
    metadata: Dict[str, Any]
    confidence_score: float = 0.0
    timestamp: str = ""

class SimpleSearchCoordinator:
    """
    Bullet-proof search coordinator that:
    - Defaults to robust APIs (Google Custom Search, official job boards, Places APIs)
    - Sandboxes any scraping behind async workers
    - Returns one standard result schema
    - Fails gracefully with cached data or local DB samples
    """
    
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.cache_db_path = "databases/search_cache.db"
        self.sample_db_path = "databases/sample_data.db"
        
        # Initialize cache database
        self._init_cache_db()
        
        # Search configuration
        self.max_results = 20
        self.cache_ttl_hours = 24
        self.fallback_to_samples = True
        
        logger.info("Simple Search Coordinator initialized")
    
    def _init_cache_db(self):
        """Initialize search cache database"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    search_type TEXT NOT NULL,
                    location TEXT,
                    results TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(query, search_type, location)
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Search cache database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize cache DB: {e}")
    
    def search(self, query: str, search_type: SearchType, location: str = "Los Angeles, CA") -> Dict[str, Any]:
        """
        Main search method - unified interface for all search types
        Returns standardized result format
        """
        try:
            logger.info(f"🔍 Search: '{query}' | Type: {search_type.value} | Location: {location}")
            
            # Check cache first
            cached_results = self._get_cached_results(query, search_type, location)
            if cached_results:
                logger.info(f"Returning cached results: {len(cached_results)} items")
                return self._format_response(cached_results, "cache")
            
            # Perform fresh search based on type
            if search_type == SearchType.JOBS:
                results = self._search_jobs(query, location)
            elif search_type == SearchType.HOUSING:
                results = self._search_housing(query, location)
            elif search_type == SearchType.SERVICES:
                results = self._search_services(query, location)
            elif search_type == SearchType.GENERAL:
                results = self._search_general(query, location)
            else:
                results = []
            
            # Cache results
            if results:
                self._cache_results(query, search_type, location, results)
            
            # Fallback to sample data if no results
            if not results and self.fallback_to_samples:
                logger.warning("No results found, using sample data")
                results = self._get_sample_data(search_type, query)
            
            return self._format_response(results, "fresh_search")
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            # Return sample data as fallback
            sample_results = self._get_sample_data(search_type, query)
            return self._format_response(sample_results, "fallback_sample")
    
    def _search_jobs(self, query: str, location: str) -> List[SearchResult]:
        """Search for jobs using robust APIs with AI enhancement"""
        results = []
        
        try:
            # AI Enhancement: Use OpenAI to expand and improve search terms
            enhanced_query = self._ai_enhance_job_query(query, location) if self.openai_api_key else query
            
            # Primary: Google Custom Search for jobs
            if self.google_api_key and self.google_cse_id:
                google_results = self._google_custom_search(f"{enhanced_query} jobs", location)
                for item in google_results:
                    results.append(SearchResult(
                        title=item.get('title', ''),
                        description=item.get('snippet', ''),
                        url=item.get('link', ''),
                        source='google_jobs',
                        type=SearchType.JOBS,
                        metadata={'search_engine': 'google', 'ai_enhanced': bool(self.openai_api_key)},
                        confidence_score=0.8
                    ))
            
            # Fallback: Use job scrapers if Google APIs not available
            else:
                scraper_results = self._scraper_job_search(query, location)
                results.extend(scraper_results)
            
            # Secondary: Indeed API (if available)
            indeed_results = self._search_indeed_api(query, location)
            results.extend(indeed_results)
            
            # Tertiary: Local job database
            local_results = self._search_local_jobs(query, location)
            results.extend(local_results)
            
        except Exception as e:
            logger.error(f"Job search error: {e}")
        
        return results[:self.max_results]
    
    def _search_housing(self, query: str, location: str) -> List[SearchResult]:
        """Search for housing using robust APIs"""
        results = []
        
        try:
            # Primary: Google Places API for housing
            if self.google_api_key:
                places_results = self._google_places_search(f"{query} housing", location)
                for item in places_results:
                    results.append(SearchResult(
                        title=item.get('name', ''),
                        description=item.get('formatted_address', ''),
                        url=item.get('website', ''),
                        source='google_places',
                        type=SearchType.HOUSING,
                        metadata={'place_id': item.get('place_id')},
                        confidence_score=0.9
                    ))
            
            # Secondary: HUD API
            hud_results = self._search_hud_api(query, location)
            results.extend(hud_results)
            
            # Tertiary: Local housing database
            local_results = self._search_local_housing(query, location)
            results.extend(local_results)
            
        except Exception as e:
            logger.error(f"Housing search error: {e}")
        
        return results[:self.max_results]
    
    def _search_services(self, query: str, location: str) -> List[SearchResult]:
        """Search for services using robust APIs"""
        results = []
        
        try:
            # Primary: Google Custom Search for services
            if self.google_api_key and self.google_cse_id:
                google_results = self._google_custom_search(f"{query} services", location)
                for item in google_results:
                    results.append(SearchResult(
                        title=item.get('title', ''),
                        description=item.get('snippet', ''),
                        url=item.get('link', ''),
                        source='google_services',
                        type=SearchType.SERVICES,
                        metadata={'search_engine': 'google'},
                        confidence_score=0.8
                    ))
            
            # Secondary: 211 API (if available)
            # Tertiary: Local services database
            local_results = self._search_local_services(query, location)
            results.extend(local_results)
            
        except Exception as e:
            logger.error(f"Services search error: {e}")
        
        return results[:self.max_results]
    
    def _search_general(self, query: str, location: str) -> List[SearchResult]:
        """General web search"""
        results = []
        
        try:
            if self.google_api_key and self.google_cse_id:
                google_results = self._google_custom_search(query, location)
                for item in google_results:
                    results.append(SearchResult(
                        title=item.get('title', ''),
                        description=item.get('snippet', ''),
                        url=item.get('link', ''),
                        source='google_general',
                        type=SearchType.GENERAL,
                        metadata={'search_engine': 'google'},
                        confidence_score=0.7
                    ))
        except Exception as e:
            logger.error(f"General search error: {e}")
        
        return results[:self.max_results]
    
    def _google_custom_search(self, query: str, location: str) -> List[Dict]:
        """Google Custom Search API"""
        try:
            import requests
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': self.google_cse_id,
                'q': f"{query} {location}",
                'num': min(self.max_results, 10)  # Google CSE limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('items', [])
            
        except Exception as e:
            logger.error(f"Google Custom Search error: {e}")
            return []
    
    def _google_places_search(self, query: str, location: str) -> List[Dict]:
        """Google Places API search"""
        try:
            import requests
            
            # First get coordinates for location
            geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
            geocode_params = {
                'address': location,
                'key': self.google_api_key
            }
            
            geocode_response = requests.get(geocode_url, params=geocode_params, timeout=10)
            geocode_data = geocode_response.json()
            
            if geocode_data.get('results'):
                location_coords = geocode_data['results'][0]['geometry']['location']
                
                # Search for places
                places_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                places_params = {
                    'query': query,
                    'location': f"{location_coords['lat']},{location_coords['lng']}",
                    'radius': 50000,  # 50km radius
                    'key': self.google_api_key
                }
                
                places_response = requests.get(places_url, params=places_params, timeout=10)
                places_data = places_response.json()
                
                return places_data.get('results', [])
            
        except Exception as e:
            logger.error(f"Google Places Search error: {e}")
        
        return []
    
    def _get_cached_results(self, query: str, search_type: SearchType, location: str) -> List[SearchResult]:
        """Get cached search results"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            # Check if cache is still valid
            cutoff_time = datetime.now() - timedelta(hours=self.cache_ttl_hours)
            
            cursor.execute("""
                SELECT results FROM search_cache 
                WHERE query = ? AND search_type = ? AND location = ? 
                AND timestamp > ?
            """, (query, search_type.value if hasattr(search_type, 'value') else str(search_type), location, cutoff_time))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                results_data = json.loads(row[0])
                return [SearchResult(**item) for item in results_data]
            
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        
        return []
    
    def _cache_results(self, query: str, search_type: SearchType, location: str, results: List[SearchResult]):
        """Cache search results"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            # Convert results to JSON-serializable format
            results_data = []
            for result in results:
                result_dict = {
                    'title': result.title,
                    'description': result.description,
                    'url': result.url,
                    'source': result.source,
                    'type': result.type.value if hasattr(result.type, 'value') else str(result.type),
                    'metadata': result.metadata,
                    'confidence_score': result.confidence_score,
                    'timestamp': datetime.now().isoformat()
                }
                results_data.append(result_dict)
            
            cursor.execute("""
                INSERT OR REPLACE INTO search_cache 
                (query, search_type, location, results) 
                VALUES (?, ?, ?, ?)
            """, (query, search_type.value if hasattr(search_type, 'value') else str(search_type), location, json.dumps(results_data)))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def _get_sample_data(self, search_type: SearchType, query: str) -> List[SearchResult]:
        """Get sample data as fallback"""
        sample_data = {
            SearchType.JOBS: [
                SearchResult(
                    title="Sample Job Opportunity",
                    description="Entry-level position with growth potential",
                    url="https://example.com/job",
                    source="sample_data",
                    type=SearchType.JOBS,
                    metadata={'sample': True},
                    confidence_score=0.5
                )
            ],
            SearchType.HOUSING: [
                SearchResult(
                    title="Sample Housing Resource",
                    description="Affordable housing option in the area",
                    url="https://example.com/housing",
                    source="sample_data",
                    type=SearchType.HOUSING,
                    metadata={'sample': True},
                    confidence_score=0.5
                )
            ],
            SearchType.SERVICES: [
                SearchResult(
                    title="Sample Service Provider",
                    description="Local service organization",
                    url="https://example.com/service",
                    source="sample_data",
                    type=SearchType.SERVICES,
                    metadata={'sample': True},
                    confidence_score=0.5
                )
            ],
            SearchType.GENERAL: [
                SearchResult(
                    title="Sample Information",
                    description="General information about your query",
                    url="https://example.com/info",
                    source="sample_data",
                    type=SearchType.GENERAL,
                    metadata={'sample': True},
                    confidence_score=0.5
                )
            ]
        }
        
        return sample_data.get(search_type, [])
    
    def _format_response(self, results: List[SearchResult], source: str) -> Dict[str, Any]:
        """Format response in standard schema"""
        return {
            'success': True,
            'results': [
                {
                    'title': result.title,
                    'description': result.description,
                    'url': result.url,
                    'source': result.source,
                    'type': result.type.value if hasattr(result.type, 'value') else str(result.type),
                    'metadata': result.metadata,
                    'confidence_score': result.confidence_score,
                    'timestamp': result.timestamp or datetime.now().isoformat()
                }
                for result in results
            ],
            'total_count': len(results),
            'source': source,
            'timestamp': datetime.now().isoformat()
        }
    
    # Placeholder methods for additional APIs
    def _search_indeed_api(self, query: str, location: str) -> List[SearchResult]:
        """Indeed API search (placeholder)"""
        return []
    
    def _search_hud_api(self, query: str, location: str) -> List[SearchResult]:
        """HUD API search (placeholder)"""
        return []
    
    def _search_local_jobs(self, query: str, location: str) -> List[SearchResult]:
        """Local jobs database search (placeholder)"""
        return []
    
    def _search_local_housing(self, query: str, location: str) -> List[SearchResult]:
        """Local housing database search (placeholder)"""
        return []
    
    def _search_local_services(self, query: str, location: str) -> List[SearchResult]:
        """Local services database search (placeholder)"""
        return []
    
    def _ai_enhance_job_query(self, query: str, location: str) -> str:
        """Use OpenAI to enhance job search query"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            prompt = f"""
            Enhance this job search query for better results:
            
            Original query: "{query}"
            Location: "{location}"
            
            Please provide a more targeted job search query that includes:
            1. Relevant synonyms and alternative job titles
            2. Industry-specific keywords
            3. Background-friendly alternatives if applicable
            
            Return only the enhanced query text, no explanations.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3
            )
            
            enhanced_query = response.choices[0].message.content.strip()
            logger.info(f"AI enhanced query: '{query}' -> '{enhanced_query}'")
            return enhanced_query
            
        except Exception as e:
            logger.error(f"AI query enhancement failed: {e}")
            return query
    
    def _scraper_job_search(self, query: str, location: str) -> List[SearchResult]:
        """Use job scrapers as fallback when APIs are unavailable"""
        try:
            # Import the job search manager to access scrapers
            from backend.modules.jobs.job_search_manager import job_search_manager
            
            # Start a quick scraper search
            search_id = f"coordinator_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            success = job_search_manager.start_search(
                search_id=search_id,
                keywords=query,
                location=location,
                max_pages=1  # Quick search with limited pages
            )
            
            if success:
                # Wait a bit for results (scrapers are async)
                import time
                max_wait = 15  # Maximum wait time in seconds
                wait_time = 0
                
                while wait_time < max_wait:
                    status = job_search_manager.get_search_status(search_id)
                    if not status.get('is_running', True):
                        break
                    time.sleep(1)
                    wait_time += 1
                
                # Get results from scrapers
                scraper_jobs = job_search_manager.get_search_results(search_id)
                
                results = []
                for job in scraper_jobs:
                    results.append(SearchResult(
                        title=job.get('title', ''),
                        description=job.get('description', job.get('content', '')),
                        url=job.get('url', job.get('link', '')),
                        source=job.get('source', 'scraper'),
                        type=SearchType.JOBS,
                        metadata={
                            'scraper_source': True,
                            'company': job.get('company', ''),
                            'location': job.get('location', location),
                            'posted_date': job.get('posted_date', ''),
                            'job_type': job.get('type', '')
                        },
                        confidence_score=0.9,  # High confidence for real scraped jobs
                        timestamp=datetime.now().isoformat()
                    ))
                
                logger.info(f"Scrapers found {len(results)} real job listings")
                return results
            
        except Exception as e:
            logger.error(f"Scraper job search failed: {e}")
        
        return []

# Global instance - lazy initialization
_coordinator: Optional[SimpleSearchCoordinator] = None

def get_coordinator() -> SimpleSearchCoordinator:
    """Get the search coordinator instance (lazy initialization)"""
    global _coordinator
    if _coordinator is None:
        _coordinator = SimpleSearchCoordinator()
    return _coordinator 