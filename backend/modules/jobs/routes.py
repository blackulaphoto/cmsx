#!/usr/bin/env python3
"""
Job Search Routes - FastAPI endpoints for job search functionality
"""

from fastapi import APIRouter, HTTPException, Request, Query, Body
# from ai_search_coordinator import ai_coordinator  # COMMENTED OUT - Using simple search
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import os
from backend.search.coordinator import get_coordinator, SearchType

import uuid
from datetime import datetime

from .job_search_manager import job_search_manager
from .scraper_search_manager import scraper_search_manager
from .simple_job_tools import get_job_search_resources
# from ai_search_coordinator import get_ai_coordinator  # COMMENTED OUT - Using simple search

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(tags=["jobs"])

# ── Low-barrier annotation ────────────────────────────────────────────────────
# Positive signals that suggest a posting is accessible to applicants with
# limited credentials or criminal justice history.
_LB_POSITIVE = [
    "entry level", "no experience required", "no experience needed",
    "no degree required", "no degree needed",
    "immediate hire", "immediate opening", "start immediately",
    "paid training", "we train", "will train",
    "temp agency", "staffing agency", "temp-to-hire", "temp to hire",
    "warehouse", "food service", "janitorial", "general labor",
    "delivery helper", "retail associate", "dishwasher", "line cook",
    "porter", "cleaner", "construction laborer",
]

# Phrases that explicitly signal a fair-chance / second-chance employer.
# Only these may be used to assert the posting is background-friendly.
_LB_FAIR_CHANCE = [
    "fair chance", "second chance", "background friendly",
    "fair chance employer", "fair-chance employer",
    "ban the box", "reentry", "re-entry",
]

# Risk/barrier signals → badge label
_LB_RISK: dict = {
    "background check required": "Background Check Mentioned",
    "clean background required": "Background Check Mentioned",
    "clean background": "Background Check Mentioned",
    "fingerprinting required": "Background Check Mentioned",
    "security clearance": "Clearance Risk",
    "government contract": "Clearance Risk",
    "school district": "Clearance Risk",
    "banking": "Clearance Risk",
    "financial services": "Clearance Risk",
    "healthcare clearance": "Clearance Risk",
    "caregiver clearance": "Clearance Risk",
    "law enforcement": "Clearance Risk",
    "clean driving record required": "Driving Record Mentioned",
    "clean driving record": "Driving Record Mentioned",
    "dmv record required": "Driving Record Mentioned",
    "motor vehicle record": "Driving Record Mentioned",
    "security guard card": "License Required",
    "professional license required": "License Required",
    "licensed and certified": "License Required",
}

# Positive badge signals → badge label
_LB_POSITIVE_BADGES: dict = {
    "entry level": "Entry Level",
    "no experience": "No Experience Listed",
    "no degree": "No Degree Listed",
    "paid training": "Paid Training",
    "we train": "Paid Training",
    "will train": "Paid Training",
    "immediate hire": "Immediate Hire",
    "immediately": "Immediate Hire",
    "temp agency": "Temp/Staffing",
    "staffing agency": "Temp/Staffing",
    "temp-to-hire": "Temp/Staffing",
    "temp to hire": "Temp/Staffing",
}


def _annotate_low_barrier(jobs: list) -> list:
    """Annotate each job dict with low_barrier_score, badges, risk_flags,
    and explicitly_fair_chance.  Does NOT remove or reorder jobs."""
    for job in jobs:
        text = " ".join([
            (job.get("title") or ""),
            (job.get("description") or ""),
            (job.get("provider") or ""),
            (job.get("source") or ""),
        ]).lower()

        score = 0
        explicitly_fair_chance = False
        risk_flags: list = []
        badges: list = []
        seen_badge_labels: set = set()

        for phrase in _LB_FAIR_CHANCE:
            if phrase in text:
                explicitly_fair_chance = True
                score += 30
                break

        for phrase in _LB_POSITIVE:
            if phrase in text:
                score += 5

        # Risk badges (unique by label)
        for phrase, label in _LB_RISK.items():
            if phrase in text and label not in seen_badge_labels:
                risk_flags.append(phrase)
                seen_badge_labels.add(label)
                badges.append({"label": label, "type": "risk"})

        # Positive badges (unique by label)
        for phrase, label in _LB_POSITIVE_BADGES.items():
            if phrase in text and label not in seen_badge_labels:
                seen_badge_labels.add(label)
                badges.append({"label": label, "type": "positive"})

        job["low_barrier_score"] = min(100, score)
        job["explicitly_fair_chance"] = explicitly_fair_chance
        job["risk_flags"] = risk_flags
        job["badges"] = badges
        # Keep legacy fields so old clients don't break
        job["background_friendly"] = explicitly_fair_chance
        job["background_friendly_score"] = 75 if explicitly_fair_chance else 0

    return jobs

