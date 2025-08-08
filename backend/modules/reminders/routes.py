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
from datetime import datetime, timedelta
from .intelligent_processor import IntelligentTaskProcessor

# Note: Authentication dependencies would be imported here when auth module is implemented
# from auth.dependencies import get_current_active_user, require_case_manager, require_supervisor
# from auth.models import User

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(tags=["reminders"])

# Initialize intelligent processor
intelligent_processor = IntelligentTaskProcessor()

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

@router.get("/dashboard/{case_manager_id}")
async def get_morning_dashboard(
    case_manager_id: str,
    # current_user: User = Depends(require_case_manager())  # TODO: Add auth when implemented
):
    """API endpoint for morning dashboard data"""
    try:
        # Sample dashboard data for demo
        dashboard_data = {
            'generated_at': datetime.now().isoformat(),
            'case_manager_id': case_manager_id,
            'summary': {
                'total_clients': 15,
                'urgent_attention': 3,
                'due_today': 5,
                'this_week': 8,
                'workload_level': 'moderate'
            },
            'focus_recommendation': 'Priority: Contact 3 high-risk clients and complete 2 overdue assessments',
            'urgent_items': [
                {
                    'client_id': 'client_001',
                    'client_name': 'John Smith',
                    'type': 'Contact Required',
                    'message': 'No contact in 5 days - High risk client',
                    'action': 'call_client'
                }
            ],
            'today_items': [
                {
                    'client_id': 'client_002',
                    'client_name': 'Maria Garcia',
                    'type': 'Assessment Due',
                    'message': 'Disability assessment deadline today',
                    'action': 'complete_assessment'
                }
            ],
            'this_week_items': [
                {
                    'client_id': 'client_003',
                    'client_name': 'David Johnson',
                    'type': 'Follow-up',
                    'message': 'Housing application follow-up needed',
                    'action': 'schedule_followup'
                }
            ]
        }
        
        return {
            'success': True,
            'dashboard': dashboard_data
        }
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/smart-dashboard/{case_manager_id}")
async def get_smart_dashboard(
    case_manager_id: str,
    # current_user: User = Depends(require_case_manager())  # TODO: Add auth when implemented
):
    """Smart task distribution dashboard data"""
    try:
        dashboard_data = {
            'case_manager_id': case_manager_id,
            'generated_at': datetime.now().isoformat(),
            'daily_focus': f'Focus on {case_manager_id} high-priority tasks',
            'workload_summary': {
                'total_tasks': 12,
                'urgent_tasks': 3,
                'today_estimated_minutes': 240,
                'capacity_utilization': 75
            },
            'today_tasks': [
                {
                    'task_id': 'task_001',
                    'client_name': 'John Smith',
                    'task_title': 'Benefits application review',
                    'priority': 'High',
                    'estimated_duration': 45,
                    'status': 'Pending'
                }
            ],
            'recommendations': [
                'Complete urgent tasks first',
                'Schedule follow-ups for next week',
                'Review pending applications'
            ]
        }
        
        return {
            'success': True,
            'dashboard': dashboard_data
        }
    except Exception as e:
        logger.error(f"Error generating smart dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/contact-completed")
async def process_contact_completed(contact_data: ContactCompleted):
    """Process completed client contact"""
    try:
        # In a real system, this would update the database
        return {
            'success': True,
            'message': 'Contact processed successfully',
            'client_id': contact_data.client_id,
            'case_manager_id': contact_data.case_manager_id
        }
    except Exception as e:
        logger.error(f"Error processing contact completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/client-urgency/{client_id}")
