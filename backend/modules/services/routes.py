#!/usr/bin/env python3
"""
Services Routes - Integrated with Virgil St database, fallback to external APIs
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# Import the guide-compliant search system
from backend.search.coordinator import get_coordinator, SearchType
# Import Virgil St database service
from backend.modules.services.virgil_db_service import get_virgil_db

logger = logging.getLogger(__name__)

# Map frontend category IDs → Resource Library primary_category values
_RL_CATEGORY_MAP = {
    'housing': 'housing_navigation',
    'benefits': 'benefits',
    'medical': 'medical',
    'dental': 'dental',
    'dental-care': 'dental',
    'mental-health': 'mental_health',
    'sud-recovery': 'sud_recovery',
    'substance-abuse': 'sud_recovery',
    'legal-aid': 'legal_aid',
    'food': 'food_support',
    'transportation': 'transportation',
    'employment': 'employment_support',
    'documents-id': 'documents_id',
    'crisis': 'crisis',
    'veterans': 'veteran_assistance',
    'disability-ihss': 'disability_housing',
    'family-parenting': 'family_shelter',
    'youth-foster': 'youth_housing',
    'reentry': 'reentry_housing',
    'domestic-violence': 'victim_services',
}

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
        "message": "Services API Ready - Integrated Virgil St Database + External APIs",
        "version": "3.0",
        "search_system": "virgil_st_db_with_fallback",
        "status": "operational",
        "database_records": "~4200 local services (resources, treatment centers, providers, meetings)"
    }

@router.get("/search")
@router.post("/search")
async def api_services_search(
    search_data: Optional[ServiceSearch] = Body(None),
    search: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    service_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    population: Optional[str] = Query(None),
    insurance_type: Optional[str] = Query(None),
    page: int = Query(1, description="Page number (starts from 1)", ge=1),
    per_page: int = Query(10, description="Results per page (max 30)", ge=1, le=30)
):
    """Services search using Virgil St database first, fallback to external APIs"""
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

        # STEP 1: Resource Library — curated internal records, always shown first on page 1
        rl_providers = []
        rl_total = 0
        if page == 1:
            try:
                from backend.modules.resource_library.database import search_resources as rl_search
                # Map frontend category ID to RL primary_category value
                rl_cat = _RL_CATEGORY_MAP.get(category or '') if (category and category != 'all') else None
                # Use user text if meaningful; fall back to category keyword so "Housing" tile still matches
                generic_terms = {'services', 'social services', 'service'}
                rl_text = search_query if search_query and search_query.lower() not in generic_terms else None
                if not rl_text and category and category not in ('all', ''):
                    rl_text = category.replace('-', ' ')
                rl_result = rl_search(
                    search=rl_text,
                    category=rl_cat,
                    active=True,
                    page=1,
                    per_page=50,  # small dataset — pull all matches at once
                )
                if rl_result["success"] and rl_result["total_count"] > 0:
                    logger.info(f"Resource Library found {rl_result['total_count']} resources")
                    rl_total = rl_result["total_count"]
                    for r in rl_result["results"]:
                        loc = r.get("locations") or []
                        first_loc = loc[0] if isinstance(loc, list) and loc else {}
                        fl = first_loc if isinstance(first_loc, dict) else {}
                        people = r.get("people_served") or []
                        serves_pop = ", ".join(str(p) for p in people[:3]) if people else ""
                        rl_providers.append({
                            "title": r.get("display_name") or r.get("provider_name"),
                            "provider_name": r.get("provider_name"),
                            "service_name": r.get("service_name"),
                            "description": r.get("description"),
                            "address": fl.get("address", ""),
                            "location": fl.get("city", ""),
                            "city": fl.get("city", ""),
                            "state": fl.get("state", "CA"),
                            "zip": fl.get("zip", ""),
                            "phone": r.get("phone") or fl.get("phone", ""),
                            "email": r.get("email"),
                            "url": r.get("website"),
                            "link": r.get("website"),
                            "service_type": r.get("primary_category", "").replace("_", " ").title(),
                            "serves_population": serves_pop,
                            "tags": r.get("tags", []),
                            "cost": r.get("cost"),
                            "languages": r.get("languages", []),
                            "verification_status": r.get("verification_status"),
                            "resource_library_id": r.get("id"),
                            "source": "Internal Resource Library",
                            "background_friendly_score": 0,
                        })
            except Exception as rl_error:
                logger.warning(f"Resource Library search failed, continuing to Virgil St: {rl_error}")

        # STEP 2: Virgil St database — label results clearly, merge with RL
        try:
            virgil_db = get_virgil_db()
            db_result = virgil_db.search_services(
                search_query,
                location_param,
                page,
                per_page,
                category=category,
                population=population,
                insurance_type=insurance_type,
            )

            if db_result['success'] and db_result['total_count'] > 0:
                logger.info(f"Virgil St DB found {db_result['total_count']} services")
                # Tag each Virgil record with a clear source label
                virgil_results = db_result['results']
                for rec in virgil_results:
                    if rec.get('source') in (None, '', 'virgil_st_resources', 'virgil_st_db'):
                        rec['source'] = 'Virgil St Resources'

                combined = rl_providers + virgil_results
                combined_total = rl_total + db_result['total_count']
                combined_pages = max(1, (combined_total + per_page - 1) // per_page)
                pagination = dict(db_result['pagination'])
                pagination['total_results'] = combined_total
                pagination['total_pages'] = combined_pages
                pagination['has_next_page'] = page < combined_pages

                return {
                    'success': True,
                    'service_providers': combined[:per_page],
                    'total_count': combined_total,
                    'pagination': pagination,
                    'source': 'resource_library' if rl_providers else db_result['source'],
                    'source_label': 'Internal Resource Library + Virgil St Resources' if rl_providers else 'Virgil St Resources',
                    'degraded': False,
                    'warning': None,
                    'timestamp': datetime.now().isoformat()
                }
            elif rl_providers:
                logger.info("Virgil St DB returned no results; returning Resource Library results only")
            else:
                logger.info("Virgil St DB returned no results, falling back to external APIs")
        except Exception as db_error:
            logger.warning(f"Virgil St DB search failed, falling back to external APIs: {db_error}")

        # If only RL results and Virgil failed/empty
        if rl_providers:
            return {
                "success": True,
                "service_providers": rl_providers,
                "total_count": rl_total,
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": rl_total,
                    "total_pages": max(1, (rl_total + per_page - 1) // per_page),
                    "has_next_page": page < max(1, (rl_total + per_page - 1) // per_page),
                    "has_prev_page": page > 1,
                    "start_index": 1,
                    "end_index": len(rl_providers),
                },
                "source": "resource_library",
                "source_label": "Internal Resource Library",
                "degraded": False,
                "warning": None,
                "timestamp": datetime.now().isoformat(),
            }

        # STEP 3: Fallback to external APIs (SerpAPI / Google CSE)
        coordinator = get_coordinator()
        result = await coordinator.search_services(search_query, location_param, page, per_page)

        if result['success']:
            logger.info(f"External API search result: {result['pagination']['total_results']} total providers, page {page}")

            # Format response to match expected structure
            return {
                'success': True,
                'service_providers': result['results'],
                'total_count': result['pagination']['total_results'],
                'pagination': result['pagination'],
                'source': result['source'],
                'source_label': 'External Search Results',
                'degraded': result.get('degraded', False),
                'warning': result.get('warning') or 'No internal database matches found, showing external search results',
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
    category: Optional[str] = Query(None),
    population: Optional[str] = Query(None),
    insurance_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=30)
):
    """Get service providers from Virgil St database first, then external APIs"""
    try:
        search_query = service_type or "social services"

        # Try Virgil St database first
        try:
            virgil_db = get_virgil_db()
            db_result = virgil_db.search_services(
                search_query,
                location,
                page,
                per_page,
                category=category,
                population=population,
                insurance_type=insurance_type,
            )

            if db_result['success'] and db_result['total_count'] > 0:
                return {
                    'success': True,
                    'providers': db_result['results'],
                    'total_count': db_result['total_count'],
                    'pagination': db_result['pagination'],
                    'source': db_result['source'],
                    'degraded': False,
                    'warning': None,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as db_error:
            logger.warning(f"Virgil St DB failed, using external APIs: {db_error}")

        # Fallback to external APIs
        coordinator = get_coordinator()
        result = await coordinator.search_services(search_query, location, page, per_page)

        if result['success']:
            return {
                'success': True,
                'providers': result['results'],
                'total_count': result['pagination']['total_results'],
                'pagination': result['pagination'],
                'source': result['source'],
                'degraded': result.get('degraded', False),
                'warning': result.get('warning'),
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
