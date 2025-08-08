#!/usr/bin/env python3
"""
Expungement Models for Case Management Suite
Comprehensive expungement eligibility, workflow, and document management
"""

import sqlite3
import logging
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class ExpungementEligibilityStatus(Enum):
    """Expungement eligibility status options"""
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    PENDING_REVIEW = "pending_review"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"

class ExpungementProcessStage(Enum):
    """Expungement process stages"""
    INTAKE = "intake"
    ELIGIBILITY_REVIEW = "eligibility_review"
    DOCUMENT_PREPARATION = "document_preparation"
    FILING = "filing"
    COURT_REVIEW = "court_review"
    HEARING_SCHEDULED = "hearing_scheduled"
    HEARING_COMPLETED = "hearing_completed"
    APPROVED = "approved"
    DENIED = "denied"
    COMPLETED = "completed"

class ExpungementServiceTier(Enum):
    """Service tier options"""
    DIY = "diy"
    ASSISTED = "assisted"
    FULL_SERVICE = "full_service"

class ExpungementCase:
    """Comprehensive expungement case management"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.expungement_id = kwargs.get('expungement_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        self.legal_case_id = kwargs.get('legal_case_id', '')
        
        # Basic Case Information
        self.case_number = kwargs.get('case_number', '')
        self.jurisdiction = kwargs.get('jurisdiction', '')  # State/County
        self.court_name = kwargs.get('court_name', '')
        self.offense_date = kwargs.get('offense_date', '')
        self.conviction_date = kwargs.get('conviction_date', '')
        self.offense_type = kwargs.get('offense_type', '')  # Felony, Misdemeanor, Infraction
        self.offense_codes = kwargs.get('offense_codes', '')  # JSON string of offense codes
        self.sentence_completed_date = kwargs.get('sentence_completed_date', '')
        
        # Eligibility Assessment
        self.eligibility_status = kwargs.get('eligibility_status', ExpungementEligibilityStatus.UNKNOWN.value)
        self.eligibility_date = kwargs.get('eligibility_date', '')  # When eligible
        self.wait_period_months = kwargs.get('wait_period_months', 0)
        self.eligibility_notes = kwargs.get('eligibility_notes', '')
        self.disqualifying_factors = kwargs.get('disqualifying_factors', '')  # JSON string
        
        # Process Management
        self.process_stage = kwargs.get('process_stage', ExpungementProcessStage.INTAKE.value)
        self.service_tier = kwargs.get('service_tier', ExpungementServiceTier.DIY.value)
        self.attorney_assigned = kwargs.get('attorney_assigned', '')
        self.case_manager_assigned = kwargs.get('case_manager_assigned', '')
        
        # Document Management
        self.required_documents = kwargs.get('required_documents', '')  # JSON string
        self.completed_documents = kwargs.get('completed_documents', '')  # JSON string
        self.missing_documents = kwargs.get('missing_documents', '')  # JSON string
        
        # Court Filing Information
        self.petition_type = kwargs.get('petition_type', '')  # PC 1203.4, PC 1203.4a, etc.
        self.filing_date = kwargs.get('filing_date', '')
        self.filing_fee = kwargs.get('filing_fee', 0.0)
        self.fee_waiver_requested = kwargs.get('fee_waiver_requested', False)
        self.fee_waiver_approved = kwargs.get('fee_waiver_approved', False)
        
        # Hearing Information
        self.hearing_date = kwargs.get('hearing_date', '')
        self.hearing_time = kwargs.get('hearing_time', '')
        self.hearing_location = kwargs.get('hearing_location', '')
        self.hearing_judge = kwargs.get('hearing_judge', '')
        self.hearing_required = kwargs.get('hearing_required', True)
        
        # Outcome and Status
        self.decision_date = kwargs.get('decision_date', '')
        self.decision_outcome = kwargs.get('decision_outcome', '')  # Granted, Denied, Continued
        self.decision_notes = kwargs.get('decision_notes', '')
        self.appeal_deadline = kwargs.get('appeal_deadline', '')
        
        # Financial Information
        self.total_cost = kwargs.get('total_cost', 0.0)
        self.amount_paid = kwargs.get('amount_paid', 0.0)
        self.payment_plan = kwargs.get('payment_plan', '')
        
        # Communication and Reminders
        self.client_notifications = kwargs.get('client_notifications', '')  # JSON string
        self.reminder_schedule = kwargs.get('reminder_schedule', '')  # JSON string
        self.last_contact_date = kwargs.get('last_contact_date', '')
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.created_by = kwargs.get('created_by', '')
        self.is_active = kwargs.get('is_active', True)
        self.notes = kwargs.get('notes', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'expungement_id': self.expungement_id,
            'client_id': self.client_id,
            'legal_case_id': self.legal_case_id,
            'case_number': self.case_number,
            'jurisdiction': self.jurisdiction,
            'court_name': self.court_name,
            'offense_date': self.offense_date,
            'conviction_date': self.conviction_date,
            'offense_type': self.offense_type,
            'offense_codes': self.offense_codes,
            'sentence_completed_date': self.sentence_completed_date,
            'eligibility_status': self.eligibility_status,
            'eligibility_date': self.eligibility_date,
            'wait_period_months': self.wait_period_months,
            'eligibility_notes': self.eligibility_notes,
            'disqualifying_factors': self.disqualifying_factors,
            'process_stage': self.process_stage,
            'service_tier': self.service_tier,
            'attorney_assigned': self.attorney_assigned,
            'case_manager_assigned': self.case_manager_assigned,
            'required_documents': self.required_documents,
            'completed_documents': self.completed_documents,
            'missing_documents': self.missing_documents,
            'petition_type': self.petition_type,
            'filing_date': self.filing_date,
            'filing_fee': self.filing_fee,
            'fee_waiver_requested': self.fee_waiver_requested,
            'fee_waiver_approved': self.fee_waiver_approved,
            'hearing_date': self.hearing_date,
            'hearing_time': self.hearing_time,
            'hearing_location': self.hearing_location,
            'hearing_judge': self.hearing_judge,
            'hearing_required': self.hearing_required,
            'decision_date': self.decision_date,
            'decision_outcome': self.decision_outcome,
            'decision_notes': self.decision_notes,
            'appeal_deadline': self.appeal_deadline,
            'total_cost': self.total_cost,
            'amount_paid': self.amount_paid,
            'payment_plan': self.payment_plan,
            'client_notifications': self.client_notifications,
            'reminder_schedule': self.reminder_schedule,
            'last_contact_date': self.last_contact_date,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'notes': self.notes
        }
    
    @property
    def is_eligible(self) -> bool:
        """Check if case is eligible for expungement"""
        return self.eligibility_status == ExpungementEligibilityStatus.ELIGIBLE.value
    
    @property
    def days_until_eligible(self) -> Optional[int]:
        """Calculate days until eligible"""
        if not self.eligibility_date:
            return None
        try:
            eligible_date = datetime.fromisoformat(self.eligibility_date)
            return (eligible_date - datetime.now()).days
        except:
            return None
    
    @property
    def balance_due(self) -> float:
        """Calculate remaining balance"""
        return max(0, self.total_cost - self.amount_paid)
    
    @property
    def document_completion_percentage(self) -> float:
        """Calculate document completion percentage"""
        try:
            required = json.loads(self.required_documents) if self.required_documents else []
            completed = json.loads(self.completed_documents) if self.completed_documents else []
            if not required:
                return 100.0
            return (len(completed) / len(required)) * 100
        except:
            return 0.0

class EligibilityRuleSet:
    """Jurisdiction-specific eligibility rules"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.rule_id = kwargs.get('rule_id', str(uuid.uuid4()))
        self.jurisdiction = kwargs.get('jurisdiction', '')  # CA, NY, TX, etc.
        self.jurisdiction_type = kwargs.get('jurisdiction_type', 'state')  # state, county, federal
        
        # Rule Information
        self.rule_name = kwargs.get('rule_name', '')
        self.statute_reference = kwargs.get('statute_reference', '')  # PC 1203.4, CPL 160.59, etc.
        self.effective_date = kwargs.get('effective_date', '')
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        
        # Eligibility Criteria
        self.eligible_offense_types = kwargs.get('eligible_offense_types', '')  # JSON string
        self.ineligible_offense_types = kwargs.get('ineligible_offense_types', '')  # JSON string
        self.wait_period_months = kwargs.get('wait_period_months', 0)
        self.probation_completion_required = kwargs.get('probation_completion_required', True)
        self.fines_payment_required = kwargs.get('fines_payment_required', True)
        self.no_new_convictions_required = kwargs.get('no_new_convictions_required', True)
        
        # Process Requirements
        self.hearing_required = kwargs.get('hearing_required', True)
        self.attorney_required = kwargs.get('attorney_required', False)
        self.filing_fee = kwargs.get('filing_fee', 0.0)
        self.fee_waiver_available = kwargs.get('fee_waiver_available', True)
        
        # Document Requirements
        self.required_documents = kwargs.get('required_documents', '')  # JSON string
        self.optional_documents = kwargs.get('optional_documents', '')  # JSON string
        
        # Timeline Information
        self.typical_processing_days = kwargs.get('typical_processing_days', 90)
        self.hearing_scheduling_days = kwargs.get('hearing_scheduling_days', 30)
        
        # Additional Information
        self.special_conditions = kwargs.get('special_conditions', '')  # JSON string
        self.notes = kwargs.get('notes', '')
        self.is_active = kwargs.get('is_active', True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'jurisdiction': self.jurisdiction,
            'jurisdiction_type': self.jurisdiction_type,
            'rule_name': self.rule_name,
            'statute_reference': self.statute_reference,
            'effective_date': self.effective_date,
            'last_updated': self.last_updated,
            'eligible_offense_types': self.eligible_offense_types,
            'ineligible_offense_types': self.ineligible_offense_types,
            'wait_period_months': self.wait_period_months,
            'probation_completion_required': self.probation_completion_required,
            'fines_payment_required': self.fines_payment_required,
            'no_new_convictions_required': self.no_new_convictions_required,
            'hearing_required': self.hearing_required,
            'attorney_required': self.attorney_required,
            'filing_fee': self.filing_fee,
            'fee_waiver_available': self.fee_waiver_available,
            'required_documents': self.required_documents,
            'optional_documents': self.optional_documents,
            'typical_processing_days': self.typical_processing_days,
            'hearing_scheduling_days': self.hearing_scheduling_days,
            'special_conditions': self.special_conditions,
            'notes': self.notes,
            'is_active': self.is_active
        }

