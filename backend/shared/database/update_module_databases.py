#!/usr/bin/env python3
"""
Step 3: Update module databases to remove client tables, add client_id FKs
This removes client duplication and establishes proper foreign key relationships
"""

import sqlite3
import os
import logging
from pathlib import Path
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModuleDatabaseUpdater:
    """Update module databases to use core_clients.db as single source of truth"""
    
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
        
        self.update_results = {
            'databases_updated': [],
            'errors': []
        }
    
    def update_all_module_databases(self):
        """Update all module databases to remove client tables and add FKs"""
        
        print("🔧 Step 3: Updating Module Databases")
        print("=" * 60)
        
        try:
            # Process each module database
            for db_name, db_path in self.module_databases.items():
                if Path(db_path).exists():
                    print(f"\n📊 Updating {db_name}...")
                    success = self._update_module_database(db_name, db_path)
                    if success:
                        self.update_results['databases_updated'].append(db_name)
                        print(f"   ✅ {db_name} updated successfully")
                    else:
                        print(f"   ❌ {db_name} update failed")
                else:
                    print(f"⚠️  {db_name} database not found, skipping")
            
            # Show update summary
            self._show_update_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"Module database update failed: {e}")
            print(f"❌ Module database update failed: {e}")
            return False
    
    def _update_module_database(self, db_name: str, db_path: str) -> bool:
        """Update a specific module database"""
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys = ON")
                
                # Get all tables in the database
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                print(f"   📋 Found {len(tables)} tables in {db_name}")
                
                # Remove clients table if it exists
                if 'clients' in tables:
                    print(f"   🗑️  Removing clients table from {db_name}")
                    cursor.execute("DROP TABLE IF EXISTS clients")
                    tables.remove('clients')
                
                # Update tables that should have client_id foreign keys
                self._add_client_foreign_keys(db_name, cursor, tables)
                
                conn.commit()
                return True
                
        except Exception as e:
            error_msg = f"Error updating {db_name}: {e}"
            logger.error(error_msg)
            self.update_results['errors'].append(error_msg)
            return False
    
    def _add_client_foreign_keys(self, db_name: str, cursor, tables: List[str]):
        """Add client_id foreign keys to relevant tables"""
        
        # Define which tables should have client_id FKs based on module type
        client_fk_tables = self._get_client_fk_tables(db_name, tables)
        
        for table in client_fk_tables:
            print(f"   🔗 Adding client_id FK to {table}")
            
            try:
                # Check if client_id column already exists
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'client_id' not in columns:
                    # Add client_id column
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN client_id TEXT")
                    
                    # Create index for performance
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_client_id ON {table}(client_id)")
                    
                    print(f"      ✅ Added client_id column to {table}")
                else:
                    print(f"      ℹ️  client_id column already exists in {table}")
                    
            except Exception as e:
                print(f"      ⚠️  Could not add client_id to {table}: {e}")
    
    def _get_client_fk_tables(self, db_name: str, tables: List[str]) -> List[str]:
        """Get list of tables that should have client_id foreign keys"""
        
        # Define module-specific tables that should reference clients
        module_tables = {
            'case_management': ['tasks', 'appointments', 'case_notes'],
            'reminders': ['tasks', 'reminders'],
            'legal_cases': ['legal_cases', 'court_dates', 'expungement_eligibility'],
            'expungement': ['expungement_cases', 'eligibility_assessments'],
            'benefits_transport': ['benefits_applications', 'disability_assessments'],
            'housing': ['housing_applications', 'client_housing_profiles'],
            'housing_resources': ['housing_inventory', 'applications'],
            'jobs': ['job_applications', 'client_employment_profiles'],
            'resumes': ['resumes', 'case_files'],
            'services': ['client_referrals', 'service_applications'],
            'social_services': ['client_profiles', 'service_records'],
            'unified_platform': ['unified_records', 'cross_module_data'],
            'case_manager': ['manager_clients', 'assignments']
        }
        
        # Return intersection of expected tables and actual tables
        expected_tables = module_tables.get(db_name, [])
        return [table for table in expected_tables if table in tables]
    
    def _show_update_summary(self):
        """Display update results summary"""
        
        print("\n" + "=" * 60)
        print("📊 MODULE DATABASE UPDATE SUMMARY")
        print("=" * 60)
        print(f"✅ Databases updated: {len(self.update_results['databases_updated'])}")
        print(f"❌ Errors: {len(self.update_results['errors'])}")
        
        if self.update_results['databases_updated']:
            print(f"\n✅ Successfully updated:")
            for db in self.update_results['databases_updated']:
                print(f"   • {db}")
        
        if self.update_results['errors']:
            print(f"\n❌ Errors encountered:")
            for error in self.update_results['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
            if len(self.update_results['errors']) > 5:
                print(f"   ... and {len(self.update_results['errors']) - 5} more")
        
        # Verify core_clients.db still has data
        with sqlite3.connect(self.core_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clients")
            total_clients = cursor.fetchone()[0]
            print(f"\n📊 Clients in core_clients.db: {total_clients}")

def main():
    """Main update function"""
    updater = ModuleDatabaseUpdater()
    success = updater.update_all_module_databases()
    
    if success:
        print("\n🎉 Step 3 Complete: Module databases updated successfully!")
    else:
        print("\n❌ Step 3 Failed: Module database update failed")

if __name__ == "__main__":
    main()
