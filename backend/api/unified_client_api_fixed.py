#!/usr/bin/env python3
"""
Unified Client API - Provides comprehensive client data across all modules
This API serves the unified client dashboard with data from all databases
FIXED VERSION with proper persistence implementation
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from shared.database.access_layer import DatabaseAccessLayer, DatabaseType
from shared.database.core_client_service import CoreClientService
from .client_data_integration import get_client_data_integrator

logger = logging.getLogger(__name__)

# Import intelligent reminder system
try:
    from modules.reminders.intelligent_processor import IntelligentTaskProcessor
    REMINDERS_AVAILABLE = True
except ImportError:
    logger.warning("Intelligent reminder system not available")
    REMINDERS_AVAILABLE = False

# Import search system (unified implementation from guides/search)
try:
    import sys as _sys
    from pathlib import Path as _Path
    _guides_search_path = _Path(__file__).resolve().parents[2] / "guides" / "search"
    if str(_guides_search_path) not in _sys.path:
        _sys.path.insert(0, str(_guides_search_path))

    # Make sure backend scrapers are importable for adapter initialization
    _scrapers_path = _Path(__file__).resolve().parents[1] / "modules" / "scrapers"
    if str(_scrapers_path) not in _sys.path:
        _sys.path.insert(0, str(_scrapers_path))

    from unified_search_system import get_coordinator, SearchType
    SEARCH_AVAILABLE = True
except Exception:
    logger.warning("Search system not available")
    SEARCH_AVAILABLE = False

# Create FastAPI router
router = APIRouter(prefix="/api/clients", tags=["unified-client"])

# Initialize services
db_access = DatabaseAccessLayer()
core_client_service = CoreClientService()

# Initialize intelligent reminder processor if available
if REMINDERS_AVAILABLE:
    intelligent_processor = IntelligentTaskProcessor()
else:
    intelligent_processor = None

@router.get("/")
async def get_all_clients(
    limit: int = Query(100, description="Maximum number of clients to return"),
    offset: int = Query(0, description="Number of clients to skip"),
    search: Optional[str] = Query(None, description="Search term for client name, email, or phone")
):
    """Get all clients with optional search and pagination"""
    
    try:
        if search:
            clients = core_client_service.search_clients(search, limit)
        else:
            clients = core_client_service.get_all_clients(limit, offset)
        
        return JSONResponse({
            "success": True,
            "clients": clients,
            "total_count": len(clients),
            "limit": limit,
            "offset": offset
        })
        
    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{client_id}")
async def get_client(client_id: str):
    """Get basic client information"""
    
    try:
        client = core_client_service.get_client(client_id)
        
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        return JSONResponse({
            "success": True,
            "client": client
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{client_id}/intelligent-tasks")
async def get_client_intelligent_tasks(
    client_id: str,
    force_regenerate: bool = Query(False, description="Force regenerate tasks"),
    include_all_processes: bool = Query(True, description="Include all process types")
):
    """
    FIXED: Get intelligent tasks with proper database-first logic
    """
    try:
        if not REMINDERS_AVAILABLE or not intelligent_processor:
            raise HTTPException(status_code=503, detail="Intelligent reminder system not available")
        
        # Get client data first
        client = core_client_service.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # STEP 1: Always check database first
        existing_tasks = intelligent_processor.get_client_tasks_from_database(client_id)
        
        if existing_tasks and not force_regenerate:
            # Return persisted tasks from database
            task_statistics = _calculate_task_statistics(existing_tasks)
            
            return JSONResponse({
                "success": True,
                "tasks": existing_tasks,
                "total_count": len(existing_tasks),
                "data_source": "database",  # FIXED: Set data_source correctly
                "client_id": client_id,
                "task_statistics": task_statistics,
                "available_processes": intelligent_processor.get_available_process_types(),
                "intelligent_features": {
                    "process_templates": True,
                    "context_aware_tasks": True,
                    "priority_scoring": True,
                    "automated_task_generation": True
                },
                "message": f"Retrieved {len(existing_tasks)} persisted tasks from database"
            })
        else:
            # STEP 2: Generate new tasks AND persist them
            logger.info(f"🔄 Generating and persisting tasks for client {client_id}")
            
            # Generate tasks using the working method
            generated_tasks = intelligent_processor.generate_and_persist_process_tasks(client_id)
            
            if generated_tasks:
                task_statistics = _calculate_task_statistics(generated_tasks)
                
                return JSONResponse({
                    "success": True,
                    "tasks": generated_tasks,
                    "total_count": len(generated_tasks),
                    "data_source": "generated_and_persisted",  # FIXED: Set data_source correctly
                    "client_id": client_id,
                    "task_statistics": task_statistics,
                    "available_processes": intelligent_processor.get_available_process_types(),
                    "intelligent_features": {
                        "process_templates": True,
                        "context_aware_tasks": True,
                        "priority_scoring": True,
                        "automated_task_generation": True
                    },
                    "message": f"Generated and persisted {len(generated_tasks)} new tasks"
                })
            else:
                # Fallback if generation fails
                return JSONResponse({
                    "success": False,
                    "tasks": [],
                    "total_count": 0,
                    "data_source": "error",
                    "client_id": client_id,
                    "error": "Failed to generate tasks"
                })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching intelligent tasks for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get intelligent tasks: {str(e)}")

def _calculate_task_statistics(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper function to calculate task statistics"""
    if not tasks:
        return {
            "total_tasks": 0,
            "high_priority": 0,
            "medium_priority": 0,
            "low_priority": 0,
            "pending_tasks": 0,
            "completed_tasks": 0
        }
    
    high_priority = len([t for t in tasks if t.get('priority', '').lower() == 'high'])
    medium_priority = len([t for t in tasks if t.get('priority', '').lower() == 'medium'])
    low_priority = len([t for t in tasks if t.get('priority', '').lower() == 'low'])
    pending_tasks = len([t for t in tasks if t.get('status', '').lower() == 'pending'])
    completed_tasks = len([t for t in tasks if t.get('status', '').lower() == 'completed'])
    
    return {
        "total_tasks": len(tasks),
        "high_priority": high_priority,
        "medium_priority": medium_priority,
        "low_priority": low_priority,
        "pending_tasks": pending_tasks,
        "completed_tasks": completed_tasks
    }
