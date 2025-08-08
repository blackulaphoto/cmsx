#!/usr/bin/env python3
"""
Final Data Integrity Fix Script
Targeted fixes for the specific schema issues identified
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

class FinalDataIntegrityFixer:
    """Final targeted fix for data integrity issues"""
    
    def __init__(self):
        self.db_paths = {
            'case_management': 'databases/case_management.db',
            'resumes': 'databases/resumes.db',
            'unified_platform': 'databases/unified_platform.db'
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
        backup_path = f"{db_path}.backup_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"❌ Failed to create backup for {db_name}: {e}")
            raise
    
    def fix_case_management_final(self) -> int:
        """Final fix for case_management database"""
        logger.info("🔧 Final fix for case_management database")
        
        fixes_count = 0
        
        try:
            # Create backup first
            self.backup_database('case_management')
            
            with self.get_db_connection('case_management') as conn:
                cursor = conn.cursor()
                
                # Create a default user if none exist
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                if user_count == 0:
                    # Create default system user
                    cursor.execute("""
                        INSERT INTO users (id, username, email, role, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        'system-user-001',
                        'system',
                        'system@casemanagement.local',
                        'admin',
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    logger.info("✅ Created default system user")
                    fixes_count += 1
                
                # Get valid client integer IDs
                cursor.execute("SELECT id FROM clients WHERE id IS NOT NULL")
                valid_client_ids = {str(row[0]) for row in cursor.fetchall()}
                logger.info(f"Found {len(valid_client_ids)} valid client integer IDs")
                
                # Get valid user IDs
                cursor.execute("SELECT id FROM users WHERE id IS NOT NULL")
                valid_user_ids = {row[0] for row in cursor.fetchall()}
                logger.info(f"Found {len(valid_user_ids)} valid user IDs")
                
                # Fix tasks - remove tasks with invalid client_id references
                if valid_client_ids:
                    # Build placeholders for the IN clause
                    placeholders = ','.join('?' * len(valid_client_ids))
                    cursor.execute(f"""
                        DELETE FROM tasks 
                        WHERE client_id NOT IN ({placeholders})
                    """, list(valid_client_ids))
                    deleted_tasks = cursor.rowcount
                    logger.info(f"Removed {deleted_tasks} tasks with invalid client_id")
                    fixes_count += deleted_tasks
                else:
                    # No valid clients, remove all tasks
                    cursor.execute("DELETE FROM tasks")
                    deleted_tasks = cursor.rowcount
                    logger.info(f"Removed {deleted_tasks} tasks (no valid clients)")
                    fixes_count += deleted_tasks
                
                # Fix user references in tasks - set to NULL if invalid
                if valid_user_ids:
                    placeholders = ','.join('?' * len(valid_user_ids))
                    
                    # Fix assigned_to
                    cursor.execute(f"""
                        UPDATE tasks SET assigned_to = NULL 
                        WHERE assigned_to IS NOT NULL AND assigned_to NOT IN ({placeholders})
                    """, list(valid_user_ids))
                    fixes_count += cursor.rowcount
                    
                    # Fix created_by
                    cursor.execute(f"""
                        UPDATE tasks SET created_by = NULL 
                        WHERE created_by IS NOT NULL AND created_by NOT IN ({placeholders})
                    """, list(valid_user_ids))
                    fixes_count += cursor.rowcount
                    
                    # Fix updated_by
                    cursor.execute(f"""
                        UPDATE tasks SET updated_by = NULL 
                        WHERE updated_by IS NOT NULL AND updated_by NOT IN ({placeholders})
                    """, list(valid_user_ids))
                    fixes_count += cursor.rowcount
                else:
                    # No valid users, set all user references to NULL
                    cursor.execute("""
                        UPDATE tasks 
                        SET assigned_to = NULL, created_by = NULL, updated_by = NULL
                        WHERE assigned_to IS NOT NULL OR created_by IS NOT NULL OR updated_by IS NOT NULL
                    """)
                    fixes_count += cursor.rowcount
                
                # Fix documents - remove documents with invalid client_id
                if valid_client_ids:
                    placeholders = ','.join('?' * len(valid_client_ids))
                    cursor.execute(f"""
                        DELETE FROM documents 
                        WHERE client_id NOT IN ({placeholders})
                    """, list(valid_client_ids))
                    deleted_docs = cursor.rowcount
                    logger.info(f"Removed {deleted_docs} documents with invalid client_id")
                    fixes_count += deleted_docs
                else:
                    cursor.execute("DELETE FROM documents")
                    deleted_docs = cursor.rowcount
                    logger.info(f"Removed {deleted_docs} documents (no valid clients)")
                    fixes_count += deleted_docs
                
                conn.commit()
                
                # Verify fixes
                cursor.execute("PRAGMA foreign_key_check")
                remaining_violations = cursor.fetchall()
                logger.info(f"Remaining violations: {len(remaining_violations)}")
                
        except Exception as e:
            logger.error(f"❌ Failed to fix case_management: {e}")
            self.fixes_applied['errors'].append(f"case_management: {e}")
        
        return fixes_count
    
    def fix_unified_platform_final(self) -> int:
        """Final fix for unified_platform database"""
        logger.info("🔧 Final fix for unified_platform database")
        
        fixes_count = 0
        
        try:
            # Create backup first
            self.backup_database('unified_platform')
            
            with self.get_db_connection('unified_platform') as conn:
                cursor = conn.cursor()
                
                # Since client_id is NOT NULL, we need to either:
                # 1. Remove the records, or 
                # 2. Temporarily disable the constraint and set to a valid value
                
                # Option 1: Remove invalid records (safest approach)
                cursor.execute("DELETE FROM benefits_applications WHERE client_id = '' OR client_id = '0'")
                deleted_benefits = cursor.rowcount
                logger.info(f"Removed {deleted_benefits} benefit applications with invalid client_id")
                fixes_count += deleted_benefits
                
                conn.commit()
                
                # Verify fixes
                cursor.execute("PRAGMA foreign_key_check")
                remaining_violations = cursor.fetchall()
                logger.info(f"Remaining violations: {len(remaining_violations)}")
                
        except Exception as e:
            logger.error(f"❌ Failed to fix unified_platform: {e}")
            self.fixes_applied['errors'].append(f"unified_platform: {e}")
        
        return fixes_count
    
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
    
    def run_final_fixes(self) -> Dict[str, any]:
        """Run final data integrity fixes"""
        logger.info("🚀 Starting final data integrity fixes")
        
        start_time = datetime.now()
        
        # Fix all foreign key violations
        case_mgmt_fixes = self.fix_case_management_final()
        unified_fixes = self.fix_unified_platform_final()
        
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
                'case_management_violations': case_mgmt_fixes,
                'unified_platform_violations': unified_fixes,
                'total_fixes': case_mgmt_fixes + unified_fixes
            },
            'verification': verification,
            'errors': self.fixes_applied['errors'],
            'success': len(self.fixes_applied['errors']) == 0 and verification['violations_remaining'] == 0
        }
        
        return results
    
    def print_results_report(self, results: Dict[str, any]):
        """Print comprehensive results report"""
        print("\n" + "="*80)
        print("🔧 FINAL DATA INTEGRITY FIXES REPORT")
        print("="*80)
        
        print(f"⏱️  Duration: {results['duration_seconds']:.2f} seconds")
        print(f"🎯 Overall Success: {'✅ SUCCESS' if results['success'] else '❌ ISSUES REMAIN'}")
        
        print("\n📊 FIXES APPLIED:")
        fixes = results['fixes_applied']
        print(f"   Case Management Violations Fixed: {fixes['case_management_violations']}")
        print(f"   Unified Platform Violations Fixed: {fixes['unified_platform_violations']}")
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
    fixer = FinalDataIntegrityFixer()
    
    try:
        results = fixer.run_final_fixes()
        fixer.print_results_report(results)
        
        # Save results to file
        results_file = f"final_data_integrity_fixes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📊 Results saved to: {results_file}")
        
        # Exit with appropriate code
        return 0 if results['success'] else 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Fix process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"💥 Final data integrity fixes failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())