#!/usr/bin/env python3
"""
Step 2: Migrate all client data from module databases to core_clients.db
This consolidates all client data into the single source of truth
"""

import sqlite3
import os
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClientDataMigrator:
    """Migrate client data from all module databases to core_clients.db"""
    
    def __init__(self):
        self.core_db_path = "databases/core_clients.db"
        self.module_databases = {
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
            'case_manager': 'databases/case_manager.db'
        }
        
        # Track migrated clients to avoid duplicates
        self.migrated_clients = set()
        self.migration_results = {
            'total_clients_found': 0,
            'clients_migrated': 0,
            'duplicates_skipped': 0,
            'errors': []
        }
    
    def migrate_all_client_data(self):
        """Migrate client data from all module databases"""
        
        print("🔄 Step 2: Migrating Client Data to core_clients.db")
        print("=" * 60)
        
        try:
            # Connect to core database
            with sqlite3.connect(self.core_db_path) as core_conn:
                core_cursor = core_conn.cursor()
                
                # Process each module database
                for db_name, db_path in self.module_databases.items():
                    if Path(db_path).exists():
                        print(f"\n📊 Processing {db_name}...")
                        self._migrate_from_database(db_name, db_path, core_cursor)
                    else:
                        print(f"⚠️  {db_name} database not found, skipping")
                
                core_conn.commit()
                
                # Show migration summary
                self._show_migration_summary()
                
                return True
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            print(f"❌ Migration failed: {e}")
            return False
    
    def _migrate_from_database(self, db_name: str, db_path: str, core_cursor):
        """Migrate client data from a specific module database"""
        
        try:
            with sqlite3.connect(db_path) as module_conn:
                module_cursor = module_conn.cursor()
                
                # Check if clients table exists
                module_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                if not module_cursor.fetchone():
                    print(f"   ℹ️  No clients table found in {db_name}")
                    return
                
                # Get all clients from this database
                module_cursor.execute("SELECT * FROM clients")
                clients = module_cursor.fetchall()
                
                if not clients:
                    print(f"   ℹ️  No client data found in {db_name}")
                    return
                
                # Get column names
                module_cursor.execute("PRAGMA table_info(clients)")
                columns = [col[1] for col in module_cursor.fetchall()]
                
                print(f"   📋 Found {len(clients)} clients in {db_name}")
                
                # Process each client
                for client_row in clients:
                    client_data = dict(zip(columns, client_row))
                    self._migrate_single_client(client_data, db_name, core_cursor)
                
        except Exception as e:
            error_msg = f"Error migrating from {db_name}: {e}"
            logger.error(error_msg)
            self.migration_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
    
    def _migrate_single_client(self, client_data: Dict[str, Any], source_db: str, core_cursor):
        """Migrate a single client to core_clients.db"""
        
        try:
            # Generate or use existing client_id
            client_id = client_data.get('client_id') or client_data.get('id')
            if not client_id:
                client_id = str(uuid.uuid4())
            
            # Check if client already migrated
            if client_id in self.migrated_clients:
                self.migration_results['duplicates_skipped'] += 1
                return
            
            # Map client data to core schema
            core_client_data = self._map_to_core_schema(client_data, client_id)
            
            # Insert into core database
            self._insert_into_core_database(core_client_data, core_cursor)
            
            # Mark as migrated
            self.migrated_clients.add(client_id)
            self.migration_results['clients_migrated'] += 1
            
        except Exception as e:
            error_msg = f"Error migrating client {client_data.get('first_name', 'Unknown')} from {source_db}: {e}"
            logger.error(error_msg)
            self.migration_results['errors'].append(error_msg)
    
    def _map_to_core_schema(self, client_data: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Map client data to core_clients.db schema"""
        
        # Field mapping from various database schemas to core schema
        field_mapping = {
            'client_id': client_id,
            'first_name': client_data.get('first_name', ''),
            'last_name': client_data.get('last_name', ''),
            'date_of_birth': client_data.get('date_of_birth') or client_data.get('dob'),
            'phone': client_data.get('phone') or client_data.get('primary_phone'),
            'email': client_data.get('email', ''),
            'address': client_data.get('address', ''),
            'emergency_contact_name': client_data.get('emergency_contact_name') or client_data.get('emergency_contact'),
            'emergency_contact_phone': client_data.get('emergency_contact_phone') or client_data.get('emergency_phone'),
            'risk_level': self._validate_risk_level(client_data.get('risk_level', 'medium')),
            'case_status': self._validate_case_status(client_data.get('case_status') or client_data.get('status', 'active')),
            'case_manager_id': client_data.get('case_manager_id', ''),
            'intake_date': client_data.get('intake_date') or client_data.get('created_at'),
            'created_at': client_data.get('created_at') or datetime.now().isoformat(),
            'updated_at': client_data.get('updated_at') or client_data.get('last_updated') or datetime.now().isoformat()
        }
        
        # Clean and validate data
        for key, value in field_mapping.items():
            if value is None:
                field_mapping[key] = ''
            elif isinstance(value, str) and value.lower() in ['none', 'null', '']:
                field_mapping[key] = ''
        
        return field_mapping
    
    def _validate_risk_level(self, risk_level: str) -> str:
        """Validate and normalize risk_level"""
        if not risk_level:
            return 'medium'
        
        risk_level = str(risk_level).lower().strip()
        
        # Map common variations to valid values
        risk_mapping = {
            'low': 'low',
            'medium': 'medium', 
            'med': 'medium',
            'high': 'high',
            'medium risk': 'medium',
            'low risk': 'low',
            'high risk': 'high'
        }
        
        return risk_mapping.get(risk_level, 'medium')
    
    def _validate_case_status(self, case_status: str) -> str:
        """Validate and normalize case_status"""
        if not case_status:
            return 'active'
        
        case_status = str(case_status).lower().strip()
        
        # Map common variations to valid values
        status_mapping = {
            'active': 'active',
            'inactive': 'inactive',
            'completed': 'completed',
            'pending': 'active',
            'open': 'active',
            'closed': 'completed'
        }
        
        return status_mapping.get(case_status, 'active')
    
    def _insert_into_core_database(self, client_data: Dict[str, Any], core_cursor):
        """Insert client data into core_clients.db"""
        
        # Check if client already exists
        core_cursor.execute("SELECT client_id FROM clients WHERE client_id = ?", (client_data['client_id'],))
        if core_cursor.fetchone():
            # Update existing client
            set_clause = ', '.join([f"{k} = ?" for k in client_data.keys() if k != 'client_id'])
            values = [v for k, v in client_data.items() if k != 'client_id'] + [client_data['client_id']]
            
            core_cursor.execute(f"UPDATE clients SET {set_clause} WHERE client_id = ?", values)
        else:
            # Insert new client
            columns = ', '.join(client_data.keys())
            placeholders = ', '.join(['?' for _ in client_data])
            values = list(client_data.values())
            
            core_cursor.execute(f"INSERT INTO clients ({columns}) VALUES ({placeholders})", values)
    
    def _show_migration_summary(self):
        """Display migration results summary"""
        
        print("\n" + "=" * 60)
        print("📊 MIGRATION SUMMARY")
        print("=" * 60)
        print(f"✅ Clients migrated: {self.migration_results['clients_migrated']}")
        print(f"⏭️  Duplicates skipped: {self.migration_results['duplicates_skipped']}")
        print(f"❌ Errors: {len(self.migration_results['errors'])}")
        
        if self.migration_results['errors']:
            print(f"\n⚠️  Errors encountered:")
            for error in self.migration_results['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
            if len(self.migration_results['errors']) > 5:
                print(f"   ... and {len(self.migration_results['errors']) - 5} more")
        
        # Show final client count in core database
        with sqlite3.connect(self.core_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clients")
            total_clients = cursor.fetchone()[0]
            print(f"\n📊 Total clients in core_clients.db: {total_clients}")

def main():
    """Main migration function"""
    migrator = ClientDataMigrator()
    success = migrator.migrate_all_client_data()
    
    if success:
        print("\n🎉 Step 2 Complete: Client data migration successful!")
    else:
        print("\n❌ Step 2 Failed: Client data migration failed")

if __name__ == "__main__":
    main()
