"""
Case Management Routes - FastAPI Router
Handles client CRUD operations, case notes, and referrals
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from .models import Client, Referral
from .database import CaseManagementDatabase
from backend.shared.database.workspace_store import workspace_store
from backend.auth.authorization import assert_client_access, effective_case_manager_id
from backend.auth.service import require_authenticated_user
from backend.shared.tenancy import multi_tenant_enabled, resolve_org_id

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(prefix="/case-management", tags=["case-management"])

# Initialize database
db = CaseManagementDatabase()

# Pydantic models for request/response
class ClientCreateRequest(BaseModel):
    # Personal Information
    first_name: str = Field(..., min_length=1, description="Client's first name")
    last_name: str = Field(..., min_length=1, description="Client's last name")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    
    # Address Information
    address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    state: str = Field("CA", description="State")
    zip_code: Optional[str] = Field(None, description="ZIP code")
    
    # Emergency Contact
    emergency_contact_name: Optional[str] = Field(None, description="Emergency contact name")
    emergency_contact_phone: Optional[str] = Field(None, description="Emergency contact phone")
    emergency_contact_relationship: Optional[str] = Field(None, description="Relationship to client")
    
    # Case Management
    case_manager_id: str = Field(..., description="Case manager ID")
    risk_level: str = Field("Medium", description="Risk level (Low, Medium, High)")
    case_status: str = Field("Active", description="Case status")
    
    # Service Status
    housing_status: Optional[str] = Field("Unknown", description="Housing status")
    employment_status: Optional[str] = Field("Unemployed", description="Employment status")
    benefits_status: Optional[str] = Field("Not Applied", description="Benefits status")
    legal_status: Optional[str] = Field("No Active Cases", description="Legal status")
    
    # Program Information
    program_type: str = Field("Reentry", description="Program type")
    referral_source: Optional[str] = Field(None, description="How client was referred")
    
    # Background Assessment
    prior_convictions: Optional[str] = Field(None, description="Prior convictions description")
    substance_abuse_history: str = Field("No", description="Substance abuse history")
    mental_health_status: str = Field("Stable", description="Mental health status")
    
    # Support & Resources
    transportation: str = Field("None", description="Transportation access")
    medical_conditions: Optional[str] = Field(None, description="Medical conditions")
    special_needs: Optional[str] = Field(None, description="Special needs/accommodations")
    
    # Goals & Planning
    goals: Optional[str] = Field(None, description="Client goals")
    barriers: Optional[str] = Field(None, description="Identified barriers")
    needs: Optional[List[str]] = Field([], description="Service needs array")
    
    # Additional Information
    notes: Optional[str] = Field(None, description="Additional notes")


class ClientResponse(BaseModel):
    success: bool
    message: str
    client_id: Optional[str] = None
    client: Optional[Dict[str, Any]] = None


class ClientListResponse(BaseModel):
    success: bool
    clients: List[Dict[str, Any]]
    total_count: int
    filters_applied: Dict[str, Any]


class CaseNoteRequest(BaseModel):
    case_manager_id: str
    note_type: str = Field("General", description="Type of note")
    title: Optional[str] = Field(None, description="Note title")
    content: str = Field(..., description="Note content")
    contact_method: Optional[str] = Field(None, description="Contact method")
    duration_minutes: int = Field(0, description="Duration in minutes")
    location: Optional[str] = Field(None, description="Location")
    client_mood: Optional[str] = Field(None, description="Client mood assessment")
    progress_rating: int = Field(0, description="Progress rating 1-5")
    barriers_identified: Optional[str] = Field(None, description="Barriers identified")
    action_items: Optional[str] = Field(None, description="Action items")
    next_contact_needed: Optional[str] = Field(None, description="Next contact needed")
    referrals_made: Optional[str] = Field(None, description="Referrals made")
    is_confidential: bool = Field(False, description="Is note confidential")
    tags: Optional[List[str]] = Field([], description="Note tags")


# =============================================================================
# CLIENT MANAGEMENT ROUTES
# =============================================================================

@router.get("/")
async def case_management_info():
    """Case Management API information"""
    return {
        "message": "Case Management API Ready",
        "version": "1.0",
        "endpoints": {
            "clients": "/api/case-management/clients",
            "client_by_id": "/api/case-management/clients/{client_id}",
            "case_notes": "/api/case-management/clients/{client_id}/notes"
        },
        "description": "Comprehensive case management system for client intake and tracking"
    }


@router.post("/clients", response_model=ClientResponse)
async def create_client(client_request: ClientCreateRequest, request: Request):
    """Create a new client - SOLE CLIENT CREATOR for the entire system"""
    try:
        current_user = require_authenticated_user(request)
        logger.info(f"Creating new client: {client_request.first_name} {client_request.last_name}")
        
        from backend.shared.database.core_client_service import CoreClientService
        
        # Initialize the core client service
        core_service = CoreClientService()
        
        # Prepare client data for core database
        client_data = client_request.dict()
        client_data["case_manager_id"] = effective_case_manager_id(current_user, client_request.case_manager_id)
        client_data['intake_date'] = datetime.now().strftime('%Y-%m-%d')
        client_data['created_at'] = datetime.now().isoformat()
        client_data['updated_at'] = datetime.now().isoformat()
        client_data['case_status'] = 'active'
        client_data['risk_level'] = 'medium'
        
        # Create client in core_clients.db (single source of truth)
        result = core_service.create_client(client_data)
        
        if result['success']:
            # Create client object for response
            client = Client(**client_data)
            client_id = result['client_id']

            # Generate intake needs and tasks in the background (non-blocking on failure)
            await _generate_initial_tasks(client, client_id)

            return ClientResponse(
                success=True,
                message=f"Client created successfully in core database",
                client_id=client_id,
                client=client.to_dict(),
                integration_results={'core_database': 'core_clients.db'}
            )
        else:
            raise HTTPException(status_code=500, detail=f"Failed to create client: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients", response_model=ClientListResponse)
async def get_clients(
    request: Request,
    case_manager_id: Optional[str] = Query(None, description="Case manager ID"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    search: Optional[str] = Query(None, description="Search by name"),
    page: int = Query(1, description="Page number"),
    per_page: int = Query(50, description="Items per page")
):
    """Get clients from core database with optional filtering"""
    try:
        current_user = require_authenticated_user(request)
        from backend.shared.database.core_client_service import CoreClientService
        
        core_service = CoreClientService()
        
        # Build filters
        filters = {}
        if risk_level:
            filters['risk_level'] = risk_level
        if search:
            filters['search'] = search
        
        # Get clients from core database
        scoped_case_manager_id = effective_case_manager_id(current_user, case_manager_id)
        # When multi-tenancy is on and no CM filter scopes the query, restrict to the caller's org.
        _org_id = resolve_org_id(current_user) if multi_tenant_enabled() else None
        if scoped_case_manager_id:
            clients_data = core_service.get_clients_by_case_manager(scoped_case_manager_id)
        elif search:
            clients_data = core_service.search_clients(search, limit=per_page, org_id=_org_id)
        else:
            offset = (page - 1) * per_page
            clients_data = core_service.get_all_clients(limit=per_page, offset=offset, org_id=_org_id)
        
        # Apply additional filters if needed
        if risk_level:
            clients_data = [c for c in clients_data if c.get('risk_level', '').lower() == risk_level.lower()]
        
        # Convert to dict format
        client_dicts = []
        for client_data in clients_data:
            try:
                client = Client(**client_data)
                client_dicts.append(client.to_dict())
            except Exception as e:
                logger.warning(f"Error converting client data: {e}")
                continue
        
        return ClientListResponse(
            success=True,
            clients=client_dicts,
            total_count=len(client_dicts),
            filters_applied=filters
        )
    
    except Exception as e:
        logger.error(f"Error getting clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/{client_id}")
async def get_client(client_id: str, request: Request):
    """Get a specific client by ID from core database"""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        from backend.shared.database.core_client_service import CoreClientService
        
        core_service = CoreClientService()
        client_data = core_service.get_client(client_id)
        
        if client_data:
            client = Client(**client_data)
            return {
                "success": True,
                "client": client.to_dict()
            }
        else:
            raise HTTPException(status_code=404, detail="Client not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clients/{client_id}")
async def update_client(client_id: str, client_request: ClientCreateRequest, request: Request):
    """Update an existing client in core database"""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        from backend.shared.database.core_client_service import CoreClientService
        
        core_service = CoreClientService()
        
        # Check if client exists
        existing_client_data = core_service.get_client(client_id)
        if not existing_client_data:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Prepare update data
        update_data = client_request.dict()
        update_data["case_manager_id"] = effective_case_manager_id(current_user, client_request.case_manager_id)
        # Preserve original intake date and creation date
        update_data['intake_date'] = existing_client_data.get('intake_date')
        update_data['created_at'] = existing_client_data.get('created_at')
        
        # Update in core database
        result = core_service.update_client(client_id, update_data)
        
        if result['success']:
            # Get updated client data
            updated_client_data = core_service.get_client(client_id)
            if updated_client_data:
                client = Client(**updated_client_data)
                return ClientResponse(
                    success=True,
                    message="Client updated successfully",
                    client_id=client.client_id,
                    client=client.to_dict()
                )
        
        raise HTTPException(status_code=500, detail=f"Failed to update client: {result.get('error', 'Unknown error')}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clients/{client_id}")
async def delete_client(client_id: str, request: Request):
    """Delete (soft delete) a client from core database"""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        from backend.shared.database.core_client_service import CoreClientService
        
        core_service = CoreClientService()
        
        # Check if client exists
        existing_client_data = core_service.get_client(client_id)
        if not existing_client_data:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Soft delete from core database
        result = core_service.delete_client(client_id)
        
        if result['success']:
            return {
                "success": True,
                "message": "Client deleted successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete client: {result.get('error', 'Unknown error')}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CASE NOTES ROUTES
# =============================================================================

@router.post("/clients/{client_id}/notes")
async def create_case_note(client_id: str, note_request: CaseNoteRequest, request: Request):
    """Create a new case note for a client"""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        logger.info(f"Creating case note for client: {client_id}")
        
        # Verify client exists
        client = db.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Create case note object
        note_data = note_request.dict()
        note_data['client_id'] = client_id
        note_data['case_manager_id'] = current_user.case_manager_id
        note_data['created_at'] = datetime.now().isoformat()
        
        case_note = CaseNote(**note_data)
        
        # Save to database
        success = db.create_case_note(case_note)
        
        if success:
            return {
                "success": True,
                "message": "Case note created successfully",
                "note_id": case_note.note_id,
                "case_note": case_note.to_dict()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create case note")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating case note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/{client_id}/notes")
async def get_client_notes(client_id: str, request: Request):
    """Get all case notes for a client"""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        logger.info(f"Getting case notes for client: {client_id}")
        
        # Verify client exists
        client = db.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Get case notes
        notes = db.get_client_notes(client_id)
        
        return {
            "success": True,
            "client_id": client_id,
            "notes": [note.to_dict() for note in notes],
            "total_count": len(notes)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting case notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DASHBOARD & ANALYTICS ROUTES
# =============================================================================

@router.get("/dashboard/{case_manager_id}")
async def get_dashboard_stats(case_manager_id: str, request: Request):
    """Get dashboard statistics for a case manager"""
    try:
        current_user = require_authenticated_user(request)
        case_manager_id = effective_case_manager_id(current_user, case_manager_id) or current_user.case_manager_id
        # Validate case_manager_id parameter
        if not case_manager_id:
            raise HTTPException(status_code=400, detail="case_manager_id is required")
        
        logger.info(f"Getting dashboard stats for case manager: {case_manager_id}")
        
        # Get all clients for this case manager
        clients = db.get_clients_by_case_manager(case_manager_id)
        
        # Calculate statistics
        total_clients = len(clients)
        active_clients = len([c for c in clients if c.case_status == 'Active'])
        high_risk_clients = len([c for c in clients if c.risk_level == 'High'])
        homeless_clients = len([c for c in clients if c.housing_status == 'Homeless'])
        # Calculate recent intakes with robust date parsing
        recent_intakes = 0
        for c in clients:
            if c.intake_date:
                try:
                    # Try different date formats
                    intake_date = None
                    for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                        try:
                            intake_date = datetime.strptime(c.intake_date, fmt)
                            break
                        except ValueError:
                            continue
                    
                    # If we successfully parsed the date, check if it's within 30 days
                    if intake_date and (datetime.now() - intake_date).days <= 30:
                        recent_intakes += 1
                        
                except (ValueError, TypeError):
                    # Skip clients with unparseable dates
                    continue
        
        # Risk level breakdown
        risk_breakdown = {
            'High': len([c for c in clients if c.risk_level == 'High']),
            'Medium': len([c for c in clients if c.risk_level == 'Medium']),
            'Low': len([c for c in clients if c.risk_level == 'Low'])
        }
        
        # Housing status breakdown
        housing_breakdown = {}
        for client in clients:
            status = client.housing_status or 'Unknown'
            housing_breakdown[status] = housing_breakdown.get(status, 0) + 1
        
        # Calculate average risk score
        if clients:
            avg_risk_score = sum(client.risk_score for client in clients) / len(clients)
        else:
            avg_risk_score = 0.0
        
        return {
            "success": True,
            "case_manager_id": case_manager_id,
            "generated_at": datetime.now().isoformat(),
            "statistics": {
                "total_clients": total_clients,
                "active_clients": active_clients,
                "high_risk_clients": high_risk_clients,
                "homeless_clients": homeless_clients,
                "recent_intakes": recent_intakes,
                "average_risk_score": round(avg_risk_score, 2)
            },
            "breakdowns": {
                "risk_levels": risk_breakdown,
                "housing_status": housing_breakdown
            },
            "recent_clients": [client.to_dict() for client in clients[:5]]
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _generate_initial_tasks(client: Client, client_id: str):
    """Derive intake needs and create initial tasks for a newly created client."""
    try:
        from backend.api.clients import derive_operational_needs
        client_dict = client.to_dict()
        client_dict["client_id"] = client_id

        needs = derive_operational_needs(client_dict)
        if not needs:
            logger.info("No intake needs derived for client %s", client_id)
            return

        workspace_store.upsert_operational_needs(
            client_id=client_id,
            needs=needs,
            source="intake",
            source_id=client_id,
        )
        created = workspace_store.create_tasks_from_operational_needs(
            client_id=client_id,
            needs=needs,
            source="intake",
            source_id=client_id,
            assigned_to="Case Manager",
        )
        logger.info(
            "Generated %d intake needs and %d initial tasks for client %s",
            len(needs), len(created), client_id,
        )
    except Exception as e:
        logger.error(f"Error generating initial tasks for {client_id}: {e}")


# =============================================================================
# NOTES ENDPOINTS (Progressive Backend Implementation)
# =============================================================================

class NoteCreateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Optional note title")
    note_type: str = Field(..., description="Type of note")
    content: str = Field(..., min_length=1, description="Note content")
    created_by: str = Field(..., description="User who created the note")

@router.post("/notes/add/{client_id}")
async def add_client_note(client_id: str, note_data: NoteCreateRequest, request: Request):
    """Add a new note for a client."""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        note = workspace_store.create_client_note(
            client_id=client_id,
            note_type=note_data.note_type,
            content=note_data.content,
            created_by=current_user.full_name,
            title=note_data.title,
        )
        logger.info("Added note %s for client %s", note["note_id"], client_id)
        
        return JSONResponse({
            "success": True,
            "note_id": note["note_id"],
            "note": note,
            "message": "Note added successfully"
        })
        
    except Exception as e:
        logger.error(f"Error adding note for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notes/list/{client_id}")
async def get_client_notes(client_id: str, request: Request):
    """Get all notes for a client"""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        return JSONResponse({
            "success": True,
            "notes": workspace_store.list_client_notes(client_id)
        })
        
    except Exception as e:
        logger.error(f"Error getting notes for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/notes/{note_id}")
async def delete_note(note_id: str, request: Request):
    """Delete a specific note."""
    try:
        current_user = require_authenticated_user(request)
        note = workspace_store.get_client_note(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        assert_client_access(current_user, note["client_id"])
        if not workspace_store.delete_client_note(note_id):
            raise HTTPException(status_code=404, detail="Note not found")
        logger.info("Deleted note %s", note_id)
        return JSONResponse({
            "success": True,
            "message": "Note deleted successfully"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting note {note_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/notes/update/{note_id}")
async def update_note(note_id: str, note_data: NoteCreateRequest, request: Request):
    """Update a specific note."""
    try:
        current_user = require_authenticated_user(request)
        existing_note = workspace_store.get_client_note(note_id)
        if not existing_note:
            raise HTTPException(status_code=404, detail="Note not found")
        assert_client_access(current_user, existing_note["client_id"])
        note = workspace_store.update_client_note(
            note_id=note_id,
            note_type=note_data.note_type,
            content=note_data.content,
            created_by=current_user.full_name,
            title=note_data.title,
        )
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return JSONResponse({
            "success": True,
            "note": note,
            "message": "Note updated successfully"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating note {note_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/add/{client_id}")
async def add_task(client_id: str, task_data: dict, request: Request):
    """Add a new task for a client"""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        task_data = {**task_data, "assigned_to": current_user.full_name}
        new_task = workspace_store.create_client_task(client_id, task_data)
        logger.info("Task added for client %s: %s", client_id, new_task["task_id"])
        
        return JSONResponse({
            "success": True,
            "task_id": new_task["task_id"],
            "task": new_task,
            "message": "Task added successfully"
        })
        
    except Exception as e:
        logger.error(f"Error adding task for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/list/{client_id}")
async def get_client_tasks(client_id: str, request: Request):
    """Get all tasks for a client"""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        tasks = workspace_store.list_client_tasks(client_id)
        logger.info("Retrieved %s tasks for client %s", len(tasks), client_id)
        
        return JSONResponse({
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving tasks for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/tasks/update/{task_id}")
async def update_task(task_id: str, task_data: dict, request: Request):
    """Update an existing task"""
    try:
        current_user = require_authenticated_user(request)
        existing_task = workspace_store.get_client_task(task_id)
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found")
        assert_client_access(current_user, existing_task["client_id"])
        task = workspace_store.update_client_task(task_id, task_data)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        logger.info("Task updated: %s", task_id)
        return JSONResponse({
            "success": True,
            "message": "Task updated successfully",
            "task": task
        })
            
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, request: Request):
    """Delete a task"""
    try:
        current_user = require_authenticated_user(request)
        existing_task = workspace_store.get_client_task(task_id)
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found")
        assert_client_access(current_user, existing_task["client_id"])
        if not workspace_store.delete_client_task(task_id):
            raise HTTPException(status_code=404, detail="Task not found")
        logger.info("Task deleted: %s", task_id)
        return JSONResponse({
            "success": True,
            "message": "Task deleted successfully"
        })
            
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Case Management API"
    }
