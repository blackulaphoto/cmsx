#!/usr/bin/env python3
"""
Intelligent Case Management Reminder System - Database Models
Advanced reminder tracking with AI-powered prioritization
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import uuid

logger = logging.getLogger(__name__)

class ClientContact:
    """Track all client interactions for intelligent reminder calculation"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.contact_id = kwargs.get('contact_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        self.case_manager_id = kwargs.get('case_manager_id', '')
        
        # Contact Details
        self.contact_date = kwargs.get('contact_date', datetime.now().isoformat())
        self.contact_type = kwargs.get('contact_type', '')  # Phone, In-Person, Email, Text
        self.contact_method = kwargs.get('contact_method', '')  # Scheduled, Walk-in, Emergency
        self.duration_minutes = kwargs.get('duration_minutes', 0)
        self.location = kwargs.get('location', '')
        
        # Content & Outcomes
        self.purpose = kwargs.get('purpose', '')
        self.topics_discussed = kwargs.get('topics_discussed', '')
        self.client_mood = kwargs.get('client_mood', '')  # Positive, Neutral, Negative, Crisis
        self.progress_assessment = kwargs.get('progress_assessment', '')
        self.barriers_identified = kwargs.get('barriers_identified', '')
        
        # Follow-up Actions
        self.action_items = kwargs.get('action_items', '')
        self.next_contact_needed = kwargs.get('next_contact_needed', '')
        self.referrals_made = kwargs.get('referrals_made', '')
        self.documents_provided = kwargs.get('documents_provided', '')
        
        # Risk Assessment
        self.risk_indicators = kwargs.get('risk_indicators', '')
        self.crisis_level = kwargs.get('crisis_level', 'None')  # None, Low, Medium, High, Emergency
        self.safety_concerns = kwargs.get('safety_concerns', '')
        
        # Compliance & Engagement
        self.client_engagement_level = kwargs.get('client_engagement_level', 'Good')  # Poor, Fair, Good, Excellent
        self.appointment_status = kwargs.get('appointment_status', 'Completed')  # Scheduled, Completed, No-Show, Cancelled
        self.compliance_status = kwargs.get('compliance_status', 'Compliant')
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.updated_at = kwargs.get('updated_at', datetime.now().isoformat())
        self.notes = kwargs.get('notes', '')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'contact_id': self.contact_id,
            'client_id': self.client_id,
            'case_manager_id': self.case_manager_id,
            'contact_date': self.contact_date,
            'contact_type': self.contact_type,
            'contact_method': self.contact_method,
            'duration_minutes': self.duration_minutes,
            'location': self.location,
            'purpose': self.purpose,
            'topics_discussed': self.topics_discussed,
            'client_mood': self.client_mood,
            'progress_assessment': self.progress_assessment,
            'barriers_identified': self.barriers_identified,
            'action_items': self.action_items,
            'next_contact_needed': self.next_contact_needed,
            'referrals_made': self.referrals_made,
            'documents_provided': self.documents_provided,
            'risk_indicators': self.risk_indicators,
            'crisis_level': self.crisis_level,
            'safety_concerns': self.safety_concerns,
            'client_engagement_level': self.client_engagement_level,
            'appointment_status': self.appointment_status,
            'compliance_status': self.compliance_status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'notes': self.notes
        }

class ReminderRule:
    """Define when and how reminders should fire"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.rule_id = kwargs.get('rule_id', str(uuid.uuid4()))
        self.rule_name = kwargs.get('rule_name', '')
        self.rule_type = kwargs.get('rule_type', '')  # Contact, Deadline, Milestone, Crisis
        
        # Trigger Conditions
        self.client_risk_level = kwargs.get('client_risk_level', '')  # High, Medium, Low
        self.days_since_contact = kwargs.get('days_since_contact', 0)
        self.days_until_deadline = kwargs.get('days_until_deadline', 0)
        self.program_phase = kwargs.get('program_phase', '')
        
        # Action Settings
        self.reminder_priority = kwargs.get('reminder_priority', 'Medium')  # Critical, High, Medium, Low
        self.notification_method = kwargs.get('notification_method', 'Dashboard')  # Dashboard, Email, SMS, Push
        self.escalation_rules = kwargs.get('escalation_rules', '')
        
        # Status
        self.is_active = kwargs.get('is_active', True)
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.updated_at = kwargs.get('updated_at', datetime.now().isoformat())
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'rule_type': self.rule_type,
            'client_risk_level': self.client_risk_level,
            'days_since_contact': self.days_since_contact,
            'days_until_deadline': self.days_until_deadline,
            'program_phase': self.program_phase,
            'reminder_priority': self.reminder_priority,
            'notification_method': self.notification_method,
            'escalation_rules': self.escalation_rules,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class ProgramMilestone:
    """Track program milestones and deadlines"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.milestone_id = kwargs.get('milestone_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        self.milestone_type = kwargs.get('milestone_type', '')  # Assessment, Deadline, Review
        self.milestone_name = kwargs.get('milestone_name', '')
        self.due_date = kwargs.get('due_date', '')
        self.status = kwargs.get('status', 'Pending')  # Pending, In Progress, Completed, Overdue
        self.priority = kwargs.get('priority', 'Medium')
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())

