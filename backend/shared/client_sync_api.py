
"""
Unified Client Synchronization API
Automatically populates all module databases when clients are created/updated
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class UnifiedClientSync:
    """Handles automatic client synchronization across all modules"""
    
    def __init__(self):
        self.db_dir = Path('databases')
        self.modules = {
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
    
    def create_client_everywhere(self, client_data: Dict) -> Dict:
        """
        Create a client in core database and automatically populate all modules
        
        Args:
            client_data: Dictionary containing client information
            
        Returns:
            Dictionary with creation results for each module
        """
        
        # Generate client ID if not provided
        if 'client_id' not in client_data:
            client_data['client_id'] = str(uuid.uuid4())
        
        results = {
            'client_id': client_data['client_id'],
            'core_creation': {'status': 'pending'},
            'module_sync': {},
            'overall_success': False,
            'errors': []
        }
        
        try:
            # Step 1: Create in core database
            core_success = self._create_in_core(client_data)
            results['core_creation'] = core_success
            
            if not core_success['success']:
                results['errors'].append(f"Core creation failed: {core_success.get('error', 'Unknown error')}")
                return results
            
            # Step 2: Sync to all modules
            sync_results = self._sync_to_all_modules(client_data)
            results['module_sync'] = sync_results
            
            # Step 3: Calculate overall success
            successful_modules = sum(1 for result in sync_results.values() if result.get('success', False))
            total_modules = len(self.modules)
            
            results['overall_success'] = successful_modules == total_modules
            results['success_rate'] = (successful_modules / total_modules) * 100 if total_modules > 0 else 0
            
            if not results['overall_success']:
                failed_modules = [name for name, result in sync_results.items() if not result.get('success', False)]
                results['errors'].append(f"Failed to sync to modules: {failed_modules}")
            
            return results
            
        except Exception as e:
            results['errors'].append(f"Unexpected error: {str(e)}")
            return results
    
    def _create_in_core(self, client_data: Dict) -> Dict:
        """Create client in core database"""
        
        try:
            with sqlite3.connect(self.db_dir / 'core_clients.db') as conn:
                cursor = conn.cursor()
                
                # Prepare core client data
                now = datetime.now().isoformat()
                
                cursor.execute("""
                    INSERT INTO clients (
                        client_id, first_name, last_name, email, phone,
                        date_of_birth, address, emergency_contact_name, emergency_contact_phone,
                        case_manager_id, risk_level, case_status, intake_date, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_data['client_id'],
                    client_data.get('first_name', ''),
                    client_data.get('last_name', ''),
                    client_data.get('email', ''),
                    client_data.get('phone', ''),
                    client_data.get('date_of_birth', ''),
                    client_data.get('address', ''),
                    client_data.get('emergency_contact_name', ''),
                    client_data.get('emergency_contact_phone', ''),
                    client_data.get('case_manager_id', 'cm_001'),
                    client_data.get('risk_level', 'Medium'),
                    client_data.get('case_status', 'active'),
                    client_data.get('intake_date', datetime.now().date().isoformat()),
                    now,
                    now
                ))
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': 'Client created in core database',
                    'timestamp': now
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _sync_to_all_modules(self, client_data: Dict) -> Dict:
        """Sync client to all module databases"""
        
        results = {}
        
        for module_name, db_file in self.modules.items():
            try:
                with sqlite3.connect(self.db_dir / db_file) as conn:
                    cursor = conn.cursor()
                    
                    # Check if clients table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                    if not cursor.fetchone():
                        results[module_name] = {
                            'success': False,
                            'error': 'Clients table does not exist',
                            'timestamp': datetime.now().isoformat()
                        }
                        continue
                    
                    # Insert basic client data
                    cursor.execute("""
                        INSERT OR REPLACE INTO clients (
                            client_id, first_name, last_name, email, phone, 
                            case_manager_id, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        client_data['client_id'],
                        client_data.get('first_name', ''),
                        client_data.get('last_name', ''),
                        client_data.get('email', ''),
                        client_data.get('phone', ''),
                        client_data.get('case_manager_id', 'cm_001'),
                        datetime.now().isoformat()
                    ))
                    
                    conn.commit()
                    
                    results[module_name] = {
                        'success': True,
                        'message': 'Client synced successfully',
                        'timestamp': datetime.now().isoformat()
                    }
                    
            except Exception as e:
                results[module_name] = {
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        return results
    
    def update_client_everywhere(self, client_id: str, update_data: Dict) -> Dict:
        """Update client across all modules"""
        
        results = {
            'client_id': client_id,
            'core_update': {'status': 'pending'},
            'module_sync': {},
            'overall_success': False,
            'errors': []
        }
        
        try:
            # Update core database
            with sqlite3.connect(self.db_dir / 'core_clients.db') as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                update_fields = []
                update_values = []
                
                for field, value in update_data.items():
                    if field != 'client_id':  # Don't update client_id
                        update_fields.append(f"{field} = ?")
                        update_values.append(value)
                
                update_fields.append("updated_at = ?")
                update_values.append(datetime.now().isoformat())
                update_values.append(client_id)
                
                cursor.execute(f"""
                    UPDATE clients 
                    SET {', '.join(update_fields)}
                    WHERE client_id = ?
                """, update_values)
                
                if cursor.rowcount == 0:
                    results['errors'].append("Client not found in core database")
                    return results
                
                conn.commit()
                results['core_update'] = {'success': True}
            
            # Update all modules
            for module_name, db_file in self.modules.items():
                try:
                    with sqlite3.connect(self.db_dir / db_file) as conn:
                        cursor = conn.cursor()
                        
                        # Update basic fields that all modules should have
                        basic_updates = {k: v for k, v in update_data.items() 
                                       if k in ['first_name', 'last_name', 'email', 'phone', 'case_manager_id']}
                        
                        if basic_updates:
                            update_fields = [f"{field} = ?" for field in basic_updates.keys()]
                            update_fields.append("updated_at = ?")
                            update_values = list(basic_updates.values())
                            update_values.append(datetime.now().isoformat())
                            update_values.append(client_id)
                            
                            cursor.execute(f"""
                                UPDATE clients 
                                SET {', '.join(update_fields)}
                                WHERE client_id = ?
                            """, update_values)
                            
                            conn.commit()
                        
                        results['module_sync'][module_name] = {'success': True}
                        
                except Exception as e:
                    results['module_sync'][module_name] = {'success': False, 'error': str(e)}
            
            # Calculate overall success
            successful_modules = sum(1 for result in results['module_sync'].values() if result.get('success', False))
            total_modules = len(self.modules)
            results['overall_success'] = successful_modules == total_modules
            
            return results
            
        except Exception as e:
            results['errors'].append(f"Update failed: {str(e)}")
            return results

# Global instance for easy import
client_sync = UnifiedClientSync()

def create_client_with_sync(client_data: Dict) -> Dict:
    """Convenience function to create client with full sync"""
    return client_sync.create_client_everywhere(client_data)

def update_client_with_sync(client_id: str, update_data: Dict) -> Dict:
    """Convenience function to update client with full sync"""
    return client_sync.update_client_everywhere(client_id, update_data)
