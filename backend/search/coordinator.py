#!/usr/bin/env python3
"""
Simple Search Coordinator - Bullet-proof unified search layer
Unifies Jobs | Housing | Services | General Web search behind ONE coordinator
"""

import os
import logging
import asyncio
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
from urllib.parse import urlparse
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

# Scrapers removed - using Google Custom Search only
SCRAPER_AVAILABLE = False
universal_scraper = None

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
        self.google_api_key = self._normalize_key(os.getenv("GOOGLE_API_KEY"))
        self.serper_api_key = self._normalize_key(
            os.getenv("SERPAPI_API_KEY") or os.getenv("SERPER_API_KEY")
        )
        
        # Services CSE (original) - for services and general searches
        self.google_cse_id = self._normalize_key(
            os.getenv("GOOGLE_CSE_ID") or os.getenv("CUSTOM_SEARCH_ENGINE_ID")
        )
        
        # NEW: Jobs-specific CSE for better job search results
        self.google_jobs_cse_id = self._normalize_key(os.getenv("GOOGLE_JOBS_CSE_ID", "b5088b7b14bdb4f11"))
        
        # NEW: Housing-specific CSE for real rental listings
        self.google_housing_cse_id = self._normalize_key(os.getenv("GOOGLE_HOUSING_CSE_ID", "268132a59ec674755"))
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.cache_db_path = "databases/search_cache.db"
        self.sample_db_path = "databases/sample_data.db"
        logger.info(f"SerpAPI Key: {'Loaded' if self.serper_api_key else 'Missing'}")
        
        # Debug API key loading
        logger.info(f"Google API Key: {'Loaded' if self.google_api_key else 'Missing'}")
        logger.info(f"Services CSE ID: {'Loaded' if self.google_cse_id else 'Missing'}")
        logger.info(f"Jobs CSE ID: {'Loaded' if self.google_jobs_cse_id else 'Missing'}")
        logger.info(f"Housing CSE ID: {'Loaded' if self.google_housing_cse_id else 'Missing'}")
        logger.info(f"OpenAI API Key: {'Loaded' if self.openai_api_key else 'Missing'}")
        
        # Initialize cache database
        self._init_cache_db()
        
        # Search configuration
        self.max_results = 20
        self.cache_ttl_hours = 0.1  # 6 minutes for testing scrapers
        self.fallback_to_samples = False
        
        logger.info("Simple Search Coordinator initialized")

    def _normalize_key(self, value: Optional[str]) -> Optional[str]:
        """Normalize API keys/CSE IDs and treat placeholders as missing."""
        if not value:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        placeholders = {
            "YOUR_GOOGLE_API_KEY_HERE",
            "YOUR_GOOGLE_API_KEY",
            "YOUR_CSE_ID_HERE",
            "CHANGE_ME",
            "CHANGEME",
        }
        if cleaned in placeholders:
            return None
        return cleaned
    
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
    
    def search(self, query: str, search_type: SearchType, location: str = "Los Angeles, CA", force_refresh: bool = False) -> Dict[str, Any]:
        """
        Main search method - unified interface for all search types
        Returns standardized result format
        """
        try:
            logger.info(f"Search: '{query}' | Type: {search_type.value} | Location: {location} | Force: {force_refresh}")
            
            # Check cache first (unless force refresh)
            if not force_refresh:
                cached_results = self._get_cached_results(query, search_type, location)
                if cached_results:
                    logger.info(f"Returning cached results: {len(cached_results)} items")
                    return self._format_response(cached_results, "cache")
            else:
                logger.info("Force refresh requested - bypassing cache")
            
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
            
            # No sample data fallback
            if not results:
                logger.info("No results found from live providers")
            
            return self._format_response(results, "fresh_search")
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return self._format_response([], "error_no_fallback")
    
    def _search_jobs(self, query: str, location: str) -> List[SearchResult]:
        """Search for jobs using Serper first, then Google CSE"""
        results = []
        
        try:
            if self.serper_api_key:
                location_phrase = f" in {location}" if location else ""
                job_query = f"{query} jobs hiring{location_phrase}"
                serp_jobs = self._serpapi_jobs_search(job_query, location, 1, self.max_results)
                serp_items = self._filter_job_results_by_location(serp_jobs.get("results", []), location, strict=False)
                if serp_items:
                    for item in serp_items:
                        link = ""
                        related_links = item.get("related_links") or []
                        if related_links:
                            link = related_links[0].get("link", "")
                        if not link:
                            link = item.get("share_link") or item.get("job_id", "")
                        results.append(SearchResult(
                            title=item.get('title', ''),
                            description=item.get('description', ''),
                            url=link,
                            source='serpapi_jobs',
                            type=SearchType.JOBS,
                            metadata={
                                'search_engine': 'serpapi_jobs',
                                'company': item.get('company_name', '')
                            },
                            confidence_score=0.9,
                            timestamp=datetime.now().isoformat()
                        ))

                if results:
                    return results[:self.max_results]

                # Fallback to Google engine + domain filter if jobs engine returns nothing
                job_query = (
                    f"{query} jobs hiring career employment "
                    "site:indeed.com OR site:linkedin.com/jobs OR site:glassdoor.com OR "
                    "site:ziprecruiter.com OR site:monster.com OR site:snagajob.com OR "
                    "site:craigslist.org OR site:governmentjobs.com OR site:usajobs.gov OR "
                    "site:caljobs.ca.gov OR site:builtin.com OR site:careerbuilder.com "
                    "-for rent -lease -commercial -real estate"
                )
                serper = self._serpapi_paginated_search(job_query, location, 1, self.max_results)
                serper_items = self._filter_job_results(serper.get("results", []))
                serper_items = self._filter_job_results_by_location(serper_items, location, strict=False)
                serper_results = self._map_serper_results(serper_items, SearchType.JOBS)
                for item in serper_results:
                    item.source = "serpapi"
                    item.metadata = {**item.metadata, "search_engine": "serpapi"}
                results.extend(serper_results)
                if results:
                    return results[:self.max_results]

            if self.google_api_key and self.google_jobs_cse_id:
                enhanced_query = f"{query} employment career position hiring"

                logger.info(f"Jobs search: '{enhanced_query}' using Jobs CSE: {self.google_jobs_cse_id}")

                google_results = self._google_custom_search_with_cse(enhanced_query, location, self.google_jobs_cse_id)
                logger.info(f"Jobs CSE returned {len(google_results)} results")

                filtered_results = self._filter_job_results(google_results)
                for item in filtered_results:
                    results.append(SearchResult(
                        title=item.get('title', ''),
                        description=item.get('snippet', ''),
                        url=item.get('link', ''),
                        source='google_jobs_cse',
                        type=SearchType.JOBS,
                        metadata={'search_engine': 'google_jobs_cse', 'cse_id': self.google_jobs_cse_id},
                        confidence_score=0.95,
                        timestamp=datetime.now().isoformat()
                    ))

            elif self.google_api_key and self.google_cse_id:
                logger.warning("Jobs CSE not available, falling back to general CSE")
                google_results = self._google_custom_search(f"{query} jobs", location)
                logger.info(f"Fallback CSE returned {len(google_results)} results")

                filtered_results = self._filter_job_results(google_results)
                for item in filtered_results:
                    results.append(SearchResult(
                        title=item.get('title', ''),
                        description=item.get('snippet', ''),
                        url=item.get('link', ''),
                        source='google_general_cse_fallback',
                        type=SearchType.JOBS,
                        metadata={'search_engine': 'google_fallback'},
                        confidence_score=0.8,
                        timestamp=datetime.now().isoformat()
                    ))

        except Exception as e:
            logger.error(f"Job search error: {e}")
            try:
                if self.google_api_key and self.google_cse_id:
                    logger.warning("Attempting fallback to general CSE after error")
                    google_results = self._google_custom_search(f"{query} jobs employment", location)
                    filtered_results = self._filter_job_results(google_results)
                    for item in filtered_results:
                        results.append(SearchResult(
                            title=item.get('title', ''),
                            description=item.get('snippet', ''),
                            url=item.get('link', ''),
                            source='google_error_fallback',
                            type=SearchType.JOBS,
                            metadata={'search_engine': 'google_error_fallback'},
                            confidence_score=0.7,
                            timestamp=datetime.now().isoformat()
                        ))
            except Exception as fallback_error:
                logger.error(f"Fallback job search also failed: {fallback_error}")
        
        return results[:self.max_results]
        
    def _search_housing(self, query: str, location: str) -> List[SearchResult]:
        """Search for housing using Google Custom Search - FIXED TO MATCH SERVICES"""
        results = []
        
        try:
            # Primary: Google Custom Search for housing (SAME AS SERVICES)
            if self.google_api_key and self.google_cse_id:
                google_results = self._google_custom_search(f"{query} housing", location)
                logger.info(f"Housing search returned {len(google_results)} results")
                
                for item in google_results:
                    results.append(SearchResult(
                        title=item.get('title', ''),
                        description=item.get('snippet', ''),
                        url=item.get('link', ''),
                        source='google_housing',
                        type=SearchType.HOUSING,
                        metadata={'search_engine': 'google'},
                        confidence_score=0.9,  # High confidence for real Google results
                        timestamp=datetime.now().isoformat()
                    ))
            
            # NO FALLBACKS - ONLY GOOGLE RESULTS (SAME AS SERVICES)
            
        except Exception as e:
            logger.error(f"Housing search error: {e}")
        
        return results[:self.max_results]
    
    def _google_custom_search(self, query: str, location: str) -> List[Dict[str, Any]]:
        """
        Google Custom Search API implementation
        Returns raw Google search results for processing
        """
        try:
            if not self.google_api_key or not self.google_cse_id:
                logger.warning("Google Custom Search API credentials not available")
                return []
            
            # Build search query with location
            search_query = f"{query} {location}" if location else query
            
            # Google Custom Search API endpoint
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': self.google_cse_id,
                'q': search_query,
                'num': 10,  # Number of results to return
                'safe': 'active'
            }
            
            logger.info(f"Google Custom Search: '{search_query}'")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            logger.info(f"Google Custom Search returned {len(items)} results")
            return items
            
        except Exception as e:
            logger.error(f"Google Custom Search error: {e}")
            return []
    
    def _search_services(self, query: str, location: str) -> List[SearchResult]:
        """Search for services using Serper first, then Google CSE"""
        results = []
        
        try:
            if self.serper_api_key:
                serper = self._serper_search(f"{query} services", location, self.max_results)
                serper_results = self._map_serper_results(serper.get("results", []), SearchType.SERVICES)
                results.extend(serper_results)
                if results:
                    return results[:self.max_results]
            
            if self.google_api_key and self.google_cse_id:
                google_results = self._google_custom_search(f"{query} services", location)
                logger.info(f"Services search returned {len(google_results)} results")
            
                for item in google_results:
                    results.append(SearchResult(
                        title=item.get('title', ''),
                        description=item.get('snippet', ''),
                        url=item.get('link', ''),
                        source='google_services',
                        type=SearchType.SERVICES,
                        metadata={'search_engine': 'google'},
                        confidence_score=0.9,
                        timestamp=datetime.now().isoformat()
                    ))
        
        except Exception as e:
            logger.error(f"Services search error: {e}")
        
        return results[:self.max_results]
        
    def _search_general(self, query: str, location: str) -> List[SearchResult]:
        """General web search"""
        results = []
        
        try:
            if self.serper_api_key:
                serper = self._serper_search(query, location, self.max_results)
                serper_results = self._map_serper_results(serper.get("results", []), SearchType.GENERAL)
                results.extend(serper_results)
                if results:
                    return results[:self.max_results]
            
            if self.google_api_key and self.google_cse_id:
                google_results = self._google_custom_search(query, location)
                logger.info(f"General search returned {len(google_results)} results")
            
                for item in google_results:
                    results.append(SearchResult(
                        title=item.get('title', ''),
                        description=item.get('snippet', ''),
                        url=item.get('link', ''),
                        source='google_general',
                        type=SearchType.GENERAL,
                        metadata={'search_engine': 'google'},
                        confidence_score=0.8,
                        timestamp=datetime.now().isoformat()
                    ))
        except Exception as e:
            logger.error(f"General search error: {e}")
        
        return results[:self.max_results]
        
    def _map_serper_results(self, items: List[Dict[str, Any]], search_type: SearchType) -> List[SearchResult]:
        """Map Serper organic results to SearchResult list."""
        results: List[SearchResult] = []
        for item in items:
            results.append(SearchResult(
                title=item.get('title', ''),
                description=item.get('snippet') or item.get('description', ''),
                url=item.get('link', ''),
                source='serpapi',
                type=search_type,
                metadata={'search_engine': 'serpapi'},
                confidence_score=0.9,
                timestamp=datetime.now().isoformat()
            ))
        return results
        
    def _google_custom_search(self, query: str, location: str) -> List[Dict]:
        """Google Custom Search API using default CSE"""
        return self._google_custom_search_with_cse(query, location, self.google_cse_id)
    
    def _google_custom_search_with_cse(self, query: str, location: str, cse_id: str) -> List[Dict]:
        """Google Custom Search API with specific CSE ID"""
        try:
            import requests

            if not self.google_api_key or not cse_id:
                logger.warning("Google Custom Search credentials not available")
                return []
            
            url = "https://www.googleapis.com/customsearch/v1"
            # Combine query and location, but handle empty location
            search_query = f"{query} {location}".strip()
            params = {
                'key': self.google_api_key,
                'cx': cse_id,
                'q': search_query,
                'num': min(self.max_results, 10)  # Google CSE limit
            }
            
            logger.info(f"Google Custom Search query: '{search_query}' using CSE: {cse_id}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            logger.info(f"Google Custom Search returned {len(items)} items")
            
            return items
            
        except Exception as e:
            logger.error(f"Google Custom Search error with CSE {cse_id}: {e}")
            return []
    
    async def _paginated_google_search(self, query: str, cse_id: str, page: int = 1, per_page: int = 10):
        """
        Perform paginated Google Custom Search API calls
        Google CSE supports max 10 results per call, so we make multiple calls if needed
        """
        try:
            import requests

            if not self.google_api_key or not cse_id:
                return {
                    'items': [],
                    'total_results': 0,
                    'actual_returned': 0,
                    'error': 'Google Custom Search credentials not available'
                }
            
            # Validate parameters
            page = max(1, page)
            per_page = min(max(1, per_page), 40)  # Max 40 results (4 API calls)
            
            # Calculate how many API calls we need
            calls_needed = min(3, (per_page + 9) // 10)  # Max 3 calls, ceiling division
            
            all_items = []
            total_results_estimate = 0
            
            # Calculate starting position for the requested page
            start_index = (page - 1) * per_page + 1
            
            logger.info(f"Paginated search: page {page}, per_page {per_page}, start_index {start_index}")
            
            # Make multiple API calls to get enough results
            for call_num in range(calls_needed):
                # Calculate start position for this API call
                api_start = start_index + (call_num * 10)
                
                # Google CSE has a limit of 100 results total
                if api_start > 100:
                    logger.warning(f"Reached Google CSE limit (start={api_start})")
                    break
                
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.google_api_key,
                    'cx': cse_id,
                    'q': query,
                    'start': api_start,
                    'num': 10  # Always request 10 per API call
                }
                
                logger.info(f"API call {call_num + 1}/{calls_needed}: start={api_start}")
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                items = data.get('items', [])
                
                # Get total results estimate from first call
                if call_num == 0:
                    search_info = data.get('searchInformation', {})
                    total_results_estimate = int(search_info.get('totalResults', '0'))
                    logger.info(f"Total results estimate: {total_results_estimate}")
                
                all_items.extend(items)
                
                # If we got fewer than 10 results, we've reached the end
                if len(items) < 10:
                    logger.info(f"Reached end of results (got {len(items)} items)")
                    break
            
            # Trim results to exactly what was requested
            trimmed_items = all_items[:per_page]
            
            logger.info(f"Paginated search complete: {len(trimmed_items)} items returned")
            
            return {
                'items': trimmed_items,
                'total_results': total_results_estimate,
                'actual_returned': len(trimmed_items)
            }
            
        except Exception as e:
            logger.error(f"Paginated Google search error: {e}")
            return {
                'items': [],
                'total_results': 0,
                'actual_returned': 0,
                'error': str(e)
            }
    
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
    
    def _analyze_result_with_ai(self, result: SearchResult) -> Dict[str, Any]:
        """Analyze search result with AI to provide recommendations"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            # Create analysis prompt based on result type
            if result.type == SearchType.JOBS:
                prompt = f"""
                Analyze this job listing for someone with a criminal background seeking employment:
                
                Title: {result.title}
                Description: {result.description[:500]}
                
                Provide a brief analysis including:
                1. Background-friendliness likelihood (1-10 scale)
                2. Key requirements that might be barriers
                3. Why this might be a good opportunity
                4. One sentence recommendation
                
                Format as JSON with keys: background_score, barriers, opportunities, recommendation
                """
            elif result.type == SearchType.SERVICES:
                prompt = f"""
                Analyze this service for someone in reentry:
                
                Title: {result.title}
                Description: {result.description[:500]}
                
                Provide a brief analysis including:
                1. Relevance for reentry population (1-10 scale)
                2. Type of support provided
                3. Potential benefits
                4. One sentence recommendation
                
                Format as JSON with keys: relevance_score, support_type, benefits, recommendation
                """
            elif result.type == SearchType.HOUSING:
                prompt = f"""
                Analyze this housing option for someone with a criminal background:
                
                Title: {result.title}
                Description: {result.description[:500]}
                
                Provide a brief analysis including:
                1. Background-friendliness likelihood (1-10 scale)
                2. Potential barriers or requirements
                3. Housing type and benefits
                4. One sentence recommendation
                
                Format as JSON with keys: background_score, barriers, housing_type, recommendation
                """
            else:
                return None
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # Try to parse as JSON, fallback to text
            try:
                import json
                analysis = json.loads(analysis_text)
                return analysis
            except:
                return {"recommendation": analysis_text}
                
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None
    
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

    def _filter_job_results(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Reduce clutter by only keeping results from known job domains."""
        allowed_domains = {
            "indeed.com",
            "linkedin.com",
            "glassdoor.com",
            "ziprecruiter.com",
            "monster.com",
            "snagajob.com",
            "craigslist.org",
            "governmentjobs.com",
            "usajobs.gov",
            "caljobs.ca.gov",
            "builtin.com",
            "careerbuilder.com",
            "simplyhired.com",
            "jobcase.com",
            "jooble.org",
            "talent.com",
            "lensa.com",
            "adzuna.com",
            "ziprecruiter.com",
            "roberthalf.com",
            "randstadusa.com",
            "myworkdayjobs.com",
            "icims.com",
            "lever.co",
            "greenhouse.io",
            "workforcenow.adp.com",
            "smartrecruiters.com"
        }

        filtered: List[Dict[str, Any]] = []
        for item in items:
            link = item.get("link", "")
            parsed = urlparse(link)
            hostname = (parsed.hostname or "").lower()
            path = (parsed.path or "").lower()
            if any(hostname.endswith(domain) for domain in allowed_domains):
                if "/browse" in path:
                    continue
                if hostname.endswith("linkedin.com") and "/jobs" not in path:
                    continue
                if hostname.endswith("indeed.com") and ("/viewjob" not in path and "/rc/clk" not in path):
                    continue
                filtered.append(item)

        return filtered

    def _filter_job_results_by_location(self, items: List[Dict[str, Any]], location: Optional[str], strict: bool = False) -> List[Dict[str, Any]]:
        """Prefer results that match the requested city name."""
        if not location:
            return items
        parts = [p.strip() for p in location.split(",")]
        city = parts[0].lower() if parts and parts[0] else ""
        state = parts[1].lower() if len(parts) > 1 else ""
        if not city:
            return items

        filtered = []
        for item in items:
            haystack = f"{item.get('title', '')} {item.get('snippet', '')} {item.get('description', '')}".lower()
            if city in haystack:
                filtered.append(item)

        if filtered:
            return filtered

        # Fallback to state-level filter (e.g., "CA" or "California")
        if state:
            state_hits = []
            for item in items:
                haystack = f"{item.get('title', '')} {item.get('snippet', '')} {item.get('description', '')}".lower()
                if state in haystack or "california" in haystack:
                    state_hits.append(item)
            if state_hits:
                return state_hits

        return [] if strict else items
    
    async def search_jobs(self, query: str, location: str = None, page: int = 1, per_page: int = 10):
        """Search for jobs using dedicated Jobs CSE with pagination support"""
        try:
            # Validate pagination parameters
            page = max(1, page)  # Ensure page is at least 1
            per_page = min(max(1, per_page), 40)  # Limit per_page between 1 and 40

            # Primary: SerpAPI when available
            if self.serper_api_key:
                location_phrase = f" in {location}" if location else ""
                job_query = f"{query} jobs hiring{location_phrase}"
                serp_jobs = self._serpapi_jobs_search(job_query, location, page, per_page)
                serp_results = self._filter_job_results_by_location(serp_jobs.get("results", []), location, strict=False)
                job_results = []
                seen_links = set()
                for item in serp_results:
                    link = ""
                    related_links = item.get("related_links") or []
                    if related_links:
                        link = related_links[0].get("link", "")
                    if not link:
                        link = item.get("share_link") or item.get("job_id", "")
                    if link and link in seen_links:
                        continue
                    if link:
                        seen_links.add(link)
                    job_results.append({
                        'title': item.get('title', ''),
                        'description': item.get('description', ''),
                        'link': link,
                        'source': 'serpapi_jobs',
                        'provider': item.get('company_name', ''),
                        'background_friendly': False
                    })

                # Fill with SerpAPI Google engine results if needed
                if len(job_results) < per_page:
                    job_query = (
                        f"{query} jobs hiring career employment Los Angeles CA "
                        "site:indeed.com OR site:linkedin.com/jobs OR site:glassdoor.com OR "
                        "site:ziprecruiter.com OR site:monster.com OR site:snagajob.com OR "
                        "site:craigslist.org OR site:governmentjobs.com OR site:usajobs.gov OR "
                        "site:caljobs.ca.gov OR site:builtin.com OR site:careerbuilder.com OR "
                        "site:simplyhired.com OR site:jobcase.com OR site:jooble.org OR "
                        "site:talent.com OR site:lensa.com OR site:adzuna.com OR "
                        "site:myworkdayjobs.com OR site:icims.com OR site:lever.co OR "
                        "site:greenhouse.io OR site:workforcenow.adp.com OR site:smartrecruiters.com "
                        "-for rent -lease -commercial -real estate"
                    )
                    serp_fallback = self._serpapi_paginated_search(job_query, location, page, per_page)
                    serp_items = self._filter_job_results(serp_fallback.get("results", []))
                    serp_items = self._filter_job_results_by_location(serp_items, location, strict=True)
                    for item in serp_items:
                        link = item.get('link', '')
                        if link and link in seen_links:
                            continue
                        if link:
                            seen_links.add(link)
                        job_results.append({
                            'title': item.get('title', ''),
                            'description': item.get('snippet', ''),
                            'link': link,
                            'source': 'serpapi',
                            'background_friendly': False
                        })
                        if len(job_results) >= per_page:
                            break

                # If still low, expand to California-wide to increase volume
                if len(job_results) < per_page:
                    job_query = (
                        f"{query} jobs hiring California "
                        "site:indeed.com OR site:linkedin.com/jobs OR site:glassdoor.com OR "
                        "site:ziprecruiter.com OR site:monster.com OR site:snagajob.com OR "
                        "site:craigslist.org OR site:governmentjobs.com OR site:usajobs.gov OR "
                        "site:caljobs.ca.gov OR site:builtin.com OR site:careerbuilder.com OR "
                        "site:simplyhired.com OR site:jobcase.com OR site:jooble.org OR "
                        "site:talent.com OR site:lensa.com OR site:adzuna.com OR "
                        "site:myworkdayjobs.com OR site:icims.com OR site:lever.co OR "
                        "site:greenhouse.io OR site:workforcenow.adp.com OR site:smartrecruiters.com "
                        "-for rent -lease -commercial -real estate"
                    )
                    serp_fallback = self._serpapi_paginated_search(job_query, "California", page, per_page)
                    serp_items = self._filter_job_results(serp_fallback.get("results", []))
                    serp_items = self._filter_job_results_by_location(serp_items, "CA", strict=True)
                    for item in serp_items:
                        link = item.get('link', '')
                        if link and link in seen_links:
                            continue
                        if link:
                            seen_links.add(link)
                        job_results.append({
                            'title': item.get('title', ''),
                            'description': item.get('snippet', ''),
                            'link': link,
                            'source': 'serpapi',
                            'background_friendly': False
                        })
                        if len(job_results) >= per_page:
                            break

                if job_results:
                    return {
                        "success": True,
                        "query": query,
                        "location": location,
                        "results": job_results[:per_page],
                        "total_count": len(job_results[:per_page]),
                        "source": "serpapi_jobs",
                        "pagination": {
                            "current_page": page,
                            "per_page": per_page,
                            "total_results": len(job_results[:per_page]),
                            "total_pages": 1,
                            "has_next_page": False,
                            "has_prev_page": False,
                            "start_index": 1 if job_results else 0,
                            "end_index": len(job_results[:per_page])
                        }
                    }

                # Fallback to Google engine with strict job domains if jobs engine returns nothing
                job_query = (
                    f"{query} jobs hiring career employment "
                    "site:indeed.com OR site:linkedin.com/jobs OR site:glassdoor.com OR "
                    "site:ziprecruiter.com OR site:monster.com OR site:snagajob.com OR "
                    "site:craigslist.org OR site:governmentjobs.com OR site:usajobs.gov OR "
                    "site:caljobs.ca.gov OR site:builtin.com OR site:careerbuilder.com "
                    "-for rent -lease -commercial -real estate"
                )
                serper_payload = self._serpapi_paginated_search(job_query, location, page, per_page)
                serper_results = self._filter_job_results(serper_payload.get("results", []))
                serper_results = self._filter_job_results_by_location(serper_results, location, strict=False)
                if serper_results:
                    job_results = []
                    for item in serper_results:
                        job_results.append({
                            'title': item.get('title', ''),
                            'description': item.get('snippet', ''),
                            'link': item.get('link', ''),
                            'source': 'serpapi',
                            'background_friendly': False
                        })
                    return {
                        "success": True,
                        "query": query,
                        "location": location,
                        "results": job_results,
                        "total_count": len(job_results),
                        "source": "serpapi",
                        "pagination": {
                            "current_page": page,
                            "per_page": per_page,
                            "total_results": len(job_results),
                            "total_pages": 1,
                            "has_next_page": False,
                            "has_prev_page": False,
                            "start_index": 1 if job_results else 0,
                            "end_index": len(job_results)
                        }
                    }
            
            # Use the dedicated jobs CSE
            cse_id = self.google_jobs_cse_id
            if not self.google_api_key or not cse_id:
                return {
                    "success": False,
                    "query": query,
                    "location": location,
                    "results": [],
                    "source": "config_missing",
                    "error": "Google API key or Jobs CSE ID not configured",
                    "pagination": {
                        "current_page": page,
                        "per_page": per_page,
                        "total_results": 0,
                        "total_pages": 0,
                        "has_next_page": False,
                        "has_prev_page": False,
                        "start_index": 0,
                        "end_index": 0
                    }
                }
            
            # Enhanced query for better job results
            enhanced_query = query
            if location:
                enhanced_query = f"{query} {location}"
            
            # Add job-specific keywords to improve relevance
            job_keywords = "employment career position hiring -for rent -lease -commercial -real estate"
            enhanced_query = f"{enhanced_query} {job_keywords}"
            
            logger.info(f"Jobs search: '{enhanced_query}' using CSE: {cse_id} (page {page}, per_page {per_page})")
            
            # Perform paginated search with jobs CSE
            paginated_results = await self._paginated_google_search(
                query=enhanced_query,
                cse_id=cse_id,
                page=page,
                per_page=per_page
            )
            
            # Format results for API compatibility
            formatted_results = []
            filtered_items = self._filter_job_results(paginated_results.get('items', []))
            filtered_items = self._filter_job_results_by_location(filtered_items, location, strict=False)
            for item in filtered_items:
                formatted_results.append({
                    'title': item.get('title', ''),
                    'description': item.get('snippet', ''),
                    'link': item.get('link', ''),
                    'source': 'google_jobs_cse'
                })
            
            # Calculate pagination metadata
            total_results = len(formatted_results)
            total_pages = max(1, (total_results + per_page - 1) // per_page)  # Ceiling division
            has_next_page = page < total_pages
            has_prev_page = page > 1
            
            # Same formatting as integration script with pagination metadata
            return {
                "success": True,
                "query": query,
                "location": location,
                "results": formatted_results,
                "source": "google_jobs_cse",
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": total_results,
                    "total_pages": total_pages,
                    "has_next_page": has_next_page,
                    "has_prev_page": has_prev_page,
                    "start_index": (page - 1) * per_page + 1,
                    "end_index": min(page * per_page, total_results)
                }
            }
            
        except Exception as e:
            logger.error(f"Jobs search error: {e}")
            # Fallback to original CSE if jobs CSE fails
            return await self._fallback_jobs_search(query, location, page, per_page)
    
    async def _fallback_jobs_search(self, query: str, location: str = None, page: int = 1, per_page: int = 10):
        """Fallback to original CSE if jobs CSE fails"""
        logger.warning("Falling back to original CSE for jobs search")
        
        enhanced_query = f"{query} jobs employment"
        if location:
            enhanced_query = f"{enhanced_query} {location}"
            
        try:
            # Use paginated search for fallback too
            paginated_results = await self._paginated_google_search(
                query=enhanced_query,
                cse_id=self.google_cse_id,  # Original CSE
                page=page,
                per_page=per_page
            )
            
            # Format results
            formatted_results = []
            for item in paginated_results['items']:
                formatted_results.append({
                    'title': item.get('title', ''),
                    'description': item.get('snippet', ''),
                    'link': item.get('link', ''),
                    'source': 'google_general_cse_fallback'
                })
            
            # Calculate pagination metadata
            total_results = paginated_results.get('total_results', len(formatted_results))
            total_pages = max(1, (total_results + per_page - 1) // per_page)
            
            return {
                "success": True,
                "query": query,
                "location": location,
                "results": formatted_results,
                "source": "google_general_cse_fallback",
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": total_results,
                    "total_pages": total_pages,
                    "has_next_page": page < total_pages,
                    "has_prev_page": page > 1,
                    "start_index": (page - 1) * per_page + 1,
                    "end_index": min(page * per_page, total_results)
                }
            }
        except Exception as e:
            logger.error(f"Fallback jobs search also failed: {e}")
            # Return empty results with pagination structure
            return {
                "success": False,
                "query": query,
                "location": location,
                "results": [],
                "source": "fallback_failed",
                "error": str(e),
                "pagination": {
                    "current_page": 1,
                    "per_page": per_page,
                    "total_results": 0,
                    "total_pages": 0,
                    "has_next_page": False,
                    "has_prev_page": False,
                    "start_index": 0,
                    "end_index": 0
                }
            }

    async def search_services(self, query: str, location: str = None, page: int = 1, per_page: int = 10):
        """Search for services using original CSE with pagination support"""
        try:
            # Validate pagination parameters
            page = max(1, page)  # Ensure page is at least 1
            per_page = min(max(1, per_page), 40)  # Limit per_page between 1 and 40

            # Primary: SerpAPI when available
            if self.serper_api_key:
                serper_payload = self._serpapi_paginated_search(query, location, page, per_page)
                serper_results = serper_payload.get("results", [])
                if serper_results:
                    formatted_results = []
                    for item in serper_results:
                        formatted_results.append({
                            'title': item.get('title', ''),
                            'description': item.get('snippet') or item.get('description', ''),
                            'link': item.get('link', ''),
                            'source': 'serpapi'
                        })

                    return {
                        "success": True,
                        "query": query,
                        "location": location,
                        "results": formatted_results,
                        "source": "serpapi",
                        "pagination": {
                            "current_page": page,
                            "per_page": per_page,
                            "total_results": len(formatted_results),
                            "total_pages": 1,
                            "has_next_page": False,
                            "has_prev_page": False,
                            "start_index": 1 if formatted_results else 0,
                            "end_index": len(formatted_results)
                        }
                    }
            
            # Use original CSE for services
            cse_id = self.google_cse_id
            if not self.google_api_key or not cse_id:
                return {
                    "success": False,
                    "query": query,
                    "location": location,
                    "results": [],
                    "source": "config_missing",
                    "error": "Google API key or Services CSE ID not configured",
                    "pagination": {
                        "current_page": page,
                        "per_page": per_page,
                        "total_results": 0,
                        "total_pages": 0,
                        "has_next_page": False,
                        "has_prev_page": False,
                        "start_index": 0,
                        "end_index": 0
                    }
                }
            
            enhanced_query = query
            if location:
                enhanced_query = f"{query} {location}"
            
            # Add service-specific keywords
            service_keywords = "therapy counseling medical benefits social services"
            enhanced_query = f"{enhanced_query} {service_keywords}"
            
            logger.info(f"Services search: '{enhanced_query}' using CSE: {cse_id} (page {page}, per_page {per_page})")
            
            # Perform paginated search with services CSE
            paginated_results = await self._paginated_google_search(
                query=enhanced_query,
                cse_id=cse_id,
                page=page,
                per_page=per_page
            )
            
            # If Google errored, fallback to SerpAPI
            if not paginated_results or paginated_results.get("error"):
                if self.serper_api_key:
                    serper_payload = self._serpapi_paginated_search(query, location, page, per_page)
                    serper_results = serper_payload.get("results", [])
                    formatted_results = []
                    for item in serper_results:
                        formatted_results.append({
                            'title': item.get('title', ''),
                            'description': item.get('snippet') or item.get('description', ''),
                            'link': item.get('link', ''),
                            'source': 'serpapi'
                        })
                    return {
                        "success": True,
                        "query": query,
                        "location": location,
                        "results": formatted_results,
                        "source": "serpapi",
                        "pagination": {
                            "current_page": page,
                            "per_page": per_page,
                            "total_results": len(formatted_results),
                            "total_pages": 1,
                            "has_next_page": False,
                            "has_prev_page": False,
                            "start_index": 1 if formatted_results else 0,
                            "end_index": len(formatted_results)
                        }
                    }

            # Format results
            formatted_results = []
            for item in paginated_results['items']:
                formatted_results.append({
                    'title': item.get('title', ''),
                    'description': item.get('snippet', ''),
                    'link': item.get('link', ''),
                    'source': 'google_services_cse'
                })
            
            # Calculate pagination metadata
            total_results = paginated_results.get('total_results', len(formatted_results))
            total_pages = max(1, (total_results + per_page - 1) // per_page)
            has_next_page = page < total_pages
            has_prev_page = page > 1
            
            return {
                "success": True,
                "query": query,
                "location": location,
                "results": formatted_results,
                "source": "google_services_cse",
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": total_results,
                    "total_pages": total_pages,
                    "has_next_page": has_next_page,
                    "has_prev_page": has_prev_page,
                    "start_index": (page - 1) * per_page + 1,
                    "end_index": min(page * per_page, total_results)
                }
            }
            
        except Exception as e:
            logger.error(f"Services search error: {e}")
            # Return error with pagination structure
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "location": location,
                "results": [],
                "source": "error",
                "pagination": {
                    "current_page": 1,
                    "per_page": per_page,
                    "total_results": 0,
                    "total_pages": 0,
                    "has_next_page": False,
                    "has_prev_page": False,
                    "start_index": 0,
                    "end_index": 0
                }
            }


    
    async def _fallback_housing_search(self, query: str, location: str = None, page: int = 1, per_page: int = 10):
        """Fallback to original CSE if housing CSE fails"""
        logger.warning("Falling back to original CSE for housing search")
        
        enhanced_query = f"{query} housing apartment rental"
        if location:
            enhanced_query = f"{enhanced_query} {location}"
            
        try:
            # Use paginated search for fallback too
            paginated_results = await self._paginated_google_search(
                query=enhanced_query,
                cse_id=self.google_cse_id,  # Original CSE
                page=page,
                per_page=per_page
            )
            
            # Format results
            formatted_results = []
            for item in paginated_results['items']:
                formatted_results.append({
                    'title': item.get('title', ''),
                    'description': item.get('snippet', ''),
                    'link': item.get('link', ''),
                    'source': 'google_general_cse_fallback'
                })
            
            # Calculate pagination metadata
            total_results = paginated_results.get('total_results', len(formatted_results))
            total_pages = max(1, (total_results + per_page - 1) // per_page)
            
            return {
                "success": True,
                "query": query,
                "location": location,
                "results": formatted_results,
                "source": "google_general_cse_fallback",
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": total_results,
                    "total_pages": total_pages,
                    "has_next_page": page < total_pages,
                    "has_prev_page": page > 1,
                    "start_index": (page - 1) * per_page + 1,
                    "end_index": min(page * per_page, total_results)
                }
            }
        except Exception as e:
            logger.error(f"Fallback housing search also failed: {e}")
            # Return empty results with pagination structure
            return {
                "success": False,
                "query": query,
                "location": location,
                "results": [],
                "source": "fallback_failed",
                "error": str(e),
                "pagination": {
                    "current_page": 1,
                    "per_page": per_page,
                    "total_results": 0,
                    "total_pages": 0,
                    "has_next_page": False,
                    "has_prev_page": False,
                    "start_index": 0,
                    "end_index": 0
                }
            }

    async def search_housing(self, query: str, location: str = None, page: int = 1, per_page: int = 10, force_refresh: bool = False):
        """
        ✅ HOUSING SEARCH METHOD - FULLY FUNCTIONAL - DO NOT MODIFY
        
        This method is working perfectly with:
        - Dedicated Google Housing CSE (ID: 268132a59ec674755)
        - Real housing listings (13M+ results)
        - Proper pagination and error handling
        - Fallback to general CSE if needed
        
        ⚠️  WARNING: CSE ID is correctly configured - do not change
        ⚠️  Response format matches frontend expectations - do not modify
        ⚠️  Pagination logic is working - do not change parameters
        
        Search for housing using dedicated Housing CSE with pagination support
        """
        try:
            # Validate pagination parameters
            page = max(1, page)  # Ensure page is at least 1
            per_page = min(max(1, per_page), 40)  # Limit per_page between 1 and 40
            
            # Use dedicated housing CSE
            housing_cse_id = self.google_housing_cse_id or self.google_cse_id
            if not self.google_api_key or not housing_cse_id:
                if self.serper_api_key:
                    serper = self._serpapi_paginated_search(f"{query} apartment rental", location, page, per_page)
                    serper_items = serper.get("results", [])
                    housing_listings = [
                        {
                            'title': item.get('title', ''),
                            'description': item.get('snippet') or item.get('description', ''),
                            'url': item.get('link', ''),
                            'link': item.get('link', ''),
                            'source': 'serpapi',
                            'background_friendly': False
                        } for item in serper_items
                    ]
                    return {
                        "success": True,
                        "query": query,
                        "location": location,
                        "housing_listings": housing_listings,
                        "total_count": len(housing_listings),
                        "source": "serpapi",
                        "pagination": {
                            "current_page": page,
                            "per_page": per_page,
                            "total_results": len(housing_listings),
                            "total_pages": 1,
                            "has_next_page": False,
                            "has_prev_page": False,
                            "start_index": 1 if housing_listings else 0,
                            "end_index": len(housing_listings)
                        }
                    }
                return {
                    "success": False,
                    "query": query,
                    "location": location,
                    "housing_listings": [],
                    "total_count": 0,
                    "source": "config_missing",
                    "error": "Google API key or Housing CSE ID not configured",
                    "pagination": {
                        "current_page": page,
                        "per_page": per_page,
                        "total_results": 0,
                        "total_pages": 0,
                        "has_next_page": False,
                        "has_prev_page": False,
                        "start_index": 0,
                        "end_index": 0
                    }
                }
            
            enhanced_query = query
            if location:
                enhanced_query = f"{query} {location}"
            
            # Add housing-specific keywords
            housing_keywords = "apartment rental housing rent lease"
            enhanced_query = f"{enhanced_query} {housing_keywords}"
            
            logger.info(f"Housing search: '{enhanced_query}' using Housing CSE: {housing_cse_id} (page {page}, per_page {per_page})")
            
            # Use paginated search
            paginated_results = await self._paginated_google_search(
                query=enhanced_query,
                cse_id=housing_cse_id,
                page=page,
                per_page=per_page
            )
            
            # Check for API errors or unexpected responses
            if not paginated_results or paginated_results.get("error"):
                error_detail = paginated_results.get("error", "Unknown error")
                logger.error(f"Housing search failed: {error_detail}")
                if self.serper_api_key:
                    serper = self._serpapi_paginated_search(f"{query} apartment rental", location, page, per_page)
                    serper_items = serper.get("results", [])
                    housing_listings = [
                        {
                            'title': item.get('title', ''),
                            'description': item.get('snippet') or item.get('description', ''),
                            'url': item.get('link', ''),
                            'link': item.get('link', ''),
                            'source': 'serpapi',
                            'background_friendly': False
                        } for item in serper_items
                    ]
                    total_results = len(housing_listings)
                    return {
                        "success": True,
                        "query": query,
                        "location": location,
                        "housing_listings": housing_listings,
                        "total_count": total_results,
                        "source": "serpapi",
                        "pagination": {
                            "current_page": page,
                            "per_page": per_page,
                            "total_results": total_results,
                            "total_pages": 1,
                            "has_next_page": False,
                            "has_prev_page": False,
                            "start_index": 1 if total_results else 0,
                            "end_index": total_results
                        }
                    }
                return {
                    "success": False,
                    "query": query,
                    "location": location,
                    "housing_listings": [],
                    "total_count": 0,
                    "source": "error",
                    "error": error_detail,
                    "pagination": {
                        "current_page": page,
                        "per_page": per_page,
                        "total_results": 0,
                        "total_pages": 0,
                        "has_next_page": False,
                        "has_prev_page": False,
                        "start_index": 0,
                        "end_index": 0
                    }
                }
            if 'items' not in paginated_results:
                logger.error(f"Paginated search returned unexpected structure: {paginated_results}")
                return await self._fallback_housing_search(query, location, page, per_page)
            
            # Format results for housing
            housing_listings = []
            for item in paginated_results['items']:
                housing_listings.append({
                    'title': item.get('title', ''),
                    'description': item.get('snippet', ''),
                    'url': item.get('link', ''),
                    'link': item.get('link', ''),  # Compatibility
                    'source': 'google_housing_cse',
                    'background_friendly': False  # Default, can be enhanced later
                })
            
            if not housing_listings and self.serper_api_key:
                serper = self._serpapi_paginated_search(f"{query} apartment rental", location, page, per_page)
                serper_items = serper.get("results", [])
                housing_listings = [
                    {
                        'title': item.get('title', ''),
                        'description': item.get('snippet') or item.get('description', ''),
                        'url': item.get('link', ''),
                        'link': item.get('link', ''),
                        'source': 'serper',
                        'background_friendly': False
                    } for item in serper_items
                ]
                total_results = len(housing_listings)
                return {
                    "success": True,
                    "query": query,
                    "location": location,
                    "housing_listings": housing_listings,
                    "total_count": total_results,
                    "source": "serper",
                    "pagination": {
                        "current_page": page,
                        "per_page": per_page,
                        "total_results": total_results,
                        "total_pages": 1,
                        "has_next_page": False,
                        "has_prev_page": False,
                        "start_index": 1 if total_results else 0,
                        "end_index": total_results
                    }
                }
            
            # Calculate pagination metadata
            total_results = paginated_results.get('total_results', len(housing_listings))
            total_pages = max(1, (total_results + per_page - 1) // per_page)
            
            return {
                "success": True,
                "query": query,
                "location": location,
                "housing_listings": housing_listings,
                "total_count": total_results,
                "source": "google_housing_cse",
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": total_results,
                    "total_pages": total_pages,
                    "has_next_page": page < total_pages,
                    "has_prev_page": page > 1,
                    "start_index": (page - 1) * per_page + 1,
                    "end_index": min(page * per_page, total_results)
                }
            }
            
        except Exception as e:
            logger.error(f"Housing search error: {e}")
            # Fallback to original CSE if housing CSE fails
            return await self._fallback_housing_search(query, location, page, per_page)
    
    async def _fallback_housing_search(self, query: str, location: str = None, page: int = 1, per_page: int = 10):
        """Fallback to original CSE if housing CSE fails"""
        logger.warning("Falling back to original CSE for housing search")
        
        enhanced_query = f"{query} housing apartment rental"
        if location:
            enhanced_query = f"{enhanced_query} {location}"
            
        try:
            # Use paginated search for fallback too
            paginated_results = await self._paginated_google_search(
                query=enhanced_query,
                cse_id=self.google_cse_id,  # Original CSE
                page=page,
                per_page=per_page
            )
            
            # Format results
            housing_listings = []
            for item in paginated_results['items']:
                housing_listings.append({
                    'title': item.get('title', ''),
                    'description': item.get('snippet', ''),
                    'url': item.get('link', ''),
                    'link': item.get('link', ''),
                    'source': 'google_general_cse_fallback',
                    'background_friendly': False
                })
            
            # Calculate pagination metadata
            total_results = paginated_results.get('total_results', len(housing_listings))
            total_pages = max(1, (total_results + per_page - 1) // per_page)
            
            return {
                "success": True,
                "query": query,
                "location": location,
                "housing_listings": housing_listings,
                "total_count": total_results,
                "source": "google_general_cse_fallback",
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": total_results,
                    "total_pages": total_pages,
                    "has_next_page": page < total_pages,
                    "has_prev_page": page > 1,
                    "start_index": (page - 1) * per_page + 1,
                    "end_index": min(page * per_page, total_results)
                }
            }
        except Exception as e:
            logger.error(f"Fallback housing search also failed: {e}")
            # Return empty results with pagination structure
            return {
                "success": False,
                "query": query,
                "location": location,
                "housing_listings": [],
                "total_count": 0,
                "source": "fallback_failed",
                "error": str(e),
                "pagination": {
                    "current_page": 1,
                    "per_page": per_page,
                    "total_results": 0,
                    "total_pages": 0,
                    "has_next_page": False,
                    "has_prev_page": False,
                    "start_index": 0,
                    "end_index": 0
                }
            }

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

    def _serper_search(self, query: str, location: Optional[str], max_results: int, start: int = 0) -> Dict[str, Any]:
        """Search using SerpAPI (google engine) for listings."""
        if not self.serper_api_key:
            return {"results": [], "error": "SerpAPI key not configured"}

        try:
            search_query = query.strip()
            if location:
                search_query = f"{search_query} {location}"

            params = {
                "engine": "google",
                "q": search_query,
                "num": max_results,
                "start": max(0, start),
                "hl": "en",
                "gl": "us",
                "api_key": self.serper_api_key
            }

            response = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {"results": data.get("organic_results", []), "error": None}
        except Exception as e:
            logger.error(f"SerpAPI search error: {e}")
            return {"results": [], "error": str(e)}

    def _serpapi_paginated_search(self, query: str, location: Optional[str], page: int, per_page: int) -> Dict[str, Any]:
        """Fetch more than 10 SerpAPI results by paging with start offsets."""
        try:
            page = max(1, page)
            per_page = min(max(1, per_page), 40)

            start_offset = (page - 1) * per_page
            remaining = per_page
            results: List[Dict[str, Any]] = []

            while remaining > 0:
                batch_size = min(10, remaining)
                payload = self._serper_search(query, location, batch_size, start=start_offset)
                if payload.get("error"):
                    return {"results": [], "error": payload.get("error")}

                batch_items = payload.get("results", [])
                results.extend(batch_items)

                if len(batch_items) < batch_size:
                    break

                remaining -= batch_size
                start_offset += batch_size

            return {"results": results, "error": None}
        except Exception as e:
            logger.error(f"SerpAPI paginated search error: {e}")
            return {"results": [], "error": str(e)}

    def _serpapi_jobs_search(self, query: str, location: Optional[str], page: int, per_page: int) -> Dict[str, Any]:
        """Use SerpAPI Google Jobs engine for cleaner job results."""
        if not self.serper_api_key:
            return {"results": [], "error": "SerpAPI key not configured"}

        try:
            page = max(1, page)
            per_page = min(max(1, per_page), 40)

            params = {
                "engine": "google_jobs",
                "q": query.strip(),
                "location": location or "",
                "hl": "en",
                "gl": "us",
                "api_key": self.serper_api_key
            }

            response = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            results = data.get("jobs_results", [])

            # google_jobs does not reliably support pagination; return first page only
            return {"results": results[:per_page], "error": None}
        except Exception as e:
            logger.error(f"SerpAPI jobs search error: {e}")
            return {"results": [], "error": str(e)}
    
    async def _paginated_google_search(self, query: str, cse_id: str, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        Perform paginated Google Custom Search API calls with robust error handling
        """
        try:
            import requests
            
            # Validate parameters
            page = max(1, page)
            per_page = min(max(1, per_page), 40)
            
            # FIXED: Add API key validation
            if not self.google_api_key:
                logger.error("Google API key not configured")
                return {
                    'items': [],
                    'total_results': 0,
                    'actual_returned': 0,
                    'error': 'API key not configured'
                }
            
            # Calculate starting position
            start_index = (page - 1) * per_page + 1
            calls_needed = min(3, (per_page + 9) // 10)
            
            all_items = []
            total_results_estimate = 0
            
            logger.info(f"Paginated search: page {page}, per_page {per_page}, start_index {start_index}")
            
            for call_num in range(calls_needed):
                api_start = start_index + (call_num * 10)
                
                if api_start > 100:
                    logger.warning(f"Reached Google CSE limit (start={api_start})")
                    break
                
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.google_api_key,
                    'cx': cse_id,
                    'q': query,
                    'start': api_start,
                    'num': 10
                }
                
                logger.info(f"API call {call_num + 1}/{calls_needed}: start={api_start}")
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # FIXED: Check if response has expected structure
                if 'items' not in data:
                    logger.warning(f"No 'items' in API response: {data}")
                    break
                    
                items = data['items']
                
                # Get total results estimate from first call
                if call_num == 0:
                    search_info = data.get('searchInformation', {})
                    total_results_estimate = int(search_info.get('totalResults', '0'))
                    logger.info(f"Total results estimate: {total_results_estimate}")
                
                all_items.extend(items)
                
                if len(items) < 10:
                    logger.info(f"Reached end of results (got {len(items)} items)")
                    break
            
            trimmed_items = all_items[:per_page]
            
            logger.info(f"Paginated search complete: {len(trimmed_items)} items returned")
            
            return {
                'items': trimmed_items,
                'total_results': total_results_estimate,
                'actual_returned': len(trimmed_items)
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error in paginated search: {e}")
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            error_message = "API request failed"
            if status_code:
                error_message = f"API request failed: HTTP {status_code}"
            return {
                'items': [],
                'total_results': 0,
                'actual_returned': 0,
                'error': error_message
            }
        except Exception as e:
            logger.error(f"Paginated Google search error: {e}")
            return {
                'items': [],
                'total_results': 0,
                'actual_returned': 0,
                'error': str(e)
            }

# ALL SCRAPER METHODS REMOVED - USING GOOGLE CUSTOM SEARCH ONLY

# Global instance - lazy initialization
_coordinator: Optional[SimpleSearchCoordinator] = None

def get_coordinator() -> SimpleSearchCoordinator:
    """Get the search coordinator instance (lazy initialization)"""
    global _coordinator
    if _coordinator is None:
        _coordinator = SimpleSearchCoordinator()
    return _coordinator 
