#!/usr/bin/env python3
"""
Housing Routes - FastAPI Router for Second Chance Jobs Platform
Background-friendly housing search and resource management
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
# from ai_search_coordinator import ai_coordinator  # COMMENTED OUT - Using simple search
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
from backend.search.coordinator import get_coordinator, SearchType

import json
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from housing.models import HousingResource, HousingDatabase
# from ai_search_coordinator import get_ai_coordinator  # COMMENTED OUT - Using simple search

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(tags=["housing"])

# Initialize database
housing_db = None

def get_housing_db():
    """Get thread-safe housing database instance"""
    global housing_db
    if housing_db is None:
        housing_db = HousingDatabase("databases/housing_resources.db")
    return housing_db

# Pydantic models
class HousingSearch(BaseModel):
    county: Optional[str] = None
    city: Optional[str] = None
    background_friendly: Optional[bool] = None
    program_type: Optional[str] = None
    max_cost: Optional[float] = None
    max_results: Optional[int] = 50

class HousingApplication(BaseModel):
    client_id: str
    housing_resource_id: str
    application_date: str = ""
    priority_level: str = "Medium"
    notes: str = ""

# =============================================================================
# API ROUTES
# =============================================================================

@router.get("/")
async def housing_api_info():
    """Housing API information and available endpoints"""
    return {
        "message": "Housing API Ready",
        "version": "1.0",
        "endpoints": {
            "search": "/api/housing/search",
            "applications": "/api/housing/applications",
            "resources": "/api/housing/resources",
            "waitlist": "/api/housing/waitlist"
        },
        "description": "Background-friendly housing resource coordination"
    }

@router.get("/search")
async def housing_search(
    county: Optional[str] = Query(None),
    city: Optional[str] = Query(None), 
    background_friendly: Optional[bool] = Query(True),
    program_type: Optional[str] = Query(None),
    max_cost: Optional[float] = Query(None),
    max_results: int = Query(50)
):
    """AI-powered housing search with real-time results"""
    try:
        # Build location string
        location = f"{city or ''} {county or 'Los Angeles'}, CA".strip()
        
        # Build search query
        query_parts = []
        if program_type:
            query_parts.append(program_type)
        query_parts.extend(["housing", "shelter", "transitional"])
        if background_friendly:
            query_parts.append("background friendly")
        
        search_query = " ".join(query_parts)
        
        logger.info(f"Housing Search: '{search_query}' in '{location}'")
        
        # Use simple search system (AI coordinator commented out)
        coordinator = get_coordinator()
        result = coordinator.search(search_query, SearchType.HOUSING, location)
        
        if result['success']:
            logger.info(f"Housing search successful: {result['total_count']} results")
            
            return {
                'success': True,
                'results': result['results'],
                'total_count': result['total_count'],
                'search_sources': [result['source']],
                'filters_applied': {
                    'county': county,
                    'city': city,
                    'background_friendly': background_friendly,
                    'program_type': program_type,
                    'max_cost': max_cost
                },
                'message': result.get('message', 'Search completed successfully')
            }
        else:
            logger.error("Housing search failed")
            raise HTTPException(status_code=500, detail="Housing search failed")
            
    except Exception as e:
        logger.error(f"Housing search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def housing_search_post(search_data: HousingSearch):
    """AI-powered housing search via POST"""
    try:
        # Use simple search system (AI coordinator commented out)
        coordinator = get_coordinator()
        location = f"{search_data.city or ''} {search_data.county or 'Los Angeles'}, CA".strip()
        query = "emergency shelter housing"
        if search_data.program_type:
            query = f"{search_data.program_type} {query}"
        if search_data.background_friendly:
            query += " background friendly"
        
        result = coordinator.search(query, SearchType.HOUSING, location)
        return result
        
    except Exception as e:
        logger.error(f"Housing search POST error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types")
async def get_housing_types():
    """Get all available housing types"""
    try:
        housing_db = get_housing_db()
        types = housing_db.get_housing_types()
        
        return {
            'success': True,
            'housing_types': types
        }
    except Exception as e:
        logger.error(f"Get housing types error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/counties")
async def get_housing_counties():
    """Get all available counties"""
    try:
        housing_db = get_housing_db()
        counties = housing_db.get_counties()
        
        return {
            'success': True,
            'counties': counties
        }
    except Exception as e:
        logger.error(f"Get counties error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cities")
async def get_housing_cities():
    """Get all available cities"""
    try:
        housing_db = get_housing_db()
        cities = housing_db.get_cities()
        
        return {
            'success': True,
            'cities': cities
        }
    except Exception as e:
        logger.error(f"Get cities error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resource/{resource_id}")
async def get_housing_resource_detail(resource_id: str):
    """Get detailed housing resource information"""
    try:
        housing_db = get_housing_db()
        resource = housing_db.get_housing_resource(resource_id)
        
        if not resource:
            raise HTTPException(status_code=404, detail="Housing resource not found")
            
        return {
            'success': True,
            'resource': resource
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get housing resource detail error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/application")
async def create_housing_application(application_data: HousingApplication):
    """Create a housing application for a client"""
    try:
        housing_db = get_housing_db()
        
        # Verify housing resource exists
        resource = housing_db.get_housing_resource(application_data.housing_resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Housing resource not found")
            
        # Create application record
        application_id = housing_db.create_housing_application(application_data.dict())
        
        return {
            'success': True,
            'message': 'Housing application created successfully',
            'application_id': application_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create housing application error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/applications/{client_id}")
async def get_client_housing_applications(client_id: str):
    """Get housing applications for a client"""
    try:
        housing_db = get_housing_db()
        applications = housing_db.get_client_housing_applications(client_id)
        
        return {
            'success': True,
            'applications': applications,
            'total_count': len(applications)
        }
        
    except Exception as e:
        logger.error(f"Get client housing applications error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/background-friendly")
async def get_background_friendly_housing():
    """Get all background-friendly housing options"""
    try:
        housing_db = get_housing_db()
        results = housing_db.search_housing_resources({'background_friendly': True})
        
        return {
            'success': True,
            'results': results,
            'total_count': len(results),
            'message': f'Found {len(results)} background-friendly housing options'
        }
        
    except Exception as e:
        logger.error(f"Get background-friendly housing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/emergency")
async def get_emergency_housing():
    """Get emergency housing options"""
    try:
        housing_db = get_housing_db()
        results = housing_db.search_housing_resources({
            'program_type': 'Emergency Shelter',
            'background_friendly': True
        })
        
        return {
            'success': True,
            'results': results,
            'total_count': len(results),
            'message': f'Found {len(results)} emergency housing options'
        }
        
    except Exception as e:
        logger.error(f"Get emergency housing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_housing_statistics():
    """Get housing resource statistics"""
    try:
        housing_db = get_housing_db()
        stats = housing_db.get_housing_statistics()
        
        return {
            'success': True,
            'statistics': stats
        }
        
    except Exception as e:
        logger.error(f"Get housing statistics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def housing_search(
    county: Optional[str] = Query(None),
    city: Optional[str] = Query(None), 
    background_friendly: Optional[bool] = Query(True),
    program_type: Optional[str] = Query(None),
    max_cost: Optional[float] = Query(None),
    max_results: int = Query(50)
):
    """Simple, working housing search using direct API calls"""
    try:
        # Build location and query
        location = f"{city or ''} {county or 'Los Angeles'}, CA".strip()
        
        query_parts = []
        if program_type:
            query_parts.append(program_type)
        query_parts.extend(["housing", "shelter", "transitional"])
        if background_friendly:
            query_parts.append("background friendly")
        
        search_query = " ".join(query_parts)
        
        logger.info(f"Simple Housing Search: '{search_query}' in '{location}'")
        
        # Use simple search system
        coordinator = get_coordinator()
        result = coordinator.search(search_query, SearchType.HOUSING, location)
        
        logger.info(f"Simple housing search: {result.get('total_count')} results")
        
        # Add filter info to result
        result['search_sources'] = [result.get('source', 'simple_search')]
        result['filters_applied'] = {
            'county': county,
            'city': city,
            'background_friendly': background_friendly,
            'program_type': program_type,
            'max_cost': max_cost
        }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Housing search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
