#!/usr/bin/env python3
"""
Complete Data Integrity Fix Script
Fixes all identified foreign key violations and schema inconsistencies
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import json
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteDataIntegrityFixer:
    """Complete fix for all data integrity issues"""
    
    def __init__(self):
        self.db_paths = {
            'case_management': 'databases/case_management.db',
            'resumes': 'databases/resumes.db',
            'unified_platform': 'databases/unified_platform.db',
            'legal_cases': 'databases/legal_cases.db',
            'core_clients': 'databases/core_clients.db'
        }
        
        self.fixes_applied = {
            'foreign_key_violations_fixed': 0,
            'orphaned_records_removed': 0,
            'schema_updates_applied': 0,
            'errors': []
        }
    
    def get_db_connection(self, db_name: str) -> sqlite3.Connection:
        """Get database connection"""
        db_path = self.db_paths.get(db_name)
        if not db_path or not Path(db_path).exists():
            raise FileNotFoundError(f"Database {db_name} not found at {db_path}")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = OFF")  # Disable during cleanup
        return conn
    
    def backup_database(self, db_name: str) -> str:
        """Create backup of database before making changes"""
        db_path = self.db_paths[db_name]
        backup_path = f"{db_path}.backup_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"❌ Failed to create backup for {db_name}: {e}")
            raise
    
    def analyze_foreign_key_violations(self, db_name: str) -> List[Dict]:
        """Analyze foreign key violations in detail"""
        violations = []
        
        try:
            with self.get_db_connection(db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_key_check")
                raw_violations = cursor.fetchall()
                
                for violation in raw_violations:
                    violations.append({
                        'table': violation[0],
                        'rowid': violation[1],
                        'parent': violation[2],
                        'fkid': violation[3]
                    })
                    
        except Exception as e:
            logger.error(f"Failed to analyze violations in {db_name}: {e}")
        
        return violations
    
    def fix_case_management_complete(self) -> int:
        """Complete fix for case_management database"""
        logger.info("🔧 Complete fix for case_management database")
        
        fixes_count = 0
        
        try:
            # Create backup first
            self.backup_database('case_management')
            
            with self.get_db_connection('case_management') as conn:
                cursor = conn.cursor()
                
                # Analyze violations first
                violations = self.analyze_foreign_key_violations('case_management')
                logger.info(f"Found {len(violations)} violations to fix")
                
                # Get valid client IDs (integer IDs)
                cursor.execute("SELECT id FROM clients WHERE id IS NOT NULL")
                valid_client_ids = {row[0] for row in cursor.fetchall()}
                logger.info(f"Found {len(valid_client_ids)} valid client IDs")
                
                # Get valid user IDs
                cursor.execute("SELECT id FROM users WHERE id IS NOT NULL")
                valid_user_ids = {row[0] for row in cursor.fetchall()}
                logger.info(f"Found {len(valid_user_ids)} valid user IDs")
                
                # Fix tasks table - client_id violations
                if valid_client_ids:
                    # Convert text client_ids to integer IDs where possible
                    cursor.execute("SELECT id, client_id FROM tasks WHERE client_id IS NOT NULL")
                    tasks_to_fix = cursor.fetchall()
                    
                    for task in tasks_to_fix:
                        task_id, client_id = task[0], task[1]
                        
                        # Try to find matching client by client_id (text field)
                        cursor.execute("SELECT id FROM clients WHERE client_id = ?", (client_id,))
                        client_match = cursor.fetchone()
                        
                        if client_match:
                            # Update task to use integer ID
                            cursor.execute("UPDATE tasks SET client_id = ? WHERE id = ?", 
                                         (client_match[0], task_id))
                            fixes_count += 1
                        else:
                            # No matching client found, remove task
                            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                            fixes_count += 1
                            logger.info(f"Removed task {task_id} with invalid client_id {client_id}")
                else:
                    # No valid clients, remove all tasks
                    cursor.execute("DELETE FROM tasks")
                    deleted_count = cursor.rowcount
                    fixes_count += deleted_count
                    logger.info(f"Removed {deleted_count} tasks (no valid clients)")
                
                # Fix tasks table - user reference violations
                if valid_user_ids:
                    # Fix assigned_to references
                    cursor.execute("UPDATE tasks SET assigned_to = NULL WHERE assigned_to NOT IN (SELECT id FROM users)")
                    fixes_count += cursor.rowcount
                    
                    # Fix created_by references
                    cursor.execute("UPDATE tasks SET created_by = NULL WHERE created_by NOT IN (SELECT id FROM users)")
                    fixes_count += cursor.rowcount
                    
                    # Fix updated_by references
                    cursor.execute("UPDATE tasks SET updated_by = NULL WHERE updated_by NOT IN (SELECT id FROM users)")
                    fixes_count += cursor.rowcount
                else:
                    # No valid users, set all user references to NULL
                    cursor.execute("UPDATE tasks SET assigned_to = NULL, created_by = NULL, updated_by = NULL")
                    fixes_count += cursor.rowcount
                
                # Fix documents table
                cursor.execute("SELECT id, client_id FROM documents WHERE client_id IS NOT NULL")
                documents_to_fix = cursor.fetchall()
                
                for doc in documents_to_fix:
                    doc_id, client_id = doc[0], doc[1]
                    
                    # Try to find matching client
                    cursor.execute("SELECT id FROM clients WHERE client_id = ? OR id = ?", (client_id, client_id))
                    client_match = cursor.fetchone()
                    
                    if client_match:
                        cursor.execute("UPDATE documents SET client_id = ? WHERE id = ?", 
                                     (client_match[0], doc_id))
                        fixes_count += 1
                    else:
                        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                        fixes_count += 1
                        logger.info(f"Removed document {doc_id} with invalid client_id {client_id}")
                
                conn.commit()
                
                # Verify fixes
                cursor.execute("PRAGMA foreign_key_check")
                remaining_violations = cursor.fetchall()
                logger.info(f"Remaining violations: {len(remaining_violations)}")
                
        except Exception as e:
            logger.error(f"❌ Failed to fix case_management: {e}")
            self.fixes_applied['errors'].append(f"case_management: {e}")
        
        return fixes_count
    
    def fix_unified_platform_complete(self) -> int:
        """Complete fix for unified_platform database"""
        logger.info("🔧 Complete fix for unified_platform database")
        
        fixes_count = 0
        
        try:
            # Create backup first
            self.backup_database('unified_platform')
            
            with self.get_db_connection('unified_platform') as conn:
                cursor = conn.cursor()
                
                # Check if clients table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                clients_exists = cursor.fetchone() is not None
                
                if clients_exists:
                    # Get valid client IDs
                    cursor.execute("SELECT client_id FROM clients WHERE client_id IS NOT NULL")
                    valid_client_ids = {row[0] for row in cursor.fetchall()}
                    logger.info(f"Found {len(valid_client_ids)} valid client IDs")
                    
                    if valid_client_ids:
                        # Remove benefits_applications with invalid client_id
                        cursor.execute("""
                            DELETE FROM benefits_applications 
                            WHERE client_id NOT IN (SELECT client_id FROM clients)
                            AND client_id IS NOT NULL AND client_id != ''
                        """)
                        fixes_count += cursor.rowcount
                    else:
                        # No valid clients, set client_id to NULL
                        cursor.execute("UPDATE benefits_applications SET client_id = NULL")
                        fixes_count += cursor.rowcount
                else:
                    # No clients table, set all client_id to NULL
                    cursor.execute("UPDATE benefits_applications SET client_id = NULL WHERE client_id IS NOT NULL")
                    fixes_count += cursor.rowcount
                    logger.info("Set all benefit application client_ids to NULL (no clients table)")
                
                conn.commit()
                
                # Verify fixes
                cursor.execute("PRAGMA foreign_key_check")
                remaining_violations = cursor.fetchall()
                logger.info(f"Remaining violations: {len(remaining_violations)}")
                
        except Exception as e:
            logger.error(f"❌ Failed to fix unified_platform: {e}")
            self.fixes_applied['errors'].append(f"unified_platform: {e}")
        
        return fixes_count
    
    def create_default_users_if_needed(self) -> int:
        """Create default users if none exist"""
        logger.info("🔧 Creating default users if needed")
        
        users_created = 0
        
        try:
            with self.get_db_connection('case_management') as conn:
                cursor = conn.cursor()
                
                # Check if users table exists and has data
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                if user_count == 0:
                    # Create default system user
                    default_user_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO users (id, username, email, full_name, role, is_active, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        1,  # Use integer ID for consistency
                        'system',
                        'system@casemanagement.local',
                        'System User',
                        'admin',
                        1,
                        datetime.now().isoformat()
                    ))
                    users_created = 1
                    logger.info("✅ Created default system user")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Failed to create default users: {e}")
            self.fixes_applied['errors'].append(f"default_users: {e}")
        
        return users_created
    
    def add_missing_columns_safe(self) -> int:
        """Safely add missing columns"""
        logger.info("🔧 Safely adding missing columns")
        
        updates_count = 0
        
        try:
            with self.get_db_connection('case_management') as conn:
                cursor = conn.cursor()
                
                # Check current columns in clients table
                cursor.execute("PRAGMA table_info(clients)")
                columns = {col[1]: col for col in cursor.fetchall()}
                
                # Add updated_at if missing (with NULL default to avoid constraint issues)
                if 'updated_at' not in columns:
                    cursor.execute("ALTER TABLE clients ADD COLUMN updated_at DATETIME")
                    # Update existing records
                    cursor.execute("UPDATE clients SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
                    logger.info("✅ Added updated_at column to clients")
                    updates_count += 1
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Failed to add missing columns: {e}")
            self.fixes_applied['errors'].append(f"missing_columns: {e}")
        
        return updates_count
    
    def verify_all_fixes(self) -> Dict[str, int]:
        """Verify all fixes across all databases"""
        logger.info("🔍 Verifying all fixes")
        
        verification_results = {
            'databases_checked': 0,
            'violations_remaining': 0,
            'clean_databases': 0,
            'details': {}
        }
        
        for db_name in ['case_management', 'resumes', 'unified_platform']:
            try:
                with self.get_db_connection(db_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA foreign_key_check")
                    violations = cursor.fetchall()
                    
                    verification_results['databases_checked'] += 1
                    verification_results['violations_remaining'] += len(violations)
                    verification_results['details'][db_name] = len(violations)
                    
                    if len(violations) == 0:
                        verification_results['clean_databases'] += 1
                        logger.info(f"✅ {db_name}: No foreign key violations")
                    else:
                        logger.warning(f"⚠️ {db_name}: {len(violations)} violations remaining")
                        # Log first few violations for debugging
                        for i, violation in enumerate(violations[:3]):
                            logger.warning(f"   Violation {i+1}: {dict(violation)}")
                        
            except Exception as e:
                logger.error(f"❌ Failed to verify {db_name}: {e}")
        
        return verification_results
    
    def run_complete_fixes(self) -> Dict[str, any]:
        """Run complete data integrity fixes"""
        logger.info("🚀 Starting complete data integrity fixes")
        
        start_time = datetime.now()
        
        # Create default users first
        users_created = self.create_default_users_if_needed()
        
        # Fix all foreign key violations
        case_mgmt_fixes = self.fix_case_management_complete()
        unified_fixes = self.fix_unified_platform_complete()
        
        # Add missing columns safely
        schema_fixes = self.add_missing_columns_safe()
        
        # Verify all fixes
        verification = self.verify_all_fixes()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Compile results
        results = {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'fixes_applied': {
                'users_created': users_created,
                'case_management_violations': case_mgmt_fixes,
                'unified_platform_violations': unified_fixes,
                'schema_updates': schema_fixes,
                'total_fixes': users_created + case_mgmt_fixes + unified_fixes + schema_fixes
            },
            'verification': verification,
            'errors': self.fixes_applied['errors'],
            'success': len(self.fixes_applied['errors']) == 0 and verification['violations_remaining'] == 0
        }
        
        return results
    
    def print_results_report(self, results: Dict[str, any]):
        """Print comprehensive results report"""
        print("\n" + "="*80)
        print("🔧 COMPLETE DATA INTEGRITY FIXES REPORT")
        print("="*80)
        
        print(f"⏱️  Duration: {results['duration_seconds']:.2f} seconds")
        print(f"🎯 Overall Success: {'✅ SUCCESS' if results['success'] else '❌ ISSUES REMAIN'}")
        
        print("\n📊 FIXES APPLIED:")
        fixes = results['fixes_applied']
        print(f"   Default Users Created: {fixes['users_created']}")
        print(f"   Case Management Violations Fixed: {fixes['case_management_violations']}")
        print(f"   Unified Platform Violations Fixed: {fixes['unified_platform_violations']}")
        print(f"   Schema Updates Applied: {fixes['schema_updates']}")
        print(f"   Total Fixes Applied: {fixes['total_fixes']}")
        
        print("\n🔍 VERIFICATION RESULTS:")
        verification = results['verification']
        print(f"   Databases Checked: {verification['databases_checked']}")
        print(f"   Clean Databases: {verification['clean_databases']}")
        print(f"   Violations Remaining: {verification['violations_remaining']}")
        
        print("\n📋 DATABASE DETAILS:")
        for db_name, violation_count in verification.get('details', {}).items():
            status = "✅" if violation_count == 0 else "❌"
            print(f"   {status} {db_name}: {violation_count} violations")
        
        if results['errors']:
            print("\n⚠️ ERRORS ENCOUNTERED:")
            for error in results['errors']:
                print(f"   • {error}")
        
        print("\n" + "="*80)
        
        if results['success']:
            print("🎉 ALL DATA INTEGRITY ISSUES FIXED SUCCESSFULLY!")
            print("✅ System is now ready for production deployment!")
        else:
            print("⚠️ SOME ISSUES REMAIN - CHECK THE DETAILS ABOVE")
        
        print("="*80)

def main():
    """Main entry point"""
    fixer = CompleteDataIntegrityFixer()
    
    try:
        results = fixer.run_complete_fixes()
        fixer.print_results_report(results)
        
        # Save results to file
        results_file = f"complete_data_integrity_fixes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📊 Results saved to: {results_file}")
        
        # Exit with appropriate code
        return 0 if results['success'] else 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Fix process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"💥 Complete data integrity fixes failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())