"""
Client Integration Service - Ensures all 15 specialized databases stay synchronized
When a client is created or updated in one module, this service propagates the changes
to all other modules that need that client information.
"""

import logging
import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

class ClientIntegrationService:
    """
    Central service for client data integration across all 15 specialized databases.
    Ensures client information flows seamlessly between modules.
    """
    
    def __init__(self):
        self.databases = {
            'case_management': 'databases/case_management.db',
            'reminders': 'databases/reminders.db',
            'legal_cases': 'databases/legal_cases.db',
            'expungement': 'databases/expungement.db',
            'benefits_transport': 'databases/benefits_transport.db',
            'housing': 'databases/housing.db',
            'housing_resources': 'databases/housing_resources.db',
            'jobs': 'databases/jobs.db',
            'resumes': 'databases/resumes.db',
            'services': 'databases/services.db',
            'social_services': 'databases/social_services.db',
            'unified_platform': 'databases/unified_platform.db',
            'case_manager': 'databases/case_manager.db',
            'search_cache': 'databases/search_cache.db',
            'auth': 'databases/auth.db'
        }
        
        # Define which databases need client information
        self.client_databases = [
            'case_management', 'reminders', 'legal_cases', 'expungement',
            'benefits_transport', 'housing', 'housing_resources', 'jobs',
            'resumes', 'services', 'social_services', 'unified_platform'
        ]
        
        # Define disability-specific databases
        self.disability_databases = [
            'benefits_transport', 'social_services', 'services'
        ]
    
    def create_client_across_all_databases(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a client record across all relevant databases
        """
        try:
            client_id = client_data.get('client_id') or str(uuid.uuid4())
            client_data['client_id'] = client_id
            
            results = {
                'client_id': client_id,
                'created_in': [],
                'errors': []
            }
            
            # Create client in case_management (primary database)
            success = self._create_client_in_database('case_management', client_data)
            if success:
                results['created_in'].append('case_management')
            else:
                results['errors'].append(f"Failed to create in case_management: {client_data.get('first_name', 'Unknown')}")
            
            # Create client in all other client databases
            for db_name in self.client_databases:
                if db_name != 'case_management':
                    try:
                        success = self._create_client_in_database(db_name, client_data)
                        if success:
                            results['created_in'].append(db_name)
                        else:
                            results['errors'].append(f"Failed to create in {db_name}")
                    except Exception as e:
                        logger.error(f"Error creating client in {db_name}: {e}")
                        results['errors'].append(f"Error in {db_name}: {str(e)}")
            
            # If client has disability, create in disability-specific databases
            if self._has_disability(client_data):
                for db_name in self.disability_databases:
                    if db_name not in results['created_in']:
                        try:
                            success = self._create_disability_client(db_name, client_data)
                            if success:
                                results['created_in'].append(f"{db_name}_disability")
                        except Exception as e:
                            logger.error(f"Error creating disability client in {db_name}: {e}")
                            results['errors'].append(f"Disability error in {db_name}: {str(e)}")
            
            # Create initial tasks/reminders
            self._create_initial_tasks(client_data)
            
            logger.info(f"Client {client_id} created in {len(results['created_in'])} databases")
            return results
            
        except Exception as e:
            logger.error(f"Error in create_client_across_all_databases: {e}")
            raise
    
    def update_client_across_all_databases(self, client_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update client information across all databases
        """
        try:
            results = {
                'client_id': client_id,
                'updated_in': [],
                'errors': []
            }
            
            # Update client in all databases
            for db_name in self.client_databases:
                try:
                    success = self._update_client_in_database(db_name, client_id, updates)
                    if success:
                        results['updated_in'].append(db_name)
                    else:
                        results['errors'].append(f"Failed to update in {db_name}")
                except Exception as e:
                    logger.error(f"Error updating client in {db_name}: {e}")
                    results['errors'].append(f"Error in {db_name}: {str(e)}")
            
            # Handle disability status changes
            if 'special_needs' in updates or 'medical_conditions' in updates:
                self._handle_disability_status_change(client_id, updates)
            
            logger.info(f"Client {client_id} updated in {len(results['updated_in'])} databases")
            return results
            
        except Exception as e:
            logger.error(f"Error in update_client_across_all_databases: {e}")
            raise
    
    def _create_client_in_database(self, db_name: str, client_data: Dict[str, Any]) -> bool:
        """Create client in specific database"""
        try:
            db_path = self.databases[db_name]
            if not Path(db_path).exists():
                logger.warning(f"Database {db_path} does not exist, skipping")
                return False
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check if clients table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                if not cursor.fetchone():
                    logger.warning(f"clients table does not exist in {db_name}")
                    return False
                
                # Get table schema
                cursor.execute("PRAGMA table_info(clients)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Prepare data based on available columns
                insert_data = self._prepare_client_data_for_database(client_data, columns)
                
                # Build dynamic INSERT statement
                placeholders = ', '.join(['?' for _ in insert_data])
                column_names = ', '.join(insert_data.keys())
                
                cursor.execute(f"INSERT INTO clients ({column_names}) VALUES ({placeholders})", 
                             list(insert_data.values()))
                
                conn.commit()
                logger.info(f"Created client {client_data['client_id']} in {db_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating client in {db_name}: {e}")
            return False
    
    def _update_client_in_database(self, db_name: str, client_id: str, updates: Dict[str, Any]) -> bool:
        """Update client in specific database"""
        try:
            db_path = self.databases[db_name]
            if not Path(db_path).exists():
                return False
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check if clients table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                if not cursor.fetchone():
                    return False
                
                # Get table schema
                cursor.execute("PRAGMA table_info(clients)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Prepare update data
                update_data = self._prepare_client_data_for_database(updates, columns)
                update_data['last_updated'] = datetime.now().isoformat()
                
                # Build dynamic UPDATE statement
                set_clause = ', '.join([f"{col} = ?" for col in update_data.keys()])
                
                cursor.execute(f"UPDATE clients SET {set_clause} WHERE client_id = ?", 
                             list(update_data.values()) + [client_id])
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating client in {db_name}: {e}")
            return False
    
    def _create_disability_client(self, db_name: str, client_data: Dict[str, Any]) -> bool:
        """Create disability-specific client record"""
        try:
            db_path = self.databases[db_name]
            if not Path(db_path).exists():
                return False
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check for disability-specific tables
                disability_tables = ['disability_clients', 'benefits_clients', 'special_needs_clients']
                table_name = None
                
                for table in disability_tables:
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    if cursor.fetchone():
                        table_name = table
                        break
                
                if not table_name:
                    # Use regular clients table
                    return self._create_client_in_database(db_name, client_data)
                
                # Create disability-specific record
                disability_data = {
                    'client_id': client_data['client_id'],
                    'first_name': client_data.get('first_name', ''),
                    'last_name': client_data.get('last_name', ''),
                    'disability_type': self._extract_disability_type(client_data),
                    'special_needs': client_data.get('special_needs', ''),
                    'medical_conditions': client_data.get('medical_conditions', ''),
                    'created_at': datetime.now().isoformat(),
                    'status': 'active'
                }
                
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Prepare data
                insert_data = {k: v for k, v in disability_data.items() if k in columns}
                placeholders = ', '.join(['?' for _ in insert_data])
                column_names = ', '.join(insert_data.keys())
                
                cursor.execute(f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})", 
                             list(insert_data.values()))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error creating disability client in {db_name}: {e}")
            return False
    
    def _prepare_client_data_for_database(self, client_data: Dict[str, Any], available_columns: List[str]) -> Dict[str, Any]:
        """Prepare client data based on available database columns"""
        prepared_data = {}
        
        # Map common fields
        field_mapping = {
            'client_id': 'client_id',
            'first_name': 'first_name',
            'last_name': 'last_name',
            'email': 'email',
            'phone': 'phone',
            'date_of_birth': 'date_of_birth',
            'address': 'address',
            'city': 'city',
            'state': 'state',
            'zip_code': 'zip_code',
            'emergency_contact_name': 'emergency_contact_name',
            'emergency_contact_phone': 'emergency_contact_phone',
            'case_manager_id': 'case_manager_id',
            'risk_level': 'risk_level',
            'status': 'status',
            'created_at': 'created_at',
            'last_updated': 'last_updated',
            'is_active': 'is_active',
            'notes': 'notes'
        }
        
        for db_col, client_field in field_mapping.items():
            if db_col in available_columns and client_field in client_data:
                prepared_data[db_col] = client_data[client_field]
        
        # Handle special fields
        if 'special_needs' in available_columns and 'special_needs' in client_data:
            prepared_data['special_needs'] = client_data['special_needs']
        
        if 'medical_conditions' in available_columns and 'medical_conditions' in client_data:
            prepared_data['medical_conditions'] = client_data['medical_conditions']
        
        if 'has_disability' in available_columns:
            prepared_data['has_disability'] = 1 if self._has_disability(client_data) else 0
        
        # Set defaults
        if 'created_at' in available_columns and 'created_at' not in prepared_data:
            prepared_data['created_at'] = datetime.now().isoformat()
        
        if 'last_updated' in available_columns and 'last_updated' not in prepared_data:
            prepared_data['last_updated'] = datetime.now().isoformat()
        
        if 'is_active' in available_columns and 'is_active' not in prepared_data:
            prepared_data['is_active'] = 1
        
        return prepared_data
    
    def _has_disability(self, client_data: Dict[str, Any]) -> bool:
        """Check if client has disability indicators"""
        special_needs = client_data.get('special_needs', '').lower()
        medical_conditions = client_data.get('medical_conditions', '').lower()
        
        disability_indicators = [
            'disability', 'disabled', 'wheelchair', 'mobility', 'vision', 'hearing',
            'cognitive', 'developmental', 'mental health', 'autism', 'adhd', 'ptsd'
        ]
        
        return any(indicator in special_needs or indicator in medical_conditions 
                  for indicator in disability_indicators)
    
    def _extract_disability_type(self, client_data: Dict[str, Any]) -> str:
        """Extract disability type from client data"""
        special_needs = client_data.get('special_needs', '').lower()
        medical_conditions = client_data.get('medical_conditions', '').lower()
        
        if 'mobility' in special_needs or 'wheelchair' in special_needs:
            return 'mobility'
        elif 'vision' in special_needs or 'blind' in special_needs:
            return 'vision'
        elif 'hearing' in special_needs or 'deaf' in special_needs:
            return 'hearing'
        elif 'cognitive' in special_needs or 'developmental' in special_needs:
            return 'cognitive'
        elif 'mental health' in special_needs or 'ptsd' in special_needs:
            return 'mental_health'
        else:
            return 'other'
    
    def _create_initial_tasks(self, client_data: Dict[str, Any]):
        """Create initial tasks and reminders for new client"""
        try:
            client_id = client_data['client_id']
            
            # Create initial assessment task in reminders database
            self._create_task_in_reminders(client_id, {
                'title': 'Complete initial client assessment',
                'description': f'Conduct comprehensive intake assessment for {client_data.get("first_name", "")} {client_data.get("last_name", "")}',
                'priority': 'high',
                'due_date': (datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)).isoformat(),
                'category': 'assessment'
            })
            
            # If client has disability, create disability-specific tasks
            if self._has_disability(client_data):
                self._create_task_in_reminders(client_id, {
                    'title': 'Disability benefits assessment',
                    'description': 'Assess eligibility for disability benefits and services',
                    'priority': 'high',
                    'due_date': (datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)).isoformat(),
                    'category': 'benefits'
                })
            
            logger.info(f"Created initial tasks for client {client_id}")
            
        except Exception as e:
            logger.error(f"Error creating initial tasks: {e}")
    
    def _create_task_in_reminders(self, client_id: str, task_data: Dict[str, Any]):
        """Create task in reminders database"""
        try:
            db_path = self.databases['reminders']
            if not Path(db_path).exists():
                return
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check if tasks table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
                if not cursor.fetchone():
                    return
                
                task_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO tasks (id, client_id, title, description, priority, due_date, category, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """, (
                    task_id, client_id, task_data['title'], task_data['description'],
                    task_data['priority'], task_data['due_date'], task_data['category'],
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error creating task in reminders: {e}")
    
    def _handle_disability_status_change(self, client_id: str, updates: Dict[str, Any]):
        """Handle changes in disability status"""
        try:
            # Check if disability status changed
            if 'special_needs' in updates or 'medical_conditions' in updates:
                # Update disability-specific databases
                for db_name in self.disability_databases:
                    self._update_disability_status(db_name, client_id, updates)
                
                # Create or update disability-related tasks
                self._update_disability_tasks(client_id, updates)
                
        except Exception as e:
            logger.error(f"Error handling disability status change: {e}")
    
    def _update_disability_status(self, db_name: str, client_id: str, updates: Dict[str, Any]):
        """Update disability status in specific database"""
        try:
            db_path = self.databases[db_name]
            if not Path(db_path).exists():
                return
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Update has_disability field if it exists
                cursor.execute("PRAGMA table_info(clients)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'has_disability' in columns:
                    has_disability = 1 if self._has_disability(updates) else 0
                    cursor.execute("UPDATE clients SET has_disability = ? WHERE client_id = ?", 
                                 (has_disability, client_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating disability status in {db_name}: {e}")
    
    def _update_disability_tasks(self, client_id: str, updates: Dict[str, Any]):
        """Update disability-related tasks"""
        try:
            if self._has_disability(updates):
                # Create disability assessment task if it doesn't exist
                self._create_task_in_reminders(client_id, {
                    'title': 'Update disability benefits assessment',
                    'description': 'Review and update disability benefits eligibility',
                    'priority': 'medium',
                    'due_date': (datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)).isoformat(),
                    'category': 'benefits'
                })
                
        except Exception as e:
            logger.error(f"Error updating disability tasks: {e}")
    
    def get_client_from_all_databases(self, client_id: str) -> Dict[str, Any]:
        """Get client information from all databases"""
        try:
            client_info = {
                'client_id': client_id,
                'databases': {},
                'consolidated': {}
            }
            
            for db_name in self.client_databases:
                try:
                    db_client = self._get_client_from_database(db_name, client_id)
                    if db_client:
                        client_info['databases'][db_name] = db_client
                        
                        # Consolidate information
                        for key, value in db_client.items():
                            if key not in client_info['consolidated'] or not client_info['consolidated'][key]:
                                client_info['consolidated'][key] = value
                        
                except Exception as e:
                    logger.error(f"Error getting client from {db_name}: {e}")
            
            return client_info
            
        except Exception as e:
            logger.error(f"Error in get_client_from_all_databases: {e}")
            raise
    
    def _get_client_from_database(self, db_name: str, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client from specific database"""
        try:
            db_path = self.databases[db_name]
            if not Path(db_path).exists():
                return None
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check if clients table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                if not cursor.fetchone():
                    return None
                
                cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
                row = cursor.fetchone()
                
                if row:
                    # Get column names
                    cursor.execute("PRAGMA table_info(clients)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    # Convert to dictionary
                    return dict(zip(columns, row))
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting client from {db_name}: {e}")
            return None
