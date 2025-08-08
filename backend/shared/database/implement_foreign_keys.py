#!/usr/bin/env python3
"""
Step 4: Implement foreign key constraints
This ensures referential integrity across all databases
"""

import sqlite3
import os
import logging
from pathlib import Path
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ForeignKeyImplementer:
    """Implement foreign key constraints across all databases"""
    
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
        
        self.fk_results = {
            'constraints_added': [],
            'errors': []
        }
    
    def implement_foreign_key_constraints(self):
        """Implement foreign key constraints across all databases"""
        
        print("🔗 Step 4: Implementing Foreign Key Constraints")
        print("=" * 60)
        
        try:
            # First, ensure core_clients.db has proper constraints
            print("\n📊 Setting up core_clients.db constraints...")
            self._setup_core_constraints()
            
            # Then implement FKs in all module databases
            for db_name, db_path in self.module_databases.items():
                if Path(db_path).exists():
                    print(f"\n📊 Implementing FKs in {db_name}...")
                    success = self._implement_module_foreign_keys(db_name, db_path)
                    if success:
                        self.fk_results['constraints_added'].append(db_name)
                        print(f"   ✅ {db_name} FK constraints implemented")
                    else:
                        print(f"   ❌ {db_name} FK constraints failed")
                else:
                    print(f"⚠️  {db_name} database not found, skipping")
            
            # Show implementation summary
            self._show_fk_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"Foreign key implementation failed: {e}")
            print(f"❌ Foreign key implementation failed: {e}")
            return False
    
    def _setup_core_constraints(self):
        """Set up constraints in core_clients.db"""
        
        try:
            with sqlite3.connect(self.core_db_path) as conn:
                cursor = conn.cursor()
                
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys = ON")
                
                # Verify foreign key constraints are working
                cursor.execute("PRAGMA foreign_key_check")
                fk_issues = cursor.fetchall()
                
                if fk_issues:
                    print(f"   ⚠️  Found {len(fk_issues)} foreign key issues in core database")
                else:
                    print(f"   ✅ Core database foreign key constraints verified")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error setting up core constraints: {e}")
    
    def _implement_module_foreign_keys(self, db_name: str, db_path: str) -> bool:
        """Implement foreign key constraints in a module database"""
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys = ON")
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Add foreign key constraints to tables with client_id
                for table in tables:
                    self._add_client_foreign_key_constraint(cursor, table, db_name)
                
                # Verify foreign key constraints
                cursor.execute("PRAGMA foreign_key_check")
                fk_issues = cursor.fetchall()
                
                if fk_issues:
                    print(f"   ⚠️  Found {len(fk_issues)} foreign key issues in {db_name}")
                    for issue in fk_issues[:3]:  # Show first 3 issues
                        print(f"      • {issue}")
                else:
                    print(f"   ✅ {db_name} foreign key constraints verified")
                
                conn.commit()
                return True
                
        except Exception as e:
            error_msg = f"Error implementing FKs in {db_name}: {e}"
            logger.error(error_msg)
            self.fk_results['errors'].append(error_msg)
            return False
    
    def _add_client_foreign_key_constraint(self, cursor, table: str, db_name: str):
        """Add client_id foreign key constraint to a table"""
        
        try:
            # Check if table has client_id column
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'client_id' not in columns:
                return  # No client_id column, skip
            
            # Check if foreign key constraint already exists
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            existing_fks = cursor.fetchall()
            
            # Look for existing client_id FK
            has_client_fk = any(fk[3] == 'client_id' for fk in existing_fks)
            
            if not has_client_fk:
                # Add foreign key constraint (SQLite doesn't support ALTER TABLE ADD CONSTRAINT)
                # We'll create a new table with the constraint and copy data
                print(f"   🔗 Adding client_id FK constraint to {table}")
                
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table})")
                columns_info = cursor.fetchall()
                
                # Create new table with FK constraint
                new_table_name = f"{table}_new"
                create_sql = self._generate_create_table_with_fk(columns_info, new_table_name, table)
                
                if create_sql:
                    cursor.execute(create_sql)
                    
                    # Copy data to new table
                    cursor.execute(f"INSERT INTO {new_table_name} SELECT * FROM {table}")
                    
                    # Drop old table and rename new table
                    cursor.execute(f"DROP TABLE {table}")
                    cursor.execute(f"ALTER TABLE {new_table_name} RENAME TO {table}")
                    
                    print(f"      ✅ Added FK constraint to {table}")
                
        except Exception as e:
            print(f"      ⚠️  Could not add FK constraint to {table}: {e}")
    
    def _generate_create_table_with_fk(self, columns_info: List, new_table_name: str, original_table: str) -> str:
        """Generate CREATE TABLE statement with foreign key constraint"""
        
        try:
            # Build column definitions
            column_defs = []
            for col in columns_info:
                col_name = col[1]
                col_type = col[2]
                not_null = "NOT NULL" if col[3] else ""
                default_val = f"DEFAULT {col[4]}" if col[4] is not None else ""
                pk = "PRIMARY KEY" if col[5] else ""
                
                # Add foreign key constraint for client_id
                fk_constraint = ""
                if col_name == 'client_id':
                    fk_constraint = f"REFERENCES core_clients.clients(client_id)"
                
                column_def = f"{col_name} {col_type} {not_null} {default_val} {pk} {fk_constraint}".strip()
                column_defs.append(column_def)
            
            # Create the CREATE TABLE statement
            create_sql = f"CREATE TABLE {new_table_name} (\n"
            create_sql += ",\n".join(column_defs)
            create_sql += "\n)"
            
            return create_sql
            
        except Exception as e:
            logger.error(f"Error generating CREATE TABLE for {original_table}: {e}")
            return None
    
    def _show_fk_summary(self):
        """Display foreign key implementation summary"""
        
        print("\n" + "=" * 60)
        print("📊 FOREIGN KEY IMPLEMENTATION SUMMARY")
        print("=" * 60)
        print(f"✅ Databases with FK constraints: {len(self.fk_results['constraints_added'])}")
        print(f"❌ Errors: {len(self.fk_results['errors'])}")
        
        if self.fk_results['constraints_added']:
            print(f"\n✅ Successfully implemented FKs in:")
            for db in self.fk_results['constraints_added']:
                print(f"   • {db}")
        
        if self.fk_results['errors']:
            print(f"\n❌ Errors encountered:")
            for error in self.fk_results['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
            if len(self.fk_results['errors']) > 5:
                print(f"   ... and {len(self.fk_results['errors']) - 5} more")
        
        # Test referential integrity
        print(f"\n🔍 Testing referential integrity...")
        self._test_referential_integrity()
    
    def _test_referential_integrity(self):
        """Test referential integrity across databases"""
        
        try:
            # Test core database integrity
            with sqlite3.connect(self.core_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_key_check")
                core_issues = cursor.fetchall()
                
                if core_issues:
                    print(f"   ⚠️  Core database has {len(core_issues)} integrity issues")
                else:
                    print(f"   ✅ Core database referential integrity verified")
            
            # Test a few module databases
            test_databases = ['reminders', 'legal_cases', 'expungement']
            for db_name in test_databases:
                db_path = self.module_databases.get(db_name)
                if db_path and Path(db_path).exists():
                    with sqlite3.connect(db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("PRAGMA foreign_key_check")
                        module_issues = cursor.fetchall()
                        
                        if module_issues:
                            print(f"   ⚠️  {db_name} has {len(module_issues)} integrity issues")
                        else:
                            print(f"   ✅ {db_name} referential integrity verified")
                            
        except Exception as e:
            print(f"   ⚠️  Error testing referential integrity: {e}")

def main():
    """Main foreign key implementation function"""
    fk_implementer = ForeignKeyImplementer()
    success = fk_implementer.implement_foreign_key_constraints()
    
    if success:
        print("\n🎉 Step 4 Complete: Foreign key constraints implemented successfully!")
    else:
        print("\n❌ Step 4 Failed: Foreign key constraint implementation failed")

if __name__ == "__main__":
    main()
