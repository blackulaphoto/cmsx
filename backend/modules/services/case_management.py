#!/usr/bin/env python3
"""
Case Management Models for Social Services Coordination
Professional client management, referral tracking, and task management
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import uuid

logger = logging.getLogger(__name__)

class Client:
    """Client data model for case management"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.client_id = kwargs.get('client_id', str(uuid.uuid4()))
        self.case_manager_id = kwargs.get('case_manager_id', '')
        
        # Personal Information
        self.first_name = kwargs.get('first_name', '')
        self.last_name = kwargs.get('last_name', '')
        self.date_of_birth = kwargs.get('date_of_birth', '')
        self.gender = kwargs.get('gender', '')
        self.primary_phone = kwargs.get('primary_phone', '')
        self.email = kwargs.get('email', '')
        
        # Address Information
        self.address = kwargs.get('address', '')
        self.city = kwargs.get('city', '')
        self.county = kwargs.get('county', '')
        self.zip_code = kwargs.get('zip_code', '')
        
        # Emergency Contact
        self.emergency_contact = kwargs.get('emergency_contact', '')
        self.emergency_phone = kwargs.get('emergency_phone', '')
        
        # Demographics and Special Populations
        self.is_veteran = kwargs.get('is_veteran', False)
        self.has_disability = kwargs.get('has_disability', False)
        self.special_populations = kwargs.get('special_populations', '')  # JSON string
        
        # Background and Status
        self.background_summary = kwargs.get('background_summary', '')
        self.sobriety_status = kwargs.get('sobriety_status', '')
        self.insurance_status = kwargs.get('insurance_status', '')
        self.housing_status = kwargs.get('housing_status', '')
        self.employment_status = kwargs.get('employment_status', '')
        
        # Service Planning
        self.service_priorities = kwargs.get('service_priorities', '')  # JSON string
        self.risk_level = kwargs.get('risk_level', 'Medium')  # Low, Medium, High
        self.discharge_date = kwargs.get('discharge_date', '')
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.is_active = kwargs.get('is_active', True)
        self.notes = kwargs.get('notes', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'client_id': self.client_id,
            'case_manager_id': self.case_manager_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'primary_phone': self.primary_phone,
            'email': self.email,
            'address': self.address,
            'city': self.city,
            'county': self.county,
            'zip_code': self.zip_code,
            'emergency_contact': self.emergency_contact,
            'emergency_phone': self.emergency_phone,
            'is_veteran': self.is_veteran,
            'has_disability': self.has_disability,
            'special_populations': self.special_populations,
            'background_summary': self.background_summary,
            'sobriety_status': self.sobriety_status,
            'insurance_status': self.insurance_status,
            'housing_status': self.housing_status,
            'employment_status': self.employment_status,
            'service_priorities': self.service_priorities,
            'risk_level': self.risk_level,
            'discharge_date': self.discharge_date,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'is_active': self.is_active,
            'notes': self.notes
        }
    
    @property
    def full_name(self) -> str:
        """Get full name for display"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def age(self) -> Optional[int]:
        """Calculate age from date of birth"""
        if not self.date_of_birth:
            return None
        try:
            birth_date = datetime.fromisoformat(self.date_of_birth)
            today = datetime.now()
            return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except:
            return None


class ServiceReferral:
    """Service referral model for tracking client service assignments"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.referral_id = kwargs.get('referral_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        self.case_manager_id = kwargs.get('case_manager_id', '')
        self.provider_id = kwargs.get('provider_id', '')
        self.service_id = kwargs.get('service_id', '')
        
        # Referral Details
        self.referral_date = kwargs.get('referral_date', datetime.now().isoformat())
        self.priority_level = kwargs.get('priority_level', 'Medium')  # Low, Medium, High, Urgent
        self.status = kwargs.get('status', 'Pending')  # Pending, Submitted, Accepted, Active, Completed, Cancelled
        self.urgency = kwargs.get('urgency', 'Standard')  # Standard, Urgent, Emergency
        
        # Timeline
        self.expected_start_date = kwargs.get('expected_start_date', '')
        self.actual_start_date = kwargs.get('actual_start_date', '')
        self.expected_completion_date = kwargs.get('expected_completion_date', '')
        self.completion_date = kwargs.get('completion_date', '')
        
        # Follow-up and Communication
        self.last_contact_date = kwargs.get('last_contact_date', '')
        self.next_follow_up_date = kwargs.get('next_follow_up_date', '')
        self.provider_response = kwargs.get('provider_response', '')
        
        # Documentation
        self.referral_reason = kwargs.get('referral_reason', '')
        self.notes = kwargs.get('notes', '')
        self.barriers_encountered = kwargs.get('barriers_encountered', '')
        self.resolution_notes = kwargs.get('resolution_notes', '')
        
        # Outcome Tracking
        self.outcome = kwargs.get('outcome', '')  # Successful, Unsuccessful, Transferred, Dropped
        self.satisfaction_rating = kwargs.get('satisfaction_rating', 0)  # 1-5 scale
        self.client_feedback = kwargs.get('client_feedback', '')
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.created_by = kwargs.get('created_by', '')
        self.last_updated_by = kwargs.get('last_updated_by', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'referral_id': self.referral_id,
            'client_id': self.client_id,
            'case_manager_id': self.case_manager_id,
            'provider_id': self.provider_id,
            'service_id': self.service_id,
            'referral_date': self.referral_date,
            'priority_level': self.priority_level,
            'status': self.status,
            'urgency': self.urgency,
            'expected_start_date': self.expected_start_date,
            'actual_start_date': self.actual_start_date,
            'expected_completion_date': self.expected_completion_date,
            'completion_date': self.completion_date,
            'last_contact_date': self.last_contact_date,
            'next_follow_up_date': self.next_follow_up_date,
            'provider_response': self.provider_response,
            'referral_reason': self.referral_reason,
            'notes': self.notes,
            'barriers_encountered': self.barriers_encountered,
            'resolution_notes': self.resolution_notes,
            'outcome': self.outcome,
            'satisfaction_rating': self.satisfaction_rating,
            'client_feedback': self.client_feedback,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'created_by': self.created_by,
            'last_updated_by': self.last_updated_by
        }
    
    @property
    def days_since_referral(self) -> int:
        """Calculate days since referral was created"""
        try:
            referral_date = datetime.fromisoformat(self.referral_date)
            return (datetime.now() - referral_date).days
        except:
            return 0
    
    @property
    def is_overdue(self) -> bool:
        """Check if referral is overdue for follow-up"""
        if not self.next_follow_up_date:
            return False
        try:
            follow_up_date = datetime.fromisoformat(self.next_follow_up_date)
            return datetime.now() > follow_up_date
        except:
            return False


