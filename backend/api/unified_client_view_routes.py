#!/usr/bin/env python3
"""
Phase 4A: Unified Client View API Routes
Enhanced GET /api/clients/{client_id}/unified-view with comprehensive features
"""

from fastapi import APIRouter, HTTPException, Path, Query, Depends
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import sys
from pathlib import Path as PathLib
import logging

# Add shared directory to path
sys.path.append(str(PathLib(__file__).parent.parent / 'shared'))

try:
    from phase_4a_unified_client_view import (
        UnifiedClientViewEngine, 
        UnifiedClientView, 
        ModuleData, 
        NavigationContext,
        DataFreshness,
        ModuleStatus
    )
    UNIFIED_VIEW_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Unified client view engine not available: {e}")
    UNIFIED_VIEW_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api", tags=["unified-client-view"])

# Initialize unified view engine
if UNIFIED_VIEW_AVAILABLE:
    unified_view_engine = UnifiedClientViewEngine()
else:
    unified_view_engine = None

# Pydantic models for API responses
class ModuleDataResponse(BaseModel):
    module_name: str
    display_name: str
    icon: str
    data: Dict[str, Any]
    last_updated: str
    freshness: str
    status: str
    record_count: int
    error_message: Optional[str] = None
    navigation_url: str
    description: str

class NavigationContextResponse(BaseModel):
    client_id: str
    current_module: str
    previous_module: Optional[str]
    breadcrumbs: List[Dict[str, Any]]
    session_id: str
    timestamp: str

class CacheInfoResponse(BaseModel):
    cached: bool
    cache_key: str
    ttl_seconds: int
    generation_time_ms: int
    cache_hit: bool = False

class UnifiedClientViewResponse(BaseModel):
    client_id: str
    core_profile: Dict[str, Any]
    modules: Dict[str, ModuleDataResponse]
    navigation_context: NavigationContextResponse
    cache_info: CacheInfoResponse
    data_freshness_summary: Dict[str, int]
    last_aggregated: str
    total_records: int
    api_version: str = "4A.1.0"
    response_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class NavigationRequest(BaseModel):
    target_module: str
    session_id: Optional[str] = None
    previous_module: Optional[str] = None

class ModuleListResponse(BaseModel):
    modules: List[Dict[str, Any]]
    total_modules: int
    active_modules: int

@router.get("/clients/{client_id}/unified-view", response_model=UnifiedClientViewResponse)
async def get_unified_client_view(
    client_id: str = Path(..., description="Client ID to retrieve unified view for"),
    session_id: Optional[str] = Query(None, description="Navigation session ID"),
    current_module: str = Query("core_clients", description="Current module context"),
    include_cache_info: bool = Query(True, description="Include cache performance info"),
    force_refresh: bool = Query(False, description="Force refresh from database")
):
    """
    Enhanced GET /api/clients/{client_id}/unified-view
    
    Aggregates data from all 10 modules with:
    - Performance caching
    - Real-time data freshness indicators
    - Cross-module navigation context
    - Comprehensive error handling
    """
    
    if not UNIFIED_VIEW_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Unified client view service is not available"
        )
    
    try:
        # Force cache refresh if requested
        if force_refresh:
            cache_key = unified_view_engine._generate_cache_key(client_id)
            if cache_key in unified_view_engine.cache_storage:
                del unified_view_engine.cache_storage[cache_key]
        
        # Get unified view
        unified_view = unified_view_engine.get_unified_client_view(
            client_id=client_id,
            session_id=session_id,
            current_module=current_module
        )
        
        if not unified_view:
            raise HTTPException(
                status_code=404,
                detail=f"Client {client_id} not found or unable to aggregate data"
            )
        
        # Convert to API response format
        modules_response = {}
        for module_name, module_data in unified_view.modules.items():
            module_config = unified_view_engine.modules.get(module_name, {})
            
            modules_response[module_name] = ModuleDataResponse(
                module_name=module_name,
                display_name=module_config.get('display_name', module_name),
                icon=module_config.get('icon', '📄'),
                data=module_data.data,
                last_updated=module_data.last_updated,
                freshness=module_data.freshness.value,
                status=module_data.status.value,
                record_count=module_data.record_count,
                error_message=module_data.error_message,
                navigation_url=module_config.get('navigation_url', '').format(client_id=client_id),
                description=module_config.get('description', '')
            )
        
        # Build response
        response = UnifiedClientViewResponse(
            client_id=unified_view.client_id,
            core_profile=unified_view.core_profile,
            modules=modules_response,
            navigation_context=NavigationContextResponse(
                client_id=unified_view.navigation_context.client_id,
                current_module=unified_view.navigation_context.current_module,
                previous_module=unified_view.navigation_context.previous_module,
                breadcrumbs=unified_view.navigation_context.breadcrumbs,
                session_id=unified_view.navigation_context.session_id,
                timestamp=unified_view.navigation_context.timestamp
            ),
            cache_info=CacheInfoResponse(
                cached=unified_view.cache_info.get('cached', False),
                cache_key=unified_view.cache_info.get('cache_key', ''),
                ttl_seconds=unified_view.cache_info.get('ttl_seconds', 0),
                generation_time_ms=unified_view.cache_info.get('generation_time_ms', 0),
                cache_hit=unified_view.cache_info.get('cache_hit', False)
            ),
            data_freshness_summary=unified_view.data_freshness_summary,
            last_aggregated=unified_view.last_aggregated,
            total_records=unified_view.total_records
        )
        
        logger.info(f"Unified view generated for client {client_id} with {len(unified_view.modules)} modules")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating unified client view: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while generating unified view: {str(e)}"
        )