# Pydantic models
class JobSearchRequest(BaseModel):
    keywords: str
    location: Optional[str] = "Los Angeles, CA"
    max_pages: Optional[int] = 2

class JobSearchResponse(BaseModel):
    status: str
    search_id: str
    message: str

@router.get("/search")
async def get_search_info():
    """Get information about available job search endpoints"""
    return {
        "message": "Job Search API Information",
        "available_endpoints": {
            "POST /search": "Start asynchronous job search",
            "GET /search/quick": "Quick real-time job search",
            "POST /search/ai": "AI-powered job search", 
            "GET /search/scrapers": "Scraper-based specific job listings",
            "GET /search/status": "Check search status by ID",
            "GET /search/results": "Get search results by ID",
            "GET /search/{search_id}": "Get detailed search information"
        },
        "example_usage": {
            "quick_search": "/api/jobs/search/quick?keywords=warehouse&location=Los Angeles",
            "async_search": "POST /api/jobs/search with {keywords, location, max_pages}",
            "ai_search": "POST /api/jobs/search/ai with {keywords, location}"
        }
    }

@router.get("/search/links")
async def get_job_search_links(
    keywords: str = Query("", description="Job search keywords"),
    location: str = Query("Los Angeles, CA", description="Job search location")
):
    """Generate client-ready job board search links for case manager workflow."""
    try:
        if not keywords.strip():
            return {
                "success": True,
                "keywords": "",
                "location": location,
                "search_urls": {},
                "background_friendly_searches": [],
                "known_employers": [],
                "message": "No keywords provided"
            }

        result = get_job_search_resources(keywords.strip(), location)
        result["message"] = f"Generated client-ready job search links for '{keywords.strip()}'"
        return result
    except Exception as e:
        logger.error(f"Job search links generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate job search links: {str(e)}")

