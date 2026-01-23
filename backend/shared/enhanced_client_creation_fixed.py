#!/usr/bin/env python3
"""
Enhanced Client Creation API - Fixed Version
Works with existing schema without cross-database foreign key issues
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
            # Open all database connections (disable foreign keys to avoid cross-db issues)
            for module_name, module_info in self.modules.items():
                db_path = self.db_dir / module_info['db_file']
                conn = sqlite3.connect(db_path)
                conn.execute("PRAGMA foreign_keys = OFF")  # Disable to avoid cross-db issues
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
                logger.info(f"Master database creation successful")
                result['transaction_log'].append("Master database creation successful")
                
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
                            logger.info(f"{module_name}: Success")
                            result['transaction_log'].append(f"{module_name}: Success")
                        else:
                            result['modules_failed'].append(module_name)
                            logger.error(f"{module_name}: {module_result['error']}")
                            result['transaction_log'].append(f"{module_name}: {module_result['error']}")
                            raise Exception(f"Module {module_name} creation failed: {module_result['error']}")
                            
                    except Exception as e:
                        result['modules_failed'].append(module_name)
                        error_msg = f"Module {module_name} creation failed: {str(e)}"
                        result['errors'].append(error_msg)
                        logger.error(error_msg)
                        result['transaction_log'].append(f"{module_name}: {str(e)}")
                        raise
                
                # If we get here, all modules succeeded
                result['overall_success'] = True
                result['success_rate'] = 100.0
                
                logger.info(f"Client creation completed successfully across all {len(result['modules_created'])} modules")
                result['transaction_log'].append(f"All modules completed successfully")
                
        except Exception as e:
            result['overall_success'] = False
            result['success_rate'] = (len(result['modules_created']) / len(self.modules)) * 100
            error_msg = f"Client creation failed: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)
            result['transaction_log'].append(f"Transaction failed: {str(e)}")
            result['transaction_log'].append("All changes rolled back")
        
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

# Global instance for easy import
enhanced_client_api = EnhancedClientCreationAPI()

def create_client_with_distribution(client_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for enhanced client creation"""
    return enhanced_client_api.create_client_with_distribution(client_data)

def test_enhanced_api():
    """Test the enhanced client creation API"""
    
    print("🧪 TESTING ENHANCED CLIENT CREATION API")
    print("=" * 50)
    
    # Test client data
    test_client = {
        'first_name': 'Enhanced',
        'last_name': 'APITest',
        'email': 'enhanced.apitest@example.com',
        'phone': '(555) 123-ENHA',
        'case_manager_id': 'cm_test',
        'risk_level': 'medium'
    }
    
    print(f"Creating test client: {test_client['first_name']} {test_client['last_name']}")
    
    # Create client using enhanced API
    result = create_client_with_distribution(test_client)
    
    print(f"\n📊 Creation Result:")
    print(f"   Client ID: {result['client_id']}")
    print(f"   Overall Success: {result['overall_success']}")
    print(f"   Success Rate: {result.get('success_rate', 0):.1f}%")
    print(f"   Modules Created: {len(result['modules_created'])}")
    print(f"   Modules Failed: {len(result['modules_failed'])}")
    
    if result['overall_success']:
        print(f"\n✅ Enhanced API test successful!")
        print(f"   Created in modules: {', '.join(result['modules_created'])}")
        
        # Verify across all modules
        verification_success = verify_test_client(result['client_id'])
        
        if verification_success:
            print(f"   ✅ Cross-module verification successful!")
        else:
            print(f"   ⚠️ Cross-module verification had issues")
        
        # Clean up test client
        cleanup_test_client(result['client_id'])
        print(f"   🧹 Test client cleaned up")
        
    else:
        print(f"\n❌ Enhanced API test failed:")
        for error in result['errors']:
            print(f"   • {error}")
        
        if result['transaction_log']:
            print(f"\n📋 Transaction Log:")
            for log_entry in result['transaction_log']:
                print(f"   • {log_entry}")
    
    return result['overall_success']

def verify_test_client(client_id: str) -> bool:
    """Verify test client exists in all modules"""
    
    db_dir = Path('databases')
    modules = {
        'core_clients': 'core_clients.db',
        'case_management': 'case_management.db',
        'housing': 'housing.db',
        'benefits': 'benefits.db',
        'legal': 'legal.db',
        'employment': 'employment.db',
        'services': 'services.db',
        'reminders': 'reminders.db',
        'ai_assistant': 'ai_assistant.db',
        'unified_platform': 'unified_platform.db'
    }
    
    found_count = 0
    total_modules = len(modules)
    
    for module_name, db_file in modules.items():
        try:
            with sqlite3.connect(db_dir / db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT first_name, last_name FROM clients WHERE client_id = ?", (client_id,))
                result = cursor.fetchone()
                
                if result:
                    found_count += 1
                    
        except Exception as e:
            logger.error(f"Verification error for {module_name}: {e}")
    
    return found_count == total_modules

def cleanup_test_client(client_id: str):
    """Clean up test client from all modules"""
    
    db_dir = Path('databases')
    modules = {
        'core_clients': 'core_clients.db',
        'case_management': 'case_management.db',
        'housing': 'housing.db',
        'benefits': 'benefits.db',
        'legal': 'legal.db',
        'employment': 'employment.db',
        'services': 'services.db',
        'reminders': 'reminders.db',
        'ai_assistant': 'ai_assistant.db',
        'unified_platform': 'unified_platform.db'
    }
    
    for module_name, db_file in modules.items():
        try:
            with sqlite3.connect(db_dir / db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Cleanup error for {module_name}: {e}")

if __name__ == "__main__":
    test_enhanced_api()