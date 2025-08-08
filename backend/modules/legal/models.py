#!/usr/bin/env python3
"""
Legal Case Management Models for Second Chance Jobs Platform
Comprehensive legal compliance tracking for justice-involved individuals
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import uuid

logger = logging.getLogger(__name__)

class LegalCase:
    """Legal case tracking for criminal justice involvement"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.case_id = kwargs.get('case_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        
        # Case Information
        self.case_number = kwargs.get('case_number', '')
        self.court_name = kwargs.get('court_name', '')
        self.court_address = kwargs.get('court_address', '')
        self.judge_name = kwargs.get('judge_name', '')
        self.case_type = kwargs.get('case_type', '')  # Felony, Misdemeanor, Probation Violation, etc.
        self.case_status = kwargs.get('case_status', 'Active')  # Active, Closed, Pending, Appealed
        
        # Charges and Convictions
        self.charges = kwargs.get('charges', '')  # JSON string of charges
        self.convictions = kwargs.get('convictions', '')  # JSON string of convictions
        self.sentence_details = kwargs.get('sentence_details', '')
        self.probation_terms = kwargs.get('probation_terms', '')
        self.parole_terms = kwargs.get('parole_terms', '')
        
        # Legal Representation
        self.attorney_name = kwargs.get('attorney_name', '')
        self.attorney_phone = kwargs.get('attorney_phone', '')
        self.attorney_email = kwargs.get('attorney_email', '')
        self.attorney_type = kwargs.get('attorney_type', '')  # Public Defender, Private, Legal Aid
        
        # Probation/Parole Officers
        self.probation_officer = kwargs.get('probation_officer', '')
        self.probation_phone = kwargs.get('probation_phone', '')
        self.probation_email = kwargs.get('probation_email', '')
        self.parole_officer = kwargs.get('parole_officer', '')
        self.parole_phone = kwargs.get('parole_phone', '')
        self.parole_email = kwargs.get('parole_email', '')
        
        # Important Dates
        self.arrest_date = kwargs.get('arrest_date', '')
        self.conviction_date = kwargs.get('conviction_date', '')
        self.sentence_start_date = kwargs.get('sentence_start_date', '')
        self.probation_start_date = kwargs.get('probation_start_date', '')
        self.probation_end_date = kwargs.get('probation_end_date', '')
        self.parole_start_date = kwargs.get('parole_start_date', '')
        self.parole_end_date = kwargs.get('parole_end_date', '')
        
        # Compliance Status
        self.compliance_status = kwargs.get('compliance_status', 'Compliant')  # Compliant, Non-Compliant, Warning
        self.last_compliance_check = kwargs.get('last_compliance_check', '')
        self.compliance_notes = kwargs.get('compliance_notes', '')
        
        # Expungement Eligibility
        self.expungement_eligible = kwargs.get('expungement_eligible', False)
        self.expungement_applied = kwargs.get('expungement_applied', False)
        self.expungement_date = kwargs.get('expungement_date', '')
        self.expungement_status = kwargs.get('expungement_status', '')
        
        # Financial Obligations
        self.fines_total = kwargs.get('fines_total', 0.0)
        self.fines_paid = kwargs.get('fines_paid', 0.0)
        self.restitution_total = kwargs.get('restitution_total', 0.0)
        self.restitution_paid = kwargs.get('restitution_paid', 0.0)
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.is_active = kwargs.get('is_active', True)
        self.notes = kwargs.get('notes', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'client_id': self.client_id,
            'case_number': self.case_number,
            'court_name': self.court_name,
            'court_address': self.court_address,
            'judge_name': self.judge_name,
            'case_type': self.case_type,
            'case_status': self.case_status,
            'charges': self.charges,
            'convictions': self.convictions,
            'sentence_details': self.sentence_details,
            'probation_terms': self.probation_terms,
            'parole_terms': self.parole_terms,
            'attorney_name': self.attorney_name,
            'attorney_phone': self.attorney_phone,
            'attorney_email': self.attorney_email,
            'attorney_type': self.attorney_type,
            'probation_officer': self.probation_officer,
            'probation_phone': self.probation_phone,
            'probation_email': self.probation_email,
            'parole_officer': self.parole_officer,
            'parole_phone': self.parole_phone,
            'parole_email': self.parole_email,
            'arrest_date': self.arrest_date,
            'conviction_date': self.conviction_date,
            'sentence_start_date': self.sentence_start_date,
            'probation_start_date': self.probation_start_date,
            'probation_end_date': self.probation_end_date,
            'parole_start_date': self.parole_start_date,
            'parole_end_date': self.parole_end_date,
            'compliance_status': self.compliance_status,
            'last_compliance_check': self.last_compliance_check,
            'compliance_notes': self.compliance_notes,
            'expungement_eligible': self.expungement_eligible,
            'expungement_applied': self.expungement_applied,
            'expungement_date': self.expungement_date,
            'expungement_status': self.expungement_status,
            'fines_total': self.fines_total,
            'fines_paid': self.fines_paid,
            'restitution_total': self.restitution_total,
            'restitution_paid': self.restitution_paid,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'is_active': self.is_active,
            'notes': self.notes
        }
    
    @property
    def fines_balance(self) -> float:
        """Calculate remaining fines balance"""
        return max(0, self.fines_total - self.fines_paid)
    
    @property
    def restitution_balance(self) -> float:
        """Calculate remaining restitution balance"""
        return max(0, self.restitution_total - self.restitution_paid)
    
    @property
    def is_probation_active(self) -> bool:
        """Check if probation is currently active"""
        if not self.probation_end_date:
            return False
        try:
            end_date = datetime.fromisoformat(self.probation_end_date)
            return datetime.now() < end_date
        except:
            return False
    
    @property
    def is_parole_active(self) -> bool:
        """Check if parole is currently active"""
        if not self.parole_end_date:
            return False
        try:
            end_date = datetime.fromisoformat(self.parole_end_date)
            return datetime.now() < end_date
        except:
            return False


