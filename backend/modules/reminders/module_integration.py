#!/usr/bin/env python3
"""
Module Integration for Real-time Reminder Generation
Creates reminders automatically when events occur in other modules
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .models import ReminderDatabase, ActiveReminder, ProgramMilestone

logger = logging.getLogger(__name__)

class ModuleIntegrationManager:
    """Manages integration between modules and reminders system"""
    
    def __init__(self):
        self.reminder_db = ReminderDatabase()
        self.case_mgmt_db_path = 'databases/case_management.db'
    
    def create_housing_reminder(self, client_id: str, event_type: str, event_data: Dict[str, Any]):
        """Create reminders based on housing module events"""
        try:
            case_manager_id = self.get_client_case_manager(client_id)
            client_name = self.get_client_name(client_id)
            
            if event_type == "application_submitted":
                # Create follow-up reminder for 2 weeks
                due_date = datetime.now() + timedelta(days=14)
                message = f"Follow up on housing application for {client_name}"
                priority = "Medium"
                
            elif event_type == "application_approved":
                # Create move-in preparation reminder
                due_date = datetime.now() + timedelta(days=7)
                message = f"Prepare move-in documentation for {client_name}"
                priority = "High"
                
            elif event_type == "application_denied":
                # Create immediate follow-up reminder
                due_date = datetime.now() + timedelta(days=1)
                message = f"URGENT: Housing application denied for {client_name} - find alternatives"
                priority = "Critical"
                
            elif event_type == "waitlist_added":
                # Create monthly check-in reminder
                due_date = datetime.now() + timedelta(days=30)
                message = f"Check housing waitlist status for {client_name}"
                priority = "Low"
                
            elif event_type == "inspection_scheduled":
                # Create preparation reminder
                inspection_date = event_data.get('inspection_date')
                if inspection_date:
                    due_date = datetime.fromisoformat(inspection_date) - timedelta(days=2)
                    message = f"Prepare {client_name} for housing inspection on {inspection_date}"
                    priority = "High"
                else:
                    return
            
            else:
                return  # Unknown event type
            
            # Create the reminder
            reminder = ActiveReminder(
                client_id=client_id,
                case_manager_id=case_manager_id,
                reminder_type="Housing",
                message=message,
                priority=priority,
                due_date=due_date.isoformat(),
                status="Active"
            )
            
            self.save_reminder(reminder)
            logger.info(f"Created housing reminder for {client_name}: {message}")
            
        except Exception as e:
            logger.error(f"Error creating housing reminder: {e}")
    
    def create_benefits_reminder(self, client_id: str, event_type: str, event_data: Dict[str, Any]):
        """Create reminders based on benefits module events"""
        try:
            case_manager_id = self.get_client_case_manager(client_id)
            client_name = self.get_client_name(client_id)
            
            if event_type == "application_started":
                # Create completion reminder
                due_date = datetime.now() + timedelta(days=7)
                message = f"Complete benefits application for {client_name}"
                priority = "High"
                
            elif event_type == "documentation_needed":
                # Create urgent documentation reminder
                due_date = datetime.now() + timedelta(days=3)
                message = f"Gather required documentation for {client_name} benefits application"
                priority = "High"
                
            elif event_type == "interview_scheduled":
                # Create preparation reminder
                interview_date = event_data.get('interview_date')
                if interview_date:
                    due_date = datetime.fromisoformat(interview_date) - timedelta(days=1)
                    message = f"Prepare {client_name} for benefits interview on {interview_date}"
                    priority = "High"
                else:
                    return
                    
            elif event_type == "benefits_approved":
                # Create follow-up reminder to ensure benefits are received
                due_date = datetime.now() + timedelta(days=14)
                message = f"Verify {client_name} is receiving approved benefits"
                priority = "Medium"
                
            elif event_type == "benefits_denied":
                # Create appeal reminder
                due_date = datetime.now() + timedelta(days=2)
                message = f"URGENT: Benefits denied for {client_name} - consider appeal process"
                priority = "Critical"
                
            elif event_type == "recertification_due":
                # Create recertification reminder
                due_date_str = event_data.get('due_date')
                if due_date_str:
                    due_date = datetime.fromisoformat(due_date_str) - timedelta(days=14)
                    message = f"Benefits recertification due for {client_name} - start process"
                    priority = "High"
                else:
                    return
            
            else:
                return  # Unknown event type
            
            # Create the reminder
            reminder = ActiveReminder(
                client_id=client_id,
                case_manager_id=case_manager_id,
                reminder_type="Benefits",
                message=message,
                priority=priority,
                due_date=due_date.isoformat(),
                status="Active"
            )
            
            self.save_reminder(reminder)
            logger.info(f"Created benefits reminder for {client_name}: {message}")
            
        except Exception as e:
            logger.error(f"Error creating benefits reminder: {e}")
    
    def create_legal_reminder(self, client_id: str, event_type: str, event_data: Dict[str, Any]):
        """Create reminders based on legal module events"""
        try:
            case_manager_id = self.get_client_case_manager(client_id)
            client_name = self.get_client_name(client_id)
            
            if event_type == "court_date_scheduled":
                # Create preparation reminder
                court_date = event_data.get('court_date')
                if court_date:
                    due_date = datetime.fromisoformat(court_date) - timedelta(days=7)
                    message = f"Prepare {client_name} for court date on {court_date}"
                    priority = "Critical"
                else:
                    return
                    
            elif event_type == "document_deadline":
                # Create document preparation reminder
                deadline = event_data.get('deadline')
                if deadline:
                    due_date = datetime.fromisoformat(deadline) - timedelta(days=3)
                    message = f"Legal documents due for {client_name} by {deadline}"
                    priority = "High"
                else:
                    return
                    
            elif event_type == "expungement_started":
                # Create follow-up reminder
                due_date = datetime.now() + timedelta(days=30)
                message = f"Follow up on expungement process for {client_name}"
                priority = "Medium"
                
            elif event_type == "attorney_meeting_scheduled":
                # Create preparation reminder
                meeting_date = event_data.get('meeting_date')
                if meeting_date:
                    due_date = datetime.fromisoformat(meeting_date) - timedelta(days=1)
                    message = f"Prepare {client_name} for attorney meeting on {meeting_date}"
                    priority = "High"
                else:
                    return
                    
            elif event_type == "case_resolved":
                # Create follow-up reminder to update records
                due_date = datetime.now() + timedelta(days=3)
                message = f"Update legal case resolution for {client_name}"
                priority = "Medium"
            
            else:
                return  # Unknown event type
            
            # Create the reminder
            reminder = ActiveReminder(
                client_id=client_id,
                case_manager_id=case_manager_id,
                reminder_type="Legal",
                message=message,
                priority=priority,
                due_date=due_date.isoformat(),
                status="Active"
            )
            
            self.save_reminder(reminder)
            logger.info(f"Created legal reminder for {client_name}: {message}")
            
        except Exception as e:
            logger.error(f"Error creating legal reminder: {e}")
    
    def create_employment_reminder(self, client_id: str, event_type: str, event_data: Dict[str, Any]):
        """Create reminders based on employment/jobs module events"""
        try:
            case_manager_id = self.get_client_case_manager(client_id)
            client_name = self.get_client_name(client_id)
            
            if event_type == "job_application_submitted":
                # Create follow-up reminder
                due_date = datetime.now() + timedelta(days=7)
                message = f"Follow up on job application for {client_name}"
                priority = "Medium"
                
            elif event_type == "interview_scheduled":
                # Create preparation reminder
                interview_date = event_data.get('interview_date')
                if interview_date:
                    due_date = datetime.fromisoformat(interview_date) - timedelta(days=1)
                    message = f"Prepare {client_name} for job interview on {interview_date}"
                    priority = "High"
                else:
                    return
                    
            elif event_type == "job_offer_received":
                # Create decision support reminder
                due_date = datetime.now() + timedelta(days=2)
                message = f"Help {client_name} evaluate job offer and make decision"
                priority = "High"
                
            elif event_type == "employment_started":
                # Create check-in reminder
                due_date = datetime.now() + timedelta(days=14)
                message = f"Check in with {client_name} on new job progress"
                priority = "Medium"
                
            elif event_type == "resume_needs_update":
                # Create resume update reminder
                due_date = datetime.now() + timedelta(days=3)
                message = f"Update resume for {client_name}"
                priority = "Medium"
                
            elif event_type == "skills_assessment_due":
                # Create assessment reminder
                due_date = datetime.now() + timedelta(days=7)
                message = f"Complete skills assessment for {client_name}"
                priority = "Medium"
            
            else:
                return  # Unknown event type
            
            # Create the reminder
            reminder = ActiveReminder(
                client_id=client_id,
                case_manager_id=case_manager_id,
                reminder_type="Employment",
                message=message,
                priority=priority,
                due_date=due_date.isoformat(),
                status="Active"
            )
            
            self.save_reminder(reminder)
            logger.info(f"Created employment reminder for {client_name}: {message}")
            
        except Exception as e:
            logger.error(f"Error creating employment reminder: {e}")
    
    def create_case_management_reminder(self, client_id: str, event_type: str, event_data: Dict[str, Any]):
        """Create reminders based on case management events"""
        try:
            case_manager_id = self.get_client_case_manager(client_id)
            client_name = self.get_client_name(client_id)
            
            if event_type == "client_intake_completed":
                # Create initial assessment reminder
                due_date = datetime.now() + timedelta(days=3)
                message = f"Complete initial assessment for new client {client_name}"
                priority = "High"
                
            elif event_type == "risk_level_increased":
                # Create immediate contact reminder
                due_date = datetime.now() + timedelta(hours=24)
                message = f"URGENT: Risk level increased for {client_name} - immediate contact required"
                priority = "Critical"
                
            elif event_type == "missed_appointment":
                # Create follow-up reminder
                due_date = datetime.now() + timedelta(days=1)
                message = f"Follow up with {client_name} - missed appointment"
                priority = "High"
                
            elif event_type == "program_milestone_approaching":
                # Create milestone preparation reminder
                milestone_date = event_data.get('milestone_date')
                milestone_name = event_data.get('milestone_name', 'Program milestone')
                if milestone_date:
                    due_date = datetime.fromisoformat(milestone_date) - timedelta(days=5)
                    message = f"Prepare {milestone_name} for {client_name}"
                    priority = "Medium"
                else:
                    return
                    
            elif event_type == "case_review_due":
                # Create case review reminder
                due_date = datetime.now() + timedelta(days=2)
                message = f"Case review due for {client_name}"
                priority = "High"
            
            else:
                return  # Unknown event type
            
            # Create the reminder
            reminder = ActiveReminder(
                client_id=client_id,
                case_manager_id=case_manager_id,
                reminder_type="Case Management",
                message=message,
                priority=priority,
                due_date=due_date.isoformat(),
                status="Active"
            )
            
            self.save_reminder(reminder)
            logger.info(f"Created case management reminder for {client_name}: {message}")
            
        except Exception as e:
            logger.error(f"Error creating case management reminder: {e}")
    
    def process_module_event(self, module_name: str, client_id: str, event_type: str, event_data: Dict[str, Any] = None):
        """Main entry point for processing module events"""
        if event_data is None:
            event_data = {}
            
        try:
            if module_name == "housing":
                self.create_housing_reminder(client_id, event_type, event_data)
            elif module_name == "benefits":
                self.create_benefits_reminder(client_id, event_type, event_data)
            elif module_name == "legal":
                self.create_legal_reminder(client_id, event_type, event_data)
            elif module_name == "employment" or module_name == "jobs":
                self.create_employment_reminder(client_id, event_type, event_data)
            elif module_name == "case_management":
                self.create_case_management_reminder(client_id, event_type, event_data)
            else:
                logger.warning(f"Unknown module for reminder integration: {module_name}")
                
        except Exception as e:
            logger.error(f"Error processing module event: {e}")
    
    def get_client_case_manager(self, client_id: str) -> str:
        """Get case manager ID for a client"""
        try:
            conn = sqlite3.connect(self.case_mgmt_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT case_manager_id FROM clients 
                WHERE client_id = ? AND is_active = 1
            """, (client_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result and result[0] else 'default_cm'
            
        except Exception as e:
            logger.error(f"Error getting client case manager: {e}")
            return 'default_cm'
    
    def get_client_name(self, client_id: str) -> str:
        """Get client name"""
        try:
            conn = sqlite3.connect(self.case_mgmt_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT first_name || ' ' || last_name as client_name
                FROM clients 
                WHERE client_id = ?
            """, (client_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else 'Unknown Client'
            
        except Exception as e:
            logger.error(f"Error getting client name: {e}")
            return 'Unknown Client'
    
    def save_reminder(self, reminder: ActiveReminder):
        """Save reminder to database"""
        try:
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                INSERT INTO active_reminders (
                    reminder_id, client_id, case_manager_id, reminder_type,
                    message, priority, due_date, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reminder.reminder_id, reminder.client_id, reminder.case_manager_id,
                reminder.reminder_type, reminder.message, reminder.priority,
                reminder.due_date, reminder.status, reminder.created_at
            ))
            self.reminder_db.connection.commit()
        except Exception as e:
            logger.error(f"Error saving reminder: {e}")
    
    def create_task_from_reminder(self, reminder_id: str, estimated_minutes: int = 60):
        """Convert a reminder into a task in the case management system"""
        try:
            # Get reminder details
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                SELECT client_id, case_manager_id, reminder_type, message, priority, due_date
                FROM active_reminders 
                WHERE reminder_id = ? AND status = 'Active'
            """, (reminder_id,))
            
            reminder_data = cursor.fetchone()
            if not reminder_data:
                return False
            
            client_id, case_manager_id, reminder_type, message, priority, due_date = reminder_data
            
            # Create task in case management database
            conn = sqlite3.connect(self.case_mgmt_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tasks (
                    client_id, title, description, due_date, priority, status,
                    category, assigned_to, created_by, task_type, ai_generated,
                    auto_generated, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id,
                message,
                f"Task created from {reminder_type} reminder",
                due_date,
                priority,
                'pending',
                reminder_type.lower(),
                case_manager_id,
                'reminder_system',
                reminder_type.lower(),
                1,  # ai_generated
                1,  # auto_generated
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # Mark reminder as converted
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                UPDATE active_reminders 
                SET status = 'Converted to Task'
                WHERE reminder_id = ?
            """, (reminder_id,))
            self.reminder_db.connection.commit()
            
            logger.info(f"Converted reminder {reminder_id} to task")
            return True
            
        except Exception as e:
            logger.error(f"Error creating task from reminder: {e}")
            return False
    
    def close(self):
        """Close database connections"""
        if self.reminder_db:
            self.reminder_db.close()

# Global instance for easy access
_integration_manager = None

def get_integration_manager() -> ModuleIntegrationManager:
    """Get global integration manager instance"""
    global _integration_manager
    if _integration_manager is None:
        _integration_manager = ModuleIntegrationManager()
    return _integration_manager

def trigger_reminder_event(module_name: str, client_id: str, event_type: str, event_data: Dict[str, Any] = None):
    """Convenience function to trigger reminder events from other modules"""
    manager = get_integration_manager()
    manager.process_module_event(module_name, client_id, event_type, event_data)