class ActiveReminder:
    """Track active reminders for case managers"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.reminder_id = kwargs.get('reminder_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        self.case_manager_id = kwargs.get('case_manager_id', '')
        self.reminder_type = kwargs.get('reminder_type', '')
        self.message = kwargs.get('message', '')
        self.priority = kwargs.get('priority', 'Medium')
        self.due_date = kwargs.get('due_date', '')
        self.status = kwargs.get('status', 'Active')
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())

class ReminderDatabase:
    """Database interface for reminder system"""
    
    def __init__(self, db_path: str = 'databases/reminders.db'):
        self.db_path = db_path
        self.case_mgmt_db_path = 'databases/case_management.db'
        self.connection = None
        self.case_mgmt_connection = None
        self.setup_database()
    
    def connect(self):
        """Connect to SQLite databases"""
        try:
            # Connect to reminder database
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            
            # Connect to case management database
            self.case_mgmt_connection = sqlite3.connect(self.case_mgmt_db_path)
            self.case_mgmt_connection.row_factory = sqlite3.Row
            
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def setup_database(self):
        """Create database tables if they don't exist"""
        if not self.connect():
            return False
        
        tables = [
            # Client contacts table
            """
            CREATE TABLE IF NOT EXISTS client_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                contact_date TEXT NOT NULL,
                contact_type TEXT NOT NULL,
                contact_method TEXT,
                duration_minutes INTEGER,
                location TEXT,
                purpose TEXT,
                topics_discussed TEXT,
                client_mood TEXT,
                progress_assessment TEXT,
                barriers_identified TEXT,
                action_items TEXT,
                next_contact_needed TEXT,
                referrals_made TEXT,
                documents_provided TEXT,
                risk_indicators TEXT,
                crisis_level TEXT,
                safety_concerns TEXT,
                client_engagement_level TEXT,
                appointment_status TEXT,
                compliance_status TEXT,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT
            )
            """,
            # Reminder rules table
            """
            CREATE TABLE IF NOT EXISTS reminder_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT UNIQUE NOT NULL,
                rule_name TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                client_risk_level TEXT,
                days_since_contact INTEGER,
                days_until_deadline INTEGER,
                program_phase TEXT,
                reminder_priority TEXT,
                notification_method TEXT,
                escalation_rules TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
            """,
            # Program milestones table
            """
            CREATE TABLE IF NOT EXISTS program_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                milestone_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                milestone_type TEXT NOT NULL,
                milestone_name TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                priority TEXT DEFAULT 'Medium',
                created_at TEXT
            )
            """,
            # Active reminders table
            """
            CREATE TABLE IF NOT EXISTS active_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT DEFAULT 'Medium',
                due_date TEXT,
                status TEXT DEFAULT 'Active',
                created_at TEXT
            )
            """
        ]
        
        try:
            for table_sql in tables:
                self.connection.execute(table_sql)
            self.connection.commit()
            logger.info("Reminder database tables created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            return False
    
    def get_client_data(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client data from case management database"""
        try:
            if not self.case_mgmt_connection:
                self.connect()
            
            cursor = self.case_mgmt_connection.cursor()
            cursor.execute("""
                SELECT 
                    c.client_id,
                    c.first_name || ' ' || c.last_name as client_name,
                    c.risk_level,
                    c.case_status,
                    c.intake_date,
                    c.case_manager_id,
                    c.phone,
                    c.email,
                    c.notes,
                    CASE 
                        WHEN c.intake_date IS NOT NULL 
                        THEN CAST((julianday('now') - julianday(c.intake_date)) AS INTEGER)
                        ELSE 0 
                    END as days_in_program
                FROM clients c 
                WHERE c.client_id = ? AND c.is_active = 1
            """, (client_id,))
            
            row = cursor.fetchone()
            if row:
                client_data = dict(row)
                
                # Calculate additional fields needed by reminder system
                client_data['crisis_level'] = self._determine_crisis_level(client_id)
                client_data['days_until_discharge'] = self._calculate_days_until_discharge(client_data)
                client_data['program_length'] = 90  # Default program length
                
                return client_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting client data: {e}")
            return None
    
    def get_last_contact(self, client_id: str, case_manager_id: str) -> Optional[Dict[str, Any]]:
        """Get last contact for client"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM client_contacts 
                WHERE client_id = ? AND case_manager_id = ? 
                ORDER BY contact_date DESC 
                LIMIT 1
            """, (client_id, case_manager_id))
            
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Error getting last contact: {e}")
            return None
    
    def get_clients_for_case_manager(self, case_manager_id: str) -> List[Dict[str, Any]]:
        """Get all clients for a case manager from case management database"""
        try:
            if not self.case_mgmt_connection:
                self.connect()
            
            cursor = self.case_mgmt_connection.cursor()
            cursor.execute("""
                SELECT 
                    client_id,
                    first_name || ' ' || last_name as client_name,
                    risk_level,
                    case_status,
                    intake_date
                FROM clients 
                WHERE case_manager_id = ? AND is_active = 1
                ORDER BY risk_level DESC, intake_date ASC
            """, (case_manager_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting clients for case manager: {e}")
            return []
    
    def save_contact(self, contact: ClientContact) -> bool:
        """Save client contact to database"""
        try:
            cursor = self.connection.cursor()
            contact_data = contact.to_dict()
            
            columns = ', '.join(contact_data.keys())
            placeholders = ', '.join(['?' for _ in contact_data])
            values = list(contact_data.values())
            
            cursor.execute(f"""
                INSERT OR REPLACE INTO client_contacts ({columns})
                VALUES ({placeholders})
            """, values)
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving contact: {e}")
            return False
    
    def close(self):
        """Close database connections"""
        if self.connection:
            self.connection.close()
        if self.case_mgmt_connection:
            self.case_mgmt_connection.close()
    
    def _determine_crisis_level(self, client_id: str) -> str:
        """Determine crisis level based on recent case notes and contacts"""
        try:
            cursor = self.case_mgmt_connection.cursor()
            
            # Check recent case notes for crisis indicators
            cursor.execute("""
                SELECT note_text, created_at
                FROM case_notes 
                WHERE client_id = ? 
                AND created_at >= datetime('now', '-7 days')
                ORDER BY created_at DESC
                LIMIT 10
            """, (client_id,))
            
            recent_notes = cursor.fetchall()
            
            # Check for crisis keywords in recent notes
            crisis_keywords = ['crisis', 'emergency', 'urgent', 'suicide', 'overdose', 'relapse', 'hospital']
            
            for note in recent_notes:
                note_text = note['note_text'].lower() if note['note_text'] else ''
                if any(keyword in note_text for keyword in crisis_keywords):
                    return 'Recent'
            
            # Check for recent contact patterns that might indicate crisis
            if hasattr(self, 'connection') and self.connection:
                cursor = self.connection.cursor()
                cursor.execute("""
                    SELECT crisis_level, contact_date
                    FROM client_contacts 
                    WHERE client_id = ? 
                    AND contact_date >= datetime('now', '-3 days')
                    AND crisis_level IN ('High', 'Emergency')
                    ORDER BY contact_date DESC
                    LIMIT 1
                """, (client_id,))
                
                recent_crisis = cursor.fetchone()
                if recent_crisis:
                    return 'Active'
            
            return 'None'
            
        except Exception as e:
            logger.error(f"Error determining crisis level: {e}")
            return 'None'
    
    def _calculate_days_until_discharge(self, client_data: Dict[str, Any]) -> int:
        """Calculate estimated days until discharge based on program type and progress"""
        try:
            days_in_program = client_data.get('days_in_program', 0)
            program_length = client_data.get('program_length', 90)
            
            # Basic calculation - can be enhanced with more sophisticated logic
            days_remaining = max(0, program_length - days_in_program)
            
            return days_remaining
            
        except Exception as e:
            logger.error(f"Error calculating discharge date: {e}")
            return 999