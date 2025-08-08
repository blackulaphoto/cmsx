#!/usr/bin/env python3
"""
Data Integrity Fix Script
Fixes identified foreign key violations and schema inconsistencies
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataIntegrityFixer:
    """Fix data integrity issues identified by testing"""
    
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
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"❌ Failed to create backup for {db_name}: {e}")
            raise
    
    def fix_case_management_violations(self) -> int:
        """Fix foreign key violations in case_management database"""
        logger.info("🔧 Fixing case_management foreign key violations")
        
        fixes_count = 0
        
        try:
            # Create backup first
            self.backup_database('case_management')
            
            with self.get_db_connection('case_management') as conn:
                cursor = conn.cursor()
                
                # Check current violations
                cursor.execute("PRAGMA foreign_key_check")
                violations = cursor.fetchall()
                logger.info(f"Found {len(violations)} foreign key violations")
                
                # Fix tasks table violations
                # Remove tasks with invalid client_id references
                cursor.execute("""
                    DELETE FROM tasks 
                    WHERE client_id NOT IN (
                        SELECT DISTINCT id FROM clients 
                        WHERE id IS NOT NULL
                    ) AND client_id IS NOT NULL
                """)
                deleted_tasks_client = cursor.rowcount
                logger.info(f"Removed {deleted_tasks_client} tasks with invalid client_id")
                
                # Remove tasks with invalid user_id references
                cursor.execute("""
                    DELETE FROM tasks 
                    WHERE user_id NOT IN (
                        SELECT DISTINCT id FROM users 
                        WHERE id IS NOT NULL
                    ) AND user_id IS NOT NULL
                """)
                deleted_tasks_user = cursor.rowcount
                logger.info(f"Removed {deleted_tasks_user} tasks with invalid user_id")
                
                # Fix documents table violations
                cursor.execute("""
                    DELETE FROM documents 
                    WHERE client_id NOT IN (
                        SELECT DISTINCT id FROM clients 
                        WHERE id IS NOT NULL
                    ) AND client_id IS NOT NULL
                """)
                deleted_documents = cursor.rowcount
                logger.info(f"Removed {deleted_documents} documents with invalid client_id")
                
                conn.commit()
                fixes_count = deleted_tasks_client + deleted_tasks_user + deleted_documents
                
                # Verify fixes
                cursor.execute("PRAGMA foreign_key_check")
                remaining_violations = cursor.fetchall()
                logger.info(f"Remaining violations: {len(remaining_violations)}")
                
        except Exception as e:
            logger.error(f"❌ Failed to fix case_management violations: {e}")
            self.fixes_applied['errors'].append(f"case_management: {e}")
        
        return fixes_count
    
    def fix_resumes_violations(self) -> int:
        """Fix foreign key violations in resumes database"""
        logger.info("🔧 Fixing resumes foreign key violations")
        
        fixes_count = 0
        
        try:
            # Create backup first
            self.backup_database('resumes')
            
            with self.get_db_connection('resumes') as conn:
                cursor = conn.cursor()
                
                # Check current violations
                cursor.execute("PRAGMA foreign_key_check")
                violations = cursor.fetchall()
                logger.info(f"Found {len(violations)} foreign key violations")
                
                # Fix resumes with invalid user_id references
                # First, let's see what users exist
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                logger.info(f"Found {user_count} users in database")
                
                if user_count == 0:
                    # No users exist, create a default user or set user_id to NULL
                    cursor.execute("""
                        UPDATE resumes 
                        SET user_id = NULL 
                        WHERE user_id = 0 OR user_id NOT IN (
                            SELECT DISTINCT id FROM users WHERE id IS NOT NULL
                        )
                    """)
                    updated_resumes = cursor.rowcount
                    logger.info(f"Set user_id to NULL for {updated_resumes} resumes")
                else:
                    # Remove resumes with invalid user_id references
                    cursor.execute("""
                        DELETE FROM resumes 
                        WHERE user_id NOT IN (
                            SELECT DISTINCT id FROM users 
                            WHERE id IS NOT NULL
                        ) AND user_id IS NOT NULL AND user_id != 0
                    """)
                    deleted_resumes = cursor.rowcount
                    logger.info(f"Removed {deleted_resumes} resumes with invalid user_id")
                    fixes_count = deleted_resumes
                
                conn.commit()
                
                # Verify fixes
                cursor.execute("PRAGMA foreign_key_check")
                remaining_violations = cursor.fetchall()
                logger.info(f"Remaining violations: {len(remaining_violations)}")
                
        except Exception as e:
            logger.error(f"❌ Failed to fix resumes violations: {e}")
            self.fixes_applied['errors'].append(f"resumes: {e}")
        
        return fixes_count
    
    def fix_unified_platform_violations(self) -> int:
        """Fix foreign key violations in unified_platform database"""
        logger.info("🔧 Fixing unified_platform foreign key violations")
        
        fixes_count = 0
        
        try:
            # Create backup first
            self.backup_database('unified_platform')
            
            with self.get_db_connection('unified_platform') as conn:
                cursor = conn.cursor()
                
                # Check current violations
                cursor.execute("PRAGMA foreign_key_check")
                violations = cursor.fetchall()
                logger.info(f"Found {len(violations)} foreign key violations")
                
                # Fix benefits_applications with invalid client_id references
                # Check if clients table exists in this database
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='clients'
                """)
                clients_table_exists = cursor.fetchone() is not None
                
                if not clients_table_exists:
                    # No clients table, set client_id to NULL or remove records
                    cursor.execute("""
                        UPDATE benefits_applications 
                        SET client_id = NULL 
                        WHERE client_id = 0
                    """)
                    updated_benefits = cursor.rowcount
                    logger.info(f"Set client_id to NULL for {updated_benefits} benefit applications")
                    fixes_count = updated_benefits
                else:
                    # Remove benefits_applications with invalid client_id references
                    cursor.execute("""
                        DELETE FROM benefits_applications 
                        WHERE client_id NOT IN (
                            SELECT DISTINCT client_id FROM clients 
                            WHERE client_id IS NOT NULL
                        ) AND client_id IS NOT NULL AND client_id != 0
                    """)
                    deleted_benefits = cursor.rowcount
                    logger.info(f"Removed {deleted_benefits} benefit applications with invalid client_id")
                    fixes_count = deleted_benefits
                
                conn.commit()
                
                # Verify fixes
                cursor.execute("PRAGMA foreign_key_check")
                remaining_violations = cursor.fetchall()
                logger.info(f"Remaining violations: {len(remaining_violations)}")
                
        except Exception as e:
            logger.error(f"❌ Failed to fix unified_platform violations: {e}")
            self.fixes_applied['errors'].append(f"unified_platform: {e}")
        
        return fixes_count
    
    def add_missing_columns(self) -> int:
        """Add missing columns identified in testing"""
        logger.info("🔧 Adding missing columns")
        
        updates_count = 0
        
        try:
            # Add updated_at column to case_management clients table if missing
            with self.get_db_connection('case_management') as conn:
                cursor = conn.cursor()
                
                # Check if updated_at column exists
                cursor.execute("PRAGMA table_info(clients)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'updated_at' not in columns:
                    cursor.execute("""
                        ALTER TABLE clients 
                        ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    """)
                    logger.info("✅ Added updated_at column to case_management.clients")
                    updates_count += 1
                
                if 'created_at' not in columns:
                    cursor.execute("""
                        ALTER TABLE clients 
                        ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    """)
                    logger.info("✅ Added created_at column to case_management.clients")
                    updates_count += 1
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Failed to add missing columns: {e}")
            self.fixes_applied['errors'].append(f"missing_columns: {e}")
        
        return updates_count
    
    def verify_fixes(self) -> Dict[str, int]:
        """Verify that fixes were successful"""
        logger.info("🔍 Verifying fixes")
        
        verification_results = {
            'databases_checked': 0,
            'violations_remaining': 0,
            'clean_databases': 0
        }
        
        for db_name in ['case_management', 'resumes', 'unified_platform']:
            try:
                with self.get_db_connection(db_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA foreign_key_check")
                    violations = cursor.fetchall()
                    
                    verification_results['databases_checked'] += 1
                    verification_results['violations_remaining'] += len(violations)
                    
                    if len(violations) == 0:
                        verification_results['clean_databases'] += 1
                        logger.info(f"✅ {db_name}: No foreign key violations")
                    else:
                        logger.warning(f"⚠️ {db_name}: {len(violations)} violations remaining")
                        
            except Exception as e:
                logger.error(f"❌ Failed to verify {db_name}: {e}")
        
        return verification_results
    
    def run_all_fixes(self) -> Dict[str, any]:
        """Run all data integrity fixes"""
        logger.info("🚀 Starting data integrity fixes")
        
        start_time = datetime.now()
        
        # Fix foreign key violations
        case_mgmt_fixes = self.fix_case_management_violations()
        resumes_fixes = self.fix_resumes_violations()
        unified_fixes = self.fix_unified_platform_violations()
        
        # Add missing columns
        schema_fixes = self.add_missing_columns()
        
        # Verify fixes
        verification = self.verify_fixes()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Compile results
        results = {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'fixes_applied': {
                'case_management_violations': case_mgmt_fixes,
                'resumes_violations': resumes_fixes,
                'unified_platform_violations': unified_fixes,
                'schema_updates': schema_fixes,
                'total_fixes': case_mgmt_fixes + resumes_fixes + unified_fixes + schema_fixes
            },
            'verification': verification,
            'errors': self.fixes_applied['errors'],
            'success': len(self.fixes_applied['errors']) == 0 and verification['violations_remaining'] == 0
        }
        
        return results
    
    def print_results_report(self, results: Dict[str, any]):
        """Print human-readable results report"""
        print("\n" + "="*80)
        print("🔧 DATA INTEGRITY FIXES REPORT")
        print("="*80)
        
        print(f"⏱️  Duration: {results['duration_seconds']:.2f} seconds")
        print(f"🎯 Overall Success: {'✅ SUCCESS' if results['success'] else '❌ ISSUES REMAIN'}")
        
        print("\n📊 FIXES APPLIED:")
        fixes = results['fixes_applied']
        print(f"   Case Management Violations Fixed: {fixes['case_management_violations']}")
        print(f"   Resumes Violations Fixed: {fixes['resumes_violations']}")
        print(f"   Unified Platform Violations Fixed: {fixes['unified_platform_violations']}")
        print(f"   Schema Updates Applied: {fixes['schema_updates']}")
        print(f"   Total Fixes Applied: {fixes['total_fixes']}")
        
        print("\n🔍 VERIFICATION RESULTS:")
        verification = results['verification']
        print(f"   Databases Checked: {verification['databases_checked']}")
        print(f"   Clean Databases: {verification['clean_databases']}")
        print(f"   Violations Remaining: {verification['violations_remaining']}")
        
        if results['errors']:
            print("\n⚠️ ERRORS ENCOUNTERED:")
            for error in results['errors']:
                print(f"   • {error}")
        
        print("\n" + "="*80)
        
        if results['success']:
            print("🎉 ALL DATA INTEGRITY ISSUES FIXED SUCCESSFULLY!")
        else:
            print("⚠️ SOME ISSUES REMAIN - CHECK THE DETAILS ABOVE")
        
        print("="*80)

def main():
    """Main entry point"""
    fixer = DataIntegrityFixer()
    
    try:
        results = fixer.run_all_fixes()
        fixer.print_results_report(results)
        
        # Save results to file
        results_file = f"data_integrity_fixes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📊 Results saved to: {results_file}")
        
        # Exit with appropriate code
        return 0 if results['success'] else 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Fix process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"💥 Data integrity fixes failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())