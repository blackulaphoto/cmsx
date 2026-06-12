#!/usr/bin/env python3
"""
Services Routes - Integrated with Virgil St database, fallback to external APIs
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import re
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

        # STEP 1: Resource Library — fetch ALL matching records (no page guard).
        # RL records always sort before Virgil; pagination is applied to the
        # combined list AFTER source-priority ordering.
        rl_providers = []
        try:
            from backend.modules.resource_library.database import search_resources as rl_search
            rl_cat = _RL_CATEGORY_MAP.get(category or '') if (category and category != 'all') else None
            generic_terms = {'services', 'social services', 'service'}
            rl_text = search_query if search_query and search_query.lower() not in generic_terms else None
            # When a direct RL category mapping exists, let the category filter drive matching.
            # Adding a hyphenated category name as text (e.g. "youth foster") fails against
            # RL tags that use underscores (e.g. "foster_youth"), producing 0 results.
            if not rl_text and not rl_cat and category and category not in ('all', ''):
                rl_text = category.replace('-', ' ')
            rl_result = rl_search(
                search=rl_text,
                category=rl_cat,
                active=True,
                page=1,
                per_page=200,  # pull all RL matches at once; dataset is small
            )
            if rl_result["success"] and rl_result["total_count"] > 0:
                logger.info(f"Resource Library found {rl_result['total_count']} resources")
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

        # STEP 2: Virgil St database — fetch ALL results at once so we can
        # deduplicate against RL before applying pagination.
        # Virgil already loads everything into memory regardless of per_page, so
        # requesting per_page=500 has the same DB cost as per_page=10.
        virgil_all: list = []
        virgil_had_results = False
        try:
            virgil_db = get_virgil_db()
            db_result = virgil_db.search_services(
                search_query,
                location_param,
                1,       # always page 1 — we paginate the combined list ourselves
                500,     # pull all Virgil results at once
                category=category,
                population=population,
                insurance_type=insurance_type,
            )

            if db_result['success'] and db_result['total_count'] > 0:
                virgil_had_results = True
                logger.info(f"Virgil St DB found {db_result['total_count']} services")
                for rec in db_result['results']:
                    if rec.get('source') in (None, '', 'virgil_st_resources', 'virgil_st_db'):
                        rec['source'] = 'Virgil St Resources'
                virgil_all = db_result['results']
            elif rl_providers:
                logger.info("Virgil St DB returned no results; using Resource Library results only")
            else:
                logger.info("Virgil St DB returned no results, falling back to external APIs")
        except Exception as db_error:
            logger.warning(f"Virgil St DB search failed, falling back to external APIs: {db_error}")

        # STEP 2b: Deduplicate — suppress Virgil records whose title matches an
        # RL record (exact or prefix match after stripping non-alphanumeric chars).
        if rl_providers and virgil_all:
            def _norm(s: str) -> str:
                return re.sub(r'[^a-z0-9]', '', (s or '').lower())

            rl_norms = [_norm(p.get("title", "") or p.get("provider_name", "")) for p in rl_providers]

            filtered_virgil = []
            for rec in virgil_all:
                v_norm = _norm(rec.get("title", "") or rec.get("provider_name", ""))
                duplicate = False
                for rn in rl_norms:
                    if not rn or not v_norm:
                        continue
                    # Exact match
                    if v_norm == rn:
                        duplicate = True
                        break
                    # Prefix overlap: RL title is a prefix of Virgil title or vice versa
                    # (min length 15 avoids false positives on short tokens)
                    min_len = min(len(v_norm), len(rn))
                    if min_len >= 15 and (v_norm.startswith(rn) or rn.startswith(v_norm)):
                        duplicate = True
                        break
                if not duplicate:
                    filtered_virgil.append(rec)

            logger.info(
                f"Dedup: kept {len(filtered_virgil)}/{len(virgil_all)} Virgil records "
                f"(suppressed {len(virgil_all) - len(filtered_virgil)} duplicates)"
            )
        else:
            filtered_virgil = virgil_all

        # STEP 2c: Combine with source-priority order, then paginate.
        if rl_providers or filtered_virgil:
            combined = rl_providers + filtered_virgil
            combined_total = len(combined)
            combined_pages = max(1, (combined_total + per_page - 1) // per_page)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_slice = combined[start_idx:end_idx]

            source_label = (
                'Internal Resource Library + Virgil St Resources'
                if (rl_providers and filtered_virgil)
                else ('Internal Resource Library' if rl_providers else 'Virgil St Resources')
            )
            return {
                'success': True,
                'service_providers': page_slice,
                'total_count': combined_total,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_results': combined_total,
                    'total_pages': combined_pages,
                    'has_next_page': page < combined_pages,
                    'has_prev_page': page > 1,
                    'start_index': start_idx + 1 if combined_total > 0 else 0,
                    'end_index': min(end_idx, combined_total),
                },
                'source': 'resource_library' if rl_providers else 'virgil_st_db',
                'source_label': source_label,
                'degraded': False,
                'warning': None,
                'timestamp': datetime.now().isoformat(),
            }

        # STEP 3: External API fallback — only for broad / no-category searches.
        # For specific category searches Virgil + RL is the definitive answer.
        # The coordinator internally calls Virgil without a category filter and
        # returns every record (show-all mode), which pollutes category results.
        if category and category not in ('all', '', None):
            return {
                "success": True,
                "service_providers": [],
                "total_count": 0,
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": 0,
                    "total_pages": 1,
                    "has_next_page": False,
                    "has_prev_page": False,
                    "start_index": 0,
                    "end_index": 0,
                },
                "source": "none",
                "source_label": "No results found",
                "degraded": False,
                "warning": f"No resources found for category '{category}'",
                "timestamp": datetime.now().isoformat(),
            }

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
