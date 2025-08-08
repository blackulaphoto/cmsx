#!/usr/bin/env python3
"""
Unified Client API - Provides comprehensive client data across all modules
This API serves the unified client dashboard with data from all databases
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from ..shared.database.access_layer import DatabaseAccessLayer, DatabaseType
from ..shared.database.core_client_service import CoreClientService

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(prefix="/api/clients", tags=["unified-client"])

# Initialize services
db_access = DatabaseAccessLayer()
core_client_service = CoreClientService()

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

@router.get("/{client_id}/unified-view")
async def get_unified_client_view(client_id: str):
    """Get comprehensive client data from all modules"""
    
    try:
        # Get core client data
        client = core_client_service.get_client(client_id)
        
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Initialize unified data structure
        unified_data = {
            "client": client,
            "housing": {},
            "employment": {},
            "benefits": {},
            "legal": {},
            "services": {},
            "tasks": [],
            "appointments": [],
            "case_notes": [],
            "goals": [],
            "barriers": []
        }
        
        # Get data from each module database
        module_name = "unified_client_api"  # This API has read access to all databases
        
        # Housing data
        try:
            housing_data = db_access.execute_query(
                module=module_name,
                database_type=DatabaseType.HOUSING,
                query="""
                    SELECT 'applications' as data_type, * FROM housing_applications WHERE client_id = ?
                    UNION ALL
                    SELECT 'profiles' as data_type, * FROM client_housing_profiles WHERE client_id = ?
                """,
                params=(client_id, client_id),
                operation="SELECT"
            )
            
            # Organize housing data
            applications = [row for row in housing_data if row.get('data_type') == 'applications']
            profiles = [row for row in housing_data if row.get('data_type') == 'profiles']
            
            unified_data["housing"] = {
                "applications": applications,
                "profile": profiles[0] if profiles else None,
                "status": get_housing_status(applications)
            }
            
        except Exception as e:
            logger.warning(f"Error fetching housing data for {client_id}: {e}")
        
        # Employment data
        try:
            employment_data = db_access.execute_query(
                module=module_name,
                database_type=DatabaseType.JOBS,
                query="""
                    SELECT 'applications' as data_type, * FROM job_applications WHERE client_id = ?
                    UNION ALL
                    SELECT 'saved_jobs' as data_type, * FROM saved_jobs WHERE client_id = ?
                """,
                params=(client_id, client_id),
                operation="SELECT"
            )
            
            # Get resumes
            resume_data = db_access.execute_query(
                module=module_name,
                database_type=DatabaseType.RESUMES,
                query="SELECT * FROM resumes WHERE client_id = ?",
                params=(client_id,),
                operation="SELECT"
            )
            
            applications = [row for row in employment_data if row.get('data_type') == 'applications']
            saved_jobs = [row for row in employment_data if row.get('data_type') == 'saved_jobs']
            
            unified_data["employment"] = {
                "applications": applications,
                "saved_jobs": saved_jobs,
                "resumes": resume_data,
                "status": get_employment_status(applications, saved_jobs)
            }
            
        except Exception as e:
            logger.warning(f"Error fetching employment data for {client_id}: {e}")
        
        # Benefits data
        try:
            benefits_data = db_access.execute_query(
                module=module_name,
                database_type=DatabaseType.BENEFITS_TRANSPORT,
                query="""
                    SELECT 'applications' as data_type, * FROM benefits_applications WHERE client_id = ?
                    UNION ALL
                    SELECT 'profiles' as data_type, * FROM client_benefits_profiles WHERE client_id = ?
                    UNION ALL
                    SELECT 'assessments' as data_type, * FROM disability_assessments WHERE client_id = ?
                """,
                params=(client_id, client_id, client_id),
                operation="SELECT"
            )
            
            applications = [row for row in benefits_data if row.get('data_type') == 'applications']
            profiles = [row for row in benefits_data if row.get('data_type') == 'profiles']
            assessments = [row for row in benefits_data if row.get('data_type') == 'assessments']
            
            unified_data["benefits"] = {
                "applications": applications,
                "profile": profiles[0] if profiles else None,
                "assessments": assessments,
                "status": get_benefits_status(applications)
            }
            
        except Exception as e:
            logger.warning(f"Error fetching benefits data for {client_id}: {e}")
        
        # Legal data
        try:
            legal_data = db_access.execute_query(
                module=module_name,
                database_type=DatabaseType.LEGAL_CASES,
                query="""
                    SELECT 'cases' as data_type, * FROM legal_cases WHERE client_id = ?
                    UNION ALL
                    SELECT 'court_dates' as data_type, * FROM court_dates WHERE client_id = ?
                """,
                params=(client_id, client_id),
                operation="SELECT"
            )
            
            # Get expungement data
            expungement_data = db_access.execute_query(
                module=module_name,
                database_type=DatabaseType.EXPUNGEMENT,
                query="SELECT * FROM expungement_eligibility WHERE client_id = ?",
                params=(client_id,),
                operation="SELECT"
            )
            
            cases = [row for row in legal_data if row.get('data_type') == 'cases']
            court_dates = [row for row in legal_data if row.get('data_type') == 'court_dates']
            
            unified_data["legal"] = {
                "cases": cases,
                "court_dates": court_dates,
                "expungement": expungement_data,
                "status": get_legal_status(cases, court_dates)
            }
            
        except Exception as e:
            logger.warning(f"Error fetching legal data for {client_id}: {e}")
        
        # Services data
        try:
            services_data = db_access.execute_query(
                module=module_name,
                database_type=DatabaseType.SERVICES,
                query="SELECT * FROM client_referrals WHERE client_id = ?",
                params=(client_id,),
                operation="SELECT"
            )
            
            unified_data["services"] = {
                "referrals": services_data
            }
            
        except Exception as e:
            logger.warning(f"Error fetching services data for {client_id}: {e}")
        
        # Tasks and appointments from case management
        try:
            case_mgmt_data = db_access.execute_query(
                module=module_name,
                database_type=DatabaseType.CASE_MANAGEMENT,
                query="""
                    SELECT 'tasks' as data_type, * FROM tasks WHERE client_id = ?
                    UNION ALL
                    SELECT 'appointments' as data_type, * FROM appointments WHERE client_id = ?
                    UNION ALL
                    SELECT 'case_notes' as data_type, * FROM case_notes WHERE client_id = ?
                """,
                params=(client_id, client_id, client_id),
                operation="SELECT"
            )
            
            unified_data["tasks"] = [row for row in case_mgmt_data if row.get('data_type') == 'tasks']
            unified_data["appointments"] = [row for row in case_mgmt_data if row.get('data_type') == 'appointments']
            unified_data["case_notes"] = [row for row in case_mgmt_data if row.get('data_type') == 'case_notes']
            
        except Exception as e:
            logger.warning(f"Error fetching case management data for {client_id}: {e}")
        
        # Goals and barriers from core database
        try:
            core_data = db_access.execute_query(
                module=module_name,
                database_type=DatabaseType.CORE_CLIENTS,
                query="""
                    SELECT 'goals' as data_type, * FROM client_goals WHERE client_id = ?
                    UNION ALL
                    SELECT 'barriers' as data_type, * FROM client_barriers WHERE client_id = ?
                """,
                params=(client_id, client_id),
                operation="SELECT"
            )
            
            unified_data["goals"] = [row for row in core_data if row.get('data_type') == 'goals']
            unified_data["barriers"] = [row for row in core_data if row.get('data_type') == 'barriers']
            
        except Exception as e:
            logger.warning(f"Error fetching goals/barriers for {client_id}: {e}")
        
        return JSONResponse({
            "success": True,
            "client_data": unified_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching unified client view for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_housing_status(applications: List[Dict]) -> str:
    """Determine housing status from applications"""
    if not applications:
        return "Unknown"
    
    # Check for approved applications
    approved = [app for app in applications if app.get('application_status') == 'approved']
    if approved:
        return "Housing Secured"
    
    # Check for pending applications
    pending = [app for app in applications if app.get('application_status') == 'under_review']
    if pending:
        return f"{len(pending)} Applications Pending"
    
    # Check for recent applications
    recent = [app for app in applications if app.get('application_status') == 'submitted']
    if recent:
        return f"{len(recent)} Applications Submitted"
    
    return "Seeking Housing"

def get_employment_status(applications: List[Dict], saved_jobs: List[Dict]) -> str:
    """Determine employment status from applications and saved jobs"""
    if not applications and not saved_jobs:
        return "Not Actively Job Searching"
    
    # Check for recent applications
    if applications:
        active_apps = [app for app in applications if app.get('status') in ['applied', 'interview', 'pending']]
        if active_apps:
            return f"{len(active_apps)} Active Applications"
    
    if saved_jobs:
        return f"{len(saved_jobs)} Jobs Saved"
    
    return "Job Searching"

def get_benefits_status(applications: List[Dict]) -> str:
    """Determine benefits status from applications"""
    if not applications:
        return "No Benefits Applied"
    
    approved = [app for app in applications if app.get('application_status') == 'approved']
    pending = [app for app in applications if app.get('application_status') == 'pending']
    
    status_parts = []
    if approved:
        status_parts.append(f"{len(approved)} Approved")
    if pending:
        status_parts.append(f"{len(pending)} Pending")
    
    return ", ".join(status_parts) if status_parts else "Applications Submitted"

def get_legal_status(cases: List[Dict], court_dates: List[Dict]) -> str:
    """Determine legal status from cases and court dates"""
    if not cases and not court_dates:
        return "No Active Legal Cases"
    
    active_cases = [case for case in cases if case.get('case_status') == 'active']
    upcoming_dates = [date for date in court_dates if date.get('status') == 'scheduled']
    
    if upcoming_dates:
        return f"Upcoming Court Date: {len(upcoming_dates)} scheduled"
    
    if active_cases:
        return f"{len(active_cases)} Active Cases"
    
    return "Legal Matters in Progress"