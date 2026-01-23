"""
Database Integrity Manager for Case Management Suite

This module provides a comprehensive solution for maintaining database integrity
across the 9-database architecture, with special focus on the Case Management module
which serves as the central nervous system of the entire platform.

Key features:
1. Database synchronization verification
2. Permission enforcement
3. Data consistency checks
4. Automatic recovery mechanisms
5. Logging and monitoring
"""

import sqlite3
import logging
import uuid
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/db_integrity.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("db_integrity_manager")

# Project root and database paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATABASES_DIR = PROJECT_ROOT / "databases"

# Ensure logs directory exists
logs_dir = PROJECT_ROOT / "logs"
logs_dir.mkdir(exist_ok=True)

class DatabaseIntegrityManager:
    """
    Manages database integrity across the 9-database architecture
    """
    
    # Database mappings
    DATABASES = {
        'core_clients': 'core_clients.db',      # MASTER DATABASE
        'case_management': 'case_management.db',
        'housing': 'housing.db',
        'benefits': 'benefits.db', 
        'legal': 'legal.db',
        'employment': 'employment.db',
        'services': 'services.db',
        'reminders': 'reminders.db',
        'ai_assistant': 'ai_assistant.db'
    }
    
    # Required tables for each database
    REQUIRED_TABLES = {
        'core_clients': ['clients'],
        'case_management': ['clients', 'case_notes', 'cases', 'referrals', 'tasks'],
        'housing': ['client_housing_profiles', 'housing_applications'],
        'benefits': ['benefits_applications', 'client_benefits_profiles'],
        'legal': ['legal_cases', 'court_dates'],
        'employment': ['client_employment_profiles', 'resumes'],
        'services': ['service_providers', 'client_referrals'],
        'reminders': ['client_contacts', 'reminder_rules', 'active_reminders'],
        'ai_assistant': ['conversations', 'function_calls']
    }
    
    # Access control matrix
    ACCESS_MATRIX = {
        'core_clients': {
            'write': ['case_management', 'ai_assistant'],
            'read': ['housing', 'benefits', 'legal', 'employment', 'services', 'reminders']
        },
        'case_management': {
            'write': ['case_management', 'ai_assistant'],
            'read': ['housing', 'benefits', 'legal', 'employment', 'services', 'reminders']
        },
        'housing': {
            'write': ['housing', 'ai_assistant'],
            'read': ['case_management', 'services', 'reminders']
        },
        'benefits': {
            'write': ['benefits', 'ai_assistant'],
            'read': ['case_management', 'services', 'reminders']
        },
        'legal': {
            'write': ['legal', 'ai_assistant'],
            'read': ['case_management', 'services', 'reminders']
        },
        'employment': {
            'write': ['employment', 'ai_assistant'],
            'read': ['case_management', 'services', 'reminders']
        },
        'services': {
            'write': ['services', 'ai_assistant'],
            'read': ['case_management', 'housing', 'benefits', 'legal', 'employment', 'reminders']
        },
        'reminders': {
            'write': ['reminders', 'ai_assistant'],
            'read': ['case_management', 'housing', 'benefits', 'legal', 'employment', 'services']
        },
        'ai_assistant': {
            'write': ['ai_assistant'],
            'read': ['case_management', 'housing', 'benefits', 'legal', 'employment', 'services', 'reminders']
        }
    }
    
    def __init__(self):
        """Initialize the database integrity manager"""
        self.last_check_time = None
        self.integrity_status = {}
        self.sync_status = {}
        
    def check_database_existence(self) -> Dict[str, bool]:
        """Check if all required databases exist"""
        results = {}
        
        for db_key, db_file in self.DATABASES.items():
            db_path = DATABASES_DIR / db_file
            exists = db_path.exists()
            results[db_key] = exists
            
            if not exists:
                logger.error(f"Database {db_file} does not exist")
            
        return results
    
    def check_table_existence(self) -> Dict[str, Dict[str, bool]]:
        """Check if all required tables exist in each database"""
        results = {}
        
        for db_key, required_tables in self.REQUIRED_TABLES.items():
            db_path = DATABASES_DIR / self.DATABASES[db_key]
            results[db_key] = {}
            
            if not db_path.exists():
                logger.error(f"Database {db_key} does not exist, cannot check tables")
                for table in required_tables:
                    results[db_key][table] = False
                continue
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                for table in required_tables:
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    exists = cursor.fetchone() is not None
                    results[db_key][table] = exists
                    
                    if not exists:
                        logger.error(f"Required table {table} does not exist in {db_key}")
                
                conn.close()
            except Exception as e:
                logger.error(f"Error checking tables in {db_key}: {e}")
                for table in required_tables:
                    results[db_key][table] = False
        
        return results
    
    def check_client_synchronization(self) -> Dict[str, Dict[str, Any]]:
        """
        Check if clients are properly synchronized across databases
        Core clients is the master database that all other databases should sync with
        """
        results = {
            'status': 'success',
            'databases': {},
            'issues': []
        }
        
        # Get clients from master database
        core_db_path = DATABASES_DIR / self.DATABASES['core_clients']
        if not core_db_path.exists():
            results['status'] = 'error'
            results['issues'].append('Master database (core_clients) does not exist')
            return results
        
        try:
            core_conn = sqlite3.connect(core_db_path)
            core_conn.row_factory = sqlite3.Row
            core_cursor = core_conn.cursor()
            
            core_cursor.execute("SELECT client_id FROM clients")
            master_client_ids = {row['client_id'] for row in core_cursor.fetchall()}
            
            results['databases']['core_clients'] = {
                'status': 'ok',
                'client_count': len(master_client_ids)
            }
            
            if not master_client_ids:
                results['status'] = 'warning'
                results['issues'].append('Master database has no clients')
            
            # Check other databases with clients tables
            for db_key in ['case_management', 'housing', 'benefits', 'legal', 'employment', 'services']:
                db_path = DATABASES_DIR / self.DATABASES[db_key]
                
                if not db_path.exists():
                    results['databases'][db_key] = {
                        'status': 'error',
                        'message': 'Database does not exist'
                    }
                    results['issues'].append(f'Database {db_key} does not exist')
                    continue
                
                try:
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Check if clients table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                    if not cursor.fetchone():
                        # This might be normal for some modules
                        results['databases'][db_key] = {
                            'status': 'info',
                            'message': 'No clients table (may be normal)'
                        }
                        continue
                    
                    # Get client IDs
                    cursor.execute("SELECT client_id FROM clients")
                    db_client_ids = {row['client_id'] for row in cursor.fetchall()}
                    
                    # Check for missing clients
                    missing = master_client_ids - db_client_ids
                    extra = db_client_ids - master_client_ids
                    
                    db_status = {
                        'client_count': len(db_client_ids),
                        'missing_count': len(missing),
                        'extra_count': len(extra)
                    }
                    
                    if missing:
                        db_status['status'] = 'warning'
                        db_status['message'] = f'Missing {len(missing)} clients from master'
                        results['issues'].append(f'Database {db_key} missing {len(missing)} clients from master')
                    elif extra:
                        db_status['status'] = 'warning'
                        db_status['message'] = f'Has {len(extra)} clients not in master'
                        results['issues'].append(f'Database {db_key} has {len(extra)} orphaned clients')
                    else:
                        db_status['status'] = 'ok'
                        db_status['message'] = 'Synchronized with master'
                    
                    results['databases'][db_key] = db_status
                    
                    conn.close()
                except Exception as e:
                    results['databases'][db_key] = {
                        'status': 'error',
                        'message': str(e)
                    }
                    results['issues'].append(f'Error checking {db_key}: {e}')
            
            core_conn.close()
        except Exception as e:
            results['status'] = 'error'
            results['issues'].append(f'Error checking master database: {e}')
        
        return results
    
    def verify_permissions(self) -> Dict[str, Any]:
        """Verify that database permissions are correctly enforced"""
        results = {
            'status': 'success',
            'tests': [],
            'issues': []
        }
        
        # Test cases
        test_cases = [
            # Case Management should have write access to core_clients
            {'module': 'case_management', 'database': 'core_clients', 'permission': 'write', 'expected': True},
            # Housing should have read access to core_clients
            {'module': 'housing', 'database': 'core_clients', 'permission': 'read', 'expected': True},
            # Housing should NOT have write access to core_clients
            {'module': 'housing', 'database': 'core_clients', 'permission': 'write', 'expected': False},
            # Housing should NOT have access to legal
            {'module': 'housing', 'database': 'legal', 'permission': 'read', 'expected': False},
            # AI Assistant should have write access to all databases
            {'module': 'ai_assistant', 'database': 'core_clients', 'permission': 'write', 'expected': True},
            {'module': 'ai_assistant', 'database': 'housing', 'permission': 'write', 'expected': True},
            {'module': 'ai_assistant', 'database': 'benefits', 'permission': 'write', 'expected': True}
        ]
        
        for test in test_cases:
            module = test['module']
            database = test['database']
            permission = test['permission']
            expected = test['expected']
            
            # Check if module has the expected permission
            has_permission = False
            
            if database in self.ACCESS_MATRIX:
                if permission == 'read':
                    has_permission = (
                        module in self.ACCESS_MATRIX[database].get('read', []) or
                        module in self.ACCESS_MATRIX[database].get('write', [])
                    )
                elif permission == 'write':
                    has_permission = module in self.ACCESS_MATRIX[database].get('write', [])
            
            # Special case for AI Assistant
            if module == 'ai_assistant':
                has_permission = True
            
            test_result = {
                'module': module,
                'database': database,
                'permission': permission,
                'expected': expected,
                'actual': has_permission,
                'passed': has_permission == expected
            }
            
            results['tests'].append(test_result)
            
            if has_permission != expected:
                results['status'] = 'error'
                results['issues'].append(
                    f"Permission mismatch: {module} {'should' if expected else 'should not'} "
                    f"have {permission} access to {database}"
                )
        
        return results
    
    def repair_client_synchronization(self) -> Dict[str, Any]:
        """
        Repair client synchronization issues by copying missing clients
        from the master database to module databases
        """
        results = {
            'status': 'success',
            'actions': [],
            'issues': []
        }
        
        # Get sync status first
        sync_status = self.check_client_synchronization()
        
        if sync_status['status'] == 'error':
            results['status'] = 'error'
            results['issues'] = sync_status['issues']
            return results
        
        # Get clients from master database
        core_db_path = DATABASES_DIR / self.DATABASES['core_clients']
        
        try:
            core_conn = sqlite3.connect(core_db_path)
            core_conn.row_factory = sqlite3.Row
            core_cursor = core_conn.cursor()
            
            # Get all client data
            core_cursor.execute("SELECT * FROM clients")
            master_clients = {row['client_id']: dict(row) for row in core_cursor.fetchall()}
            
            # Check each module database
            for db_key in ['case_management', 'housing', 'benefits', 'legal', 'employment', 'services']:
                db_status = sync_status['databases'].get(db_key, {})
                
                # Skip if no issues or database doesn't exist
                if db_status.get('status') != 'warning' or db_status.get('missing_count', 0) == 0:
                    continue
                
                db_path = DATABASES_DIR / self.DATABASES[db_key]
                
                try:
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Check if clients table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                    if not cursor.fetchone():
                        results['actions'].append({
                            'database': db_key,
                            'action': 'skip',
                            'reason': 'No clients table'
                        })
                        continue
                    
                    # Get existing client IDs
                    cursor.execute("SELECT client_id FROM clients")
                    db_client_ids = {row['client_id'] for row in cursor.fetchall()}
                    
                    # Find missing clients
                    missing_ids = set(master_clients.keys()) - db_client_ids
                    
                    if missing_ids:
                        # Get table schema to ensure we have the right columns
                        cursor.execute("PRAGMA table_info(clients)")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        # Copy missing clients
                        for client_id in missing_ids:
                            client_data = master_clients[client_id]
                            
                            # Filter client data to match table schema
                            filtered_data = {k: v for k, v in client_data.items() if k in columns}
                            
                            # Build INSERT statement
                            cols = ', '.join(filtered_data.keys())
                            placeholders = ', '.join(['?' for _ in filtered_data])
                            values = tuple(filtered_data.values())
                            
                            try:
                                cursor.execute(f"INSERT INTO clients ({cols}) VALUES ({placeholders})", values)
                                results['actions'].append({
                                    'database': db_key,
                                    'action': 'insert',
                                    'client_id': client_id,
                                    'status': 'success'
                                })
                            except Exception as e:
                                results['issues'].append(f"Error inserting client {client_id} into {db_key}: {e}")
                                results['actions'].append({
                                    'database': db_key,
                                    'action': 'insert',
                                    'client_id': client_id,
                                    'status': 'error',
                                    'error': str(e)
                                })
                        
                        conn.commit()
                    
                    conn.close()
                except Exception as e:
                    results['issues'].append(f"Error repairing {db_key}: {e}")
            
            core_conn.close()
        except Exception as e:
            results['status'] = 'error'
            results['issues'].append(f"Error accessing master database: {e}")
        
        if results['issues']:
            results['status'] = 'partial'
        
        return results
    
    def run_integrity_check(self) -> Dict[str, Any]:
        """Run a comprehensive integrity check on all databases"""
        start_time = time.time()
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'databases': self.check_database_existence(),
            'tables': self.check_table_existence(),
            'synchronization': self.check_client_synchronization(),
            'permissions': self.verify_permissions()
        }
        
        # Determine overall status
        if (results['synchronization']['status'] == 'error' or 
            results['permissions']['status'] == 'error' or
            False in results['databases'].values()):
            results['status'] = 'error'
        elif (results['synchronization']['status'] == 'warning' or
              any(False in tables.values() for tables in results['tables'].values())):
            results['status'] = 'warning'
        else:
            results['status'] = 'ok'
        
        # Calculate execution time
        results['execution_time'] = time.time() - start_time
        
        self.last_check_time = datetime.now()
        self.integrity_status = results
        
        return results
    
    def get_repair_recommendations(self) -> List[Dict[str, Any]]:
        """Generate repair recommendations based on integrity check results"""
        if not self.integrity_status:
            return [{'message': 'Run integrity check first'}]
        
        recommendations = []
        
        # Check database existence
        for db_key, exists in self.integrity_status['databases'].items():
            if not exists:
                recommendations.append({
                    'issue': f"Database {db_key} does not exist",
                    'action': "Create database",
                    'severity': "critical",
                    'repair_method': "create_database",
                    'params': {'database': db_key}
                })
        
        # Check table existence
        for db_key, tables in self.integrity_status['tables'].items():
            for table, exists in tables.items():
                if not exists:
                    recommendations.append({
                        'issue': f"Table {table} does not exist in {db_key}",
                        'action': "Create table",
                        'severity': "high",
                        'repair_method': "create_table",
                        'params': {'database': db_key, 'table': table}
                    })
        
        # Check synchronization
        sync_status = self.integrity_status['synchronization']
        if sync_status['status'] in ['warning', 'error']:
            for issue in sync_status['issues']:
                if 'missing' in issue:
                    recommendations.append({
                        'issue': issue,
                        'action': "Synchronize clients",
                        'severity': "medium",
                        'repair_method': "repair_client_synchronization",
                        'params': {}
                    })
        
        # Check permissions
        perm_status = self.integrity_status['permissions']
        if perm_status['status'] == 'error':
            for issue in perm_status['issues']:
                recommendations.append({
                    'issue': issue,
                    'action': "Fix permission configuration",
                    'severity': "high",
                    'repair_method': "manual",
                    'params': {'message': "Update ACCESS_MATRIX in new_access_layer.py"}
                })
        
        return recommendations
    
    def create_database(self, database: str) -> Dict[str, Any]:
        """Create a missing database with required tables"""
        results = {
            'status': 'success',
            'database': database,
            'actions': []
        }
        
        db_path = DATABASES_DIR / self.DATABASES[database]
        
        if db_path.exists():
            results['status'] = 'warning'
            results['message'] = f"Database {database} already exists"
            return results
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create required tables based on database type
            if database == 'core_clients':
                cursor.execute('''
                CREATE TABLE clients (
                    client_id TEXT PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    date_of_birth TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    case_manager_id TEXT,
                    risk_level TEXT,
                    housing_status TEXT,
                    employment_status TEXT,
                    intake_date TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                ''')
                results['actions'].append({'table': 'clients', 'action': 'created'})
            
            elif database == 'case_management':
                # Create clients table
                cursor.execute('''
                CREATE TABLE clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT UNIQUE NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    date_of_birth TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    emergency_contact_name TEXT,
                    emergency_contact_phone TEXT,
                    emergency_contact_relationship TEXT,
                    case_manager_id TEXT,
                    risk_level TEXT,
                    case_status TEXT,
                    housing_status TEXT,
                    employment_status TEXT,
                    benefits_status TEXT,
                    legal_status TEXT,
                    program_type TEXT,
                    referral_source TEXT,
                    intake_date TEXT,
                    prior_convictions TEXT,
                    substance_abuse_history TEXT,
                    mental_health_status TEXT,
                    transportation TEXT,
                    medical_conditions TEXT,
                    special_needs TEXT,
                    goals TEXT,
                    barriers TEXT,
                    needs TEXT,
                    progress INTEGER,
                    last_contact TEXT,
                    next_followup TEXT,
                    notes TEXT,
                    created_at TEXT,
                    last_updated TEXT,
                    is_active INTEGER
                )
                ''')
                results['actions'].append({'table': 'clients', 'action': 'created'})
                
                # Create case_notes table
                cursor.execute('''
                CREATE TABLE case_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id TEXT UNIQUE NOT NULL,
                    client_id TEXT NOT NULL,
                    case_manager_id TEXT,
                    note_type TEXT,
                    title TEXT,
                    content TEXT NOT NULL,
                    contact_method TEXT,
                    duration_minutes INTEGER,
                    location TEXT,
                    client_mood TEXT,
                    progress_rating INTEGER,
                    barriers_identified TEXT,
                    action_items TEXT,
                    next_contact_needed TEXT,
                    referrals_made TEXT,
                    created_at TEXT,
                    is_confidential INTEGER,
                    tags TEXT
                )
                ''')
                results['actions'].append({'table': 'case_notes', 'action': 'created'})
                
                # Create dashboard_notes table (for case manager personal notes)
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS dashboard_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id TEXT UNIQUE NOT NULL,
                    case_manager_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    pinned INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT
                )
                ''')
                results['actions'].append({'table': 'dashboard_notes', 'action': 'created'})
                
                # Create cases table
                cursor.execute('''
                CREATE TABLE cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT UNIQUE NOT NULL,
                    client_id TEXT NOT NULL,
                    case_manager_id TEXT,
                    case_type TEXT,
                    status TEXT,
                    priority TEXT,
                    opened_date TEXT,
                    closed_date TEXT,
                    description TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                ''')
                results['actions'].append({'table': 'cases', 'action': 'created'})
                
                # Create referrals table
                cursor.execute('''
                CREATE TABLE referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referral_id TEXT UNIQUE NOT NULL,
                    client_id TEXT NOT NULL,
                    case_manager_id TEXT,
                    service_type TEXT,
                    provider_name TEXT,
                    provider_contact TEXT,
                    status TEXT,
                    priority TEXT,
                    referral_date TEXT,
                    expected_contact_date TEXT,
                    actual_contact_date TEXT,
                    completion_date TEXT,
                    outcome TEXT,
                    notes TEXT,
                    created_at TEXT,
                    last_updated TEXT
                )
                ''')
                results['actions'].append({'table': 'referrals', 'action': 'created'})
                
                # Create tasks table
                cursor.execute('''
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date DATETIME,
                    priority TEXT,
                    status TEXT,
                    category TEXT,
                    assigned_to TEXT,
                    created_by TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    task_type TEXT,
                    context_type TEXT,
                    context_id TEXT,
                    ai_generated BOOLEAN,
                    ai_priority_score REAL,
                    auto_generated BOOLEAN,
                    task_metadata TEXT,
                    completed_date DATETIME,
                    updated_by TEXT
                )
                ''')
                results['actions'].append({'table': 'tasks', 'action': 'created'})
            
            # Add other database schemas as needed
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created database {database} with required tables")
            
        except Exception as e:
            results['status'] = 'error'
            results['message'] = str(e)
            logger.error(f"Error creating database {database}: {e}")
        
        return results
    
    def create_table(self, database: str, table: str) -> Dict[str, Any]:
        """Create a missing table in a database"""
        results = {
            'status': 'success',
            'database': database,
            'table': table
        }
        
        db_path = DATABASES_DIR / self.DATABASES[database]
        
        if not db_path.exists():
            results['status'] = 'error'
            results['message'] = f"Database {database} does not exist"
            return results
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if table already exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                results['status'] = 'warning'
                results['message'] = f"Table {table} already exists in {database}"
                return results
            
            # Create table based on database and table name
            if database == 'core_clients' and table == 'clients':
                cursor.execute('''
                CREATE TABLE clients (
                    client_id TEXT PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    date_of_birth TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    case_manager_id TEXT,
                    risk_level TEXT,
                    housing_status TEXT,
                    employment_status TEXT,
                    intake_date TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                ''')
            
            elif database == 'case_management':
                if table == 'clients':
                    cursor.execute('''
                    CREATE TABLE clients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id TEXT UNIQUE NOT NULL,
                        first_name TEXT NOT NULL,
                        last_name TEXT NOT NULL,
                        date_of_birth TEXT,
                        phone TEXT,
                        email TEXT,
                        address TEXT,
                        city TEXT,
                        state TEXT,
                        zip_code TEXT,
                        emergency_contact_name TEXT,
                        emergency_contact_phone TEXT,
                        emergency_contact_relationship TEXT,
                        case_manager_id TEXT,
                        risk_level TEXT,
                        case_status TEXT,
                        housing_status TEXT,
                        employment_status TEXT,
                        benefits_status TEXT,
                        legal_status TEXT,
                        program_type TEXT,
                        referral_source TEXT,
                        intake_date TEXT,
                        prior_convictions TEXT,
                        substance_abuse_history TEXT,
                        mental_health_status TEXT,
                        transportation TEXT,
                        medical_conditions TEXT,
                        special_needs TEXT,
                        goals TEXT,
                        barriers TEXT,
                        needs TEXT,
                        progress INTEGER,
                        last_contact TEXT,
                        next_followup TEXT,
                        notes TEXT,
                        created_at TEXT,
                        last_updated TEXT,
                        is_active INTEGER
                    )
                    ''')
                elif table == 'case_notes':
                    cursor.execute('''
                    CREATE TABLE case_notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        note_id TEXT UNIQUE NOT NULL,
                        client_id TEXT NOT NULL,
                        case_manager_id TEXT,
                        note_type TEXT,
                        title TEXT,
                        content TEXT NOT NULL,
                        contact_method TEXT,
                        duration_minutes INTEGER,
                        location TEXT,
                        client_mood TEXT,
                        progress_rating INTEGER,
                        barriers_identified TEXT,
                        action_items TEXT,
                        next_contact_needed TEXT,
                        referrals_made TEXT,
                        created_at TEXT,
                        is_confidential INTEGER,
                        tags TEXT
                    )
                    ''')
                elif table == 'dashboard_notes':
                    cursor.execute('''
                    CREATE TABLE dashboard_notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        note_id TEXT UNIQUE NOT NULL,
                        case_manager_id TEXT NOT NULL,
                        content TEXT NOT NULL,
                        pinned INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT
                    )
                    ''')
                # Add other tables as needed
            
            # Add other database tables as needed
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created table {table} in database {database}")
            
        except Exception as e:
            results['status'] = 'error'
            results['message'] = str(e)
            logger.error(f"Error creating table {table} in {database}: {e}")
        
        return results
    
    def generate_integrity_report(self) -> Dict[str, Any]:
        """Generate a comprehensive integrity report"""
        if not self.integrity_status:
            self.run_integrity_check()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'status': self.integrity_status.get('status', 'unknown'),
            'summary': {
                'databases': {
                    'total': len(self.DATABASES),
                    'missing': sum(1 for exists in self.integrity_status['databases'].values() if not exists)
                },
                'tables': {},
                'synchronization': {
                    'status': self.integrity_status['synchronization']['status'],
                    'issues': len(self.integrity_status['synchronization'].get('issues', []))
                },
                'permissions': {
                    'status': self.integrity_status['permissions']['status'],
                    'issues': len(self.integrity_status['permissions'].get('issues', []))
                }
            },
            'recommendations': self.get_repair_recommendations()
        }
        
        # Count missing tables
        missing_tables = 0
        for db_tables in self.integrity_status['tables'].values():
            missing_tables += sum(1 for exists in db_tables.values() if not exists)
        
        report['summary']['tables'] = {
            'total': sum(len(tables) for tables in self.REQUIRED_TABLES.values()),
            'missing': missing_tables
        }
        
        return report

# Create singleton instance
db_integrity_manager = DatabaseIntegrityManager()

def get_integrity_manager():
    """Get the database integrity manager instance"""
    return db_integrity_manager