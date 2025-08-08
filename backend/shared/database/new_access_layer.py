"""
NEW DATABASE ACCESS LAYER
Implements the 9-database architecture with proper access controls
AI Assistant has FULL CRUD permissions to all databases
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager

# Project root and database paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATABASES_DIR = PROJECT_ROOT / "databases"

class DatabaseAccessLayer:
    """
    Centralized database access layer implementing the 9-database architecture
    with proper access controls and AI full CRUD permissions
    """
    
    # Database file mappings
    DATABASES = {
        'core_clients': 'core_clients.db',      # MASTER DATABASE
        'housing': 'housing.db',
        'benefits': 'benefits.db', 
        'legal': 'legal.db',
        'employment': 'employment.db',
        'services': 'services.db',
        'reminders': 'reminders.db',
        'ai_assistant': 'ai_assistant.db',      # FULL CRUD
        'cache': 'cache.db'
    }
    
    # Access control matrix
    ACCESS_MATRIX = {
        'core_clients': {
            'write': ['case_management'],
            'read': ['housing', 'benefits', 'legal', 'employment', 'services', 'reminders', 'ai_assistant']
        },
        'housing': {
            'write': ['housing'],
            'read': ['case_management', 'services', 'reminders', 'ai_assistant']
        },
        'benefits': {
            'write': ['benefits'],
            'read': ['case_management', 'services', 'reminders', 'ai_assistant']
        },
        'legal': {
            'write': ['legal'],
            'read': ['case_management', 'services', 'reminders', 'ai_assistant']
        },
        'employment': {
            'write': ['employment', 'resume'],
            'read': ['case_management', 'services', 'reminders', 'ai_assistant']
        },
        'services': {
            'write': ['services'],
            'read': ['case_management', 'housing', 'benefits', 'legal', 'employment', 'reminders', 'ai_assistant']
        },
        'reminders': {
            'write': ['reminders'],
            'read': ['case_management', 'housing', 'benefits', 'legal', 'employment', 'services', 'ai_assistant']
        },
        'ai_assistant': {
            'write': ['ai_assistant'],
            'read': ['case_management', 'housing', 'benefits', 'legal', 'employment', 'services', 'reminders'],
            'special': 'FULL_CRUD_ALL_DATABASES'
        },
        'cache': {
            'write': ['system'],
            'read': ['all_modules']
        }
    }
    
    def __init__(self):
        self.ensure_databases_exist()
        
    def ensure_databases_exist(self):
        """Ensure all required databases exist"""
        for db_key, db_file in self.DATABASES.items():
            db_path = DATABASES_DIR / db_file
            if not db_path.exists():
                print(f"⚠️  Database {db_file} not found. Run rebuild_database_system.py first.")
                
    @contextmanager
    def get_connection(self, database: str, module: str = None):
        """
        Get database connection with access control
        AI Assistant gets full access to all databases
        """
        if database not in self.DATABASES:
            raise ValueError(f"Unknown database: {database}")
            
        db_path = DATABASES_DIR / self.DATABASES[database]
        
        # AI Assistant gets full CRUD access to ALL databases
        if module == 'ai_assistant':
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
            return
            
        # Check access permissions for other modules
        if module and database in self.ACCESS_MATRIX:
            access_rules = self.ACCESS_MATRIX[database]
            if module not in access_rules.get('read', []) and module not in access_rules.get('write', []):
                raise PermissionError(f"Module '{module}' does not have access to database '{database}'")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
            
    def can_write(self, database: str, module: str) -> bool:
        """Check if module has write access to database"""
        # AI Assistant has full CRUD access to all databases
        if module == 'ai_assistant':
            return True
            
        if database not in self.ACCESS_MATRIX:
            return False
            
        access_rules = self.ACCESS_MATRIX[database]
        return module in access_rules.get('write', [])
        
    def can_read(self, database: str, module: str) -> bool:
        """Check if module has read access to database"""
        # AI Assistant has full CRUD access to all databases
        if module == 'ai_assistant':
            return True
            
        if database not in self.ACCESS_MATRIX:
            return False
            
        access_rules = self.ACCESS_MATRIX[database]
        return module in access_rules.get('read', []) or module in access_rules.get('write', [])

class CoreClientsService:
    """Service for the MASTER core_clients.db database"""
    
    def __init__(self, access_layer: DatabaseAccessLayer):
        self.db = access_layer
        
    def create_client(self, client_data: Dict, module: str = 'case_management') -> str:
        """Create a new client (only Case Management or AI can create)"""
        if not self.db.can_write('core_clients', module):
            raise PermissionError(f"Module '{module}' cannot create clients")
            
        client_id = str(uuid.uuid4())
        
        with self.db.get_connection('core_clients', module) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO clients (
                    client_id, first_name, last_name, date_of_birth,
                    phone, email, address, emergency_contact_name,
                    emergency_contact_phone, risk_level, case_status,
                    case_manager_id, intake_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                client_id,
                client_data.get('first_name', ''),
                client_data.get('last_name', ''),
                client_data.get('date_of_birth'),
                client_data.get('phone'),
                client_data.get('email'),
                client_data.get('address'),
                client_data.get('emergency_contact_name'),
                client_data.get('emergency_contact_phone'),
                client_data.get('risk_level', 'medium'),
                client_data.get('case_status', 'active'),
                client_data.get('case_manager_id'),
                client_data.get('intake_date', datetime.now().date().isoformat())
            ))
            conn.commit()
            
        return client_id
        
    def get_client(self, client_id: str, module: str) -> Optional[Dict]:
        """Get client by ID"""
        if not self.db.can_read('core_clients', module):
            raise PermissionError(f"Module '{module}' cannot read clients")
            
        with self.db.get_connection('core_clients', module) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clients WHERE client_id = ?', (client_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
    def get_all_clients(self, module: str) -> List[Dict]:
        """Get all clients"""
        if not self.db.can_read('core_clients', module):
            raise PermissionError(f"Module '{module}' cannot read clients")
            
        with self.db.get_connection('core_clients', module) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clients ORDER BY created_at DESC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    def update_client(self, client_id: str, updates: Dict, module: str) -> bool:
        """Update client data"""
        if not self.db.can_write('core_clients', module):
            raise PermissionError(f"Module '{module}' cannot update clients")
            
        # Build dynamic update query
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key != 'client_id':  # Don't allow ID changes
                set_clauses.append(f"{key} = ?")
                values.append(value)
                
        if not set_clauses:
            return False
            
        values.append(client_id)
        query = f"UPDATE clients SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE client_id = ?"
        
        with self.db.get_connection('core_clients', module) as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
            
    def add_case_note(self, client_id: str, note_data: Dict, module: str) -> str:
        """Add case note for client"""
        if not self.db.can_write('core_clients', module):
            raise PermissionError(f"Module '{module}' cannot add case notes")
            
        note_id = str(uuid.uuid4())
        
        with self.db.get_connection('core_clients', module) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO case_notes (note_id, client_id, note_type, content, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                note_id,
                client_id,
                note_data.get('note_type', 'general'),
                note_data.get('content', ''),
                note_data.get('created_by', module)
            ))
            conn.commit()
            
        return note_id

class AIAssistantService:
    """
    AI Assistant Service with FULL CRUD permissions to ALL databases
    This is the only service that can read/write across all databases
    """
    
    def __init__(self, access_layer: DatabaseAccessLayer):
        self.db = access_layer
        self.module = 'ai_assistant'
        
    def get_client_complete_profile(self, client_id: str) -> Dict:
        """Get complete client profile across all databases"""
        profile = {
            'client_info': None,
            'housing': {},
            'benefits': {},
            'legal': {},
            'employment': {},
            'services': {},
            'reminders': [],
            'ai_analytics': {}
        }
        
        # Core client info
        with self.db.get_connection('core_clients', self.module) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clients WHERE client_id = ?', (client_id,))
            row = cursor.fetchone()
            if row:
                profile['client_info'] = dict(row)
                
        # Housing data
        with self.db.get_connection('housing', self.module) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM client_housing_profiles WHERE client_id = ?', (client_id,))
            row = cursor.fetchone()
            if row:
                profile['housing']['profile'] = dict(row)
                
            cursor.execute('SELECT * FROM housing_applications WHERE client_id = ?', (client_id,))
            profile['housing']['applications'] = [dict(row) for row in cursor.fetchall()]
            
        # Benefits data
        with self.db.get_connection('benefits', self.module) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM client_benefits_profiles WHERE client_id = ?', (client_id,))
            row = cursor.fetchone()
            if row:
                profile['benefits']['profile'] = dict(row)
                
            cursor.execute('SELECT * FROM benefits_applications WHERE client_id = ?', (client_id,))
            profile['benefits']['applications'] = [dict(row) for row in cursor.fetchall()]
            
        # Legal data
        with self.db.get_connection('legal', self.module) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM legal_cases WHERE client_id = ?', (client_id,))
            profile['legal']['cases'] = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('SELECT * FROM expungement_eligibility WHERE client_id = ?', (client_id,))
            row = cursor.fetchone()
            if row:
                profile['legal']['expungement'] = dict(row)
                
        # Employment data
        with self.db.get_connection('employment', self.module) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM client_employment_profiles WHERE client_id = ?', (client_id,))
            row = cursor.fetchone()
            if row:
                profile['employment']['profile'] = dict(row)
                
            cursor.execute('SELECT * FROM resumes WHERE client_id = ?', (client_id,))
            profile['employment']['resumes'] = [dict(row) for row in cursor.fetchall()]
            
        # Services data
        with self.db.get_connection('services', self.module) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM client_referrals WHERE client_id = ?', (client_id,))
            profile['services']['referrals'] = [dict(row) for row in cursor.fetchall()]
            
        # Reminders
        with self.db.get_connection('reminders', self.module) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM reminders WHERE client_id = ? ORDER BY due_date', (client_id,))
            profile['reminders'] = [dict(row) for row in cursor.fetchall()]
            
        # AI Analytics
        with self.db.get_connection('ai_assistant', self.module) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM client_analytics WHERE client_id = ?', (client_id,))
            row = cursor.fetchone()
            if row:
                profile['ai_analytics'] = dict(row)
                
        return profile
        
    def create_client_anywhere(self, client_data: Dict) -> str:
        """AI can create clients directly"""
        core_service = CoreClientsService(self.db)
        return core_service.create_client(client_data, self.module)
        
    def update_any_database(self, database: str, table: str, record_id: str, updates: Dict) -> bool:
        """AI can update any record in any database"""
        with self.db.get_connection(database, self.module) as conn:
            cursor = conn.cursor()
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
                
            if not set_clauses:
                return False
                
            # Determine primary key column name (assume it ends with _id)
            pk_column = f"{table.rstrip('s')}_id" if not table.endswith('_id') else table
            values.append(record_id)
            
            query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {pk_column} = ?"
            
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
            
    def save_conversation(self, conversation_data: Dict) -> str:
        """Save AI conversation"""
        conversation_id = str(uuid.uuid4())
        
        with self.db.get_connection('ai_assistant', self.module) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ai_conversations (conversation_id, client_id, user_id, messages, context_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                conversation_id,
                conversation_data.get('client_id'),
                conversation_data.get('user_id'),
                json.dumps(conversation_data.get('messages', [])),
                json.dumps(conversation_data.get('context_data', {}))
            ))
            conn.commit()
            
        return conversation_id
        
    def update_client_analytics(self, client_id: str, analytics_data: Dict) -> str:
        """Update or create client analytics"""
        with self.db.get_connection('ai_assistant', self.module) as conn:
            cursor = conn.cursor()
            
            # Check if analytics already exist for this client
            cursor.execute('SELECT analytics_id FROM client_analytics WHERE client_id = ?', (client_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                analytics_id = existing[0]
                cursor.execute('''
                    UPDATE client_analytics 
                    SET risk_factors = ?, success_probability = ?, recommended_actions = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE client_id = ?
                ''', (
                    json.dumps(analytics_data.get('risk_factors', {})),
                    analytics_data.get('success_probability', 0.0),
                    json.dumps(analytics_data.get('recommended_actions', [])),
                    client_id
                ))
            else:
                # Create new record
                analytics_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO client_analytics 
                    (analytics_id, client_id, risk_factors, success_probability, recommended_actions)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    analytics_id,
                    client_id,
                    json.dumps(analytics_data.get('risk_factors', {})),
                    analytics_data.get('success_probability', 0.0),
                    json.dumps(analytics_data.get('recommended_actions', []))
                ))
            
            conn.commit()
            
        return analytics_id

# Global instances
db_access = DatabaseAccessLayer()
core_clients_service = CoreClientsService(db_access)
ai_service = AIAssistantService(db_access)

# Export for use in other modules
__all__ = [
    'DatabaseAccessLayer',
    'CoreClientsService', 
    'AIAssistantService',
    'db_access',
    'core_clients_service',
    'ai_service'
]