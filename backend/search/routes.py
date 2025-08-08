#!/usr/bin/env python3
"""
Simple Search API Routes - Unified search endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging

from .coordinator import get_coordinator, SearchType

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(prefix="/search", tags=["search"])

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    search_type: str  # "jobs", "housing", "services", "general"
    location: Optional[str] = "Los Angeles, CA"
    max_results: Optional[int] = 20

class SearchResponse(BaseModel):
    success: bool
    results: List[Dict[str, Any]]
    total_count: int
    source: str
    timestamp: str

@router.get("/")
async def search_api_info():
    """Search API information"""
    return {
        "message": "Simple Search API Ready",
        "version": "1.0",
        "search_types": ["jobs", "housing", "services", "general"],
        "features": [
            "Unified search interface",
            "Robust API fallbacks",
            "Caching system",
            "Sample data fallback"
        ]
    }

@router.get("/jobs")
async def search_jobs(
    query: str = Query(..., description="Job search query"),
    location: str = Query("Los Angeles, CA", description="Search location"),
    max_results: int = Query(20, description="Maximum number of results")
):
    """Search for jobs"""
    try:
        logger.info(f"🔍 Job search: '{query}' in '{location}'")
        
        # Update max results
        coordinator = get_coordinator()
        coordinator.max_results = max_results
        
        result = coordinator.search(query, SearchType.JOBS, location)
        return result
        
    except Exception as e:
        logger.error(f"Job search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/housing")
async def search_housing(
    query: str = Query(..., description="Housing search query"),
    location: str = Query("Los Angeles, CA", description="Search location"),
    max_results: int = Query(20, description="Maximum number of results")
):
    """Search for housing"""
    try:
        logger.info(f"Housing search: '{query}' in '{location}'")
        
        # Update max results
        coordinator = get_coordinator()
        coordinator.max_results = max_results
        
        result = coordinator.search(query, SearchType.HOUSING, location)
        return result
        
    except Exception as e:
        logger.error(f"Housing search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services")
async def search_services(
    query: str = Query(..., description="Services search query"),
    location: str = Query("Los Angeles, CA", description="Search location"),
    max_results: int = Query(20, description="Maximum number of results")
):
    """Search for services"""
    try:
        logger.info(f"Services search: '{query}' in '{location}'")
        
        # Update max results
        coordinator = get_coordinator()
        coordinator.max_results = max_results
        
        result = coordinator.search(query, SearchType.SERVICES, location)
        return result
        
    except Exception as e:
        logger.error(f"Services search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/general")
async def search_general(
    query: str = Query(..., description="General search query"),
    location: str = Query("Los Angeles, CA", description="Search location"),
    max_results: int = Query(20, description="Maximum number of results")
):
    """General web search"""
    try:
        logger.info(f"🌐 General search: '{query}' in '{location}'")
        
        # Update max results
        coordinator = get_coordinator()
        coordinator.max_results = max_results
        
        result = coordinator.search(query, SearchType.GENERAL, location)
        return result
        
    except Exception as e:
        logger.error(f"General search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/unified")
async def unified_search(request: SearchRequest):
    """Unified search endpoint - accepts any search type"""
    try:
        # Validate search type
        valid_types = ["jobs", "housing", "services", "general"]
        if request.search_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid search_type. Must be one of: {valid_types}"
            )
        
        # Convert string to SearchType enum
        search_type_map = {
            "jobs": SearchType.JOBS,
            "housing": SearchType.HOUSING,
            "services": SearchType.SERVICES,
            "general": SearchType.GENERAL
        }
        
        search_type = search_type_map[request.search_type]
        
        logger.info(f"🔍 Unified search: '{request.query}' | Type: {request.search_type} | Location: {request.location}")
        
        # Update max results
        coordinator = get_coordinator()
        coordinator.max_results = request.max_results or 20
        
        result = coordinator.search(request.query, search_type, request.location)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unified search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def search_health():
    """Search system health check"""
    try:
        coordinator = get_coordinator()
        return {
            "status": "healthy",
            "search_coordinator": "initialized",
            "google_api_configured": bool(coordinator.google_api_key),
            "google_cse_configured": bool(coordinator.google_cse_id),
            "cache_enabled": True,
            "fallback_enabled": coordinator.fallback_to_samples,
            "max_results": coordinator.max_results,
            "cache_ttl_hours": coordinator.cache_ttl_hours
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/cache/clear")
async def clear_search_cache():
    """Clear search cache (admin endpoint)"""
    try:
        import sqlite3
        conn = sqlite3.connect(get_coordinator().cache_db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM search_cache")
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Search cache cleared successfully"
        }
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache/stats")
async def get_cache_stats():
    """Get search cache statistics"""
    try:
        import sqlite3
        conn = sqlite3.connect(get_coordinator().cache_db_path)
        cursor = conn.cursor()
        
        # Get total cache entries
        cursor.execute("SELECT COUNT(*) FROM search_cache")
        total_entries = cursor.fetchone()[0]
        
        # Get cache entries by type
        cursor.execute("""
            SELECT search_type, COUNT(*) 
            FROM search_cache 
            GROUP BY search_type
        """)
        entries_by_type = dict(cursor.fetchall())
        
        # Get oldest and newest entries
        cursor.execute("""
            SELECT MIN(timestamp), MAX(timestamp) 
            FROM search_cache
        """)
        oldest, newest = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_entries": total_entries,
            "entries_by_type": entries_by_type,
            "oldest_entry": oldest,
            "newest_entry": newest,
            "cache_ttl_hours": get_coordinator().cache_ttl_hours
        }
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 