class CaseManagementTask:
    """Task model for case management workflow"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.task_id = kwargs.get('task_id', str(uuid.uuid4()))
        self.case_manager_id = kwargs.get('case_manager_id', '')
        self.client_id = kwargs.get('client_id', '')
        self.referral_id = kwargs.get('referral_id', '')
        
        # Task Details
        self.task_type = kwargs.get('task_type', 'General')  # General, Follow-up, Documentation, Contact, Assessment
        self.title = kwargs.get('title', '')
        self.description = kwargs.get('description', '')
        self.priority = kwargs.get('priority', 'Medium')  # Low, Medium, High, Urgent
        
        # Timeline
        self.due_date = kwargs.get('due_date', '')
        self.reminder_date = kwargs.get('reminder_date', '')
        self.status = kwargs.get('status', 'Pending')  # Pending, In Progress, Completed, Cancelled, Overdue
        
        # Assignment
        self.assigned_to = kwargs.get('assigned_to', '')
        self.assigned_by = kwargs.get('assigned_by', '')
        
        # Completion
        self.completed_date = kwargs.get('completed_date', '')
        self.completion_notes = kwargs.get('completion_notes', '')
        self.time_spent_minutes = kwargs.get('time_spent_minutes', 0)
        
        # Automation
        self.is_automated = kwargs.get('is_automated', False)
        self.recurring_interval = kwargs.get('recurring_interval', '')  # None, Daily, Weekly, Monthly
        self.parent_task_id = kwargs.get('parent_task_id', '')
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.created_by = kwargs.get('created_by', '')
        self.last_updated_by = kwargs.get('last_updated_by', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'case_manager_id': self.case_manager_id,
            'client_id': self.client_id,
            'referral_id': self.referral_id,
            'task_type': self.task_type,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'due_date': self.due_date,
            'reminder_date': self.reminder_date,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'assigned_by': self.assigned_by,
            'completed_date': self.completed_date,
            'completion_notes': self.completion_notes,
            'time_spent_minutes': self.time_spent_minutes,
            'is_automated': self.is_automated,
            'recurring_interval': self.recurring_interval,
            'parent_task_id': self.parent_task_id,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'created_by': self.created_by,
            'last_updated_by': self.last_updated_by
        }
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date or self.status in ['Completed', 'Cancelled']:
            return False
        try:
            due_date = datetime.fromisoformat(self.due_date)
            return datetime.now() > due_date
        except:
            return False
    
    @property
    def days_until_due(self) -> Optional[int]:
        """Calculate days until task is due"""
        if not self.due_date:
            return None
        try:
            due_date = datetime.fromisoformat(self.due_date)
            return (due_date - datetime.now()).days
        except:
            return None


class CaseManagementDatabase:
    """Extended database for case management functionality"""
    
    def __init__(self, db_path: str = "social_services.db"):
        self.db_path = db_path
        self.connection = None
        self.ensure_case_management_tables()
    
    def connect(self):
        """Connect to SQLite database"""
        try:
            # Use check_same_thread=False for Flask threading compatibility
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to case management database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to case management database: {e}")
            raise
    
    def ensure_case_management_tables(self):
        """Ensure case management tables exist"""
        if not self.connection:
            self.connect()
        
        # Create clients table if it doesn't exist
        create_clients_sql = """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL,
            case_manager_id TEXT NOT NULL,
            
            -- Personal Information
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            date_of_birth TEXT,
            gender TEXT,
            primary_phone TEXT,
            email TEXT,
            
            -- Address Information
            address TEXT,
            city TEXT,
            county TEXT,
            zip_code TEXT,
            
            -- Emergency Contact
            emergency_contact TEXT,
            emergency_phone TEXT,
            
            -- Demographics and Special Populations
            is_veteran INTEGER DEFAULT 0,
            has_disability INTEGER DEFAULT 0,
            special_populations TEXT,
            
            -- Background and Status
            background_summary TEXT,
            sobriety_status TEXT,
            insurance_status TEXT,
            housing_status TEXT,
            employment_status TEXT,
            
            -- Service Planning
            service_priorities TEXT,
            risk_level TEXT DEFAULT 'Medium',
            discharge_date TEXT,
            
            -- Metadata
            created_at TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            notes TEXT
        );
        """
        
        # Update clients table with additional fields (for existing tables)
        update_clients_sql = """
        ALTER TABLE clients ADD COLUMN risk_level TEXT DEFAULT 'Medium';
        ALTER TABLE clients ADD COLUMN discharge_date TEXT;
        """
        
        # Update referrals table with additional fields
        update_referrals_sql = """
        ALTER TABLE service_referrals ADD COLUMN urgency TEXT DEFAULT 'Standard';
        ALTER TABLE service_referrals ADD COLUMN expected_completion_date TEXT;
        ALTER TABLE service_referrals ADD COLUMN last_contact_date TEXT;
        ALTER TABLE service_referrals ADD COLUMN next_follow_up_date TEXT;
        ALTER TABLE service_referrals ADD COLUMN provider_response TEXT;
        ALTER TABLE service_referrals ADD COLUMN referral_reason TEXT;
        ALTER TABLE service_referrals ADD COLUMN resolution_notes TEXT;
        ALTER TABLE service_referrals ADD COLUMN client_feedback TEXT;
        ALTER TABLE service_referrals ADD COLUMN created_by TEXT;
        ALTER TABLE service_referrals ADD COLUMN last_updated_by TEXT;
        """
        
        # Update tasks table with additional fields
        update_tasks_sql = """
        ALTER TABLE case_management_tasks ADD COLUMN reminder_date TEXT;
        ALTER TABLE case_management_tasks ADD COLUMN time_spent_minutes INTEGER DEFAULT 0;
        ALTER TABLE case_management_tasks ADD COLUMN is_automated INTEGER DEFAULT 0;
        ALTER TABLE case_management_tasks ADD COLUMN recurring_interval TEXT;
        ALTER TABLE case_management_tasks ADD COLUMN parent_task_id TEXT;
        ALTER TABLE case_management_tasks ADD COLUMN created_by TEXT;
        ALTER TABLE case_management_tasks ADD COLUMN last_updated_by TEXT;
        """
        
        # Create communication logs table
        create_communication_logs_sql = """
        CREATE TABLE IF NOT EXISTS communication_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            communication_id TEXT UNIQUE NOT NULL,
            case_manager_id TEXT NOT NULL,
            provider_id TEXT,
            client_id TEXT,
            referral_id TEXT,
            communication_type TEXT DEFAULT 'Email',
            direction TEXT DEFAULT 'Outbound',
            subject TEXT,
            content TEXT,
            priority TEXT DEFAULT 'Normal',
            to_contacts TEXT,
            cc_contacts TEXT,
            from_contact TEXT,
            status TEXT DEFAULT 'Sent',
            read_date TEXT,
            reply_date TEXT,
            follow_up_required INTEGER DEFAULT 0,
            follow_up_date TEXT,
            attachments TEXT,
            related_documents TEXT,
            tags TEXT,
            created_at TEXT,
            created_by TEXT,
            is_confidential INTEGER DEFAULT 1,
            is_archived INTEGER DEFAULT 0
        );
        """
        
        # Create case management tasks table
        create_tasks_sql = """
        CREATE TABLE IF NOT EXISTS case_management_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            case_manager_id TEXT NOT NULL,
            client_id TEXT,
            referral_id TEXT,
            
            -- Task Details
            task_type TEXT DEFAULT 'General',
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'Medium',
            
            -- Timeline
            due_date TEXT,
            reminder_date TEXT,
            status TEXT DEFAULT 'Pending',
            
            -- Assignment
            assigned_to TEXT,
            assigned_by TEXT,
            
            -- Completion
            completed_date TEXT,
            completion_notes TEXT,
            time_spent_minutes INTEGER DEFAULT 0,
            
            -- Automation
            is_automated INTEGER DEFAULT 0,
            recurring_interval TEXT,
            parent_task_id TEXT,
            
            -- Metadata
            created_at TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            created_by TEXT,
            last_updated_by TEXT
        );
        """
        
        # Create service referrals table
        create_referrals_sql = """
        CREATE TABLE IF NOT EXISTS service_referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referral_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            case_manager_id TEXT NOT NULL,
            provider_id TEXT NOT NULL,
            service_id TEXT NOT NULL,
            
            -- Referral Details
            referral_date TEXT NOT NULL,
            priority_level TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Pending',
            urgency TEXT DEFAULT 'Standard',
            
            -- Timeline
            expected_start_date TEXT,
            actual_start_date TEXT,
            expected_completion_date TEXT,
            completion_date TEXT,
            
            -- Follow-up and Communication
            last_contact_date TEXT,
            next_follow_up_date TEXT,
            provider_response TEXT,
            
            -- Documentation
            referral_reason TEXT,
            notes TEXT,
            barriers_encountered TEXT,
            resolution_notes TEXT,
            
            -- Outcome Tracking
            outcome TEXT,
            satisfaction_rating INTEGER DEFAULT 0,
            client_feedback TEXT,
            
            -- Metadata
            created_at TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            created_by TEXT,
            last_updated_by TEXT
        );
        """
        
        # Create enhanced dashboard tables (ClickUp-like features)
        create_notes_sql = """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_archived INTEGER DEFAULT 0
        );
        """
        
        create_bookmarks_sql = """
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bookmark_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            is_archived INTEGER DEFAULT 0
        );
        """
        
        create_folders_sql = """
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            is_archived INTEGER DEFAULT 0
        );
        """
        
        create_documents_sql = """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            folder_id TEXT,
            client_id TEXT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_archived INTEGER DEFAULT 0,
            FOREIGN KEY (folder_id) REFERENCES folders(folder_id),
            FOREIGN KEY (client_id) REFERENCES clients(client_id)
        );
        """
        
        try:
            # Create clients table if it doesn't exist
            try:
                self.connection.execute(create_clients_sql)
            except sqlite3.OperationalError:
                pass  # Table already exists
            
            # Try to add new columns (will fail silently if they already exist)
            for sql in update_clients_sql.split(';'):
                if sql.strip():
                    try:
                        self.connection.execute(sql)
                    except sqlite3.OperationalError:
                        pass  # Column already exists
            
            for sql in update_referrals_sql.split(';'):
                if sql.strip():
                    try:
                        self.connection.execute(sql)
                    except sqlite3.OperationalError:
                        pass  # Column already exists
            
            for sql in update_tasks_sql.split(';'):
                if sql.strip():
                    try:
                        self.connection.execute(sql)
                    except sqlite3.OperationalError:
                        pass  # Column already exists
            
            # Create case management tables
            try:
                self.connection.execute(create_tasks_sql)
                self.connection.execute(create_referrals_sql)
            except sqlite3.OperationalError:
                pass  # Tables already exist
            
            # Create communication logs table
            try:
                self.connection.execute(create_communication_logs_sql)
            except sqlite3.OperationalError:
                pass  # Table already exists
            
            # Create enhanced dashboard tables
            try:
                self.connection.execute(create_notes_sql)
                self.connection.execute(create_bookmarks_sql)
                self.connection.execute(create_folders_sql)
                self.connection.execute(create_documents_sql)
            except sqlite3.OperationalError:
                pass  # Tables already exist
            
            self.connection.commit()
            logger.info("Case management tables updated successfully")
        except Exception as e:
            logger.error(f"Failed to update case management tables: {e}")
            raise
    
    def save_client(self, client: Client) -> int:
        """Save a client to the database"""
        if not self.connection:
            self.connect()
        
        insert_sql = """
        INSERT INTO clients (
            client_id, case_manager_id, first_name, last_name, date_of_birth, gender,
            primary_phone, email, address, city, county, zip_code,
            emergency_contact, emergency_phone, is_veteran, has_disability, special_populations,
            background_summary, sobriety_status, insurance_status, housing_status, employment_status,
            service_priorities, risk_level, discharge_date, created_at, last_updated, is_active, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                client.client_id, client.case_manager_id, client.first_name, client.last_name,
                client.date_of_birth, client.gender, client.primary_phone, client.email,
                client.address, client.city, client.county, client.zip_code,
                client.emergency_contact, client.emergency_phone, client.is_veteran,
                client.has_disability, client.special_populations, client.background_summary,
                client.sobriety_status, client.insurance_status, client.housing_status,
                client.employment_status, client.service_priorities, client.risk_level,
                client.discharge_date, client.created_at, client.last_updated,
                client.is_active, client.notes
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save client: {e}")
            raise
    
    def save_referral(self, referral: ServiceReferral) -> int:
        """Save a service referral to the database"""
        if not self.connection:
            self.connect()
        
        insert_sql = """
        INSERT INTO service_referrals (
            referral_id, client_id, case_manager_id, provider_id, service_id,
            referral_date, priority_level, status, urgency, expected_start_date, actual_start_date,
            expected_completion_date, completion_date, last_contact_date, next_follow_up_date,
            provider_response, referral_reason, notes, barriers_encountered, resolution_notes,
            outcome, satisfaction_rating, client_feedback, created_at, last_updated,
            created_by, last_updated_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                referral.referral_id, referral.client_id, referral.case_manager_id,
                referral.provider_id, referral.service_id, referral.referral_date,
                referral.priority_level, referral.status, referral.urgency,
                referral.expected_start_date, referral.actual_start_date,
                referral.expected_completion_date, referral.completion_date,
                referral.last_contact_date, referral.next_follow_up_date,
                referral.provider_response, referral.referral_reason, referral.notes,
                referral.barriers_encountered, referral.resolution_notes, referral.outcome,
                referral.satisfaction_rating, referral.client_feedback, referral.created_at,
                referral.last_updated, referral.created_by, referral.last_updated_by
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save referral: {e}")
            raise
    
    def save_task(self, task: CaseManagementTask) -> int:
        """Save a case management task to the database"""
        if not self.connection:
            self.connect()
        
        insert_sql = """
        INSERT INTO case_management_tasks (
            task_id, case_manager_id, client_id, referral_id, task_type, title, description,
            priority, due_date, reminder_date, status, assigned_to, assigned_by,
            completed_date, completion_notes, time_spent_minutes, is_automated,
            recurring_interval, parent_task_id, created_at, last_updated,
            created_by, last_updated_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                task.task_id, task.case_manager_id, task.client_id, task.referral_id,
                task.task_type, task.title, task.description, task.priority,
                task.due_date, task.reminder_date, task.status, task.assigned_to,
                task.assigned_by, task.completed_date, task.completion_notes,
                task.time_spent_minutes, task.is_automated, task.recurring_interval,
                task.parent_task_id, task.created_at, task.last_updated,
                task.created_by, task.last_updated_by
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save task: {e}")
            raise
    
    def get_case_manager_dashboard(self, case_manager_id: str) -> Dict[str, Any]:
        """Get comprehensive dashboard data for a case manager"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Get client counts
            cursor.execute("""
                SELECT COUNT(*) as total_clients,
                       SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_clients,
                       SUM(CASE WHEN discharge_date != '' AND discharge_date IS NOT NULL THEN 1 ELSE 0 END) as clients_with_discharge
                FROM clients 
                WHERE case_manager_id = ? AND is_active = 1
            """, (case_manager_id,))
            client_stats = dict(cursor.fetchone())
            
            # Get referral counts
            cursor.execute("""
                SELECT COUNT(*) as total_referrals,
                       SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_referrals,
                       SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_referrals,
                       SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_referrals
                FROM service_referrals 
                WHERE case_manager_id = ?
            """, (case_manager_id,))
            referral_stats = dict(cursor.fetchone())
            
            # Get task counts
            cursor.execute("""
                SELECT COUNT(*) as total_tasks,
                       SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_tasks,
                       SUM(CASE WHEN status = 'Overdue' OR (due_date < datetime('now') AND status != 'Completed') THEN 1 ELSE 0 END) as overdue_tasks,
                       SUM(CASE WHEN priority = 'High' OR priority = 'Urgent' THEN 1 ELSE 0 END) as high_priority_tasks
                FROM case_management_tasks 
                WHERE case_manager_id = ?
            """, (case_manager_id,))
            task_stats = dict(cursor.fetchone())
            
            # Get recent activity
            cursor.execute("""
                SELECT 'referral' as activity_type, referral_id as id, 
                       'Referral created for ' || c.first_name || ' ' || c.last_name as description,
                       r.created_at as timestamp
                FROM service_referrals r
                JOIN clients c ON r.client_id = c.client_id
                WHERE r.case_manager_id = ?
                UNION ALL
                SELECT 'task' as activity_type, task_id as id,
                       title as description, created_at as timestamp
                FROM case_management_tasks
                WHERE case_manager_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (case_manager_id, case_manager_id))
            recent_activity = [dict(row) for row in cursor.fetchall()]
            
            return {
                'client_stats': client_stats,
                'referral_stats': referral_stats,
                'task_stats': task_stats,
                'recent_activity': recent_activity
            }
        except Exception as e:
            logger.error(f"Failed to get case manager dashboard: {e}")
            return {}
    
    def get_clients(self, case_manager_id: str, search_term: str = '', status_filter: str = '') -> List[Dict[str, Any]]:
        """Get clients for a case manager with optional search and filtering"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            query = """
                SELECT * FROM clients 
                WHERE case_manager_id = ? AND is_active = 1
            """
            params = [case_manager_id]
            
            if search_term:
                query += " AND (first_name LIKE ? OR last_name LIKE ? OR primary_phone LIKE ?)"
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            if status_filter:
                query += " AND housing_status = ?"
                params.append(status_filter)
            
            query += " ORDER BY last_updated DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get clients: {e}")
            return []
    
    def get_client(self, client_id: str) -> Dict[str, Any]:
        """Get a specific client by ID"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get client: {e}")
            return None
    
    def update_client(self, client_id: str, data: Dict[str, Any]) -> bool:
        """Update client information"""
        if not self.connection:
            self.connect()
        
        try:
            # Build update query dynamically based on provided data
            update_fields = []
            params = []
            
            for field, value in data.items():
                if field != 'client_id':  # Don't update the ID
                    update_fields.append(f"{field} = ?")
                    params.append(value)
            
            if not update_fields:
                return False
            
            # Add last_updated timestamp
            update_fields.append("last_updated = ?")
            params.append(datetime.now().isoformat())
            
            # Add client_id for WHERE clause
            params.append(client_id)
            
            query = f"UPDATE clients SET {', '.join(update_fields)} WHERE client_id = ?"
            
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update client: {e}")
            return False
    
    def get_client_referrals(self, client_id: str) -> List[Dict[str, Any]]:
        """Get all referrals for a specific client"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT r.*, sp.name as provider_name, ss.service_type
                FROM service_referrals r
                LEFT JOIN service_providers sp ON r.provider_id = sp.provider_id
                LEFT JOIN social_services ss ON r.service_id = ss.service_id
                WHERE r.client_id = ?
                ORDER BY r.created_at DESC
            """, (client_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get client referrals: {e}")
            return []
    
    def get_client_tasks(self, client_id: str) -> List[Dict[str, Any]]:
        """Get all tasks for a specific client"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM case_management_tasks 
                WHERE client_id = ?
                ORDER BY created_at DESC
            """, (client_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get client tasks: {e}")
            return []
    
    def get_referrals(self, case_manager_id: str, status_filter: str = '', client_id: str = '') -> List[Dict[str, Any]]:
        """Get referrals for a case manager with optional filtering"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            query = """
                SELECT r.*, c.first_name, c.last_name, sp.name as provider_name, ss.service_type
                FROM service_referrals r
                LEFT JOIN clients c ON r.client_id = c.client_id
                LEFT JOIN service_providers sp ON r.provider_id = sp.provider_id
                LEFT JOIN social_services ss ON r.service_id = ss.service_id
                WHERE r.case_manager_id = ?
            """
            params = [case_manager_id]
            
            if status_filter:
                query += " AND r.status = ?"
                params.append(status_filter)
            
            if client_id:
                query += " AND r.client_id = ?"
                params.append(client_id)
            
            query += " ORDER BY r.created_at DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get referrals: {e}")
            return []
    
    def update_referral_status(self, referral_id: str, new_status: str, notes: str = '') -> bool:
        """Update referral status"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE service_referrals 
                SET status = ?, notes = ?, last_updated = ?
                WHERE referral_id = ?
            """, (new_status, notes, datetime.now().isoformat(), referral_id))
            self.connection.commit()
            
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update referral status: {e}")
            return False
    
    def get_tasks(self, case_manager_id: str, status_filter: str = '', client_id: str = '') -> List[Dict[str, Any]]:
        """Get tasks for a case manager with optional filtering"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            query = """
                SELECT t.*, c.first_name, c.last_name
                FROM case_management_tasks t
                LEFT JOIN clients c ON t.client_id = c.client_id
                WHERE t.case_manager_id = ?
            """
            params = [case_manager_id]
            
            if status_filter:
                query += " AND t.status = ?"
                params.append(status_filter)
            
            if client_id:
                query += " AND t.client_id = ?"
                params.append(client_id)
            
            query += " ORDER BY t.due_date ASC, t.priority DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return []
    
    def update_task_status(self, task_id: str, new_status: str, notes: str = '') -> bool:
        """Update task status"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            update_data = {
                'status': new_status,
                'last_updated': datetime.now().isoformat()
            }
            
            if new_status == 'Completed':
                update_data['completed_date'] = datetime.now().isoformat()
            
            if notes:
                update_data['completion_notes'] = notes
            
            # Build update query
            set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
            values = list(update_data.values()) + [task_id]
            
            cursor.execute(f"""
                UPDATE case_management_tasks 
                SET {set_clause}
                WHERE task_id = ?
            """, values)
            self.connection.commit()
            
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            return False
    
    def get_client_dashboard(self, client_id: str) -> Dict[str, Any]:
        """Get comprehensive dashboard data for a specific client"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Get client info
            client = self.get_client(client_id)
            if not client:
                return {}
            
            # Get client referrals
            referrals = self.get_client_referrals(client_id)
            
            # Get client tasks
            tasks = self.get_client_tasks(client_id)
            
            # Get client notes
            cursor.execute("""
                SELECT * FROM client_notes 
                WHERE client_id = ? AND is_archived = 0 
                ORDER BY created_at DESC
                LIMIT 10
            """, (client_id,))
            notes = [dict(row) for row in cursor.fetchall()]
            
            # Get client appointments
            cursor.execute("""
                SELECT * FROM client_appointments 
                WHERE client_id = ? AND is_cancelled = 0 
                ORDER BY appointment_date ASC
                LIMIT 10
            """, (client_id,))
            appointments = [dict(row) for row in cursor.fetchall()]
            
            # Get documents
            cursor.execute("""
                SELECT * FROM documents 
                WHERE client_id = ? AND is_archived = 0 
                ORDER BY created_at DESC
                LIMIT 10
            """, (client_id,))
            documents = [dict(row) for row in cursor.fetchall()]
            
            # Get emergency log
            cursor.execute("""
                SELECT * FROM emergency_log 
                WHERE client_id = ? 
                ORDER BY logged_at DESC
                LIMIT 5
            """, (client_id,))
            emergency_log = [dict(row) for row in cursor.fetchall()]
            
            # Calculate statistics
            active_referrals = len([r for r in referrals if r.get('status') in ['Pending', 'Active']])
            completed_referrals = len([r for r in referrals if r.get('status') == 'Completed'])
            pending_tasks = len([t for t in tasks if t.get('status') == 'Pending'])
            completed_tasks = len([t for t in tasks if t.get('status') == 'Completed'])
            
            dashboard_data = {
                'client': client,
                'stats': {
                    'total_referrals': len(referrals),
                    'active_referrals': active_referrals,
                    'completed_referrals': completed_referrals,
                    'total_tasks': len(tasks),
                    'pending_tasks': pending_tasks,
                    'completed_tasks': completed_tasks,
                    'total_notes': len(notes),
                    'total_appointments': len(appointments),
                    'total_documents': len(documents),
                    'emergency_incidents': len(emergency_log)
                },
                'recent_referrals': referrals[:5],
                'recent_tasks': tasks[:5],
                'recent_notes': notes[:5],
                'upcoming_appointments': appointments[:5],
                'recent_documents': documents[:5],
                'emergency_log': emergency_log
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get client dashboard: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Case management database connection closed")