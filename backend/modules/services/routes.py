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
    max_results: Optional[int] = Query(None),
    service_type: Optional[str] = Query(None)
):
    """Simple, working services search using direct API calls"""
    try:
        # Handle both GET and POST requests
        if search_data:
            search_query = search_data.search
            location_param = search_data.location or "Los Angeles, CA"
            max_results_param = search_data.max_results or 20
        else:
            search_query = search or service_type or "services"
            location_param = location or "Los Angeles, CA"
            max_results_param = max_results or 20
        
        if not search_query:
            return {
                'success': False,
                'message': 'Search query is required',
                'service_providers': [],
                'total_count': 0
            }
        
        logger.info(f"Simple Services Search: '{search_query}' in '{location_param}'")
        
        # Use the guide-compliant search coordinator
        coordinator = get_coordinator()
        result = coordinator.search(search_query, SearchType.SERVICES, location_param)
        
        logger.info(f"Simple search result: {result.get('total_count')} providers found")
        
        return result
        
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
