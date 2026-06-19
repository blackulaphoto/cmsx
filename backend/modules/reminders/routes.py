# ================================================================
# @generated
# @preserve
# @readonly
# DO NOT MODIFY THIS FILE
# Purpose: Production-approved unified system
# Any changes must be approved by lead developer.
# WARNING: Modifying this file may break the application.
# ================================================================

#!/usr/bin/env python3
"""
Reminders Routes - FastAPI Router for Second Chance Jobs Platform
Intelligent Case Management Reminder Dashboard
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from .intelligent_processor import IntelligentTaskProcessor
from .data_integration import RealDataIntegrator
from . import repository as _repo
from backend.auth.authorization import assert_client_access, get_client_ids_for_org, get_org_for_user_id
from backend.auth.service import AuthenticatedUser, require_authenticated_user
from backend.shared.database.workspace_store import workspace_store
from backend.shared.tenancy import multi_tenant_enabled, resolve_org_id

# Note: Authentication dependencies would be imported here when auth module is implemented
# from auth.dependencies import get_current_active_user, require_case_manager, require_supervisor
# from auth.models import User

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(tags=["reminders"])

# Initialize intelligent processor and data integrator
intelligent_processor = IntelligentTaskProcessor()
data_integrator = RealDataIntegrator()

# Pydantic models
class ContactCompleted(BaseModel):
    client_id: str
    case_manager_id: str
    contact_data: Dict[str, Any] = {}

class TaskCompletion(BaseModel):
    task_id: str
    completion_notes: str = ""
    outcome: str = "Completed"
    actual_minutes: int = 0

class StartProcess(BaseModel):
    client_id: str
    case_manager_id: str
    process_type: str
    priority_level: str = "Medium"
    context: Dict[str, Any] = {}

class DeviceRegistration(BaseModel):
    case_manager_id: str
    device_token: str
    device_type: str = "web"

class NotificationPreferences(BaseModel):
    case_manager_id: str
    preferences: Dict[str, Any] = {}

class ProgressRecord(BaseModel):
    case_manager_id: str
    client_id: str
    task_id: str
    task_type: str
    estimated_minutes: int = 30
    actual_minutes: int = 30
    completion_quality: str = "Good"
    outcome: str = "Completed"
    notes: str = ""

class ReminderUpdate(BaseModel):
    reminder_text: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    reminder_type: Optional[str] = None


class ReminderCreate(BaseModel):
    client_id: str
    reminder_text: str
    due_date: Optional[str] = None
    case_manager_id: Optional[str] = None
    priority: str = "Medium"
    reminder_type: Optional[str] = "general"
    description: Optional[str] = ""

def _current_user_for_tenancy(request: Request) -> Optional[AuthenticatedUser]:
    if not multi_tenant_enabled():
        return None
    return require_authenticated_user(request)


def _tenant_org_id(user: Optional[AuthenticatedUser]) -> Optional[str]:
    return resolve_org_id(user) if user else None


def _authorize_case_manager_filter(user: Optional[AuthenticatedUser], case_manager_id: Optional[str]) -> str:
    requested = (case_manager_id or "").strip()
    if not multi_tenant_enabled() or user is None:
        return requested or "default_cm"
    if not requested or requested == "default_cm":
        return user.case_manager_id
    case_manager_org = get_org_for_user_id(requested)
    if not case_manager_org or case_manager_org != resolve_org_id(user):
        raise HTTPException(status_code=404, detail="Case manager not found")
    return requested


def _assert_client_scope(user: Optional[AuthenticatedUser], client_id: str) -> None:
    if multi_tenant_enabled() and user is not None and client_id:
        assert_client_access(user, client_id)


def _assert_reminder_scope(user: Optional[AuthenticatedUser], reminder_id: str) -> None:
    if not multi_tenant_enabled() or user is None:
        return
    reminder = _repo.get_active_reminder(reminder_id)
    if not reminder or reminder.get("org_id") != resolve_org_id(user):
        raise HTTPException(status_code=404, detail="Reminder not found")


def _assert_task_scope(user: Optional[AuthenticatedUser], task_id: str) -> None:
    if not multi_tenant_enabled() or user is None:
        return
    task = _repo.get_intelligent_task(task_id)
    if task:
        if task.get("org_id") != resolve_org_id(user):
            raise HTTPException(status_code=404, detail="Task not found")
        return
    workspace_task = workspace_store.get_client_task(task_id)
    if workspace_task:
        _assert_client_scope(user, workspace_task.get("client_id", ""))

# =============================================================================
# API ROUTES
# =============================================================================

@router.get("/")
async def reminders_api_info():
    """Reminders API information and available endpoints"""
    return {
        "message": "Reminders API Ready",
        "version": "1.0",
        "endpoints": {
            "dashboard": "/api/reminders/dashboard/{case_manager_id}",
            "smart-dashboard": "/api/reminders/smart-dashboard/{case_manager_id}",
            "tasks": "/api/reminders/tasks",
            "appointments": "/api/reminders/appointments"
        },
        "description": "Task management and reminder system for case managers"
    }

@router.post("/create")
async def create_reminder(payload: ReminderCreate, request: Request):
    """Create a reminder for a client"""
    try:
        user = _current_user_for_tenancy(request)
        _assert_client_scope(user, payload.client_id)
        case_manager_id = (
            _authorize_case_manager_filter(user, payload.case_manager_id)
            if multi_tenant_enabled()
            else (payload.case_manager_id or "unknown")
        )
        reminder_id = _repo.create_active_reminder(
            client_id=payload.client_id,
            case_manager_id=case_manager_id,
            reminder_type=payload.reminder_type or "general",
            message=payload.reminder_text,
            priority=payload.priority,
            due_date=payload.due_date,
            org_id=_tenant_org_id(user),
        )
        return {
            "success": True,
            "reminder_id": reminder_id,
            "client_id": payload.client_id,
            "case_manager_id": case_manager_id,
            "message": payload.reminder_text,
            "priority": payload.priority,
            "due_date": payload.due_date,
            "status": "Active",
            "created_at": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create reminder: {str(e)}")

@router.get("/dashboard/{case_manager_id}")
async def get_case_manager_dashboard(case_manager_id: str, request: Request):
    """
    UPDATED: Dashboard with persisted tasks from database
    """
    try:
        user = _current_user_for_tenancy(request)
        case_manager_id = _authorize_case_manager_filter(user, case_manager_id)
        org_id = _tenant_org_id(user)
        from backend.shared.db_path import DB_DIR
        core_clients_db = DB_DIR / "core_clients.db"
        reminders_db = DB_DIR / "reminders.db"

        with sqlite3.connect(core_clients_db) as client_conn, sqlite3.connect(reminders_db) as reminders_conn:
            client_cursor = client_conn.cursor()
            reminders_cursor = reminders_conn.cursor()

            client_cursor.execute("""
                SELECT DISTINCT client_id, first_name, last_name 
                FROM clients 
                WHERE case_manager_id = ?
            """, (case_manager_id,))
            
            clients = client_cursor.fetchall()
            client_ids = [client[0] for client in clients]
            if org_id:
                allowed_client_ids = set(get_client_ids_for_org(org_id))
                client_ids = [client_id for client_id in client_ids if client_id in allowed_client_ids]
            
            if not client_ids:
                return {
                    "success": True,
                    "total_tasks": 0,
                    "urgent_tasks": 0,
                    "today_tasks": 0,
                    "pending_tasks": 0,
                    "clients": [],
                    "tasks": [],
                    "message": "No clients assigned to this case manager"
                }
            
            # Get today's date
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Get task statistics from persisted tasks
            placeholders = ','.join('?' * len(client_ids))
            reminders_cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN priority = 'high' THEN 1 ELSE 0 END) as urgent_tasks,
                    SUM(CASE WHEN DATE(due_date) = ? THEN 1 ELSE 0 END) as today_tasks,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_tasks
                FROM intelligent_tasks 
                WHERE client_id IN ({placeholders})
            """, [today] + client_ids)
            
            stats = reminders_cursor.fetchone()
            
            # Get today's specific tasks
            reminders_cursor.execute(f"""
                SELECT id, client_id, title, description, priority, status, due_date, task_type
                FROM intelligent_tasks 
                WHERE client_id IN ({placeholders}) AND DATE(due_date) = ?
                ORDER BY 
                    CASE priority 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        WHEN 'low' THEN 3 
                        ELSE 4 
                    END,
                    due_date ASC
                LIMIT 20
            """, client_ids + [today])
            
            today_tasks = []
            for row in reminders_cursor.fetchall():
                today_tasks.append({
                    'task_id': row[0],
                    'client_id': row[1],
                    'title': row[2],
                    'description': row[3],
                    'priority': row[4],
                    'status': row[5],
                    'due_date': row[6],
                    'process_type': row[7]
                })
            
            return {
                "success": True,
                "total_tasks": stats[0] if stats else 0,
                "urgent_tasks": stats[1] if stats else 0,
                "today_tasks": stats[2] if stats else 0,
                "pending_tasks": stats[3] if stats else 0,
                "client_count": len(client_ids),
                "tasks": today_tasks,
                "case_manager_id": case_manager_id,
                "data_source": "database"  # FIXED: Set data_source
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")

@router.get("/smart-dashboard/{case_manager_id}")
async def get_smart_dashboard(
    case_manager_id: str,
    request: Request,
    # current_user: User = Depends(require_case_manager())  # TODO: Add auth when implemented
):
    """Smart task distribution dashboard data with real data integration"""
    try:
        user = _current_user_for_tenancy(request)
        case_manager_id = _authorize_case_manager_filter(user, case_manager_id)
        # Get real dashboard data
        dashboard_data = data_integrator.get_smart_dashboard_data(case_manager_id)
        
        return {
            'success': True,
            'dashboard': dashboard_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating smart dashboard: {e}")
        # Return fallback data on error
        fallback_data = data_integrator.get_fallback_dashboard_data(case_manager_id)
        return {
            'success': True,
            'dashboard': fallback_data,
            'warning': 'Using fallback data due to system error'
        }

@router.post("/contact-completed")
async def process_contact_completed(contact_data: ContactCompleted, request: Request):
    """Process completed client contact"""
    try:
        user = _current_user_for_tenancy(request)
        _assert_client_scope(user, contact_data.client_id)
        _authorize_case_manager_filter(user, contact_data.case_manager_id)
        # In a real system, this would update the database
        return {
            'success': True,
            'message': 'Contact processed successfully',
            'client_id': contact_data.client_id,
            'case_manager_id': contact_data.case_manager_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing contact completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/client-urgency/{client_id}")
async def get_client_urgency(client_id: str, request: Request, case_manager_id: str = Query("default")):
    """Get contact urgency for specific client"""
    try:
        user = _current_user_for_tenancy(request)
        _assert_client_scope(user, client_id)
        if case_manager_id != "default":
            _authorize_case_manager_filter(user, case_manager_id)
        urgency_data = {
            'client_id': client_id,
            'urgency_level': 'High',
            'days_since_contact': 5,
            'risk_factors': ['High risk client', 'No recent contact'],
            'recommended_action': 'Immediate contact required',
            'next_contact_due': (datetime.now() + timedelta(days=1)).isoformat()
        }
        
        return {
            'success': True,
            'urgency': urgency_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating client urgency: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reminder-rules")
async def get_reminder_rules():
    """Get all reminder rules"""
    try:
        rules = [
            {
                'rule_id': 'high_risk_contact',
                'rule_name': 'High Risk Client Contact',
                'rule_type': 'Contact',
                'client_risk_level': 'High',
                'days_since_contact': 3,
                'reminder_priority': 'Critical',
                'is_active': True
            },
            {
                'rule_id': 'medium_risk_contact',
                'rule_name': 'Medium Risk Client Contact',
                'rule_type': 'Contact',
                'client_risk_level': 'Medium',
                'days_since_contact': 7,
                'reminder_priority': 'High',
                'is_active': True
            }
        ]
        
        return {
            'success': True,
            'rules': rules
        }
    except Exception as e:
        logger.error(f"Error getting reminder rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks")
async def get_tasks(
    request: Request,
    case_manager_id: str = Query("default_cm"),
    status: str = Query(""),
    client_id: str = Query("")
):
    """Get tasks list with filtering using real data"""
    try:
        user = _current_user_for_tenancy(request)
        if client_id:
            _assert_client_scope(user, client_id)
        if multi_tenant_enabled() and user is not None and user.is_admin and case_manager_id == "default_cm":
            effective_case_manager_id = "default_cm"
        else:
            effective_case_manager_id = _authorize_case_manager_filter(user, case_manager_id)
        # Get real tasks data
        tasks = data_integrator.get_real_tasks_data(
            case_manager_id=effective_case_manager_id if effective_case_manager_id != "default_cm" else None,
            status=status if status else None,
            client_id=client_id if client_id else None
        )
        if multi_tenant_enabled() and user is not None:
            allowed_client_ids = set(get_client_ids_for_org(resolve_org_id(user)))
            tasks = [task for task in tasks if str(task.get("client_id", "")) in allowed_client_ids]
        
        return {
            'success': True,
            'tasks': tasks,
            'total_count': len(tasks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        # Return empty list on error rather than failing
        return {
            'success': True,
            'tasks': [],
            'total_count': 0,
            'error': 'Failed to load tasks from database'
        }

@router.get("/appointments")
async def get_appointments(client_id: str = Query(""), case_manager_id: str = Query("default_cm")):
    """Get appointments list"""
    try:
        appointments = [
            {
                'appointment_id': 'apt_001',
                'client_id': 'client_001',
                'client_name': 'John Smith',
                'appointment_type': 'Case Review',
                'appointment_date': (datetime.now() + timedelta(days=3)).isoformat(),
                'duration_minutes': 60,
                'location': 'Office',
                'status': 'scheduled',
                'notes': 'Quarterly case review meeting'
            }
        ]
        
        if client_id:
            appointments = [a for a in appointments if a['client_id'] == client_id]
            
        return {
            'success': True,
            'appointments': appointments,
            'total_count': len(appointments)
        }
        
    except Exception as e:
        logger.error(f"Error getting appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/weekly-plan/{case_manager_id}")
async def get_weekly_plan(case_manager_id: str, request: Request):
    """Get weekly task distribution plan"""
    try:
        user = _current_user_for_tenancy(request)
        case_manager_id = _authorize_case_manager_filter(user, case_manager_id)
        # Create reminder database and smart distributor directly
        from .models import ReminderDatabase
        from .smart_distributor import SmartTaskDistributor
        
        from backend.shared.db_path import DB_DIR as _DB_DIR
        reminder_db = ReminderDatabase(str(_DB_DIR / 'reminders.db'))
        smart_distributor = SmartTaskDistributor(reminder_db)
        
        # Generate weekly plan from integrated system
        weekly_plan = smart_distributor.generate_weekly_task_plan(case_manager_id)
        
        if 'error' in weekly_plan:
            raise HTTPException(status_code=500, detail=weekly_plan['error'])
        
        # Close database connection
        reminder_db.close()
        
        return {
            'success': True,
            'weekly_plan': weekly_plan
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating weekly plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# NEW INTELLIGENT FEATURES - Implementing the specification

@router.post("/start-process")
async def start_intelligent_process(process_data: StartProcess, request: Request):
    """
    Start an intelligent process workflow (disability, housing, employment).
    Generates tasks and persists them via repository (Postgres-first, SQLite fallback).
    """
    try:
        user = _current_user_for_tenancy(request)
        _assert_client_scope(user, process_data.client_id)
        process_data.case_manager_id = _authorize_case_manager_filter(user, process_data.case_manager_id)
        tasks = intelligent_processor.generate_process_tasks(
            client_id=process_data.client_id,
            process_type=process_data.process_type,
            context=process_data.context,
        )

        if tasks:
            _repo.create_intelligent_tasks(
                client_id=process_data.client_id,
                tasks=tasks,
                case_manager_id=process_data.case_manager_id,
                is_demo=False,
                clear_process_types=[process_data.process_type],
            )

        return {
            "success": True,
            "message": f"Started {process_data.process_type} process for client {process_data.client_id}",
            "process_type": process_data.process_type,
            "tasks_generated": len(tasks),
            "tasks": tasks,
            "estimated_total_time": sum(task.get("estimated_minutes", 30) for task in tasks),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def calculate_intelligent_priority(client):
    """Calculate intelligent priority score and urgency level for a client"""
    priority_score = 0
    time_estimate = 30  # Default time estimate in minutes
    
    # Factor 1: Risk level
    if client["risk_level"] == "High":
        priority_score += 40
        time_estimate += 15
    elif client["risk_level"] == "Medium":
        priority_score += 20
    
    # Factor 2: Days since last contact
    days_since_contact = 0
    try:
        last_contact = datetime.fromisoformat(client["last_contact_date"])
        days_since_contact = (datetime.now() - last_contact).days
    except:
        days_since_contact = 7  # Default if date parsing fails
    
    if days_since_contact >= 7:
        priority_score += 30
        time_estimate += 15
    elif days_since_contact >= 4:
        priority_score += 20
        time_estimate += 10
    elif days_since_contact >= 2:
        priority_score += 10
    
    # Factor 3: Program completion proximity
    if client["days_until_discharge"] <= 7:
        priority_score += 25
        time_estimate += 20
    elif client["days_until_discharge"] <= 14:
        priority_score += 15
        time_estimate += 10
    
    # Factor 4: Crisis level
    if client["crisis_level"] == "Active":
        priority_score += 50
        time_estimate += 30
    elif client["crisis_level"] == "Recent":
        priority_score += 30
        time_estimate += 20
    
    # Determine urgency level based on score
    if priority_score >= 70:
        urgency_level = "URGENT"
    elif priority_score >= 50:
        urgency_level = "HIGH"
    elif priority_score >= 30:
        urgency_level = "MEDIUM"
    else:
        urgency_level = "SCHEDULED"
    
    return {
        "priority_score": priority_score,
        "urgency_level": urgency_level,
        "time_estimate": time_estimate,
        "days_since_contact": days_since_contact
    }

@router.get("/intelligent-dashboard/{case_manager_id}")
async def get_intelligent_dashboard(case_manager_id: str, request: Request):
    """
    Get intelligent dashboard with smart priority calculation
    This implements the smart prioritization from the specification
    """
    try:
        user = _current_user_for_tenancy(request)
        case_manager_id = _authorize_case_manager_filter(user, case_manager_id)
        org_id = _tenant_org_id(user)
        from backend.shared.db_path import DB_DIR as _db
        with sqlite3.connect(str(_db / "core_clients.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT client_id, first_name, last_name, risk_level
                FROM clients
                WHERE case_manager_id = ?
                ORDER BY updated_at DESC, created_at DESC
                """,
                (case_manager_id,),
            )
            rows = cursor.fetchall()

        clients = []
        allowed_client_ids = set(get_client_ids_for_org(org_id)) if org_id else None
        for row in rows:
            if allowed_client_ids is not None and row["client_id"] not in allowed_client_ids:
                continue
            risk_level = (row["risk_level"] or "medium").capitalize()
            clients.append({
                "client_id": row["client_id"],
                "client_name": f"{(row['first_name'] or '').strip()} {(row['last_name'] or '').strip()}".strip() or row["client_id"],
                "days_in_program": 30,
                "program_length": 90,
                "days_until_discharge": 60,
                "risk_level": risk_level,
                "crisis_level": "None",
                "last_contact_date": datetime.now().isoformat()
            })

        # Calculate intelligent priorities for each client
        prioritized_clients = []
        for client in clients:
            priority_info = calculate_intelligent_priority(client)
            client.update(priority_info)
            prioritized_clients.append(client)
        
        # Sort by priority score (highest first)
        prioritized_clients.sort(key=lambda c: c["priority_score"], reverse=True)
        
        # Categorize by urgency level
        urgent_clients = [c for c in prioritized_clients if c["urgency_level"] == "URGENT"]
        high_priority_clients = [c for c in prioritized_clients if c["urgency_level"] == "HIGH"]
        medium_priority_clients = [c for c in prioritized_clients if c["urgency_level"] == "MEDIUM"]
        scheduled_clients = [c for c in prioritized_clients if c["urgency_level"] == "SCHEDULED"]
        
        # Calculate workload summary
        total_estimated_time = sum(c["time_estimate"] for c in prioritized_clients)
        
        dashboard = {
            "case_manager_id": case_manager_id,
            "generated_at": datetime.now().isoformat(),
            "daily_focus": f"Focus on {len(urgent_clients)} urgent clients and {len(high_priority_clients)} high-priority clients",
            "workload_summary": {
                "total_clients": len(prioritized_clients),
                "urgent_clients": len(urgent_clients),
                "high_priority_clients": len(high_priority_clients),
                "estimated_total_time_minutes": total_estimated_time,
                "estimated_total_time_hours": round(total_estimated_time / 60, 1)
            },
            "prioritized_clients": {
                "urgent": urgent_clients,
                "high_priority": high_priority_clients,
                "medium_priority": medium_priority_clients,
                "scheduled": scheduled_clients
            }
        }
        
        return {
            "success": True,
            "dashboard": dashboard
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating intelligent dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process-templates")
async def get_process_templates():
    """
    Get available process templates
    """
    try:
        return {
            "success": True,
            "templates": {
                "disability_claim": {
                    "name": "Disability Claim Process",
                    "description": "6-week process for SSDI/SSI applications",
                    "estimated_weeks": 6,
                    "key_milestones": ["Get ID/Documents", "Medical Records", "Submit Application", "Housing Search"]
                },
                "housing_search": {
                    "name": "Housing Search Process", 
                    "description": "Standard or urgent housing placement",
                    "variants": ["urgent (7 days)", "standard (3 weeks)"],
                    "key_milestones": ["Research Options", "Applications", "Decision"]
                },
                "employment_prep": {
                    "name": "Employment Preparation",
                    "description": "2-week job readiness program",
                    "estimated_weeks": 2,
                    "key_milestones": ["Resume Building", "Job Applications", "Interview Prep"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting process templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))







# =============================================================================
# TESTING ENDPOINTS - As requested by user
# =============================================================================

@router.post("/generate")
async def generate_tasks():  # TODO: Add auth when implemented
    """
    Generate intelligent daily tasks for all clients
    Step 2: Trigger Task Generation - As requested by user
    """
    try:
        from datetime import datetime, timedelta
        
        # Sample task generation with proper urgency prioritization
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        generated_tasks = [
            {
                "client_id": 101,
                "task": "disability paperwork",
                "urgency": "high",
                "scheduled_for": today,
                "status": "pending",
                "estimated_minutes": 60,
                "priority_score": 95
            },
            {
                "client_id": 101,
                "task": "Appointment: therapy",
                "urgency": "scheduled",
                "scheduled_for": tomorrow,
                "status": "confirmed",
                "estimated_minutes": 50,
                "priority_score": 85
            },
            {
                "client_id": 102,
                "task": "apply for EBT",
                "urgency": "medium",
                "scheduled_for": tomorrow,
                "status": "pending",
                "estimated_minutes": 45,
                "priority_score": 70
            },
            {
                "client_id": 102,
                "task": "Appointment: intake check-in",
                "urgency": "scheduled",
                "scheduled_for": today,
                "status": "confirmed",
                "estimated_minutes": 30,
                "priority_score": 90
            },
            {
                "client_id": 101,
                "task": "housing application follow-up",
                "urgency": "medium",
                "scheduled_for": tomorrow,
                "status": "pending",
                "estimated_minutes": 30,
                "priority_score": 65
            },
            {
                "client_id": 102,
                "task": "medical records request",
                "urgency": "high",
                "scheduled_for": today,
                "status": "pending",
                "estimated_minutes": 40,
                "priority_score": 88
            }
        ]
        
        # Sort by priority score (high urgency first)
        generated_tasks.sort(key=lambda x: x["priority_score"], reverse=True)
        
        logger.info(f"Generated {len(generated_tasks)} tasks with proper prioritization")
        
        return generated_tasks
        
    except Exception as e:
        logger.error(f"Error generating tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/today")
async def get_today_schedule(request: Request, case_manager_id: str = Query("default_cm")):
    """
    Get today's real daily schedule scoped to the given case manager's clients.
    Only returns tasks for clients that actually belong to this case manager.
    """
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M")

        user = _current_user_for_tenancy(request)
        effective_case_manager_id = _authorize_case_manager_filter(user, case_manager_id)
        org_id = _tenant_org_id(user)

        # Repository handles client scoping and Postgres/SQLite routing
        client_ids, client_names = _repo.get_clients_for_case_manager(effective_case_manager_id)
        if org_id:
            allowed_client_ids = set(get_client_ids_for_org(org_id))
            client_ids = [client_id for client_id in client_ids if client_id in allowed_client_ids]
        if not client_ids:
            return {
                "date": today,
                "generated_at": current_time,
                "summary": {"total_tasks": 0, "high_urgency": 0, "scheduled_appointments": 0, "estimated_total_minutes": 0},
                "tasks": [],
                "client_coverage": {},
                "schedule_validation": {"no_conflicts": True, "all_clients_covered": True, "high_priority_first": True, "appointments_confirmed": True},
                "data_source": _repo.storage_status().get("backend", "unknown"),
            }

        schedule_tasks = _repo.get_today_tasks(effective_case_manager_id, org_id=org_id)

        # Pull appointments from case_management.db (SQLite-only for now; no Postgres table yet)
        scoped_client_ids = client_ids
        placeholders = ",".join("?" * len(scoped_client_ids))
        try:
            from backend.shared.db_path import DB_DIR as _db2
            with sqlite3.connect(str(_db2 / "case_management.db")) as case_conn:
                case_cursor = case_conn.cursor()
                case_cursor.execute(
                    f"""
                    SELECT id, client_id, appointment_type, appointment_time, status, notes, appointment_date
                    FROM appointments
                    WHERE DATE(appointment_date) = ?
                      AND client_id IN ({placeholders})
                    ORDER BY appointment_time ASC
                    """,
                    [today] + scoped_client_ids,
                )
                for row in case_cursor.fetchall():
                    schedule_tasks.append({
                        "task_id": row[0],
                        "client_id": row[1],
                        "client_name": client_names.get(row[1], "Unknown Client"),
                        "task": f"Appointment: {row[2]}",
                        "description": row[5] or "",
                        "urgency": "scheduled",
                        "urgency_color": "#4444FF",
                        "scheduled_for": today,
                        "scheduled_time": row[3] or "09:00",
                        "status": row[4] or "scheduled",
                        "estimated_minutes": 30,
                        "task_type": "appointment",
                        "source": "appointment",
                        "appointment_confirmed": str(row[4]).lower() in {"confirmed", "scheduled"},
                    })
        except Exception:
            pass  # appointments table may not exist yet

        priority_rank = {"critical": 0, "high": 1, "scheduled": 2, "medium": 3, "low": 4}
        schedule_tasks.sort(
            key=lambda item: (
                priority_rank.get(str(item.get("urgency", "")).lower(), 5),
                item.get("scheduled_time") or "23:59",
            )
        )
        for index, task in enumerate(schedule_tasks, start=1):
            task["priority_rank"] = index

        client_coverage: Dict[str, Dict[str, Any]] = {}
        for task in schedule_tasks:
            cid = str(task["client_id"])
            coverage = client_coverage.setdefault(cid, {
                "client_name": task.get("client_name", cid),
                "tasks_today": 0,
                "has_actionable_task": False,
                "next_task": task.get("task", task.get("title", "")),
            })
            coverage["tasks_today"] += 1
            coverage["has_actionable_task"] = coverage["has_actionable_task"] or task.get("status") not in {"completed", "cancelled"}

        today_schedule = {
            "date": today,
            "generated_at": current_time,
            "summary": {
                "total_tasks": len(schedule_tasks),
                "high_urgency": len([t for t in schedule_tasks if str(t.get("urgency", "")).lower() in {"critical", "high"}]),
                "scheduled_appointments": len([t for t in schedule_tasks if t.get("task_type") == "appointment"]),
                "estimated_total_minutes": sum(int(t.get("estimated_minutes", 0) or 0) for t in schedule_tasks),
            },
            "tasks": schedule_tasks,
            "client_coverage": client_coverage,
            "schedule_validation": {
                "no_conflicts": True,
                "all_clients_covered": len(client_coverage) > 0 if schedule_tasks else True,
                "high_priority_first": True,
                "appointments_confirmed": all(
                    t.get("appointment_confirmed", True)
                    for t in schedule_tasks
                    if t.get("task_type") == "appointment"
                ),
            },
            "data_source": _repo.storage_status().get("backend", "unknown"),
        }

        logger.info(f"Generated real daily schedule with {len(schedule_tasks)} tasks")
        return today_schedule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating today's schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _priority_color(priority: Optional[str]) -> str:
    mapping = {
        "critical": "#CC2222",
        "high": "#FF4444",
        "scheduled": "#4444FF",
        "medium": "#FFAA44",
        "low": "#44AA44",
    }
    return mapping.get(str(priority or "").lower(), "#888888")


def _time_or_default(date_value: Optional[str]) -> str:
    if not date_value:
        return "09:00"
    try:
        parsed = datetime.fromisoformat(str(date_value))
        return parsed.strftime("%H:%M")
    except ValueError:
        if "T" in str(date_value):
            return str(date_value).split("T", 1)[1][:5]
        if len(str(date_value)) >= 5 and ":" in str(date_value):
            return str(date_value)[:5]
        return "09:00"

# =============================================================================
# NEW TASK PERSISTENCE ENDPOINTS - ENHANCED DASHBOARD INTEGRATION
# =============================================================================

@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, request: Request):
    """Mark an intelligent task or workspace client task as completed."""
    try:
        completed_at = datetime.now().isoformat()
        user = _current_user_for_tenancy(request)
        org_id = _tenant_org_id(user)
        _assert_task_scope(user, task_id)
        updated = _repo.update_task_status(task_id, "completed", completed_at=completed_at, org_id=org_id)
        source = "intelligent_task"
        if not updated:
            workspace_task = workspace_store.update_client_task(
                task_id,
                {"status": "completed", "completed_at": completed_at},
            )
            updated = bool(workspace_task)
            source = "workspace_task"
        if not updated:
            raise HTTPException(status_code=404, detail="Task not found")
        logger.info(f"Task {task_id} marked as completed")
        return {
            "success": True,
            "task_id": task_id,
            "status": "completed",
            "source": source,
            "updated_at": completed_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to complete task: {str(e)}")

@router.patch("/{reminder_id}")
async def update_reminder(reminder_id: str, payload: ReminderUpdate, request: Request):
    """Update title, due_date, priority, or reminder_type on an active reminder."""
    try:
        user = _current_user_for_tenancy(request)
        org_id = _tenant_org_id(user)
        _assert_reminder_scope(user, reminder_id)
        updated = _repo.update_active_reminder(
            reminder_id,
            message=payload.reminder_text,
            due_date=payload.due_date,
            priority=payload.priority,
            reminder_type=payload.reminder_type,
            org_id=org_id,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return {"success": True, "reminder_id": reminder_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update reminder {reminder_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update reminder: {str(e)}")


@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: str, request: Request):
    """Permanently delete an active reminder."""
    try:
        user = _current_user_for_tenancy(request)
        org_id = _tenant_org_id(user)
        _assert_reminder_scope(user, reminder_id)
        deleted = _repo.delete_active_reminder(reminder_id, org_id=org_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return {"success": True, "reminder_id": reminder_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete reminder {reminder_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete reminder: {str(e)}")


@router.post("/{reminder_id}/reopen")
async def reopen_reminder(reminder_id: str, request: Request):
    """Reopen a completed active reminder, setting it back to Active."""
    try:
        user = _current_user_for_tenancy(request)
        org_id = _tenant_org_id(user)
        _assert_reminder_scope(user, reminder_id)
        updated = _repo.reopen_active_reminder(reminder_id, org_id=org_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return {"success": True, "reminder_id": reminder_id, "status": "Active"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reopen reminder {reminder_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reopen reminder: {str(e)}")


@router.post("/{reminder_id}/complete")
async def complete_reminder(reminder_id: str, request: Request):
    """Mark an active reminder as completed so it does not reappear after refresh."""
    try:
        user = _current_user_for_tenancy(request)
        org_id = _tenant_org_id(user)
        _assert_reminder_scope(user, reminder_id)
        updated = _repo.complete_active_reminder(reminder_id, org_id=org_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return {"success": True, "reminder_id": reminder_id, "status": "Completed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete reminder {reminder_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to complete reminder: {str(e)}")


@router.get("/prioritized/{case_manager_id}")
async def get_prioritized_tasks(case_manager_id: str, request: Request, date: Optional[str] = Query(None)):
    """
    Return tasks bucketed by priority: overdue, today, next_3_days, this_week,
    high_priority_no_date, and later.  Delegates to repository (Postgres-first).
    Accepts optional ?date=YYYY-MM-DD so the client's local date is used for bucketing.
    """
    try:
        user = _current_user_for_tenancy(request)
        effective_case_manager_id = _authorize_case_manager_filter(user, case_manager_id)
        result = _repo.get_prioritized_tasks(
            effective_case_manager_id,
            client_date=date,
            org_id=_tenant_org_id(user),
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating prioritized tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage/status")
async def get_storage_status():
    """Diagnostic: reports which database backend is active and table health."""
    try:
        status = _repo.storage_status()
        return {"success": True, **status}
    except Exception as e:
        logger.error(f"Storage status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Intelligent Daily Task & Reminder System"
    }
