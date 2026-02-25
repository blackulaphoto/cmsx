#!/usr/bin/env python3
"""
Services Routes - Updated to use simple search system that works
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# Import the guide-compliant search system
from backend.search.coordinator import get_coordinator, SearchType

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(tags=["services"])

# Pydantic models
class ServiceSearch(BaseModel):
    search: Optional[str] = None
    location: Optional[str] = None
    max_results: Optional[int] = None

@router.get("/")
async def services_api_info():
    """Services API information"""
    return {
        "message": "Services API Ready - Using Simple Search System",
        "version": "2.0",
        "search_system": "simple_direct_api",
        "status": "operational"
    }

@router.get("/search")
@router.post("/search")
async def api_services_search(
    search_data: Optional[ServiceSearch] = Body(None),
    search: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    service_type: Optional[str] = Query(None),
    page: int = Query(1, description="Page number (starts from 1)", ge=1),
    per_page: int = Query(10, description="Results per page (max 30)", ge=1, le=30)
):
    """Simple, working services search using direct API calls with pagination"""
    try:
        # Handle both GET and POST requests
        if search_data:
            search_query = search_data.search
            location_param = search_data.location or "Los Angeles, CA"
        else:
            search_query = search or service_type or "services"
            location_param = location or "Los Angeles, CA"
        
        if not search_query:
            return {
                'success': False,
                'message': 'Search query is required',
                'service_providers': [],
                'total_count': 0,
                'pagination': {
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
        
        logger.info(f"Services Search: '{search_query}' in '{location_param}' (page {page}, per_page {per_page})")
        
        # Use the new paginated search coordinator
        coordinator = get_coordinator()
        result = await coordinator.search_services(search_query, location_param, page, per_page)
        
        if result['success']:
            logger.info(f"Services search result: {result['pagination']['total_results']} total providers, page {page}")
            
            # Format response to match expected structure
            return {
                'success': True,
                'service_providers': result['results'],
                'total_count': result['pagination']['total_results'],
                'pagination': result['pagination'],
                'source': result['source'],
                'timestamp': datetime.now().isoformat()
            }
        else:
            logger.error(f"Services search failed: {result.get('error', 'Unknown error')}")
            return {
                'success': False,
                'message': result.get('error', 'Search failed'),
                'service_providers': [],
                'total_count': 0,
                'pagination': result.get('pagination', {
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
        logger.error(f"Services search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Add other necessary endpoints here...
@router.get("/health")
async def health_check():
    """Health check for services"""
    return {
        "status": "healthy",
        "search_system": "simple_direct_api",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/providers")
async def get_providers(
    location: Optional[str] = Query("Los Angeles, CA"),
    service_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=30)
):
    """Get service providers"""
    try:
        search_query = service_type or "social services"
        
        # Use the search coordinator
        coordinator = get_coordinator()
        result = await coordinator.search_services(search_query, location, page, per_page)
        
        if result['success']:
            return {
                'success': True,
                'providers': result['results'],
                'total_count': result['pagination']['total_results'],
                'pagination': result['pagination'],
                'source': result['source'],
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': result.get('error', 'Search failed'),
                'providers': [],
                'total_count': 0,
                'pagination': result.get('pagination', {
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
        logger.error(f"Error getting providers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
