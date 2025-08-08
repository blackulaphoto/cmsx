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
from backend.search.coordinator import get_coordinator, SearchType

import uuid
from datetime import datetime
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from jobs.job_search_manager import job_search_manager
# from ai_search_coordinator import get_ai_coordinator  # COMMENTED OUT - Using simple search

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(tags=["jobs"])

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
    background_friendly: bool = Query(False, description="Filter for background-friendly jobs"),
    max_results: int = Query(20, description="Maximum number of results")
):
    """Quick job search with real-time results"""
    try:
        if not keywords:
            return {
                "success": True,
                "jobs": [],
                "total_count": 0,
                "message": "No keywords provided"
            }
        
        logger.info(f"Quick Job Search: '{keywords}' in '{location}' (background_friendly: {background_friendly})")
        
        # Use simple search system (AI coordinator commented out)
        coordinator = get_coordinator()
        result = coordinator.search(keywords, SearchType.JOBS, location)
        
        if result['success']:
            logger.info(f"Job search successful: {result['total_count']} results")
            
            return {
                "success": True,
                "jobs": result['results'],
                "total_count": result['total_count'],
                "source": "simple_search",
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.warning(f"Job search failed: {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "jobs": [],
                "total_count": 0,
                "error": result.get('error', 'Search failed'),
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error in quick job search: {e}")
        raise HTTPException(status_code=500, detail=f"Quick search failed: {str(e)}")

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
    background_friendly: bool = Query(False, description="Filter for background-friendly jobs"),
    max_results: int = Query(20, description="Maximum number of results")
):
    """AI-powered job search with real-time results"""
    try:
        if not keywords:
            return {"jobs": [], "message": "No keywords provided"}
        
        # Use simple search system (AI coordinator commented out)
        coordinator = get_coordinator()
        
        logger.info(f"💼 Simple Job Search: '{keywords}' in '{location}' (background_friendly: {background_friendly})")
        
        # Perform simple job search
        result = coordinator.search(keywords, SearchType.JOBS, location)
        
        if result['success'] and result.get('jobs'):
            logger.info(f"Simple Job Search Success: {len(result['jobs'])} jobs found")
            
            return {
                "success": True,
                "jobs": result['jobs'],
                "total_count": result['total_count'],
                "source": "ai_enhanced_search",
                "ai_metadata": {
                    "enhanced_query": result.get('enhanced_query'),
                    "ai_confidence": result.get('ai_confidence'),
                    "search_time": result.get('search_time')
                },
                "search_parameters": {
                    "keywords": keywords,
                    "location": location,
                    "background_friendly": background_friendly
                }
            }
        else:
            logger.warning(f"🔄 AI job search failed: {result.get('error_reason', 'Unknown error')}")
            
            # Fallback to existing job search manager
            manager = job_search_manager
            google_jobs = manager._search_google_jobs(keywords, location)
            
            # Apply background-friendly filtering if requested
            if background_friendly:
                filtered_jobs = []
                for job in google_jobs:
                    score = manager._calculate_background_score(job)
                    if score >= 60:
                        job['background_friendly_score'] = score
                        filtered_jobs.append(job)
                google_jobs = filtered_jobs
            
            return {
                "success": True,
                "jobs": google_jobs[:max_results],
                "total_count": len(google_jobs),
                "source": "fallback_search",
                "message": f"Using fallback search: {result.get('error_reason', 'AI search unavailable')}"
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



@router.get("/simple_search")
async def search_jobs_simple(
    keywords: str = Query("", description="Job search keywords"),
    location: str = Query("Los Angeles, CA", description="Job search location"),
    background_friendly: bool = Query(False, description="Filter for background-friendly jobs"),
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
