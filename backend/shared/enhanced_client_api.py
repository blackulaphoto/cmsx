
"""
Enhanced Client Creation API - Phase 2A
Automatic distribution across all 10 modules with transaction rollback
"""

import sqlite3
import uuid
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import traceback

# Set up logging
logger = logging.getLogger(__name__)

class EnhancedClientCreationAPI:
    """Enhanced client creation with automatic distribution and transaction management"""
    
    def __init__(self):
        self.db_dir = Path('databases')
        self.modules = {
            'core_clients': {
                'db_file': 'core_clients.db',
                'is_master': True,
                'default_values': {
                    'case_status': 'active',
                    'risk_level': 'medium',
                    'intake_date': lambda: datetime.now().date().isoformat(),
                    'created_at': lambda: datetime.now().isoformat(),
                    'updated_at': lambda: datetime.now().isoformat()
                }
            },
            'case_management': {
                'db_file': 'case_management.db',
                'is_master': False,
                'default_values': {
                    'case_manager_id': 'cm_001',
                    'created_at': lambda: datetime.now().isoformat(),
                    'updated_at': lambda: datetime.now().isoformat()
                }
            },
            'housing': {
                'db_file': 'housing.db',
                'is_master': False,
                'default_values': {
                    'housing_status': 'Unknown',
                    'created_at': lambda: datetime.now().isoformat(),
                    'updated_at': lambda: datetime.now().isoformat()
                }
            },
            'benefits': {
                'db_file': 'benefits.db',
                'is_master': False,
                'default_values': {
                    'benefits_status': 'Not Applied',
                    'eligibility_score': 0.0,
                    'created_at': lambda: datetime.now().isoformat(),
                    'updated_at': lambda: datetime.now().isoformat()
                }
            },
            'legal': {
                'db_file': 'legal.db',
                'is_master': False,
                'default_values': {
                    'legal_status': 'No Active Cases',
                    'priority': 'Medium',
                    'created_at': lambda: datetime.now().isoformat(),
                    'updated_at': lambda: datetime.now().isoformat()
                }
            },
            'employment': {
                'db_file': 'employment.db',
                'is_master': False,
                'default_values': {
                    'employment_status': 'Unemployed',
                    'created_at': lambda: datetime.now().isoformat(),
                    'updated_at': lambda: datetime.now().isoformat()
                }
            },
            'services': {
                'db_file': 'services.db',
                'is_master': False,
                'default_values': {
                    'has_disability': 0,
                    'created_at': lambda: datetime.now().isoformat(),
                    'updated_at': lambda: datetime.now().isoformat()
                }
            },
            'reminders': {
                'db_file': 'reminders.db',
                'is_master': False,
                'default_values': {
                    'contact_frequency': 'weekly',
                    'preferred_contact_method': 'phone',
                    'created_at': lambda: datetime.now().isoformat(),
                    'updated_at': lambda: datetime.now().isoformat()
                }
            },
            'ai_assistant': {
                'db_file': 'ai_assistant.db',
                'is_master': False,
                'default_values': {
                    'ai_interaction_count': 0,
                    'conversation_history_enabled': 1,
                    'created_at': lambda: datetime.now().isoformat(),
                    'updated_at': lambda: datetime.now().isoformat()
                }
            },
            'unified_platform': {
                'db_file': 'unified_platform.db',
                'is_master': False,
                'default_values': {
                    'platform_status': 'active',
                    'integration_status': 'synced',
                    'created_at': lambda: datetime.now().isoformat(),
                    'updated_at': lambda: datetime.now().isoformat()
                }
            }
        }
    
    @contextmanager
    def transaction_manager(self):
        """Context manager for handling transactions across multiple databases"""
        connections = {}
        try:
            # Open all database connections
            for module_name, module_info in self.modules.items():
                db_path = self.db_dir / module_info['db_file']
                conn = sqlite3.connect(db_path)
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("BEGIN TRANSACTION")
                connections[module_name] = conn
            
            yield connections
            
            # Commit all transactions
            for conn in connections.values():
                conn.commit()
                
        except Exception as e:
            # Rollback all transactions
            logger.error(f"Transaction failed, rolling back: {e}")
            for conn in connections.values():
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            # Close all connections
            for conn in connections.values():
                try:
                    conn.close()
                except:
                    pass
    
    def create_client_with_distribution(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create client with automatic distribution across all modules
        
        Args:
            client_data: Dictionary containing client information
            
        Returns:
            Dictionary with creation results and detailed logging
        """
        
        # Generate client ID if not provided
        if 'client_id' not in client_data:
            client_data['client_id'] = str(uuid.uuid4())
        
        client_id = client_data['client_id']
        
        # Initialize result structure
        result = {
            'client_id': client_id,
            'overall_success': False,
            'modules_created': [],
            'modules_failed': [],
            'detailed_results': {},
            'transaction_log': [],
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Starting enhanced client creation for: {client_id}")
        result['transaction_log'].append(f"Started client creation: {client_id}")
        
        try:
            with self.transaction_manager() as connections:
                
                # Step 1: Create in master database (core_clients)
                logger.info(f"Creating client in master database: core_clients")
                result['transaction_log'].append("Creating in master database: core_clients")
                
                master_success = self._create_in_master(connections['core_clients'], client_data)
                result['detailed_results']['core_clients'] = master_success
                
                if not master_success['success']:
                    raise Exception(f"Master database creation failed: {master_success['error']}")
                
                result['modules_created'].append('core_clients')
                logger.info(f"✅ Master database creation successful")
                result['transaction_log'].append("✅ Master database creation successful")
                
                # Step 2: Create in all module databases
                for module_name, module_info in self.modules.items():
                    if module_info['is_master']:
                        continue  # Skip master, already done
                    
                    logger.info(f"Creating client in module: {module_name}")
                    result['transaction_log'].append(f"Creating in module: {module_name}")
                    
                    try:
                        module_result = self._create_in_module(
                            connections[module_name], 
                            client_data, 
                            module_name
                        )
                        result['detailed_results'][module_name] = module_result
                        
                        if module_result['success']:
                            result['modules_created'].append(module_name)
                            logger.info(f"✅ {module_name}: Success")
                            result['transaction_log'].append(f"✅ {module_name}: Success")
                        else:
                            result['modules_failed'].append(module_name)
                            logger.error(f"❌ {module_name}: {module_result['error']}")
                            result['transaction_log'].append(f"❌ {module_name}: {module_result['error']}")
                            raise Exception(f"Module {module_name} creation failed: {module_result['error']}")
                            
                    except Exception as e:
                        result['modules_failed'].append(module_name)
                        error_msg = f"Module {module_name} creation failed: {str(e)}"
                        result['errors'].append(error_msg)
                        logger.error(error_msg)
                        result['transaction_log'].append(f"❌ {module_name}: {str(e)}")
                        raise
                
                # If we get here, all modules succeeded
                result['overall_success'] = True
                result['success_rate'] = 100.0
                
                logger.info(f"🎉 Client creation completed successfully across all {len(result['modules_created'])} modules")
                result['transaction_log'].append(f"🎉 All modules completed successfully")
                
        except Exception as e:
            result['overall_success'] = False
            result['success_rate'] = (len(result['modules_created']) / len(self.modules)) * 100
            error_msg = f"Client creation failed: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)
            result['transaction_log'].append(f"❌ Transaction failed: {str(e)}")
            result['transaction_log'].append("🔄 All changes rolled back")
        
        return result
    
    def _create_in_master(self, connection: sqlite3.Connection, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create client in master database (core_clients)"""
        
        try:
            cursor = connection.cursor()
            
            # Prepare data with defaults
            master_data = client_data.copy()
            defaults = self.modules['core_clients']['default_values']
            
            for field, default_value in defaults.items():
                if field not in master_data or master_data[field] is None:
                    if callable(default_value):
                        master_data[field] = default_value()
                    else:
                        master_data[field] = default_value
            
            # Insert into core_clients
            cursor.execute("""
                INSERT INTO clients (
                    client_id, first_name, last_name, date_of_birth, phone, email, address,
                    emergency_contact_name, emergency_contact_phone, risk_level, case_status,
                    case_manager_id, intake_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                master_data['client_id'],
                master_data.get('first_name', ''),
                master_data.get('last_name', ''),
                master_data.get('date_of_birth', ''),
                master_data.get('phone', ''),
                master_data.get('email', ''),
                master_data.get('address', ''),
                master_data.get('emergency_contact_name', ''),
                master_data.get('emergency_contact_phone', ''),
                master_data['risk_level'],
                master_data['case_status'],
                master_data.get('case_manager_id', 'cm_001'),
                master_data['intake_date'],
                master_data['created_at'],
                master_data['updated_at']
            ))
            
            return {
                'success': True,
                'message': 'Master database creation successful',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _create_in_module(self, connection: sqlite3.Connection, client_data: Dict[str, Any], module_name: str) -> Dict[str, Any]:
        """Create client in a specific module database"""
        
        try:
            cursor = connection.cursor()
            
            # Prepare data with module-specific defaults
            module_data = client_data.copy()
            defaults = self.modules[module_name]['default_values']
            
            for field, default_value in defaults.items():
                if field not in module_data or module_data[field] is None:
                    if callable(default_value):
                        module_data[field] = default_value()
                    else:
                        module_data[field] = default_value
            
            # Get table schema to determine available columns
            cursor.execute("PRAGMA table_info(clients)")
            available_columns = [row[1] for row in cursor.fetchall()]
            
            # Build dynamic insert query based on available columns
            insert_columns = []
            insert_values = []
            
            # Always include required fields
            required_fields = ['client_id', 'first_name', 'last_name']
            for field in required_fields:
                if field in available_columns:
                    insert_columns.append(field)
                    insert_values.append(module_data.get(field, ''))
            
            # Add optional fields that exist in both data and schema
            optional_fields = ['email', 'phone', 'case_manager_id', 'created_at', 'updated_at']
            for field in optional_fields:
                if field in available_columns and field not in insert_columns:
                    insert_columns.append(field)
                    insert_values.append(module_data.get(field, ''))
            
            # Add module-specific default fields
            for field, value in defaults.items():
                if field in available_columns and field not in insert_columns:
                    insert_columns.append(field)
                    if callable(value):
                        insert_values.append(value())
                    else:
                        insert_values.append(value)
            
            # Execute insert
            placeholders = ', '.join(['?' for _ in insert_columns])
            columns_str = ', '.join(insert_columns)
            
            cursor.execute(f"""
                INSERT OR REPLACE INTO clients ({columns_str})
                VALUES ({placeholders})
            """, insert_values)
            
            return {
                'success': True,
                'message': f'Module {module_name} creation successful',
                'columns_inserted': len(insert_columns),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def bulk_sync_existing_clients(self) -> Dict[str, Any]:
        """Bulk sync existing clients to all modules with duplicate prevention"""
        
        logger.info("Starting bulk sync of existing clients")
        
        result = {
            'total_clients': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'module_results': {},
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Get all clients from master database
            with sqlite3.connect(self.db_dir / 'core_clients.db') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT client_id, first_name, last_name, date_of_birth, phone, email, 
                           address, emergency_contact_name, emergency_contact_phone, 
                           risk_level, case_status, case_manager_id
                    FROM clients 
                    WHERE case_status = 'active'
                """)
                existing_clients = cursor.fetchall()
            
            result['total_clients'] = len(existing_clients)
            logger.info(f"Found {len(existing_clients)} existing clients to sync")
            
            # Sync each client
            for client_row in existing_clients:
                client_data = {
                    'client_id': client_row[0],
                    'first_name': client_row[1],
                    'last_name': client_row[2],
                    'date_of_birth': client_row[3],
                    'phone': client_row[4],
                    'email': client_row[5],
                    'address': client_row[6],
                    'emergency_contact_name': client_row[7],
                    'emergency_contact_phone': client_row[8],
                    'risk_level': client_row[9],
                    'case_status': client_row[10],
                    'case_manager_id': client_row[11]
                }
                
                try:
                    # Use the enhanced creation API (without master database)
                    sync_result = self._sync_client_to_modules(client_data)
                    
                    if sync_result['overall_success']:
                        result['successful_syncs'] += 1
                    else:
                        result['failed_syncs'] += 1
                        result['errors'].extend(sync_result['errors'])
                    
                    # Aggregate module results
                    for module, module_result in sync_result['detailed_results'].items():
                        if module not in result['module_results']:
                            result['module_results'][module] = {'success': 0, 'failed': 0}
                        
                        if module_result['success']:
                            result['module_results'][module]['success'] += 1
                        else:
                            result['module_results'][module]['failed'] += 1
                
                except Exception as e:
                    result['failed_syncs'] += 1
                    error_msg = f"Failed to sync client {client_data['client_id']}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
            
            result['success_rate'] = (result['successful_syncs'] / result['total_clients']) * 100 if result['total_clients'] > 0 else 0
            
            logger.info(f"Bulk sync completed: {result['successful_syncs']}/{result['total_clients']} successful ({result['success_rate']:.1f}%)")
            
        except Exception as e:
            error_msg = f"Bulk sync failed: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)
        
        return result
    
    def _sync_client_to_modules(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync a single client to all module databases (excluding master)"""
        
        result = {
            'client_id': client_data['client_id'],
            'overall_success': False,
            'modules_synced': [],
            'modules_failed': [],
            'detailed_results': {},
            'errors': []
        }
        
        try:
            with self.transaction_manager() as connections:
                
                # Sync to all module databases (skip master)
                for module_name, module_info in self.modules.items():
                    if module_info['is_master']:
                        continue  # Skip master database
                    
                    try:
                        module_result = self._create_in_module(
                            connections[module_name], 
                            client_data, 
                            module_name
                        )
                        result['detailed_results'][module_name] = module_result
                        
                        if module_result['success']:
                            result['modules_synced'].append(module_name)
                        else:
                            result['modules_failed'].append(module_name)
                            raise Exception(f"Module {module_name} sync failed: {module_result['error']}")
                            
                    except Exception as e:
                        result['modules_failed'].append(module_name)
                        error_msg = f"Module {module_name} sync failed: {str(e)}"
                        result['errors'].append(error_msg)
                        raise
                
                # If we get here, all modules succeeded
                result['overall_success'] = True
                
        except Exception as e:
            result['overall_success'] = False
            error_msg = f"Client sync failed: {str(e)}"
            result['errors'].append(error_msg)
        
        return result

# Global instance for easy import
enhanced_client_api = EnhancedClientCreationAPI()

def create_client_with_distribution(client_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for enhanced client creation"""
    return enhanced_client_api.create_client_with_distribution(client_data)

def bulk_sync_existing_clients() -> Dict[str, Any]:
    """Convenience function for bulk client synchronization"""
    return enhanced_client_api.bulk_sync_existing_clients()