class CourtDate:
    """Court date and hearing tracking"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.court_date_id = kwargs.get('court_date_id', str(uuid.uuid4()))
        self.case_id = kwargs.get('case_id', '')
        self.client_id = kwargs.get('client_id', '')
        
        # Court Date Details
        self.hearing_date = kwargs.get('hearing_date', '')
        self.hearing_time = kwargs.get('hearing_time', '')
        self.court_name = kwargs.get('court_name', '')
        self.courtroom = kwargs.get('courtroom', '')
        self.judge_name = kwargs.get('judge_name', '')
        
        # Hearing Information
        self.hearing_type = kwargs.get('hearing_type', '')  # Arraignment, Plea, Sentencing, Probation Review, etc.
        self.hearing_purpose = kwargs.get('hearing_purpose', '')
        self.required_attendance = kwargs.get('required_attendance', True)
        self.attorney_required = kwargs.get('attorney_required', False)
        
        # Preparation and Documents
        self.documents_needed = kwargs.get('documents_needed', '')  # JSON string
        self.preparation_notes = kwargs.get('preparation_notes', '')
        self.transportation_arranged = kwargs.get('transportation_arranged', False)
        self.work_excuse_needed = kwargs.get('work_excuse_needed', False)
        
        # Status and Outcome
        self.status = kwargs.get('status', 'Scheduled')  # Scheduled, Attended, Missed, Rescheduled, Cancelled
        self.attendance_status = kwargs.get('attendance_status', '')  # On Time, Late, Absent
        self.outcome = kwargs.get('outcome', '')
        self.next_hearing_scheduled = kwargs.get('next_hearing_scheduled', '')
        
        # Reminders and Notifications
        self.reminder_sent = kwargs.get('reminder_sent', False)
        self.reminder_date = kwargs.get('reminder_date', '')
        self.confirmation_received = kwargs.get('confirmation_received', False)
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.created_by = kwargs.get('created_by', '')
        self.notes = kwargs.get('notes', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'court_date_id': self.court_date_id,
            'case_id': self.case_id,
            'client_id': self.client_id,
            'hearing_date': self.hearing_date,
            'hearing_time': self.hearing_time,
            'court_name': self.court_name,
            'courtroom': self.courtroom,
            'judge_name': self.judge_name,
            'hearing_type': self.hearing_type,
            'hearing_purpose': self.hearing_purpose,
            'required_attendance': self.required_attendance,
            'attorney_required': self.attorney_required,
            'documents_needed': self.documents_needed,
            'preparation_notes': self.preparation_notes,
            'transportation_arranged': self.transportation_arranged,
            'work_excuse_needed': self.work_excuse_needed,
            'status': self.status,
            'attendance_status': self.attendance_status,
            'outcome': self.outcome,
            'next_hearing_scheduled': self.next_hearing_scheduled,
            'reminder_sent': self.reminder_sent,
            'reminder_date': self.reminder_date,
            'confirmation_received': self.confirmation_received,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'created_by': self.created_by,
            'notes': self.notes
        }
    
    @property
    def days_until_hearing(self) -> Optional[int]:
        """Calculate days until hearing"""
        if not self.hearing_date:
            return None
        try:
            hearing_date = datetime.fromisoformat(self.hearing_date)
            return (hearing_date - datetime.now()).days
        except:
            return None
    
    @property
    def is_upcoming(self) -> bool:
        """Check if hearing is upcoming (within next 30 days)"""
        days_until = self.days_until_hearing
        return days_until is not None and 0 <= days_until <= 30


class LegalDocument:
    """Legal document tracking and generation"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.document_id = kwargs.get('document_id', str(uuid.uuid4()))
        self.case_id = kwargs.get('case_id', '')
        self.client_id = kwargs.get('client_id', '')
        
        # Document Information
        self.document_type = kwargs.get('document_type', '')  # Court Letter, Compliance Report, Expungement Application, etc.
        self.document_title = kwargs.get('document_title', '')
        self.document_purpose = kwargs.get('document_purpose', '')
        self.document_status = kwargs.get('document_status', 'Draft')  # Draft, Generated, Submitted, Approved, Rejected
        
        # Content and Generation
        self.template_used = kwargs.get('template_used', '')
        self.document_content = kwargs.get('document_content', '')
        self.variables_data = kwargs.get('variables_data', '')  # JSON string of template variables
        self.file_path = kwargs.get('file_path', '')
        self.file_format = kwargs.get('file_format', 'PDF')
        
        # Submission and Tracking
        self.submitted_to = kwargs.get('submitted_to', '')
        self.submitted_date = kwargs.get('submitted_date', '')
        self.due_date = kwargs.get('due_date', '')
        self.response_received = kwargs.get('response_received', False)
        self.response_date = kwargs.get('response_date', '')
        self.response_notes = kwargs.get('response_notes', '')
        
        # Related Information
        self.related_court_date = kwargs.get('related_court_date', '')
        self.required_for = kwargs.get('required_for', '')  # Court, Probation, Employer, etc.
        self.urgency_level = kwargs.get('urgency_level', 'Normal')  # Low, Normal, High, Urgent
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.created_by = kwargs.get('created_by', '')
        self.notes = kwargs.get('notes', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'case_id': self.case_id,
            'client_id': self.client_id,
            'document_type': self.document_type,
            'document_title': self.document_title,
            'document_purpose': self.document_purpose,
            'document_status': self.document_status,
            'template_used': self.template_used,
            'document_content': self.document_content,
            'variables_data': self.variables_data,
            'file_path': self.file_path,
            'file_format': self.file_format,
            'submitted_to': self.submitted_to,
            'submitted_date': self.submitted_date,
            'due_date': self.due_date,
            'response_received': self.response_received,
            'response_date': self.response_date,
            'response_notes': self.response_notes,
            'related_court_date': self.related_court_date,
            'required_for': self.required_for,
            'urgency_level': self.urgency_level,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'created_by': self.created_by,
            'notes': self.notes
        }