class ExpungementTask:
    """Task management for expungement process"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.task_id = kwargs.get('task_id', str(uuid.uuid4()))
        self.expungement_id = kwargs.get('expungement_id', '')
        self.client_id = kwargs.get('client_id', '')
        
        # Task Information
        self.task_type = kwargs.get('task_type', '')  # document_collection, filing, hearing_prep, etc.
        self.task_title = kwargs.get('task_title', '')
        self.task_description = kwargs.get('task_description', '')
        self.priority = kwargs.get('priority', 'medium')  # low, medium, high, urgent
        self.status = kwargs.get('status', 'pending')  # pending, in_progress, completed, cancelled
        
        # Scheduling
        self.due_date = kwargs.get('due_date', '')
        self.scheduled_date = kwargs.get('scheduled_date', '')
        self.completed_date = kwargs.get('completed_date', '')
        self.estimated_hours = kwargs.get('estimated_hours', 1.0)
        
        # Assignment
        self.assigned_to = kwargs.get('assigned_to', '')  # staff member or client
        self.assigned_type = kwargs.get('assigned_type', 'staff')  # staff, client, attorney
        
        # Dependencies
        self.depends_on = kwargs.get('depends_on', '')  # JSON string of task IDs
        self.blocks_tasks = kwargs.get('blocks_tasks', '')  # JSON string of task IDs
        
        # Reminders and Notifications
        self.reminder_sent = kwargs.get('reminder_sent', False)
        self.reminder_date = kwargs.get('reminder_date', '')
        self.notification_preferences = kwargs.get('notification_preferences', '')  # JSON string
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.created_by = kwargs.get('created_by', '')
        self.notes = kwargs.get('notes', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'expungement_id': self.expungement_id,
            'client_id': self.client_id,
            'task_type': self.task_type,
            'task_title': self.task_title,
            'task_description': self.task_description,
            'priority': self.priority,
            'status': self.status,
            'due_date': self.due_date,
            'scheduled_date': self.scheduled_date,
            'completed_date': self.completed_date,
            'estimated_hours': self.estimated_hours,
            'assigned_to': self.assigned_to,
            'assigned_type': self.assigned_type,
            'depends_on': self.depends_on,
            'blocks_tasks': self.blocks_tasks,
            'reminder_sent': self.reminder_sent,
            'reminder_date': self.reminder_date,
            'notification_preferences': self.notification_preferences,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'created_by': self.created_by,
            'notes': self.notes
        }
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date or self.status == 'completed':
            return False
        try:
            due_date = datetime.fromisoformat(self.due_date)
            return datetime.now() > due_date
        except:
            return False
    
    @property
    def days_until_due(self) -> Optional[int]:
        """Calculate days until due"""
        if not self.due_date:
            return None
        try:
            due_date = datetime.fromisoformat(self.due_date)
            return (due_date - datetime.now()).days
        except:
            return None

class ExpungementDatabase:
    """Database operations for expungement management"""
    
    def __init__(self, db_path: str = "databases/expungement.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize expungement database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Expungement Cases table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS expungement_cases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        expungement_id TEXT UNIQUE NOT NULL,
                        client_id TEXT NOT NULL,
                        legal_case_id TEXT,
                        case_number TEXT,
                        jurisdiction TEXT,
                        court_name TEXT,
                        offense_date TEXT,
                        conviction_date TEXT,
                        offense_type TEXT,
                        offense_codes TEXT,
                        sentence_completed_date TEXT,
                        eligibility_status TEXT,
                        eligibility_date TEXT,
                        wait_period_months INTEGER DEFAULT 0,
                        eligibility_notes TEXT,
                        disqualifying_factors TEXT,
                        process_stage TEXT,
                        service_tier TEXT,
                        attorney_assigned TEXT,
                        case_manager_assigned TEXT,
                        required_documents TEXT,
                        completed_documents TEXT,
                        missing_documents TEXT,
                        petition_type TEXT,
                        filing_date TEXT,
                        filing_fee REAL DEFAULT 0.0,
                        fee_waiver_requested BOOLEAN DEFAULT FALSE,
                        fee_waiver_approved BOOLEAN DEFAULT FALSE,
                        hearing_date TEXT,
                        hearing_time TEXT,
                        hearing_location TEXT,
                        hearing_judge TEXT,
                        hearing_required BOOLEAN DEFAULT TRUE,
                        decision_date TEXT,
                        decision_outcome TEXT,
                        decision_notes TEXT,
                        appeal_deadline TEXT,
                        total_cost REAL DEFAULT 0.0,
                        amount_paid REAL DEFAULT 0.0,
                        payment_plan TEXT,
                        client_notifications TEXT,
                        reminder_schedule TEXT,
                        last_contact_date TEXT,
                        created_at TEXT,
                        last_updated TEXT,
                        created_by TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        notes TEXT
                    )
                ''')
                
                # Eligibility Rules table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS eligibility_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rule_id TEXT UNIQUE NOT NULL,
                        jurisdiction TEXT NOT NULL,
                        jurisdiction_type TEXT,
                        rule_name TEXT,
                        statute_reference TEXT,
                        effective_date TEXT,
                        last_updated TEXT,
                        eligible_offense_types TEXT,
                        ineligible_offense_types TEXT,
                        wait_period_months INTEGER DEFAULT 0,
                        probation_completion_required BOOLEAN DEFAULT TRUE,
                        fines_payment_required BOOLEAN DEFAULT TRUE,
                        no_new_convictions_required BOOLEAN DEFAULT TRUE,
                        hearing_required BOOLEAN DEFAULT TRUE,
                        attorney_required BOOLEAN DEFAULT FALSE,
                        filing_fee REAL DEFAULT 0.0,
                        fee_waiver_available BOOLEAN DEFAULT TRUE,
                        required_documents TEXT,
                        optional_documents TEXT,
                        typical_processing_days INTEGER DEFAULT 90,
                        hearing_scheduling_days INTEGER DEFAULT 30,
                        special_conditions TEXT,
                        notes TEXT,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                # Expungement Tasks table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS expungement_tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT UNIQUE NOT NULL,
                        expungement_id TEXT NOT NULL,
                        client_id TEXT NOT NULL,
                        task_type TEXT,
                        task_title TEXT,
                        task_description TEXT,
                        priority TEXT DEFAULT 'medium',
                        status TEXT DEFAULT 'pending',
                        due_date TEXT,
                        scheduled_date TEXT,
                        completed_date TEXT,
                        estimated_hours REAL DEFAULT 1.0,
                        assigned_to TEXT,
                        assigned_type TEXT DEFAULT 'staff',
                        depends_on TEXT,
                        blocks_tasks TEXT,
                        reminder_sent BOOLEAN DEFAULT FALSE,
                        reminder_date TEXT,
                        notification_preferences TEXT,
                        created_at TEXT,
                        last_updated TEXT,
                        created_by TEXT,
                        notes TEXT
                    )
                ''')
                
                conn.commit()
                logger.info("Expungement database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def save_expungement_case(self, case: ExpungementCase) -> str:
        """Save expungement case to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                case_dict = case.to_dict()
                case_dict.pop('id', None)  # Remove id for insert
                
                columns = ', '.join(case_dict.keys())
                placeholders = ', '.join(['?' for _ in case_dict])
                values = list(case_dict.values())
                
                cursor.execute(f'''
                    INSERT INTO expungement_cases ({columns})
                    VALUES ({placeholders})
                ''', values)
                
                conn.commit()
                return case.expungement_id
                
        except Exception as e:
            logger.error(f"Save expungement case error: {e}")
            raise
    
    def get_expungement_cases(self, client_id: Optional[str] = None) -> List[ExpungementCase]:
        """Get expungement cases from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if client_id:
                    cursor.execute('''
                        SELECT * FROM expungement_cases 
                        WHERE client_id = ? AND is_active = TRUE
                        ORDER BY created_at DESC
                    ''', (client_id,))
                else:
                    cursor.execute('''
                        SELECT * FROM expungement_cases 
                        WHERE is_active = TRUE
                        ORDER BY created_at DESC
                    ''')
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                cases = []
                for row in rows:
                    case_dict = dict(zip(columns, row))
                    cases.append(ExpungementCase(**case_dict))
                
                return cases
                
        except Exception as e:
            logger.error(f"Get expungement cases error: {e}")
            return []
    
    def save_expungement_task(self, task: ExpungementTask) -> str:
        """Save expungement task to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                task_dict = task.to_dict()
                task_dict.pop('id', None)  # Remove id for insert
                
                columns = ', '.join(task_dict.keys())
                placeholders = ', '.join(['?' for _ in task_dict])
                values = list(task_dict.values())
                
                cursor.execute(f'''
                    INSERT INTO expungement_tasks ({columns})
                    VALUES ({placeholders})
                ''', values)
                
                conn.commit()
                return task.task_id
                
        except Exception as e:
            logger.error(f"Save expungement task error: {e}")
            raise
    
    def get_expungement_tasks(self, expungement_id: Optional[str] = None, client_id: Optional[str] = None) -> List[ExpungementTask]:
        """Get expungement tasks from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if expungement_id:
                    cursor.execute('''
                        SELECT * FROM expungement_tasks 
                        WHERE expungement_id = ?
                        ORDER BY due_date ASC, priority DESC
                    ''', (expungement_id,))
                elif client_id:
                    cursor.execute('''
                        SELECT * FROM expungement_tasks 
                        WHERE client_id = ?
                        ORDER BY due_date ASC, priority DESC
                    ''', (client_id,))
                else:
                    cursor.execute('''
                        SELECT * FROM expungement_tasks 
                        ORDER BY due_date ASC, priority DESC
                    ''')
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                tasks = []
                for row in rows:
                    task_dict = dict(zip(columns, row))
                    tasks.append(ExpungementTask(**task_dict))
                
                return tasks
                
        except Exception as e:
            logger.error(f"Get expungement tasks error: {e}")
            return []