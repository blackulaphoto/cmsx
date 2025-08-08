#!/usr/bin/env python3
"""
Database Index Optimization Script
Creates and optimizes indexes for better performance across all databases
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseIndexOptimizer:
    """Optimize database indexes for performance"""
    
    def __init__(self):
        self.db_paths = {
            'core_clients': 'databases/core_clients.db',
            'case_management': 'databases/case_management.db',
            'legal_cases': 'databases/legal_cases.db',
            'expungement': 'databases/expungement.db',
            'reminders': 'databases/reminders.db',
            'benefits_transport': 'databases/benefits_transport.db',
            'housing_resources': 'databases/housing_resources.db',
            'social_services': 'databases/social_services.db',
            'resumes': 'databases/resumes.db',
            'search_cache': 'databases/search_cache.db',
            'unified_platform': 'databases/unified_platform.db'
        }
        
        # Define optimal indexes for each database
        self.index_definitions = {
            'core_clients': [
                ('idx_clients_client_id', 'clients', ['client_id']),
                ('idx_clients_case_status', 'clients', ['case_status']),
                ('idx_clients_risk_level', 'clients', ['risk_level']),
                ('idx_clients_case_manager', 'clients', ['case_manager_id']),
                ('idx_clients_status_risk', 'clients', ['case_status', 'risk_level']),
                ('idx_clients_name', 'clients', ['last_name', 'first_name']),
                ('idx_client_goals_client_id', 'client_goals', ['client_id']),
                ('idx_client_barriers_client_id', 'client_barriers', ['client_id']),
                ('idx_case_notes_client_id', 'case_notes', ['client_id']),
                ('idx_case_notes_created_at', 'case_notes', ['created_at'])
            ],
            
            'case_management': [
                ('idx_clients_client_id', 'clients', ['client_id']),
                ('idx_clients_case_status', 'clients', ['case_status']),
                ('idx_clients_risk_level', 'clients', ['risk_level']),
                ('idx_clients_case_manager', 'clients', ['case_manager_id']),
                ('idx_clients_status_risk', 'clients', ['case_status', 'risk_level']),
                ('idx_clients_name', 'clients', ['last_name', 'first_name']),
                ('idx_clients_intake_date', 'clients', ['intake_date']),
                ('idx_clients_created_at', 'clients', ['created_at'])
            ],
            
            'legal_cases': [
                ('idx_legal_cases_case_id', 'legal_cases', ['case_id']),
                ('idx_legal_cases_client_id', 'legal_cases', ['client_id']),
                ('idx_legal_cases_status', 'legal_cases', ['case_status']),
                ('idx_legal_cases_type', 'legal_cases', ['case_type']),
                ('idx_legal_cases_client_status', 'legal_cases', ['client_id', 'case_status']),
                ('idx_legal_cases_created_at', 'legal_cases', ['created_at']),
                ('idx_court_dates_case_id', 'court_dates', ['case_id']),
                ('idx_court_dates_client_id', 'court_dates', ['client_id']),
                ('idx_court_dates_date', 'court_dates', ['court_date']),
                ('idx_court_dates_status', 'court_dates', ['status'])
            ],
            
            'expungement': [
                ('idx_expungement_cases_client_id', 'expungement_cases', ['client_id']),
                ('idx_expungement_cases_legal_case_id', 'expungement_cases', ['legal_case_id']),
                ('idx_expungement_cases_status', 'expungement_cases', ['status']),
                ('idx_expungement_cases_score', 'expungement_cases', ['eligibility_score']),
                ('idx_expungement_cases_created_at', 'expungement_cases', ['created_at'])
            ],
            
            'reminders': [
                ('idx_reminders_reminder_id', 'reminders', ['reminder_id']),
                ('idx_reminders_client_id', 'reminders', ['client_id']),
                ('idx_reminders_status', 'reminders', ['status']),
                ('idx_reminders_priority', 'reminders', ['priority']),
                ('idx_reminders_due_date', 'reminders', ['due_date']),
                ('idx_reminders_assigned_to', 'reminders', ['assigned_to']),
                ('idx_reminders_client_status', 'reminders', ['client_id', 'status']),
                ('idx_reminders_status_priority', 'reminders', ['status', 'priority']),
                ('idx_reminders_due_priority', 'reminders', ['due_date', 'priority']),
                ('idx_reminders_created_at', 'reminders', ['created_at'])
            ],
            
            'benefits_transport': [
                ('idx_benefit_applications_client_id', 'benefit_applications', ['client_id']),
                ('idx_benefit_applications_status', 'benefit_applications', ['application_status']),
                ('idx_benefit_applications_type', 'benefit_applications', ['benefit_type']),
                ('idx_benefit_applications_client_status', 'benefit_applications', ['client_id', 'application_status']),
                ('idx_benefit_applications_submitted', 'benefit_applications', ['submitted_date']),
                ('idx_disability_assessments_client_id', 'disability_assessments', ['client_id']),
                ('idx_disability_assessments_probability', 'disability_assessments', ['approval_probability'])
            ],
            
            'housing_resources': [
                ('idx_housing_inventory_property_id', 'housing_inventory', ['property_id']),
                ('idx_housing_inventory_background_friendly', 'housing_inventory', ['background_friendly']),
                ('idx_housing_inventory_rent', 'housing_inventory', ['rent_amount']),
                ('idx_housing_inventory_bedrooms', 'housing_inventory', ['bedrooms']),
                ('idx_housing_inventory_available', 'housing_inventory', ['available_date']),
                ('idx_housing_applications_client_id', 'housing_applications', ['client_id']),
                ('idx_housing_applications_property_id', 'housing_applications', ['property_id']),
                ('idx_housing_applications_status', 'housing_applications', ['application_status'])
            ],
            
            'social_services': [
                ('idx_service_providers_provider_id', 'service_providers', ['provider_id']),
                ('idx_service_providers_type', 'service_providers', ['service_type']),
                ('idx_service_providers_background_policy', 'service_providers', ['background_check_policy']),
                ('idx_client_referrals_client_id', 'client_referrals', ['client_id']),
                ('idx_client_referrals_provider_id', 'client_referrals', ['provider_id']),
                ('idx_client_referrals_status', 'client_referrals', ['status']),
                ('idx_client_referrals_date', 'client_referrals', ['referral_date'])
            ],
            
            'resumes': [
                ('idx_resumes_client_id', 'resumes', ['client_id']),
                ('idx_resumes_template_type', 'resumes', ['template_type']),
                ('idx_resumes_created_at', 'resumes', ['created_at']),
                ('idx_client_employment_profiles_client_id', 'client_employment_profiles', ['client_id']),
                ('idx_job_applications_client_id', 'job_applications', ['client_id']),
                ('idx_job_applications_status', 'job_applications', ['application_status']),
                ('idx_job_applications_applied_date', 'job_applications', ['applied_date'])
            ],
            
            'search_cache': [
                ('idx_search_cache_key', 'search_cache', ['cache_key']),
                ('idx_search_cache_expires', 'search_cache', ['expires_at'])
            ]
        }
    
    def get_db_connection(self, db_name: str) -> sqlite3.Connection:
        """Get database connection"""
        db_path = self.db_paths.get(db_name)
        if not db_path or not Path(db_path).exists():
            raise FileNotFoundError(f"Database {db_name} not found at {db_path}")
        
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Check if table exists"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone()[0] > 0
    
    def index_exists(self, conn: sqlite3.Connection, index_name: str) -> bool:
        """Check if index exists"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='index' AND name=?
        """, (index_name,))
        return cursor.fetchone()[0] > 0
    
    def create_index(self, conn: sqlite3.Connection, index_name: str, table_name: str, columns: List[str]) -> bool:
        """Create an index"""
        try:
            columns_str = ', '.join(columns)
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_str})"
            
            start_time = time.time()
            conn.execute(sql)
            conn.commit()
            duration = time.time() - start_time
            
            logger.info(f"✅ Created index {index_name} on {table_name}({columns_str}) in {duration:.3f}s")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"❌ Failed to create index {index_name}: {e}")
            return False
    
    def analyze_table(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Run ANALYZE on a table to update statistics"""
        try:
            start_time = time.time()
            conn.execute(f"ANALYZE {table_name}")
            conn.commit()
            duration = time.time() - start_time
            
            logger.info(f"📊 Analyzed table {table_name} in {duration:.3f}s")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"❌ Failed to analyze table {table_name}: {e}")
            return False
    
    def get_table_stats(self, conn: sqlite3.Connection, table_name: str) -> Dict:
        """Get table statistics"""
        try:
            cursor = conn.cursor()
            
            # Row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Table info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            return {
                'row_count': row_count,
                'column_count': len(columns),
                'columns': [col[1] for col in columns]
            }
            
        except sqlite3.Error as e:
            logger.warning(f"Could not get stats for {table_name}: {e}")
            return {'row_count': 0, 'column_count': 0, 'columns': []}
    
    def optimize_database(self, db_name: str) -> Dict:
        """Optimize a single database"""
        logger.info(f"🔧 Optimizing database: {db_name}")
        
        results = {
            'database': db_name,
            'indexes_created': 0,
            'indexes_skipped': 0,
            'indexes_failed': 0,
            'tables_analyzed': 0,
            'errors': []
        }
        
        try:
            with self.get_db_connection(db_name) as conn:
                # Get index definitions for this database
                indexes = self.index_definitions.get(db_name, [])
                
                for index_name, table_name, columns in indexes:
                    # Check if table exists
                    if not self.table_exists(conn, table_name):
                        logger.warning(f"⚠️ Table {table_name} not found in {db_name}, skipping index {index_name}")
                        results['indexes_skipped'] += 1
                        continue
                    
                    # Check if index already exists
                    if self.index_exists(conn, index_name):
                        logger.info(f"ℹ️ Index {index_name} already exists, skipping")
                        results['indexes_skipped'] += 1
                        continue
                    
                    # Create the index
                    if self.create_index(conn, index_name, table_name, columns):
                        results['indexes_created'] += 1
                    else:
                        results['indexes_failed'] += 1
                
                # Analyze all tables to update statistics
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    if self.analyze_table(conn, table):
                        results['tables_analyzed'] += 1
                
                # Run VACUUM to optimize database file
                logger.info(f"🧹 Running VACUUM on {db_name}")
                start_time = time.time()
                conn.execute("VACUUM")
                vacuum_duration = time.time() - start_time
                logger.info(f"✅ VACUUM completed in {vacuum_duration:.3f}s")
                
                results['vacuum_duration'] = vacuum_duration
                
        except Exception as e:
            error_msg = f"Failed to optimize {db_name}: {e}"
            logger.error(f"❌ {error_msg}")
            results['errors'].append(error_msg)
        
        return results
    
    def optimize_all_databases(self) -> Dict:
        """Optimize all databases"""
        logger.info("🚀 Starting database optimization for all databases")
        
        start_time = time.time()
        overall_results = {
            'start_time': start_time,
            'databases_processed': 0,
            'databases_successful': 0,
            'total_indexes_created': 0,
            'total_indexes_skipped': 0,
            'total_indexes_failed': 0,
            'total_tables_analyzed': 0,
            'database_results': {},
            'errors': []
        }
        
        for db_name in self.db_paths.keys():
            try:
                if not Path(self.db_paths[db_name]).exists():
                    logger.warning(f"⚠️ Database {db_name} not found, skipping")
                    continue
                
                db_results = self.optimize_database(db_name)
                overall_results['database_results'][db_name] = db_results
                overall_results['databases_processed'] += 1
                
                if not db_results.get('errors'):
                    overall_results['databases_successful'] += 1
                
                overall_results['total_indexes_created'] += db_results['indexes_created']
                overall_results['total_indexes_skipped'] += db_results['indexes_skipped']
                overall_results['total_indexes_failed'] += db_results['indexes_failed']
                overall_results['total_tables_analyzed'] += db_results['tables_analyzed']
                
            except Exception as e:
                error_msg = f"Failed to process database {db_name}: {e}"
                logger.error(f"❌ {error_msg}")
                overall_results['errors'].append(error_msg)
        
        end_time = time.time()
        overall_results['end_time'] = end_time
        overall_results['total_duration'] = end_time - start_time
        
        return overall_results
    
    def print_optimization_report(self, results: Dict):
        """Print optimization report"""
        print("\n" + "="*80)
        print("🔧 DATABASE OPTIMIZATION REPORT")
        print("="*80)
        
        print(f"⏱️  Total Duration: {results['total_duration']:.2f} seconds")
        print(f"🗄️  Databases Processed: {results['databases_processed']}")
        print(f"✅ Databases Successful: {results['databases_successful']}")
        print(f"📊 Total Indexes Created: {results['total_indexes_created']}")
        print(f"⏭️  Total Indexes Skipped: {results['total_indexes_skipped']}")
        print(f"❌ Total Indexes Failed: {results['total_indexes_failed']}")
        print(f"📈 Total Tables Analyzed: {results['total_tables_analyzed']}")
        
        print("\n📋 DATABASE DETAILS:")
        for db_name, db_results in results['database_results'].items():
            status = "✅" if not db_results.get('errors') else "❌"
            print(f"   {status} {db_name}:")
            print(f"      Indexes Created: {db_results['indexes_created']}")
            print(f"      Indexes Skipped: {db_results['indexes_skipped']}")
            print(f"      Tables Analyzed: {db_results['tables_analyzed']}")
            if db_results.get('vacuum_duration'):
                print(f"      VACUUM Duration: {db_results['vacuum_duration']:.3f}s")
            if db_results.get('errors'):
                print(f"      Errors: {len(db_results['errors'])}")
        
        if results['errors']:
            print("\n⚠️ OVERALL ERRORS:")
            for error in results['errors']:
                print(f"   • {error}")
        
        print("\n" + "="*80)
        
        if results['databases_successful'] == results['databases_processed']:
            print("🎉 ALL DATABASES OPTIMIZED SUCCESSFULLY!")
        else:
            print("⚠️ SOME DATABASES HAD ISSUES - CHECK THE DETAILS ABOVE")
        
        print("="*80)

def main():
    """Main entry point"""
    optimizer = DatabaseIndexOptimizer()
    
    try:
        results = optimizer.optimize_all_databases()
        optimizer.print_optimization_report(results)
        
        # Exit with appropriate code
        if results['databases_successful'] == results['databases_processed']:
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Optimization interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"💥 Database optimization failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())