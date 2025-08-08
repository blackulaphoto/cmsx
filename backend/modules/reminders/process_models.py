#!/usr/bin/env python3
"""
Intelligent Daily Task Distribution System
Advanced process automation and smart workload management
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import uuid
from .models import ReminderDatabase

logger = logging.getLogger(__name__)

class ProcessTemplate:
    """Template for complex multi-step processes"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.template_id = kwargs.get('template_id', str(uuid.uuid4()))
        self.process_name = kwargs.get('process_name', '')
        self.process_type = kwargs.get('process_type', '')  # disability_claim, housing_search, employment_prep
        self.estimated_weeks = kwargs.get('estimated_weeks', 4)
        self.estimated_total_hours = kwargs.get('estimated_total_hours', 20)
        
        # Process steps by week
        self.steps = kwargs.get('steps', {})  # {week_1: [tasks], week_2: [tasks]}
        
        # Prerequisites and dependencies
        self.prerequisites = kwargs.get('prerequisites', [])
        self.dependencies = kwargs.get('dependencies', [])
        
        # Success criteria
        self.success_criteria = kwargs.get('success_criteria', [])
        self.completion_indicators = kwargs.get('completion_indicators', [])
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.is_active = kwargs.get('is_active', True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'template_id': self.template_id,
            'process_name': self.process_name,
            'process_type': self.process_type,
            'estimated_weeks': self.estimated_weeks,
            'estimated_total_hours': self.estimated_total_hours,
            'steps': self.steps,
            'prerequisites': self.prerequisites,
            'dependencies': self.dependencies,
            'success_criteria': self.success_criteria,
            'completion_indicators': self.completion_indicators,
            'created_at': self.created_at,
            'is_active': self.is_active
        }

