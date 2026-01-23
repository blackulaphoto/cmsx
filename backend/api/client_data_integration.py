#!/usr/bin/env python3
"""
Client Data Integration - Real database integration for client overview
Fixes the empty notes/tasks issue by connecting to actual populated databases
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)

class ClientDataIntegrator:
    """Integrates real data from all databases for client overview"""
    
    def __init__(self):
        self.case_mgmt_db_path = 'databases/case_management.db'
        self.reminders_db_path = 'databases/reminders.db'
        
    def get_client_overview_data(self, client_id: str) -> Dict[str, Any]:
        """Get comprehensive client overview data from real databases"""
        try:
            overview_data = {
                "client_id": client_id,
                "tasks": self.get_real_client_tasks(client_id),
                "case_notes": self.get_real_case_notes(client_id),
                "appointments": self.get_real_appointments(client_id),
                "reminders": self.get_real_client_reminders(client_id),
                "recent_activity": self.get_recent_activity(client_id),
                "goals": self.get_client_goals(client_id),
                "barriers": self.get_client_barriers(client_id),
                "contact_history": self.get_contact_history(client_id),
                "program_milestones": self.get_program_milestones(client_id)
            }
            
            # Add summary statistics
            overview_data["summary"] = {
                "total_tasks": len(overview_data["tasks"]),
                "pending_tasks": len([t for t in overview_data["tasks"] if t.get("status") == "pending"]),
                "completed_tasks": len([t for t in overview_data["tasks"] if t.get("status") == "completed"]),
                "total_notes": len(overview_data["case_notes"]),
                "upcoming_appointments": len([a for a in overview_data["appointments"] if a.get("status") == "scheduled"]),
                "active_reminders": len([r for r in overview_data["reminders"] if r.get("status") == "Active"]),
                "last_contact": self.get_last_contact_date(client_id)
            }
            
            return overview_data
            
        except Exception as e:
            logger.error(f"Error getting client overview data: {e}")
            return self.get_fallback_overview_data(client_id)
    
    def get_real_client_tasks(self, client_id: str) -> List[Dict[str, Any]]:
        """Get real tasks for client from case management database"""
        try:
            conn = sqlite3.connect(self.case_mgmt_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    task_id,
                    title,
                    description,
                    due_date,
                    priority,
                    status,
                    category,
                    assigned_to,
                    created_by,
                    task_type,
                    created_at,
                    updated_at,
                    completed_at
                FROM tasks 
                WHERE client_id = ?
                ORDER BY 
                    CASE priority 
                        WHEN 'Critical' THEN 1
                        WHEN 'High' THEN 2
                        WHEN 'Medium' THEN 3
                        ELSE 4
                    END,
                    due_date ASC
            """, (client_id,))
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'task_id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'due_date': row[3],
                    'priority': row[4],
                    'status': row[5],
                    'category': row[6],
                    'assigned_to': row[7],
                    'created_by': row[8],
                    'task_type': row[9],
                    'created_at': row[10],
                    'updated_at': row[11],
                    'completed_at': row[12],
                    'is_overdue': self.is_task_overdue(row[3], row[5])
                })
            
            conn.close()
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting real client tasks: {e}")
            return []
    
    def get_real_case_notes(self, client_id: str) -> List[Dict[str, Any]]:
        """Get real case notes for client"""
        try:
            conn = sqlite3.connect(self.case_mgmt_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    note_id,
                    note_text,
                    note_type,
                    created_by,
                    created_at,
                    is_private,
                    tags
                FROM case_notes 
                WHERE client_id = ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (client_id,))
            
            notes = []
            for row in cursor.fetchall():
                notes.append({
                    'note_id': row[0],
                    'note_text': row[1],
                    'note_type': row[2],
                    'created_by': row[3],
                    'created_at': row[4],
                    'is_private': bool(row[5]),
                    'tags': row[6].split(',') if row[6] else [],
                    'formatted_date': self.format_date(row[4])
                })
            
            conn.close()
            return notes
            
        except Exception as e:
            logger.error(f"Error getting real case notes: {e}")
            return []
    
    def get_real_appointments(self, client_id: str) -> List[Dict[str, Any]]:
        """Get real appointments for client"""
        try:
            conn = sqlite3.connect(self.case_mgmt_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    appointment_id,
                    appointment_date,
                    appointment_time,
                    appointment_type,
                    status,
                    location,
                    notes,
                    created_by,
                    created_at
                FROM appointments 
                WHERE client_id = ?
                ORDER BY appointment_date DESC, appointment_time DESC
                LIMIT 20
            """, (client_id,))
            
            appointments = []
            for row in cursor.fetchall():
                appointments.append({
                    'appointment_id': row[0],
                    'appointment_date': row[1],
                    'appointment_time': row[2],
                    'appointment_type': row[3],
                    'status': row[4],
                    'location': row[5],
                    'notes': row[6],
                    'created_by': row[7],
                    'created_at': row[8],
                    'is_upcoming': self.is_appointment_upcoming(row[1], row[2])
                })
            
            conn.close()
            return appointments
            
        except Exception as e:
            logger.error(f"Error getting real appointments: {e}")
            return []
    
    def get_real_client_reminders(self, client_id: str) -> List[Dict[str, Any]]:
        """Get real reminders for client from reminders database"""
        try:
            conn = sqlite3.connect(self.reminders_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    reminder_id,
                    reminder_type,
                    message,
                    priority,
                    due_date,
                    status,
                    created_at,
                    case_manager_id
                FROM active_reminders 
                WHERE client_id = ?
                ORDER BY 
                    CASE priority 
                        WHEN 'Critical' THEN 1
                        WHEN 'High' THEN 2
                        WHEN 'Medium' THEN 3
                        ELSE 4
                    END,
                    due_date ASC
            """, (client_id,))
            
            reminders = []
            for row in cursor.fetchall():
                reminders.append({
                    'reminder_id': row[0],
                    'reminder_type': row[1],
                    'message': row[2],
                    'priority': row[3],
                    'due_date': row[4],
                    'status': row[5],
                    'created_at': row[6],
                    'case_manager_id': row[7],
                    'is_overdue': self.is_reminder_overdue(row[4])
                })
            
            conn.close()
            return reminders
            
        except Exception as e:
            logger.error(f"Error getting real client reminders: {e}")
            return []
    
    def get_recent_activity(self, client_id: str) -> List[Dict[str, Any]]:
        """Get recent activity for client across all systems"""
        activities = []
        
        try:
            # Get recent tasks
            tasks = self.get_real_client_tasks(client_id)
            for task in tasks[:5]:  # Last 5 tasks
                activities.append({
                    'type': 'task',
                    'action': f"Task {task['status']}: {task['title']}",
                    'date': task['updated_at'] or task['created_at'],
                    'priority': task['priority'],
                    'category': task.get('category', 'general')
                })
            
            # Get recent notes
            notes = self.get_real_case_notes(client_id)
            for note in notes[:3]:  # Last 3 notes
                activities.append({
                    'type': 'note',
                    'action': f"Case note added: {note['note_type']}",
                    'date': note['created_at'],
                    'priority': 'Medium',
                    'category': 'documentation'
                })
            
            # Get recent reminders
            reminders = self.get_real_client_reminders(client_id)
            for reminder in reminders[:3]:  # Last 3 reminders
                activities.append({
                    'type': 'reminder',
                    'action': f"Reminder created: {reminder['reminder_type']}",
                    'date': reminder['created_at'],
                    'priority': reminder['priority'],
                    'category': 'reminder'
                })
            
            # Sort by date
            activities.sort(key=lambda x: x['date'] or '', reverse=True)
            return activities[:10]  # Return top 10 most recent
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []
    
    def get_contact_history(self, client_id: str) -> List[Dict[str, Any]]:
        """Get contact history from reminders database"""
        try:
            conn = sqlite3.connect(self.reminders_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    contact_id,
                    contact_date,
                    contact_type,
                    contact_method,
                    outcome,
                    notes,
                    case_manager_id,
                    created_at
                FROM client_contacts 
                WHERE client_id = ?
                ORDER BY contact_date DESC
                LIMIT 20
            """, (client_id,))
            
            contacts = []
            for row in cursor.fetchall():
                contacts.append({
                    'contact_id': row[0],
                    'contact_date': row[1],
                    'contact_type': row[2],
                    'contact_method': row[3],
                    'outcome': row[4],
                    'notes': row[5],
                    'case_manager_id': row[6],
                    'created_at': row[7],
                    'formatted_date': self.format_date(row[1])
                })
            
            conn.close()
            return contacts
            
        except Exception as e:
            logger.error(f"Error getting contact history: {e}")
            return []
    
    def get_program_milestones(self, client_id: str) -> List[Dict[str, Any]]:
        """Get program milestones from reminders database"""
        try:
            conn = sqlite3.connect(self.reminders_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    milestone_id,
                    milestone_name,
                    milestone_type,
                    target_date,
                    completion_date,
                    status,
                    description,
                    created_at
                FROM program_milestones 
                WHERE client_id = ?
                ORDER BY target_date ASC
            """, (client_id,))
            
            milestones = []
            for row in cursor.fetchall():
                milestones.append({
                    'milestone_id': row[0],
                    'milestone_name': row[1],
                    'milestone_type': row[2],
                    'target_date': row[3],
                    'completion_date': row[4],
                    'status': row[5],
                    'description': row[6],
                    'created_at': row[7],
                    'is_overdue': self.is_milestone_overdue(row[3], row[5])
                })
            
            conn.close()
            return milestones
            
        except Exception as e:
            logger.error(f"Error getting program milestones: {e}")
            return []
    
    def get_client_goals(self, client_id: str) -> List[Dict[str, Any]]:
        """Get client goals from case management database"""
        try:
            conn = sqlite3.connect(self.case_mgmt_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    goal_id,
                    goal_text,
                    goal_type,
                    target_date,
                    status,
                    progress_notes,
                    created_at
                FROM client_goals 
                WHERE client_id = ?
                ORDER BY created_at DESC
            """, (client_id,))
            
            goals = []
            for row in cursor.fetchall():
                goals.append({
                    'goal_id': row[0],
                    'goal_text': row[1],
                    'goal_type': row[2],
                    'target_date': row[3],
                    'status': row[4],
                    'progress_notes': row[5],
                    'created_at': row[6]
                })
            
            conn.close()
            return goals
            
        except Exception as e:
            logger.error(f"Error getting client goals: {e}")
            return []
    
    def get_client_barriers(self, client_id: str) -> List[Dict[str, Any]]:
        """Get client barriers from case management database"""
        try:
            conn = sqlite3.connect(self.case_mgmt_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    barrier_id,
                    barrier_text,
                    barrier_type,
                    severity,
                    status,
                    mitigation_plan,
                    created_at
                FROM client_barriers 
                WHERE client_id = ?
                ORDER BY severity DESC, created_at DESC
            """, (client_id,))
            
            barriers = []
            for row in cursor.fetchall():
                barriers.append({
                    'barrier_id': row[0],
                    'barrier_text': row[1],
                    'barrier_type': row[2],
                    'severity': row[3],
                    'status': row[4],
                    'mitigation_plan': row[5],
                    'created_at': row[6]
                })
            
            conn.close()
            return barriers
            
        except Exception as e:
            logger.error(f"Error getting client barriers: {e}")
            return []
    
    def get_last_contact_date(self, client_id: str) -> Optional[str]:
        """Get the date of last contact with client"""
        try:
            conn = sqlite3.connect(self.reminders_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT MAX(contact_date)
                FROM client_contacts 
                WHERE client_id = ?
            """, (client_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result and result[0] else None
            
        except Exception as e:
            logger.error(f"Error getting last contact date: {e}")
            return None
    
    # Helper methods
    def is_task_overdue(self, due_date: str, status: str) -> bool:
        """Check if task is overdue"""
        if not due_date or status in ['completed', 'cancelled']:
            return False
        try:
            due = datetime.fromisoformat(due_date)
            return due < datetime.now()
        except:
            return False
    
    def is_reminder_overdue(self, due_date: str) -> bool:
        """Check if reminder is overdue"""
        if not due_date:
            return False
        try:
            due = datetime.fromisoformat(due_date)
            return due < datetime.now()
        except:
            return False
    
    def is_appointment_upcoming(self, appointment_date: str, appointment_time: str) -> bool:
        """Check if appointment is upcoming"""
        if not appointment_date:
            return False
        try:
            appt_datetime = datetime.fromisoformat(f"{appointment_date} {appointment_time or '00:00:00'}")
            return appt_datetime > datetime.now()
        except:
            return False
    
    def is_milestone_overdue(self, target_date: str, status: str) -> bool:
        """Check if milestone is overdue"""
        if not target_date or status == 'completed':
            return False
        try:
            target = datetime.fromisoformat(target_date)
            return target < datetime.now()
        except:
            return False
    
    def format_date(self, date_str: str) -> str:
        """Format date for display"""
        if not date_str:
            return ""
        try:
            date_obj = datetime.fromisoformat(date_str)
            return date_obj.strftime("%B %d, %Y at %I:%M %p")
        except:
            return date_str
    
    def get_fallback_overview_data(self, client_id: str) -> Dict[str, Any]:
        """Fallback data when database queries fail"""
        return {
            "client_id": client_id,
            "tasks": [],
            "case_notes": [],
            "appointments": [],
            "reminders": [],
            "recent_activity": [],
            "goals": [],
            "barriers": [],
            "contact_history": [],
            "program_milestones": [],
            "summary": {
                "total_tasks": 0,
                "pending_tasks": 0,
                "completed_tasks": 0,
                "total_notes": 0,
                "upcoming_appointments": 0,
                "active_reminders": 0,
                "last_contact": None
            },
            "error": "Database connection failed - using fallback data"
        }

# Global instance
_client_data_integrator = None

def get_client_data_integrator() -> ClientDataIntegrator:
    """Get global client data integrator instance"""
    global _client_data_integrator
    if _client_data_integrator is None:
        _client_data_integrator = ClientDataIntegrator()
    return _client_data_integrator