@router.post("/search", response_model=JobSearchResponse)
async def start_job_search(request: JobSearchRequest):
    """Start an asynchronous job search"""
    try:
        # Generate unique search ID
        search_id = str(uuid.uuid4())
        
        # Validate input
        if not request.keywords or len(request.keywords.strip()) < 2:
            raise HTTPException(status_code=400, detail="Keywords must be at least 2 characters")
        
        if request.max_pages and (request.max_pages < 1 or request.max_pages > 5):
            raise HTTPException(status_code=400, detail="Max pages must be between 1 and 5")
        
        # Start the search
        success = job_search_manager.start_search(
            search_id=search_id,
            keywords=request.keywords.strip(),
            location=request.location or "Los Angeles, CA",
            max_pages=request.max_pages or 2
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start job search")
        
        logger.info(f"Started job search {search_id} for '{request.keywords}'")
        
        return JobSearchResponse(
            status="started",
            search_id=search_id,
            message=f"Job search started for '{request.keywords}'"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting job search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search/status")
async def get_search_status(search_id: str = Query(..., description="Search ID to check status for")):
    """Get the current status of a job search"""
    try:
        status = job_search_manager.get_search_status(search_id)
        
        if not status or status.get('current_source') == 'Not found':
            raise HTTPException(status_code=404, detail="Search not found")
        
        # Clean up the status for API response
        api_status = {
            'is_running': status.get('is_running', False),
            'progress': status.get('progress', 0),
            'current_source': status.get('current_source', 'Unknown'),
            'total_jobs_found': status.get('total_jobs_found', 0),
            'completed_sources': status.get('completed_sources', 0),
            'total_sources': status.get('total_sources', 0),
            'has_errors': len(status.get('errors', [])) > 0,
            'results': not status.get('is_running', True)  # Results available when not running
        }
        
        return api_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting search status: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/search/results")
async def get_search_results(search_id: str = Query(..., description="Search ID to get results for")):
    """Get the results of a completed job search"""
    try:
        # Check if search exists and is complete
        status = job_search_manager.get_search_status(search_id)
        if not status or status.get('current_source') == 'Not found':
            raise HTTPException(status_code=404, detail="Search not found")
        
        if status.get('is_running', True):
            raise HTTPException(status_code=202, detail="Search still in progress")
        
        # Get results
        results = job_search_manager.get_search_results(search_id)
        
        return {
            'search_id': search_id,
            'total_jobs': len(results),
            'jobs': results,
            'search_completed': True,
            'errors': status.get('errors', [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting search results: {e}")
        raise HTTPException(status_code=500, detail=f"Results retrieval failed: {str(e)}")

@router.get("/search/quick")
async def search_jobs_quick(
    keywords: str = Query("", description="Job search keywords"),
    location: str = Query("Los Angeles, CA", description="Job search location"),
    # `low_barrier` replaces the deprecated `background_friendly` param.
    # Both are accepted; neither filters results — annotation is always applied.
    low_barrier: bool = Query(False, description="Hint to surface fewer-barrier jobs first"),
    background_friendly: bool = Query(False, description="Deprecated alias for low_barrier"),
    page: int = Query(1, description="Page number (starts from 1)", ge=1),
    per_page: int = Query(10, description="Results per page (max 40)", ge=1, le=40)
):
    """Quick job search with real-time results and low-barrier annotation"""
    try:
        if not keywords:
            return {
                "success": True,
                "jobs": [],
                "total_count": 0,
                "message": "No keywords provided",
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

        logger.info(f"Quick Job Search: '{keywords}' in '{location}' (page {page}, per_page {per_page})")

        # Use new paginated search system
        coordinator = get_coordinator()
        result = await coordinator.search_jobs(keywords, location, page, per_page)

        if result['success']:
            source = result['source']
            total = result['pagination']['total_results']
            logger.info(f"Job search successful: '{keywords}' → {total} results via {source} (page {page})")

            annotated_jobs = _annotate_low_barrier(result['results'])

            return {
                "success": True,
                "jobs": annotated_jobs,
                "total_count": result['pagination']['total_results'],
                "query_used": result.get('query_used', keywords),
                "source": source,
                "degraded": result.get('degraded', False),
                "warning": result.get('warning'),
                "pagination": result['pagination'],
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.warning(f"Job search failed: {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "jobs": [],
                "total_count": 0,
                "error": result.get('error', 'Search failed'),
                "degraded": result.get('degraded', False),
                "warning": result.get('warning'),
                "pagination": result.get('pagination', {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": 0,
                    "total_pages": 0,
                    "has_next_page": False,
                    "has_prev_page": False,
                    "start_index": 0,
                    "end_index": 0
                }),
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error in quick job search: {e}")
        raise HTTPException(status_code=500, detail=f"Quick search failed: {str(e)}")

@router.get("/search/scrapers")
async def search_jobs_scrapers(
    keywords: str = Query("", description="Job search keywords"),
    location: str = Query("Los Angeles, CA", description="Job search location"),
    low_barrier: bool = Query(False, description="Hint to surface fewer-barrier jobs first"),
    background_friendly: bool = Query(False, description="Deprecated alias for low_barrier"),
    page: int = Query(1, description="Page number (starts from 1)", ge=1),
    per_page: int = Query(10, description="Results per page (max 40)", ge=1, le=40),
    sources: Optional[str] = Query(None, description="Comma-separated list of scrapers to use (craigslist,builtinla,government,city_la)")
):
    """Scraper-based job search with real-time results from specific job sites"""
    try:
        if not keywords:
            return {
                "success": True,
                "jobs": [],
                "total_count": 0,
                "message": "No keywords provided",
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
        
        # Parse sources parameter
        source_list = None
        if sources:
            source_list = [s.strip() for s in sources.split(',') if s.strip()]
        
        logger.info(f"Scraper Job Search: '{keywords}' in '{location}' (page {page}, per_page {per_page}, sources: {source_list})")

        # Use scraper search manager
        result = await scraper_search_manager.search_jobs(
            keywords=keywords,
            location=location,
            sources=source_list,
            max_results=per_page * 10,  # Get more results for better pagination
            background_friendly_only=False,  # Never filter — annotate instead
            page=page,
            strict_matching=True,
            per_page=per_page
        )
        
        if result['success']:
            logger.info(f"Scraper search successful: {result['pagination']['total_results']} total results, page {page}")
            
            # Transform results to match frontend expectations
            transformed_jobs = []
            for job in result['jobs']:
                job_url = job.get('source_url', '')
                
                # If no URL provided, create a fallback search URL based on the source
                if not job_url:
                    job_source = job.get('source', 'unknown')
                    job_title = job.get('title', '')
                    job_location = job.get('location', location)
                    
                    if job_source == 'craigslist':
                        # Create Craigslist search URL
                        search_query = job_title.replace(' ', '+')
                        job_url = f"https://losangeles.craigslist.org/search/jjj?query={search_query}"
                    elif job_source == 'builtinla':
                        # Create BuiltIn LA search URL
                        search_query = job_title.replace(' ', '%20')
                        job_url = f"https://builtin.com/jobs/los-angeles?q={search_query}"
                    elif job_source == 'government':
                        # Create USAJobs search URL
                        search_query = job_title.replace(' ', '+')
                        job_url = f"https://www.usajobs.gov/Search/Results?k={search_query}"
                    else:
                        # Generic Google search as fallback
                        search_query = f"{job_title} {job_location}".replace(' ', '+')
                        job_url = f"https://www.google.com/search?q={search_query}+jobs"
                
                transformed_job = {
                    'title': job.get('title', ''),
                    'company': job.get('company', ''),
                    'location': job.get('location', location),
                    'salary': job.get('salary', 'See job posting'),
                    'description': job.get('description', ''),
                    'url': job_url,
                    'link': job_url,  # Alternative field name
                    'source': job.get('source', 'scraper'),
                    'background_friendly_score': job.get('background_friendly_score', 0),
                    'metadata': job.get('metadata', {}),
                    'scraped_date': job.get('scraped_date', ''),
                    'external_id': job.get('external_id', '')
                }
                transformed_jobs.append(transformed_job)
            
            annotated_jobs = _annotate_low_barrier(transformed_jobs)

            return {
                "success": True,
                "jobs": annotated_jobs,
                "total_count": result['pagination']['total_results'],
                "source": result['source'],
                "pagination": result['pagination'],
                "search_metadata": result.get('search_metadata', {}),
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.warning(f"Scraper search failed: {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "jobs": [],
                "total_count": 0,
                "error": result.get('error', 'Scraper search failed'),
                "pagination": result.get('pagination', {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": 0,
                    "total_pages": 0,
                    "has_next_page": False,
                    "has_prev_page": False,
                    "start_index": 0,
                    "end_index": 0
                }),
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error in scraper job search: {e}")
        return {
            "success": False,
            "jobs": [],
            "total_count": 0,
            "error": f"Scraper search failed: {str(e)}",
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
            "timestamp": datetime.now().isoformat()
        }

@router.get("/search/{search_id}")
async def get_search_details(search_id: str):
    """Get detailed information about a specific search"""
    try:
        status = job_search_manager.get_search_status(search_id)
        results = job_search_manager.get_search_results(search_id)
        
        if not status or status.get('current_source') == 'Not found':
            raise HTTPException(status_code=404, detail="Search not found")
        
        return {
            'search_id': search_id,
            'status': status,
            'results_count': len(results),
            'sample_jobs': results[:5] if results else [],  # First 5 jobs as sample
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting search details: {e}")
        raise HTTPException(status_code=500, detail=f"Search details failed: {str(e)}")

# AI-enhanced endpoint for real-time job search
@router.get("")
async def search_jobs_ai(
    keywords: str = Query("", description="Job search keywords"),
    location: str = Query("Los Angeles, CA", description="Job search location"),
    low_barrier: bool = Query(False, description="Deprecated — annotation is always applied"),
    background_friendly: bool = Query(False, description="Deprecated alias for low_barrier"),
    page: int = Query(1, description="Page number (starts from 1)", ge=1),
    per_page: int = Query(10, description="Results per page (max 40)", ge=1, le=40)
):
    """AI-powered job search with real-time results and pagination"""
    try:
        if not keywords:
            return {
                "jobs": [], 
                "message": "No keywords provided",
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
        
        # Use new paginated search system
        coordinator = get_coordinator()
        
        logger.info(f"AI Job Search: '{keywords}' in '{location}' (page {page}, per_page {per_page})")
        
        # Perform paginated job search
        result = await coordinator.search_jobs(keywords, location, page, per_page)
        
        if result['success']:
            logger.info(f"AI Job Search Success: {result['pagination']['total_results']} total jobs, page {page}")
            
            return {
                "success": True,
                "jobs": result['results'],
                "total_count": result['pagination']['total_results'],
                "source": "ai_enhanced_search",
                "pagination": result['pagination'],
                "ai_metadata": {
                    "enhanced_query": result.get('enhanced_query'),
                    "ai_confidence": result.get('ai_confidence'),
                    "search_time": result.get('search_time')
                },
                "search_parameters": {
                    "keywords": keywords,
                    "location": location,
                    "page": page,
                    "per_page": per_page
                }
            }
        else:
            logger.warning(f"🔄 AI job search failed: {result.get('error', 'Unknown error')}")
            
            # Return error with pagination structure
            return {
                "success": False,
                "jobs": [],
                "total_count": 0,
                "source": "error",
                "error": result.get('error', 'Search failed'),
                "pagination": result.get('pagination', {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": 0,
                    "total_pages": 0,
                    "has_next_page": False,
                    "has_prev_page": False,
                    "start_index": 0,
                    "end_index": 0
                })
            }
            
    except Exception as e:
        logger.error(f"Job search error: {e}")
        return {"jobs": [], "error": str(e)}

# Also add a new dedicated AI job search endpoint
@router.post("/search/ai")
async def ai_job_search(request: JobSearchRequest):
    """Advanced AI-powered job search"""
    try:
        # Use simple search system (AI coordinator commented out)
        coordinator = get_coordinator()
        
        result = coordinator.search(
            request.keywords, 
            SearchType.JOBS,
            request.location or "Los Angeles, CA"
        )
        
        return {
            "search_id": str(uuid.uuid4()),
            "status": "completed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"AI job search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup")
async def cleanup_old_searches():
    """Clean up old search data (admin endpoint)"""
    try:
        job_search_manager.cleanup_old_searches(max_age_hours=24)
        return {"message": "Old searches cleaned up successfully"}
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if scrapers are initialized
        scraper_count = len(job_search_manager.scrapers)
        
        # Check if Google Custom Search is configured
        google_configured = bool(job_search_manager.google_api_key and job_search_manager.custom_search_engine_id)
        
        return {
            "status": "healthy",
            "scrapers_available": scraper_count,
            "google_search_configured": google_configured,
            "active_searches": len(job_search_manager.search_status),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/scrapers/health")
async def scrapers_health_check():
    """Health check endpoint for scraper system"""
    try:
        health_status = scraper_search_manager.get_health_status()
        available_scrapers = scraper_search_manager.get_available_scrapers()
        
        return {
            "status": health_status["status"],
            "scrapers_available": health_status["scrapers_available"],
            "scrapers_list": health_status["scrapers_list"],
            "available_scrapers": available_scrapers,
            "cache_enabled": health_status["cache_enabled"],
            "cache_ttl_minutes": health_status["cache_ttl_minutes"],
            "max_workers": health_status["max_workers"],
            "search_timeout": health_status["search_timeout"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Scrapers health check error: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "scrapers_available": 0,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/simple_search")
async def search_jobs_simple(
    keywords: str = Query("", description="Job search keywords"),
    location: str = Query("Los Angeles, CA", description="Job search location"),
    low_barrier: bool = Query(False, description="Deprecated — annotation is always applied"),
    background_friendly: bool = Query(False, description="Deprecated alias for low_barrier"),
    max_results: int = Query(20, description="Maximum number of results")
):
    """Simple, working job search using direct API calls"""
    try:
        if not keywords:
            return {
                "success": True,
                "jobs": [],
                "total_count": 0,
                "message": "No keywords provided"
            }
        
        logger.info(f"Simple Job Search: '{keywords}' in '{location}'")
        
        # Use simple search system
        coordinator = get_coordinator()
        result = coordinator.search(keywords, SearchType.JOBS, location)
        
        logger.info(f"Simple job search: {result.get('total_count')} jobs")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Job search error: {e}")
        return {
            "success": False,
            "jobs": [],
            "total_count": 0,
            "error": str(e)
        }

# Pydantic model for saving jobs
class SaveJobRequest(BaseModel):
    job_id: str
    client_id: str
    notes: Optional[str] = ""
    title: Optional[str] = ""
    company: Optional[str] = ""
    location: Optional[str] = ""
    salary: Optional[str] = ""
    url: Optional[str] = ""

@router.post("/save")
async def save_job(request: SaveJobRequest):
    """Save a job for a client"""
    try:
        # Create saved_jobs directory if it doesn't exist
        saved_jobs_dir = os.path.join(os.path.dirname(__file__), "saved_jobs")
        os.makedirs(saved_jobs_dir, exist_ok=True)
        
        # Create SQLite database for saved jobs
        db_path = os.path.join(saved_jobs_dir, "saved_jobs.db")
        
        # Initialize database
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                title TEXT,
                company TEXT,
                location TEXT,
                salary TEXT,
                url TEXT,
                notes TEXT,
                saved_date TEXT NOT NULL,
                UNIQUE(job_id, client_id)
            )
        ''')

        cursor.execute("PRAGMA table_info(saved_jobs)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        columns_to_add = {
            "title": "TEXT",
            "company": "TEXT",
            "location": "TEXT",
            "salary": "TEXT",
            "url": "TEXT",
        }
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                cursor.execute(f"ALTER TABLE saved_jobs ADD COLUMN {column_name} {column_type}")
        
        # Insert or update the saved job
        cursor.execute('''
            INSERT OR REPLACE INTO saved_jobs (
                job_id, client_id, title, company, location, salary, url, notes, saved_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.job_id,
            request.client_id,
            request.title,
            request.company,
            request.location,
            request.salary,
            request.url,
            request.notes,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Job {request.job_id} saved for client {request.client_id}")
        
        return {
            "success": True,
            "message": "Job saved successfully",
            "job_id": request.job_id,
            "client_id": request.client_id,
            "saved_date": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error saving job: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/saved/{client_id}")
async def get_saved_jobs(client_id: str):
    """Get all saved jobs for a client"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), "saved_jobs", "saved_jobs.db")
        
        if not os.path.exists(db_path):
            return {
                "success": True,
                "saved_jobs": [],
                "total_count": 0
            }
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT job_id, client_id, title, company, location, salary, url, notes, saved_date
            FROM saved_jobs
            WHERE client_id = ?
            ORDER BY saved_date DESC
        ''', (client_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        saved_jobs = []
        for row in rows:
            saved_jobs.append({
                "job_id": row[0],
                "client_id": row[1],
                "title": row[2],
                "company": row[3],
                "location": row[4],
                "salary": row[5],
                "url": row[6],
                "notes": row[7],
                "saved_date": row[8]
            })
        
        return {
            "success": True,
            "saved_jobs": saved_jobs,
            "total_count": len(saved_jobs)
        }
        
    except Exception as e:
        logger.error(f"Error getting saved jobs: {e}")
        return {
            "success": False,
            "error": str(e),
            "saved_jobs": [],
            "total_count": 0
        }
