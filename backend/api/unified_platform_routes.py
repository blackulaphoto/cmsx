#!/usr/bin/env python3
"""
Phase 4B: Unified Platform Database API Routes
API endpoints for comprehensive client summaries, search, filtering, and AI insights
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
    from phase_4b_unified_platform_database import UnifiedPlatformDatabase, ClientRiskLevel, ServicePriority
    from phase_4b_enhanced_ai_assistant import EnhancedAIAssistant
    UNIFIED_PLATFORM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Unified platform not available: {e}")
    UNIFIED_PLATFORM_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api", tags=["unified-platform"])

# Initialize unified platform components
if UNIFIED_PLATFORM_AVAILABLE:
    unified_db = UnifiedPlatformDatabase()
    ai_assistant = EnhancedAIAssistant()
else:
    unified_db = None
    ai_assistant = None

# Pydantic models for API responses
class ClientSummaryResponse(BaseModel):
    client_id: str
    full_name: str
    primary_phone: Optional[str]
    primary_email: Optional[str]
    case_manager: Optional[str]
    enrollment_date: Optional[str]
    last_contact: Optional[str]
    active_services: int
    completed_services: int
    risk_level: str
    priority_score: float
    housing_status: Optional[str]
    employment_status: Optional[str]
    benefits_status: Optional[str]
    legal_issues_count: int
    upcoming_appointments: int
    overdue_tasks: int
    ai_insights: Dict[str, Any]
    last_updated: str

class SearchFilters(BaseModel):
    risk_level: Optional[str] = None
    housing_status: Optional[str] = None
    employment_status: Optional[str] = None
    benefits_status: Optional[str] = None
    min_priority_score: Optional[float] = None
    max_priority_score: Optional[float] = None
    case_manager: Optional[str] = None
    has_overdue_tasks: Optional[bool] = None

class SearchResponse(BaseModel):
    results: List[ClientSummaryResponse]
    total_results: int
    search_query: Optional[str]
    filters_applied: Dict[str, Any]
    search_time_ms: float

class AIInsightResponse(BaseModel):
    insight_type: str
    title: str
    content: str
    confidence: float
    priority: str
    affected_modules: List[str]
    recommendations: List[str]
    data_sources: List[str]
    generated_at: str

class ComprehensiveClientViewResponse(BaseModel):
    client_id: str
    client_summary: ClientSummaryResponse
    cross_module_insights: List[Dict[str, Any]]
    ai_insights: Dict[str, Any]
    analytics: Dict[str, Any]
    last_updated: str
    view_generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class PlatformAnalyticsResponse(BaseModel):
    total_clients: int
    risk_distribution: Dict[str, int]
    service_statistics: Dict[str, float]
    engagement_metrics: Dict[str, float]
    insight_summary: Dict[str, int]
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class AIInsightRequest(BaseModel):
    insight_types: Optional[List[str]] = None
    include_predictions: bool = True
    include_recommendations: bool = True

@router.get("/clients/summaries", response_model=List[ClientSummaryResponse])
async def get_all_client_summaries(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    sort_by: str = Query("priority_score", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """
    Get all client summaries with pagination and sorting
    """
    
    if not UNIFIED_PLATFORM_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Unified platform service is not available"
        )
    
    try:
        # Get all clients with basic filtering
        all_clients = unified_db.search_clients("", {})
        
        # Apply sorting
        reverse_sort = sort_order == "desc"
        if sort_by in ['priority_score', 'active_services', 'completed_services', 'legal_issues_count']:
            all_clients.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse_sort)
        elif sort_by in ['full_name', 'risk_level', 'housing_status', 'employment_status']:
            all_clients.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse_sort)
        else:
            all_clients.sort(key=lambda x: x.get('last_updated', ''), reverse=reverse_sort)
        
        # Apply pagination
        paginated_clients = all_clients[offset:offset + limit]
        
        # Convert to response format
        summaries = []
        for client in paginated_clients:
            ai_insights = client.get('ai_insights', '{}')
            if isinstance(ai_insights, str):
                import json
                try:
                    ai_insights = json.loads(ai_insights)
                except:
                    ai_insights = {}
            
            summary = ClientSummaryResponse(
                client_id=client['client_id'],
                full_name=client.get('full_name', ''),
                primary_phone=client.get('primary_phone'),
                primary_email=client.get('primary_email'),
                case_manager=client.get('case_manager'),
                enrollment_date=client.get('enrollment_date'),
                last_contact=client.get('last_contact'),
                active_services=client.get('active_services', 0),
                completed_services=client.get('completed_services', 0),
                risk_level=client.get('risk_level', 'medium'),
                priority_score=client.get('priority_score', 0.5),
                housing_status=client.get('housing_status'),
                employment_status=client.get('employment_status'),
                benefits_status=client.get('benefits_status'),
                legal_issues_count=client.get('legal_issues_count', 0),
                upcoming_appointments=client.get('upcoming_appointments', 0),
                overdue_tasks=client.get('overdue_tasks', 0),
                ai_insights=ai_insights,
                last_updated=client.get('last_updated', '')
            )
            summaries.append(summary)
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error getting client summaries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/clients/search", response_model=SearchResponse)
async def search_clients(
    query: str = Query("", description="Search query text"),
    filters: SearchFilters = None,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    Advanced client search with filtering capabilities
    """
    
    if not UNIFIED_PLATFORM_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Unified platform service is not available"
        )
    
    try:
        import time
        start_time = time.time()
        
        # Build filter dictionary
        filter_dict = {}
        if filters:
            if filters.risk_level:
                filter_dict['risk_level'] = filters.risk_level
            if filters.housing_status:
                filter_dict['housing_status'] = filters.housing_status
            if filters.employment_status:
                filter_dict['employment_status'] = filters.employment_status
            if filters.benefits_status:
                filter_dict['benefits_status'] = filters.benefits_status
            if filters.min_priority_score is not None:
                filter_dict['min_priority_score'] = filters.min_priority_score
            if filters.case_manager:
                filter_dict['case_manager'] = filters.case_manager
        
        # Perform search
        results = unified_db.search_clients(query, filter_dict)
        
        # Apply additional filters
        if filters and filters.has_overdue_tasks is not None:
            if filters.has_overdue_tasks:
                results = [r for r in results if r.get('overdue_tasks', 0) > 0]
            else:
                results = [r for r in results if r.get('overdue_tasks', 0) == 0]
        
        if filters and filters.max_priority_score is not None:
            results = [r for r in results if r.get('priority_score', 0) <= filters.max_priority_score]
        
        # Apply pagination
        total_results = len(results)
        paginated_results = results[offset:offset + limit]
        
        # Convert to response format
        client_summaries = []
        for client in paginated_results:
            ai_insights = client.get('ai_insights', '{}')
            if isinstance(ai_insights, str):
                import json
                try:
                    ai_insights = json.loads(ai_insights)
                except:
                    ai_insights = {}
            
            summary = ClientSummaryResponse(
                client_id=client['client_id'],
                full_name=client.get('full_name', ''),
                primary_phone=client.get('primary_phone'),
                primary_email=client.get('primary_email'),
                case_manager=client.get('case_manager'),
                enrollment_date=client.get('enrollment_date'),
                last_contact=client.get('last_contact'),
                active_services=client.get('active_services', 0),
                completed_services=client.get('completed_services', 0),
                risk_level=client.get('risk_level', 'medium'),
                priority_score=client.get('priority_score', 0.5),
                housing_status=client.get('housing_status'),
                employment_status=client.get('employment_status'),
                benefits_status=client.get('benefits_status'),
                legal_issues_count=client.get('legal_issues_count', 0),
                upcoming_appointments=client.get('upcoming_appointments', 0),
                overdue_tasks=client.get('overdue_tasks', 0),
                ai_insights=ai_insights,
                last_updated=client.get('last_updated', '')
            )
            client_summaries.append(summary)
        
        search_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=client_summaries,
            total_results=total_results,
            search_query=query if query else None,
            filters_applied=filter_dict,
            search_time_ms=round(search_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Error searching clients: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/clients/{client_id}/comprehensive-view", response_model=ComprehensiveClientViewResponse)
async def get_comprehensive_client_view(
    client_id: str = Path(..., description="Client ID"),
    include_ai_insights: bool = Query(True, description="Include AI insights"),
    include_analytics: bool = Query(True, description="Include analytics data")
):
    """
    Get comprehensive client view with all unified data and AI insights
    """
    
    if not UNIFIED_PLATFORM_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Unified platform service is not available"
        )
    
    try:
        # Get comprehensive view from unified database
        comprehensive_view = unified_db.get_client_comprehensive_view(client_id)
        
        if not comprehensive_view:
            raise HTTPException(
                status_code=404,
                detail=f"Client {client_id} not found"
            )
        
        # Get AI insights if requested
        ai_insights = {}
        if include_ai_insights and ai_assistant:
            ai_insights = ai_assistant.generate_comprehensive_client_insights(client_id)
        
        # Build client summary response
        client_summary_data = comprehensive_view['client_summary']
        ai_insights_data = client_summary_data.get('ai_insights', '{}')
        if isinstance(ai_insights_data, str):
            import json
            try:
                ai_insights_data = json.loads(ai_insights_data)
            except:
                ai_insights_data = {}
        
        client_summary = ClientSummaryResponse(
            client_id=client_summary_data['client_id'],
            full_name=client_summary_data.get('full_name', ''),
            primary_phone=client_summary_data.get('primary_phone'),
            primary_email=client_summary_data.get('primary_email'),
            case_manager=client_summary_data.get('case_manager'),
            enrollment_date=client_summary_data.get('enrollment_date'),
            last_contact=client_summary_data.get('last_contact'),
            active_services=client_summary_data.get('active_services', 0),
            completed_services=client_summary_data.get('completed_services', 0),
            risk_level=client_summary_data.get('risk_level', 'medium'),
            priority_score=client_summary_data.get('priority_score', 0.5),
            housing_status=client_summary_data.get('housing_status'),
            employment_status=client_summary_data.get('employment_status'),
            benefits_status=client_summary_data.get('benefits_status'),
            legal_issues_count=client_summary_data.get('legal_issues_count', 0),
            upcoming_appointments=client_summary_data.get('upcoming_appointments', 0),
            overdue_tasks=client_summary_data.get('overdue_tasks', 0),
            ai_insights=ai_insights_data,
            last_updated=client_summary_data.get('last_updated', '')
        )
        
        # Build comprehensive response
        response = ComprehensiveClientViewResponse(
            client_id=client_id,
            client_summary=client_summary,
            cross_module_insights=comprehensive_view.get('cross_module_insights', []),
            ai_insights=ai_insights if include_ai_insights else {},
            analytics=comprehensive_view.get('analytics', {}) if include_analytics else {},
            last_updated=comprehensive_view.get('last_updated', '')
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting comprehensive client view: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/clients/{client_id}/ai-insights", response_model=Dict[str, Any])
async def generate_ai_insights(
    client_id: str = Path(..., description="Client ID"),
    request: AIInsightRequest = None
):
    """
    Generate AI insights for specific client
    """
    
    if not UNIFIED_PLATFORM_AVAILABLE or not ai_assistant:
        raise HTTPException(
            status_code=503,
            detail="AI Assistant service is not available"
        )
    
    try:
        # Generate comprehensive insights
        insights = ai_assistant.generate_comprehensive_client_insights(client_id)
        
        if 'error' in insights:
            raise HTTPException(
                status_code=404,
                detail=insights['error']
            )
        
        # Filter insights if specific types requested
        if request and request.insight_types:
            filtered_insights = {}
            for insight_type in request.insight_types:
                if insight_type in insights:
                    filtered_insights[insight_type] = insights[insight_type]
            insights = filtered_insights
        
        # Remove predictions if not requested
        if request and not request.include_predictions:
            insights.pop('predictive_analysis', None)
            insights.pop('outcome_predictions', None)
        
        # Remove recommendations if not requested
        if request and not request.include_recommendations:
            for insight_key, insight_value in insights.items():
                if hasattr(insight_value, 'recommendations'):
                    insight_value.recommendations = []
        
        return {
            'client_id': client_id,
            'insights': insights,
            'generated_at': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating AI insights: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/clients/{client_id}/ai-dashboard", response_model=Dict[str, Any])
async def get_ai_dashboard(
    client_id: str = Path(..., description="Client ID")
):
    """
    Get comprehensive AI dashboard for client
    """
    
    if not UNIFIED_PLATFORM_AVAILABLE or not ai_assistant:
        raise HTTPException(
            status_code=503,
            detail="AI Assistant service is not available"
        )
    
    try:
        dashboard = ai_assistant.get_client_ai_dashboard(client_id)
        
        if not dashboard:
            raise HTTPException(
                status_code=404,
                detail=f"Client {client_id} not found or no dashboard data available"
            )
        
        return dashboard
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/analytics/platform", response_model=PlatformAnalyticsResponse)
async def get_platform_analytics():
    """
    Get platform-wide analytics and insights
    """
    
    if not UNIFIED_PLATFORM_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Unified platform service is not available"
        )
    
    try:
        analytics = unified_db.get_platform_analytics()
        
        return PlatformAnalyticsResponse(
            total_clients=analytics.get('total_clients', 0),
            risk_distribution=analytics.get('risk_distribution', {}),
            service_statistics=analytics.get('service_statistics', {}),
            engagement_metrics=analytics.get('engagement_metrics', {}),
            insight_summary=analytics.get('insight_summary', {})
        )
        
    except Exception as e:
        logger.error(f"Error getting platform analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/system/refresh-materialized-views")
async def refresh_materialized_views():
    """
    Refresh materialized views for performance optimization
    """
    
    if not UNIFIED_PLATFORM_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Unified platform service is not available"
        )
    
    try:
        import time
        start_time = time.time()
        
        success = unified_db.refresh_materialized_views()
        refresh_time = (time.time() - start_time) * 1000
        
        if success:
            return {
                'status': 'success',
                'message': 'Materialized views refreshed successfully',
                'refresh_time_ms': round(refresh_time, 2),
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to refresh materialized views"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing materialized views: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/system/populate-summaries")
async def populate_client_summaries():
    """
    Populate or refresh client summaries from all modules
    """
    
    if not UNIFIED_PLATFORM_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Unified platform service is not available"
        )
    
    try:
        import time
        start_time = time.time()
        
        populated_count = unified_db.populate_client_summaries()
        population_time = (time.time() - start_time) * 1000
        
        return {
            'status': 'success',
            'message': f'Client summaries populated successfully',
            'clients_processed': populated_count,
            'population_time_ms': round(population_time, 2),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error populating client summaries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/system/unified-platform/status")
async def get_unified_platform_status():
    """
    Get unified platform system status
    """
    
    if not UNIFIED_PLATFORM_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={
                'status': 'unavailable',
                'message': 'Unified platform is not available',
                'timestamp': datetime.now().isoformat()
            }
        )
    
    try:
        # Get platform analytics for status
        analytics = unified_db.get_platform_analytics()
        
        # Test AI assistant
        ai_status = 'operational' if ai_assistant else 'unavailable'
        
        return {
            'status': 'operational',
            'version': '4B.1.0',
            'components': {
                'unified_database': 'operational',
                'ai_assistant': ai_status,
                'materialized_views': 'active',
                'search_engine': 'active'
            },
            'statistics': {
                'total_clients': analytics.get('total_clients', 0),
                'total_insights': sum(analytics.get('insight_summary', {}).values()),
                'risk_distribution': analytics.get('risk_distribution', {})
            },
            'features': [
                'Comprehensive client summaries',
                'Advanced search and filtering',
                'Cross-module AI insights',
                'Predictive analytics',
                'Materialized views for performance',
                'Real-time platform analytics'
            ],
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting platform status: {e}")
        return JSONResponse(
            status_code=503,
            content={
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        )

# Health check endpoint
@router.get("/health/unified-platform")
async def unified_platform_health_check():
    """
    Health check for unified platform system
    """
    
    if not UNIFIED_PLATFORM_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={
                'status': 'unhealthy',
                'message': 'Unified platform is not available',
                'timestamp': datetime.now().isoformat()
            }
        )
    
    try:
        # Test database connectivity
        analytics = unified_db.get_platform_analytics()
        
        # Test AI assistant
        ai_healthy = ai_assistant is not None
        
        if analytics and ai_healthy:
            return {
                'status': 'healthy',
                'components': {
                    'database': 'healthy',
                    'ai_assistant': 'healthy',
                    'search': 'healthy'
                },
                'clients_available': analytics.get('total_clients', 0),
                'timestamp': datetime.now().isoformat()
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    'status': 'degraded',
                    'message': 'Some components not fully operational',
                    'timestamp': datetime.now().isoformat()
                }
            )
            
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