@router.post("/clients/{client_id}/navigate")
async def navigate_to_module(
    client_id: str = Path(..., description="Client ID for navigation"),
    navigation_request: NavigationRequest = None
):
    """
    Navigate to a specific module while maintaining client context
    """
    
    if not UNIFIED_VIEW_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Navigation service is not available"
        )
    
    try:
        navigation_context = unified_view_engine.navigate_to_module(
            client_id=client_id,
            target_module=navigation_request.target_module,
            session_id=navigation_request.session_id or unified_view_engine._generate_session_id(),
            previous_module=navigation_request.previous_module
        )
        
        if not navigation_context:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to navigate to module {navigation_request.target_module}"
            )
        
        return NavigationContextResponse(
            client_id=navigation_context.client_id,
            current_module=navigation_context.current_module,
            previous_module=navigation_context.previous_module,
            breadcrumbs=navigation_context.breadcrumbs,
            session_id=navigation_context.session_id,
            timestamp=navigation_context.timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error navigating to module: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during navigation: {str(e)}"
        )

@router.get("/clients/{client_id}/modules", response_model=ModuleListResponse)
async def get_available_modules(
    client_id: str = Path(..., description="Client ID to check module availability for")
):
    """
    Get list of available modules for client with status information
    """
    
    if not UNIFIED_VIEW_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Module listing service is not available"
        )
    
    try:
        modules_list = []
        active_count = 0
        
        for module_name, module_config in unified_view_engine.modules.items():
            # Check if client has data in this module
            module_data = unified_view_engine._get_module_data(client_id, module_name, module_config)
            
            is_active = module_data.status == ModuleStatus.ACTIVE
            if is_active:
                active_count += 1
            
            modules_list.append({
                'module_name': module_name,
                'display_name': module_config.get('display_name', module_name),
                'icon': module_config.get('icon', '📄'),
                'priority': module_config.get('priority', 999),
                'status': module_data.status.value,
                'record_count': module_data.record_count,
                'last_updated': module_data.last_updated,
                'freshness': module_data.freshness.value,
                'navigation_url': module_config.get('navigation_url', '').format(client_id=client_id),
                'description': module_config.get('description', ''),
                'is_master': module_config.get('is_master', False)
            })
        
        # Sort by priority
        modules_list.sort(key=lambda x: x['priority'])
        
        return ModuleListResponse(
            modules=modules_list,
            total_modules=len(modules_list),
            active_modules=active_count
        )
        
    except Exception as e:
        logger.error(f"Error getting module list: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while getting module list: {str(e)}"
        )