class LegalDatabase:
    """Legal case management database"""
    
    def __init__(self, db_path: str = "legal_cases.db"):
        self.db_path = db_path
        self.connection = None
        self.create_tables()
    
    def connect(self):
        """Connect to SQLite database"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to legal database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to legal database: {e}")
            raise
    
    def migrate_database(self):
        """Migrate existing database to add missing columns"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Get current columns
            cursor.execute("PRAGMA table_info(legal_cases)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # List of all columns that should exist
            required_columns = [
                ('court_address', 'TEXT'),
                ('judge_name', 'TEXT'),
                ('case_status', 'TEXT DEFAULT "Active"'),
                ('charges', 'TEXT'),
                ('convictions', 'TEXT'),
                ('sentence_details', 'TEXT'),
                ('probation_terms', 'TEXT'),
                ('parole_terms', 'TEXT'),
                ('attorney_name', 'TEXT'),
                ('attorney_phone', 'TEXT'),
                ('attorney_email', 'TEXT'),
                ('attorney_type', 'TEXT'),
                ('probation_officer', 'TEXT'),
                ('probation_phone', 'TEXT'),
                ('probation_email', 'TEXT'),
                ('parole_officer', 'TEXT'),
                ('parole_phone', 'TEXT'),
                ('parole_email', 'TEXT'),
                ('arrest_date', 'TEXT'),
                ('conviction_date', 'TEXT'),
                ('sentence_start_date', 'TEXT'),
                ('probation_start_date', 'TEXT'),
                ('probation_end_date', 'TEXT'),
                ('parole_start_date', 'TEXT'),
                ('parole_end_date', 'TEXT'),
                ('compliance_status', 'TEXT DEFAULT "Compliant"'),
                ('last_compliance_check', 'TEXT'),
                ('compliance_notes', 'TEXT'),
                ('expungement_eligible', 'INTEGER DEFAULT 0'),
                ('expungement_applied', 'INTEGER DEFAULT 0'),
                ('expungement_date', 'TEXT'),
                ('expungement_status', 'TEXT'),
                ('fines_total', 'REAL DEFAULT 0.0'),
                ('fines_paid', 'REAL DEFAULT 0.0'),
                ('restitution_total', 'REAL DEFAULT 0.0'),
                ('restitution_paid', 'REAL DEFAULT 0.0'),
                ('created_at', 'TEXT'),
                ('last_updated', 'TEXT'),
                ('is_active', 'INTEGER DEFAULT 1'),
                ('notes', 'TEXT')
            ]
            
            # Add missing columns
            for column_name, column_definition in required_columns:
                if column_name not in existing_columns:
                    try:
                        # Note: SQLite ALTER TABLE ADD COLUMN doesn't support DEFAULT with spaces
                        # So we add the column and then update defaults if needed
                        base_definition = column_definition.split(' DEFAULT ')[0]
                        cursor.execute(f"ALTER TABLE legal_cases ADD COLUMN {column_name} {base_definition}")
                        logger.info(f"Added column {column_name} to legal_cases table")
                        
                        # Handle default values
                        if 'DEFAULT' in column_definition:
                            default_value = column_definition.split('DEFAULT ')[1].strip('"')
                            if column_name == 'case_status':
                                cursor.execute(f"UPDATE legal_cases SET {column_name} = ? WHERE {column_name} IS NULL", (default_value,))
                            elif column_name == 'compliance_status':
                                cursor.execute(f"UPDATE legal_cases SET {column_name} = ? WHERE {column_name} IS NULL", (default_value,))
                            elif 'INTEGER DEFAULT 0' in column_definition:
                                cursor.execute(f"UPDATE legal_cases SET {column_name} = 0 WHERE {column_name} IS NULL")
                            elif 'REAL DEFAULT 0.0' in column_definition:
                                cursor.execute(f"UPDATE legal_cases SET {column_name} = 0.0 WHERE {column_name} IS NULL")
                                
                    except Exception as e:
                        logger.warning(f"Could not add column {column_name}: {e}")
            
            # Also handle the 'status' -> 'case_status' rename by copying data if needed
            if 'status' in existing_columns and 'case_status' in [col[0] for col in required_columns]:
                cursor.execute("UPDATE legal_cases SET case_status = status WHERE case_status IS NULL")
            
            # Migrate court_dates table
            self._migrate_court_dates_table(cursor)
            
            # Migrate legal_documents table  
            self._migrate_legal_documents_table(cursor)
                
            self.connection.commit()
            logger.info("Database migration completed successfully")
            
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            raise
    
    def _migrate_court_dates_table(self, cursor):
        """Migrate court_dates table to add missing columns"""
        try:
            # Get current columns for court_dates
            cursor.execute("PRAGMA table_info(court_dates)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # Required columns for court_dates
            required_court_date_columns = [
                ('client_id', 'TEXT'),
                ('courtroom', 'TEXT'),
                ('judge_name', 'TEXT'),
                ('hearing_purpose', 'TEXT'),
                ('required_attendance', 'INTEGER DEFAULT 1'),
                ('attorney_required', 'INTEGER DEFAULT 0'),
                ('documents_needed', 'TEXT'),
                ('preparation_notes', 'TEXT'),
                ('transportation_arranged', 'INTEGER DEFAULT 0'),
                ('work_excuse_needed', 'INTEGER DEFAULT 0'),
                ('attendance_status', 'TEXT'),
                ('outcome', 'TEXT'),
                ('next_hearing_scheduled', 'TEXT'),
                ('reminder_sent', 'INTEGER DEFAULT 0'),
                ('reminder_date', 'TEXT'),
                ('confirmation_received', 'INTEGER DEFAULT 0'),
                ('created_at', 'TEXT'),
                ('last_updated', 'TEXT'),
                ('created_by', 'TEXT'),
                ('notes', 'TEXT')
            ]
            
            # Add missing columns to court_dates
            for column_name, column_definition in required_court_date_columns:
                if column_name not in existing_columns:
                    try:
                        base_definition = column_definition.split(' DEFAULT ')[0]
                        cursor.execute(f"ALTER TABLE court_dates ADD COLUMN {column_name} {base_definition}")
                        logger.info(f"Added column {column_name} to court_dates table")
                        
                        # Handle default values
                        if 'DEFAULT' in column_definition:
                            default_value = column_definition.split('DEFAULT ')[1].strip()
                            if 'INTEGER DEFAULT 1' in column_definition:
                                cursor.execute(f"UPDATE court_dates SET {column_name} = 1 WHERE {column_name} IS NULL")
                            elif 'INTEGER DEFAULT 0' in column_definition:
                                cursor.execute(f"UPDATE court_dates SET {column_name} = 0 WHERE {column_name} IS NULL")
                                
                    except Exception as e:
                        logger.warning(f"Could not add column {column_name} to court_dates: {e}")
            
            logger.info("Court dates table migration completed")
            
        except Exception as e:
            logger.error(f"Court dates table migration failed: {e}")
            
    def _migrate_legal_documents_table(self, cursor):
        """Migrate legal_documents table to add missing columns"""
        try:
            # Get current columns for legal_documents
            cursor.execute("PRAGMA table_info(legal_documents)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # Required columns for legal_documents (if needed)
            required_document_columns = [
                ('client_id', 'TEXT'),
                ('document_type', 'TEXT'),
                ('document_title', 'TEXT'),
                ('document_purpose', 'TEXT'),
                ('document_status', 'TEXT DEFAULT "Draft"'),
                ('template_used', 'TEXT'),
                ('document_content', 'TEXT'),
                ('variables_data', 'TEXT'),
                ('file_path', 'TEXT'),
                ('file_format', 'TEXT DEFAULT "PDF"'),
                ('submitted_to', 'TEXT'),
                ('submitted_date', 'TEXT'),
                ('due_date', 'TEXT'),
                ('response_received', 'INTEGER DEFAULT 0'),
                ('response_date', 'TEXT'),
                ('response_notes', 'TEXT'),
                ('related_court_date', 'TEXT'),
                ('required_for', 'TEXT'),
                ('urgency_level', 'TEXT DEFAULT "Normal"'),
                ('created_at', 'TEXT'),
                ('last_updated', 'TEXT'),
                ('created_by', 'TEXT'),
                ('notes', 'TEXT')
            ]
            
            # Add missing columns to legal_documents
            for column_name, column_definition in required_document_columns:
                if column_name not in existing_columns:
                    try:
                        base_definition = column_definition.split(' DEFAULT ')[0]
                        cursor.execute(f"ALTER TABLE legal_documents ADD COLUMN {column_name} {base_definition}")
                        logger.info(f"Added column {column_name} to legal_documents table")
                        
                        # Handle default values
                        if 'DEFAULT' in column_definition:
                            default_value = column_definition.split('DEFAULT ')[1].strip('"')
                            if column_name == 'document_status':
                                cursor.execute(f"UPDATE legal_documents SET {column_name} = ? WHERE {column_name} IS NULL", (default_value,))
                            elif column_name == 'file_format':
                                cursor.execute(f"UPDATE legal_documents SET {column_name} = ? WHERE {column_name} IS NULL", (default_value,))
                            elif column_name == 'urgency_level':
                                cursor.execute(f"UPDATE legal_documents SET {column_name} = ? WHERE {column_name} IS NULL", (default_value,))
                            elif 'INTEGER DEFAULT 0' in column_definition:
                                cursor.execute(f"UPDATE legal_documents SET {column_name} = 0 WHERE {column_name} IS NULL")
                                
                    except Exception as e:
                        logger.warning(f"Could not add column {column_name} to legal_documents: {e}")
            
            logger.info("Legal documents table migration completed")
            
        except Exception as e:
            logger.error(f"Legal documents table migration failed: {e}")

    def create_tables(self):
        """Create legal case management tables"""
        if not self.connection:
            self.connect()
        
        # First try to migrate existing tables
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='legal_cases'")
            if cursor.fetchone():
                logger.info("Existing legal_cases table found, performing migration")
                self.migrate_database()
                return
        except Exception as e:
            logger.warning(f"Migration check failed: {e}")
        
        # Legal cases table
        create_cases_sql = """
        CREATE TABLE IF NOT EXISTS legal_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            case_number TEXT,
            court_name TEXT,
            court_address TEXT,
            judge_name TEXT,
            case_type TEXT,
            case_status TEXT DEFAULT 'Active',
            charges TEXT,
            convictions TEXT,
            sentence_details TEXT,
            probation_terms TEXT,
            parole_terms TEXT,
            attorney_name TEXT,
            attorney_phone TEXT,
            attorney_email TEXT,
            attorney_type TEXT,
            probation_officer TEXT,
            probation_phone TEXT,
            probation_email TEXT,
            parole_officer TEXT,
            parole_phone TEXT,
            parole_email TEXT,
            arrest_date TEXT,
            conviction_date TEXT,
            sentence_start_date TEXT,
            probation_start_date TEXT,
            probation_end_date TEXT,
            parole_start_date TEXT,
            parole_end_date TEXT,
            compliance_status TEXT DEFAULT 'Compliant',
            last_compliance_check TEXT,
            compliance_notes TEXT,
            expungement_eligible INTEGER DEFAULT 0,
            expungement_applied INTEGER DEFAULT 0,
            expungement_date TEXT,
            expungement_status TEXT,
            fines_total REAL DEFAULT 0.0,
            fines_paid REAL DEFAULT 0.0,
            restitution_total REAL DEFAULT 0.0,
            restitution_paid REAL DEFAULT 0.0,
            created_at TEXT,
            last_updated TEXT,
            is_active INTEGER DEFAULT 1,
            notes TEXT
        );
        """
        
        # Court dates table
        create_court_dates_sql = """
        CREATE TABLE IF NOT EXISTS court_dates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            court_date_id TEXT UNIQUE NOT NULL,
            case_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            hearing_date TEXT,
            hearing_time TEXT,
            court_name TEXT,
            courtroom TEXT,
            judge_name TEXT,
            hearing_type TEXT,
            hearing_purpose TEXT,
            required_attendance INTEGER DEFAULT 1,
            attorney_required INTEGER DEFAULT 0,
            documents_needed TEXT,
            preparation_notes TEXT,
            transportation_arranged INTEGER DEFAULT 0,
            work_excuse_needed INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Scheduled',
            attendance_status TEXT,
            outcome TEXT,
            next_hearing_scheduled TEXT,
            reminder_sent INTEGER DEFAULT 0,
            reminder_date TEXT,
            confirmation_received INTEGER DEFAULT 0,
            created_at TEXT,
            last_updated TEXT,
            created_by TEXT,
            notes TEXT,
            FOREIGN KEY (case_id) REFERENCES legal_cases (case_id)
        );
        """
        
        # Legal documents table
        create_documents_sql = """
        CREATE TABLE IF NOT EXISTS legal_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT UNIQUE NOT NULL,
            case_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            document_type TEXT,
            document_title TEXT,
            document_purpose TEXT,
            document_status TEXT DEFAULT 'Draft',
            template_used TEXT,
            document_content TEXT,
            variables_data TEXT,
            file_path TEXT,
            file_format TEXT DEFAULT 'PDF',
            submitted_to TEXT,
            submitted_date TEXT,
            due_date TEXT,
            response_received INTEGER DEFAULT 0,
            response_date TEXT,
            response_notes TEXT,
            related_court_date TEXT,
            required_for TEXT,
            urgency_level TEXT DEFAULT 'Normal',
            created_at TEXT,
            last_updated TEXT,
            created_by TEXT,
            notes TEXT,
            FOREIGN KEY (case_id) REFERENCES legal_cases (case_id)
        );
        """
        
        try:
            self.connection.execute(create_cases_sql)
            self.connection.execute(create_court_dates_sql)
            self.connection.execute(create_documents_sql)
            self.connection.commit()
            logger.info("Legal case management tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create legal tables: {e}")
            raise
    
    def save_legal_case(self, case: LegalCase) -> int:
        """Save a legal case to the database"""
        if not self.connection:
            self.connect()
        
        insert_sql = """
        INSERT INTO legal_cases (
            case_id, client_id, case_number, court_name, court_address, judge_name,
            case_type, case_status, charges, convictions, sentence_details,
            probation_terms, parole_terms, attorney_name, attorney_phone, attorney_email,
            attorney_type, probation_officer, probation_phone, probation_email,
            parole_officer, parole_phone, parole_email, arrest_date, conviction_date,
            sentence_start_date, probation_start_date, probation_end_date,
            parole_start_date, parole_end_date, compliance_status, last_compliance_check,
            compliance_notes, expungement_eligible, expungement_applied, expungement_date,
            expungement_status, fines_total, fines_paid, restitution_total, restitution_paid,
            created_at, last_updated, is_active, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                case.case_id, case.client_id, case.case_number, case.court_name,
                case.court_address, case.judge_name, case.case_type, case.case_status,
                case.charges, case.convictions, case.sentence_details, case.probation_terms,
                case.parole_terms, case.attorney_name, case.attorney_phone, case.attorney_email,
                case.attorney_type, case.probation_officer, case.probation_phone,
                case.probation_email, case.parole_officer, case.parole_phone, case.parole_email,
                case.arrest_date, case.conviction_date, case.sentence_start_date,
                case.probation_start_date, case.probation_end_date, case.parole_start_date,
                case.parole_end_date, case.compliance_status, case.last_compliance_check,
                case.compliance_notes, case.expungement_eligible, case.expungement_applied,
                case.expungement_date, case.expungement_status, case.fines_total,
                case.fines_paid, case.restitution_total, case.restitution_paid,
                case.created_at, case.last_updated, case.is_active, case.notes
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save legal case: {e}")
            raise
    
    def save_court_date(self, court_date: CourtDate) -> int:
        """Save a court date to the database"""
        if not self.connection:
            self.connect()
        
        insert_sql = """
        INSERT INTO court_dates (
            court_date_id, case_id, client_id, hearing_date, hearing_time, court_name,
            courtroom, judge_name, hearing_type, hearing_purpose, required_attendance,
            attorney_required, documents_needed, preparation_notes, transportation_arranged,
            work_excuse_needed, status, attendance_status, outcome, next_hearing_scheduled,
            reminder_sent, reminder_date, confirmation_received, created_at, last_updated,
            created_by, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                court_date.court_date_id, court_date.case_id, court_date.client_id,
                court_date.hearing_date, court_date.hearing_time, court_date.court_name,
                court_date.courtroom, court_date.judge_name, court_date.hearing_type,
                court_date.hearing_purpose, court_date.required_attendance,
                court_date.attorney_required, court_date.documents_needed,
                court_date.preparation_notes, court_date.transportation_arranged,
                court_date.work_excuse_needed, court_date.status, court_date.attendance_status,
                court_date.outcome, court_date.next_hearing_scheduled, court_date.reminder_sent,
                court_date.reminder_date, court_date.confirmation_received, court_date.created_at,
                court_date.last_updated, court_date.created_by, court_date.notes
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save court date: {e}")
            raise
    
    def get_upcoming_court_dates(self, client_id: str = None, days_ahead: int = 30) -> List[CourtDate]:
        """Get upcoming court dates"""
        if not self.connection:
            self.connect()
        
        future_date = (datetime.now() + timedelta(days=days_ahead)).isoformat()
        
        try:
            cursor = self.connection.cursor()
            if client_id:
                cursor.execute("""
                    SELECT * FROM court_dates 
                    WHERE client_id = ? AND hearing_date <= ? AND hearing_date >= datetime('now')
                    AND status = 'Scheduled'
                    ORDER BY hearing_date ASC
                """, (client_id, future_date))
            else:
                cursor.execute("""
                    SELECT * FROM court_dates 
                    WHERE hearing_date <= ? AND hearing_date >= datetime('now')
                    AND status = 'Scheduled'
                    ORDER BY hearing_date ASC
                """, (future_date,))
            
            rows = cursor.fetchall()
            return [CourtDate(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get upcoming court dates: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Legal database connection closed")