class ClientProcess:
    """Active process for a specific client"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.process_id = kwargs.get('process_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        self.case_manager_id = kwargs.get('case_manager_id', '')
        self.template_id = kwargs.get('template_id', '')
        
        # Process details
        self.process_type = kwargs.get('process_type', '')
        self.process_name = kwargs.get('process_name', '')
        self.priority_level = kwargs.get('priority_level', 'Medium')  # Critical, High, Medium, Low
        self.urgency_factor = kwargs.get('urgency_factor', 1.0)
        
        # Timeline
        self.started_date = kwargs.get('started_date', datetime.now().isoformat())
        self.target_completion_date = kwargs.get('target_completion_date', '')
        self.actual_completion_date = kwargs.get('actual_completion_date', '')
        
        # Progress tracking
        self.current_week = kwargs.get('current_week', 1)
        self.current_step = kwargs.get('current_step', 0)
        self.completion_percentage = kwargs.get('completion_percentage', 0)
        self.status = kwargs.get('status', 'Active')  # Active, Completed, Paused, Cancelled
        
        # Context and notes
        self.context = kwargs.get('context', {})  # Client-specific context
        self.barriers_encountered = kwargs.get('barriers_encountered', [])
        self.adaptations_made = kwargs.get('adaptations_made', [])
        self.notes = kwargs.get('notes', '')
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.updated_at = kwargs.get('updated_at', datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'process_id': self.process_id,
            'client_id': self.client_id,
            'case_manager_id': self.case_manager_id,
            'template_id': self.template_id,
            'process_type': self.process_type,
            'process_name': self.process_name,
            'priority_level': self.priority_level,
            'urgency_factor': self.urgency_factor,
            'started_date': self.started_date,
            'target_completion_date': self.target_completion_date,
            'actual_completion_date': self.actual_completion_date,
            'current_week': self.current_week,
            'current_step': self.current_step,
            'completion_percentage': self.completion_percentage,
            'status': self.status,
            'context': self.context,
            'barriers_encountered': self.barriers_encountered,
            'adaptations_made': self.adaptations_made,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class DistributedTask:
    """Individual task distributed across daily schedule"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.task_id = kwargs.get('task_id', str(uuid.uuid4()))
        self.case_manager_id = kwargs.get('case_manager_id', '')
        self.client_id = kwargs.get('client_id', '')
        self.process_id = kwargs.get('process_id', '')
        
        # Task details
        self.task_type = kwargs.get('task_type', '')  # phone_call, appointment, paperwork, follow_up
        self.task_description = kwargs.get('task_description', '')
        self.task_context = kwargs.get('task_context', '')
        self.expected_outcome = kwargs.get('expected_outcome', '')
        
        # Scheduling
        self.scheduled_date = kwargs.get('scheduled_date', '')
        self.scheduled_time = kwargs.get('scheduled_time', '')
        self.estimated_minutes = kwargs.get('estimated_minutes', 30)
        self.actual_minutes = kwargs.get('actual_minutes', 0)
        
        # Priority and urgency
        self.priority_level = kwargs.get('priority_level', 'Medium')
        self.urgency_score = kwargs.get('urgency_score', 0)
        self.deadline = kwargs.get('deadline', '')
        
        # Status tracking
        self.status = kwargs.get('status', 'Scheduled')  # Scheduled, In Progress, Completed, Cancelled, Rescheduled
        self.completion_date = kwargs.get('completion_date', '')
        self.completion_notes = kwargs.get('completion_notes', '')
        self.outcome = kwargs.get('outcome', '')
        
        # Dependencies
        self.prerequisite_tasks = kwargs.get('prerequisite_tasks', [])
        self.blocks_tasks = kwargs.get('blocks_tasks', [])
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.updated_at = kwargs.get('updated_at', datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'case_manager_id': self.case_manager_id,
            'client_id': self.client_id,
            'process_id': self.process_id,
            'task_type': self.task_type,
            'task_description': self.task_description,
            'task_context': self.task_context,
            'expected_outcome': self.expected_outcome,
            'scheduled_date': self.scheduled_date,
            'scheduled_time': self.scheduled_time,
            'estimated_minutes': self.estimated_minutes,
            'actual_minutes': self.actual_minutes,
            'priority_level': self.priority_level,
            'urgency_score': self.urgency_score,
            'deadline': self.deadline,
            'status': self.status,
            'completion_date': self.completion_date,
            'completion_notes': self.completion_notes,
            'outcome': self.outcome,
            'prerequisite_tasks': self.prerequisite_tasks,
            'blocks_tasks': self.blocks_tasks,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class ProcessDatabase:
    """Database for process templates and distributed tasks"""
    
    def __init__(self, reminder_db: ReminderDatabase):
        self.reminder_db = reminder_db
        self.connection = reminder_db.connection
        self.create_process_tables()
    
    def create_process_tables(self):
        """Create process management tables"""
        
        # Process Templates Table
        process_templates_sql = """
        CREATE TABLE IF NOT EXISTS process_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id TEXT UNIQUE NOT NULL,
            process_name TEXT NOT NULL,
            process_type TEXT NOT NULL,
            estimated_weeks INTEGER DEFAULT 4,
            estimated_total_hours INTEGER DEFAULT 20,
            steps TEXT,
            prerequisites TEXT,
            dependencies TEXT,
            success_criteria TEXT,
            completion_indicators TEXT,
            created_at TEXT,
            is_active INTEGER DEFAULT 1
        );
        """
        
        # Client Processes Table
        client_processes_sql = """
        CREATE TABLE IF NOT EXISTS client_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            process_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            case_manager_id TEXT NOT NULL,
            template_id TEXT NOT NULL,
            process_type TEXT NOT NULL,
            process_name TEXT NOT NULL,
            priority_level TEXT DEFAULT 'Medium',
            urgency_factor REAL DEFAULT 1.0,
            started_date TEXT NOT NULL,
            target_completion_date TEXT,
            actual_completion_date TEXT,
            current_week INTEGER DEFAULT 1,
            current_step INTEGER DEFAULT 0,
            completion_percentage REAL DEFAULT 0,
            status TEXT DEFAULT 'Active',
            context TEXT,
            barriers_encountered TEXT,
            adaptations_made TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
        
        # Distributed Tasks Table
        distributed_tasks_sql = """
        CREATE TABLE IF NOT EXISTS distributed_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            case_manager_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            process_id TEXT,
            task_type TEXT NOT NULL,
            task_description TEXT NOT NULL,
            task_context TEXT,
            expected_outcome TEXT,
            scheduled_date TEXT NOT NULL,
            scheduled_time TEXT,
            estimated_minutes INTEGER DEFAULT 30,
            actual_minutes INTEGER DEFAULT 0,
            priority_level TEXT DEFAULT 'Medium',
            urgency_score INTEGER DEFAULT 0,
            deadline TEXT,
            status TEXT DEFAULT 'Scheduled',
            completion_date TEXT,
            completion_notes TEXT,
            outcome TEXT,
            prerequisite_tasks TEXT,
            blocks_tasks TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
        
        try:
            self.connection.execute(process_templates_sql)
            self.connection.execute(client_processes_sql)
            self.connection.execute(distributed_tasks_sql)
            
            # Create indexes
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_processes_client ON client_processes(client_id)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_case_manager_date ON distributed_tasks(case_manager_id, scheduled_date)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON distributed_tasks(status)")
            
            self.connection.commit()
            logger.info("Process management tables created successfully")
            
            # Insert default templates
            self._insert_default_templates()
            
        except Exception as e:
            logger.error(f"Failed to create process tables: {e}")
            raise
    
    def _insert_default_templates(self):
        """Insert default process templates"""
        
        default_templates = [
            {
                'template_id': 'disability_claim_process',
                'process_name': 'Disability Claim Filing',
                'process_type': 'disability_claim',
                'estimated_weeks': 4,
                'estimated_total_hours': 25,
                'steps': {
                    'week_1': [
                        {'task': 'Get state ID/documents', 'type': 'appointment', 'minutes': 120},
                        {'task': 'Request medical records (3-5 providers)', 'type': 'phone_call', 'minutes': 90},
                        {'task': 'Contact previous doctors', 'type': 'phone_call', 'minutes': 60}
                    ],
                    'week_2': [
                        {'task': 'Follow up on pending records', 'type': 'phone_call', 'minutes': 45},
                        {'task': 'Complete disability application', 'type': 'paperwork', 'minutes': 180},
                        {'task': 'Gather supporting documents', 'type': 'paperwork', 'minutes': 60}
                    ],
                    'week_3': [
                        {'task': 'Submit disability claim', 'type': 'paperwork', 'minutes': 30},
                        {'task': 'Get confirmation receipt', 'type': 'follow_up', 'minutes': 15},
                        {'task': 'Start housing search (SSI-eligible)', 'type': 'research', 'minutes': 120}
                    ],
                    'week_4': [
                        {'task': 'Housing applications', 'type': 'paperwork', 'minutes': 90},
                        {'task': 'Follow up on disability status', 'type': 'phone_call', 'minutes': 30},
                        {'task': 'Prepare for appeal if needed', 'type': 'paperwork', 'minutes': 60}
                    ]
                },
                'prerequisites': ['Valid ID', 'Contact information for medical providers'],
                'success_criteria': ['Disability claim filed', 'Receipt confirmation obtained'],
                'completion_indicators': ['Claim number received', 'Housing applications submitted']
            },
            {
                'template_id': 'urgent_housing_search',
                'process_name': 'Urgent Housing Search',
                'process_type': 'housing_search',
                'estimated_weeks': 1,
                'estimated_total_hours': 15,
                'steps': {
                    'day_1': [
                        {'task': 'Call 5 emergency housing options', 'type': 'phone_call', 'minutes': 90},
                        {'task': 'Complete 3 applications', 'type': 'paperwork', 'minutes': 120},
                        {'task': 'Gather required documents', 'type': 'paperwork', 'minutes': 45}
                    ],
                    'day_2': [
                        {'task': 'Follow up with landlords', 'type': 'phone_call', 'minutes': 60},
                        {'task': 'Submit additional applications', 'type': 'paperwork', 'minutes': 90},
                        {'task': 'Schedule viewings', 'type': 'phone_call', 'minutes': 30}
                    ],
                    'day_3': [
                        {'task': 'Attend viewings', 'type': 'appointment', 'minutes': 180},
                        {'task': 'Submit final applications', 'type': 'paperwork', 'minutes': 60}
                    ]
                },
                'prerequisites': ['ID', 'Income verification', 'References'],
                'success_criteria': ['Housing secured', 'Move-in date confirmed'],
                'completion_indicators': ['Lease signed', 'First payment made']
            },
            {
                'template_id': 'employment_preparation',
                'process_name': 'Employment Preparation',
                'process_type': 'employment_prep',
                'estimated_weeks': 2,
                'estimated_total_hours': 12,
                'steps': {
                    'week_1': [
                        {'task': 'Resume creation/update', 'type': 'paperwork', 'minutes': 120},
                        {'task': 'Job search training', 'type': 'appointment', 'minutes': 90},
                        {'task': 'Interview preparation', 'type': 'appointment', 'minutes': 60}
                    ],
                    'week_2': [
                        {'task': 'Apply to 10+ positions', 'type': 'paperwork', 'minutes': 180},
                        {'task': 'Follow up on applications', 'type': 'phone_call', 'minutes': 60},
                        {'task': 'Schedule interviews', 'type': 'phone_call', 'minutes': 30}
                    ]
                },
                'prerequisites': ['Work-appropriate clothing', 'Transportation plan'],
                'success_criteria': ['Resume completed', 'At least 10 applications submitted'],
                'completion_indicators': ['Interview scheduled', 'Job offers received']
            }
        ]
        
        for template_data in default_templates:
            template = ProcessTemplate(**template_data)
            self.save_process_template(template)
        
        logger.info("Default process templates created successfully")
    
    def save_process_template(self, template: ProcessTemplate) -> int:
        """Save a process template"""
        insert_sql = """
        INSERT OR REPLACE INTO process_templates (
            template_id, process_name, process_type, estimated_weeks, estimated_total_hours,
            steps, prerequisites, dependencies, success_criteria, completion_indicators,
            created_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                template.template_id, template.process_name, template.process_type,
                template.estimated_weeks, template.estimated_total_hours,
                json.dumps(template.steps), json.dumps(template.prerequisites),
                json.dumps(template.dependencies), json.dumps(template.success_criteria),
                json.dumps(template.completion_indicators), template.created_at, template.is_active
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save process template: {e}")
            raise
    
    def save_client_process(self, process: ClientProcess) -> int:
        """Save a client process"""
        insert_sql = """
        INSERT OR REPLACE INTO client_processes (
            process_id, client_id, case_manager_id, template_id, process_type, process_name,
            priority_level, urgency_factor, started_date, target_completion_date,
            actual_completion_date, current_week, current_step, completion_percentage,
            status, context, barriers_encountered, adaptations_made, notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                process.process_id, process.client_id, process.case_manager_id,
                process.template_id, process.process_type, process.process_name,
                process.priority_level, process.urgency_factor, process.started_date,
                process.target_completion_date, process.actual_completion_date,
                process.current_week, process.current_step, process.completion_percentage,
                process.status, json.dumps(process.context), json.dumps(process.barriers_encountered),
                json.dumps(process.adaptations_made), process.notes, process.created_at, process.updated_at
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save client process: {e}")
            raise
    
    def save_distributed_task(self, task: DistributedTask) -> int:
        """Save a distributed task"""
        insert_sql = """
        INSERT OR REPLACE INTO distributed_tasks (
            task_id, case_manager_id, client_id, process_id, task_type, task_description,
            task_context, expected_outcome, scheduled_date, scheduled_time,
            estimated_minutes, actual_minutes, priority_level, urgency_score,
            deadline, status, completion_date, completion_notes, outcome,
            prerequisite_tasks, blocks_tasks, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                task.task_id, task.case_manager_id, task.client_id, task.process_id,
                task.task_type, task.task_description, task.task_context,
                task.expected_outcome, task.scheduled_date, task.scheduled_time,
                task.estimated_minutes, task.actual_minutes, task.priority_level,
                task.urgency_score, task.deadline, task.status, task.completion_date,
                task.completion_notes, task.outcome, json.dumps(task.prerequisite_tasks),
                json.dumps(task.blocks_tasks), task.created_at, task.updated_at
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save distributed task: {e}")
            raise
    
    def get_process_template(self, template_id: str) -> Optional[ProcessTemplate]:
        """Get a process template by ID"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM process_templates WHERE template_id = ?", (template_id,))
            row = cursor.fetchone()
            
            if row:
                template_dict = dict(row)
                template_dict['steps'] = json.loads(template_dict['steps'])
                template_dict['prerequisites'] = json.loads(template_dict['prerequisites'])
                template_dict['dependencies'] = json.loads(template_dict['dependencies'])
                template_dict['success_criteria'] = json.loads(template_dict['success_criteria'])
                template_dict['completion_indicators'] = json.loads(template_dict['completion_indicators'])
                return ProcessTemplate(**template_dict)
            return None
        except Exception as e:
            logger.error(f"Failed to get process template: {e}")
            return None
    
    def get_client_processes(self, client_id: str) -> List[ClientProcess]:
        """Get all active processes for a client"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM client_processes 
                WHERE client_id = ? AND status = 'Active'
                ORDER BY priority_level DESC, started_date ASC
            """, (client_id,))
            
            rows = cursor.fetchall()
            processes = []
            for row in rows:
                process_dict = dict(row)
                process_dict['context'] = json.loads(process_dict['context'] or '{}')
                process_dict['barriers_encountered'] = json.loads(process_dict['barriers_encountered'] or '[]')
                process_dict['adaptations_made'] = json.loads(process_dict['adaptations_made'] or '[]')
                processes.append(ClientProcess(**process_dict))
            return processes
        except Exception as e:
            logger.error(f"Failed to get client processes: {e}")
            return []
    
    def get_daily_tasks(self, case_manager_id: str, date: str) -> List[DistributedTask]:
        """Get all tasks for a specific date"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM distributed_tasks 
                WHERE case_manager_id = ? AND scheduled_date = ?
                ORDER BY priority_level DESC, urgency_score DESC, scheduled_time ASC
            """, (case_manager_id, date))
            
            rows = cursor.fetchall()
            tasks = []
            for row in rows:
                task_dict = dict(row)
                task_dict['prerequisite_tasks'] = json.loads(task_dict['prerequisite_tasks'] or '[]')
                task_dict['blocks_tasks'] = json.loads(task_dict['blocks_tasks'] or '[]')
                tasks.append(DistributedTask(**task_dict))
            return tasks
        except Exception as e:
            logger.error(f"Failed to get daily tasks: {e}")
            return []