#!/usr/bin/env python3
"""
Enhanced Client Routes - Phase 2A Integration
Integrates the enhanced client creation API with FastAPI backend
"""

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
import sys
from pathlib import Path

# Add shared directory to path
sys.path.append(str(Path(__file__).parent.parent / 'shared'))

try:
    from enhanced_client_creation_fixed import create_client_with_distribution
    ENHANCED_API_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Enhanced client API not available: {e}")
    ENHANCED_API_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class EnhancedClientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    risk_level: Optional[str] = "medium"
    case_status: Optional[str] = "active"
    case_manager_id: Optional[str] = "cm_001"

class ClientCreationResponse(BaseModel):
    client_id: str
    overall_success: bool
    success_rate: float
    modules_created: List[str]
    modules_failed: List[str]
    detailed_results: Dict[str, Any]
    transaction_log: List[str]
    errors: List[str]
    timestamp: str

@router.post("/api/clients/enhanced", response_model=ClientCreationResponse)
async def create_client_enhanced(client_data: EnhancedClientCreate):
    """
    Enhanced client creation endpoint - Phase 2A
    Automatically distributes client across all 10 modules with transaction rollback
    """
    
    if not ENHANCED_API_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Enhanced client creation API is not available"
        )
    
    try:
        logger.info(f"Enhanced client creation request: {client_data.first_name} {client_data.last_name}")
        
        # Convert Pydantic model to dict
        client_dict = client_data.dict()
        
        # Create client using enhanced API
        result = create_client_with_distribution(client_dict)
        
        if result['overall_success']:
            logger.info(f"Enhanced client creation successful: {result['client_id']}")
            return ClientCreationResponse(**result)
        else:
            logger.error(f"Enhanced client creation failed: {result['errors']}")
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Client creation failed",
                    "errors": result['errors'],
                    "modules_failed": result['modules_failed'],
                    "transaction_log": result['transaction_log']
                }
            )
            
    except Exception as e:
        logger.error(f"Enhanced client creation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during client creation: {str(e)}"
        )

@router.get("/api/clients/enhanced/status")
async def get_enhanced_api_status():
    """Get status of enhanced client creation API"""
    
    return {
        "enhanced_api_available": ENHANCED_API_AVAILABLE,
        "features": {
            "automatic_distribution": True,
            "transaction_rollback": True,
            "comprehensive_logging": True,
            "duplicate_prevention": True,
            "cross_module_sync": True
        },
        "supported_modules": [
            "core_clients", "case_management", "housing", "benefits", "legal",
            "employment", "services", "reminders", "ai_assistant", "unified_platform"
        ]
    }

@router.post("/api/clients/enhanced/test")
async def test_enhanced_client_creation():
    """Test endpoint for enhanced client creation"""
    
    if not ENHANCED_API_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Enhanced client creation API is not available"
        )
    
    # Test client data
    test_client = EnhancedClientCreate(
        first_name="Test",
        last_name="Enhanced",
        email="test.enhanced@example.com",
        phone="(555) 123-TEST",
        case_manager_id="cm_test",
        risk_level="medium"
    )
    
    try:
        # Create test client
        result = create_client_with_distribution(test_client.dict())
        
        # Clean up test client if successful
        if result['overall_success']:
            from enhanced_client_creation_fixed import cleanup_test_client
            cleanup_test_client(result['client_id'])
            
            return {
                "test_result": "success",
                "message": "Enhanced client creation test passed",
                "modules_tested": len(result['modules_created']),
                "success_rate": result['success_rate']
            }
        else:
            return {
                "test_result": "failed",
                "message": "Enhanced client creation test failed",
                "errors": result['errors'],
                "modules_failed": result['modules_failed']
            }
            
    except Exception as e:
        logger.error(f"Enhanced client creation test error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Test failed: {str(e)}"
        )