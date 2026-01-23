#!/usr/bin/env python3
"""
Enhanced Client Update Routes - Phase 3A Integration
Implements cross-module update propagation with conflict resolution
"""

from fastapi import APIRouter, HTTPException, Body, Path
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
import sys
from pathlib import Path as PathLib

# Add shared directory to path
sys.path.append(str(PathLib(__file__).parent.parent / 'shared'))

try:
    from phase_3a_update_propagation import UpdatePropagationSystem
    UPDATE_SYSTEM_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Update propagation system not available: {e}")
    UPDATE_SYSTEM_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class ClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    risk_level: Optional[str] = None
    case_status: Optional[str] = None
    case_manager_id: Optional[str] = None
    # Module-specific fields
    housing_status: Optional[str] = None
    employment_status: Optional[str] = None
    benefits_status: Optional[str] = None

class UpdateResponse(BaseModel):
    client_id: str
    overall_success: bool
    modules_updated: List[str]
    modules_failed: List[str]
    conflicts_resolved: List[str]
    selective_updates: Dict[str, Dict[str, Any]]
    update_summary: Dict[str, Any]
    timestamp: str

# Initialize update system
if UPDATE_SYSTEM_AVAILABLE:
    update_system = UpdatePropagationSystem()

@router.put("/api/clients/{client_id}", response_model=UpdateResponse)
async def update_client_enhanced(
    client_id: str = Path(..., description="Client ID to update"),
    update_data: ClientUpdate = Body(..., description="Client update data")
):
    """
    Enhanced client update endpoint - Phase 3A
    Updates client across all modules with selective field updates and conflict resolution
    """
    
    if not UPDATE_SYSTEM_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Update propagation system is not available"
        )
    
    try:
        logger.info(f"Enhanced client update request for: {client_id}")
        
        # Convert Pydantic model to dict, excluding None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(
                status_code=400,
                detail="No update data provided"
            )
        
        # Perform cross-module update
        result = update_system.update_client_all_modules(client_id, update_dict)
        
        if result['overall_success']:
            logger.info(f"Enhanced client update successful: {client_id}")
            return UpdateResponse(**result)
        else:
            logger.error(f"Enhanced client update failed: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Client update failed",
                    "error": result.get('error', 'Unknown error'),
                    "modules_failed": result['modules_failed'],
                    "conflicts_resolved": result['conflicts_resolved']
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced client update error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during client update: {str(e)}"
        )

@router.put("/api/clients/{client_id}/housing")
async def update_client_housing(
    client_id: str = Path(..., description="Client ID to update"),
    housing_data: Dict[str, Any] = Body(..., description="Housing update data")
):
    """Housing-specific update that triggers core client sync"""
    
    if not UPDATE_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Update system not available")
    
    try:
        # Add housing-specific logic here
        result = update_system.update_client_all_modules(
            client_id, housing_data, source_module='housing'
        )
        
        return {"message": "Housing update completed", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/clients/{client_id}/employment")
async def update_client_employment(
    client_id: str = Path(..., description="Client ID to update"),
    employment_data: Dict[str, Any] = Body(..., description="Employment update data")
):
    """Employment-specific update that triggers core client sync"""
    
    if not UPDATE_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Update system not available")
    
    try:
        result = update_system.update_client_all_modules(
            client_id, employment_data, source_module='employment'
        )
        
        return {"message": "Employment update completed", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/clients/{client_id}/benefits")
async def update_client_benefits(
    client_id: str = Path(..., description="Client ID to update"),
    benefits_data: Dict[str, Any] = Body(..., description="Benefits update data")
):
    """Benefits-specific update that triggers core client sync"""
    
    if not UPDATE_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Update system not available")
    
    try:
        result = update_system.update_client_all_modules(
            client_id, benefits_data, source_module='benefits'
        )
        
        return {"message": "Benefits update completed", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/clients/{client_id}/update-history")
async def get_client_update_history(client_id: str):
    """Get update history for a specific client"""
    
    if not UPDATE_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Update system not available")
    
    try:
        history = [
            update for update in update_system.update_history.values()
            if update['client_id'] == client_id
        ]
        
        return {
            "client_id": client_id,
            "update_history": history,
            "total_updates": len(history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/system/update-propagation/status")
async def get_update_system_status():
    """Get status of update propagation system"""
    
    return {
        "update_system_available": UPDATE_SYSTEM_AVAILABLE,
        "features": {
            "cross_module_updates": True,
            "selective_field_updates": True,
            "conflict_resolution": True,
            "bidirectional_sync": True,
            "update_history_tracking": True
        },
        "supported_modules": list(update_system.modules.keys()) if UPDATE_SYSTEM_AVAILABLE else [],
        "conflict_resolution_strategies": ["timestamp", "priority", "merge"] if UPDATE_SYSTEM_AVAILABLE else []
    }