@router.get("/clients/{client_id}/freshness-summary")
async def get_data_freshness_summary(
    client_id: str = Path(..., description="Client ID to check data freshness for")
):
    """
    Get detailed data freshness summary for client across all modules
    """
    
    if not UNIFIED_VIEW_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Data freshness service is not available"
        )
    
    try:
        unified_view = unified_view_engine.get_unified_client_view(client_id)
        
        if not unified_view:
            raise HTTPException(
                status_code=404,
                detail=f"Client {client_id} not found"
            )
        
        # Detailed freshness breakdown
        freshness_details = {}
        for module_name, module_data in unified_view.modules.items():
            module_config = unified_view_engine.modules.get(module_name, {})
            
            freshness_details[module_name] = {
                'display_name': module_config.get('display_name', module_name),
                'freshness': module_data.freshness.value,
                'last_updated': module_data.last_updated,
                'status': module_data.status.value,
                'icon': module_config.get('icon', '📄')
            }
        
        return {
            'client_id': client_id,
            'summary': unified_view.data_freshness_summary,
            'details': freshness_details,
            'last_checked': unified_view.last_aggregated,
            'total_modules': len(unified_view.modules)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting freshness summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while getting freshness summary: {str(e)}"
        )

@router.get("/system/unified-view/status")
async def get_unified_view_system_status():
    """
    Get unified view system status and performance metrics
    """
    
    if not UNIFIED_VIEW_AVAILABLE:
        return {
            'status': 'unavailable',
            'message': 'Unified view engine is not available',
            'timestamp': datetime.now().isoformat()
        }
    
    try:
        # Get cache statistics
        cache_stats = {
            'total_cached_items': len(unified_view_engine.cache_storage),
            'cache_ttl_seconds': unified_view_engine.cache_ttl,
            'memory_cache_active': True
        }
        
        # Get module configuration
        module_stats = {
            'total_modules': len(unified_view_engine.modules),
            'configured_modules': list(unified_view_engine.modules.keys())
        }
        
        return {
            'status': 'operational',
            'version': '4A.1.0',
            'cache_stats': cache_stats,
            'module_stats': module_stats,
            'features': [
                'Enhanced unified view API',
                'Performance caching',
                'Real-time data freshness indicators',
                'Cross-module navigation',
                'Breadcrumb navigation',
                'Session management'
            ],
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@router.delete("/clients/{client_id}/cache")
async def clear_client_cache(
    client_id: str = Path(..., description="Client ID to clear cache for")
):
    """
    Clear cached data for specific client
    """
    
    if not UNIFIED_VIEW_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Cache management service is not available"
        )
    
    try:
        cache_key = unified_view_engine._generate_cache_key(client_id)
        
        # Clear memory cache
        cache_cleared = False
        if cache_key in unified_view_engine.cache_storage:
            del unified_view_engine.cache_storage[cache_key]
            cache_cleared = True
        
        if cache_key in unified_view_engine.cache_timestamps:
            del unified_view_engine.cache_timestamps[cache_key]
        
        return {
            'client_id': client_id,
            'cache_cleared': cache_cleared,
            'cache_key': cache_key,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing client cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while clearing cache: {str(e)}"
        )

# Health check endpoint
@router.get("/health/unified-view")
async def unified_view_health_check():
    """
    Health check for unified view system
    """
    
    if not UNIFIED_VIEW_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={
                'status': 'unhealthy',
                'message': 'Unified view engine is not available',
                'timestamp': datetime.now().isoformat()
            }
        )
    
    try:
        # Test basic functionality
        test_client_id = unified_view_engine.get_test_client_id()
        
        if test_client_id:
            # Test unified view generation
            unified_view = unified_view_engine.get_unified_client_view(test_client_id)
            
            if unified_view:
                return {
                    'status': 'healthy',
                    'test_client_id': test_client_id[:8] + '...',
                    'modules_available': len(unified_view.modules),
                    'cache_operational': True,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return JSONResponse(
                    status_code=503,
                    content={
                        'status': 'unhealthy',
                        'message': 'Unable to generate unified view',
                        'timestamp': datetime.now().isoformat()
                    }
                )
        else:
            return {
                'status': 'healthy',
                'message': 'System operational but no test data available',
                'modules_configured': len(unified_view_engine.modules),
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        )