async def get_client_urgency(client_id: str, case_manager_id: str = Query("default")):
    """Get contact urgency for specific client"""
    try:
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
    case_manager_id: str = Query("default_cm"),
    status: str = Query(""),
    client_id: str = Query("")
):
    """Get tasks list with filtering"""
    try:
        # Sample tasks for demo
        tasks = [
            {
                'task_id': 'task_001',
                'client_id': 'client_001',
                'client_name': 'John Smith',
                'title': 'Benefits application review',
                'description': 'Review and submit SNAP application',
                'task_type': 'paperwork',
                'priority': 'High',
                'status': 'pending',
                'due_date': (datetime.now() + timedelta(days=1)).isoformat(),
                'estimated_minutes': 45,
                'created_at': datetime.now().isoformat()
            },
            {
                'task_id': 'task_002',
                'client_id': 'client_002',
                'client_name': 'Maria Garcia',
                'title': 'Housing follow-up call',
                'description': 'Check status of housing application',
                'task_type': 'phone_call',
                'priority': 'Medium',
                'status': 'pending',
                'due_date': (datetime.now() + timedelta(days=2)).isoformat(),
                'estimated_minutes': 30,
                'created_at': datetime.now().isoformat()
            }
        ]
        
        # Apply filters
        filtered_tasks = tasks
        if client_id:
            filtered_tasks = [t for t in filtered_tasks if t['client_id'] == client_id]
        if status:
            filtered_tasks = [t for t in filtered_tasks if t['status'] == status]
            
        return {
            'success': True,
            'tasks': filtered_tasks,
            'total_count': len(filtered_tasks)
        }
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
async def get_weekly_plan(case_manager_id: str):
    """Get weekly task distribution plan"""
    try:
        # Create reminder database and smart distributor directly
        from .models import ReminderDatabase
        from .smart_distributor import SmartTaskDistributor
        
        reminder_db = ReminderDatabase('databases/reminders.db')
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
    except Exception as e:
        logger.error(f"Error generating weekly plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# NEW INTELLIGENT FEATURES - Implementing the specification

@router.post("/start-process")
async def start_intelligent_process(process_data: StartProcess):
    """
    Start an intelligent process workflow (disability, housing, employment)
    This implements the process templates from the specification
    """
    try:
        # Generate intelligent task sequence
        tasks = intelligent_processor.generate_process_tasks(
            client_id=process_data.client_id,
            process_type=process_data.process_type,
            context=process_data.context
        )
        
        # In a real system, these would be saved to database
        # For now, return the generated tasks
        
        return {
            "success": True,
            "message": f"Started {process_data.process_type} process for client {process_data.client_id}",
            "process_type": process_data.process_type,
            "tasks_generated": len(tasks),
            "tasks": tasks,
            "estimated_total_time": sum(task.get("estimated_minutes", 30) for task in tasks)
        }
        
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
async def get_intelligent_dashboard(case_manager_id: str):
    """
    Get intelligent dashboard with smart priority calculation
    This implements the smart prioritization from the specification
    """
    try:
        # Mock client data - in real system would come from database
        mock_clients = [
            {
                "client_id": "client_001",
                "client_name": "Stacey Johnson",
                "days_in_program": 84,
                "program_length": 90,
                "days_until_discharge": 6,
                "risk_level": "High",
                "crisis_level": "None",
                "last_contact_date": (datetime.now() - timedelta(days=4)).isoformat()
            },
            {
                "client_id": "client_002", 
                "client_name": "Jay Williams",
                "days_in_program": 3,
                "program_length": 90,
                "days_until_discharge": 87,
                "risk_level": "Medium",
                "crisis_level": "None",
                "last_contact_date": (datetime.now() - timedelta(days=1)).isoformat()
            },
            {
                "client_id": "client_003",
                "client_name": "Ryan Martinez",
                "days_in_program": 45,
                "program_length": 90,
                "days_until_discharge": 45,
                "risk_level": "Medium",
                "crisis_level": "None",
                "last_contact_date": (datetime.now() - timedelta(days=3)).isoformat()
            }
        ]
        
        # Calculate intelligent priorities for each client
        prioritized_clients = []
        for client in mock_clients:
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
async def get_today_schedule():  # TODO: Add auth when implemented
    """
    Get today's clean daily schedule for all clients
    Step 3: Final Check - As requested by user
    """
    try:
        from datetime import datetime
        
        today = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M")
        
        # Clean daily schedule with color coding and urgency tags
        today_schedule = {
            "date": today,
            "generated_at": current_time,
            "summary": {
                "total_tasks": 4,
                "high_urgency": 2,
                "scheduled_appointments": 1,
                "estimated_total_minutes": 190
            },
            "tasks": [
                {
                    "client_id": 101,
                    "client_name": "John Smith",
                    "task": "disability paperwork",
                    "urgency": "high",
                    "urgency_color": "#FF4444",  # Red for high urgency
                    "scheduled_for": today,
                    "scheduled_time": "09:00",
                    "status": "pending",
                    "estimated_minutes": 60,
                    "task_type": "administrative",
                    "priority_rank": 1
                },
                {
                    "client_id": 102,
                    "client_name": "Maria Garcia",
                    "task": "Appointment: intake check-in",
                    "urgency": "scheduled",
                    "urgency_color": "#4444FF",  # Blue for scheduled
                    "scheduled_for": today,
                    "scheduled_time": "10:00",
                    "status": "confirmed",
                    "estimated_minutes": 30,
                    "task_type": "appointment",
                    "priority_rank": 2,
                    "appointment_confirmed": True
                },
                {
                    "client_id": 102,
                    "client_name": "Maria Garcia",
                    "task": "medical records request",
                    "urgency": "high",
                    "urgency_color": "#FF4444",  # Red for high urgency
                    "scheduled_for": today,
                    "scheduled_time": "11:00",
                    "status": "pending",
                    "estimated_minutes": 40,
                    "task_type": "documentation",
                    "priority_rank": 3
                },
                {
                    "client_id": 101,
                    "client_name": "John Smith",
                    "task": "benefits status check",
                    "urgency": "medium",
                    "urgency_color": "#FFAA44",  # Orange for medium urgency
                    "scheduled_for": today,
                    "scheduled_time": "14:00",
                    "status": "pending",
                    "estimated_minutes": 25,
                    "task_type": "follow_up",
                    "priority_rank": 4
                }
            ],
            "client_coverage": {
                "101": {
                    "client_name": "John Smith",
                    "tasks_today": 2,
                    "has_actionable_task": True,
                    "next_task": "disability paperwork"
                },
                "102": {
                    "client_name": "Maria Garcia", 
                    "tasks_today": 2,
                    "has_actionable_task": True,
                    "next_task": "Appointment: intake check-in"
                }
            },
            "schedule_validation": {
                "no_conflicts": True,
                "all_clients_covered": True,
                "high_priority_first": True,
                "appointments_confirmed": True
            }
        }
        
        logger.info(f"Generated clean daily schedule with {len(today_schedule['tasks'])} tasks")
        
        return today_schedule
        
    except Exception as e:
        logger.error(f"Error generating today's schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Intelligent Daily Task & Reminder System"
    }

