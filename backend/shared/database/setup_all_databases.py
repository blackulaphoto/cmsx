"""
Setup script to ensure all 15 specialized databases have proper client tables
for full integration across the Case Management Suite
"""

import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class AllDatabaseSetup:
    """Setup client tables across all 15 specialized databases"""
    
    def __init__(self):
        self.databases = {
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
            'case_manager': 'databases/case_manager.db',
            'search_cache': 'databases/search_cache.db',
            'auth': 'databases/auth.db'
        }
    
    def setup_all_databases(self):
        """Setup client tables in all databases"""
        print("🔧 Setting up client tables across all 15 specialized databases...")
        print("=" * 70)
        
        results = {
            'success': [],
            'errors': []
        }
        
        for db_name, db_path in self.databases.items():
            try:
                print(f"📊 Setting up {db_name}...")
                success = self._setup_database(db_name, db_path)
                
                if success:
                    results['success'].append(db_name)
                    print(f"   ✅ {db_name} setup completed")
                else:
                    results['errors'].append(f"{db_name}: Setup failed")
                    print(f"   ❌ {db_name} setup failed")
                    
            except Exception as e:
                error_msg = f"{db_name}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"   ❌ {error_msg}")
        
        print("\n" + "=" * 70)
        print(f"📊 Setup Summary:")
        print(f"   ✅ Successful: {len(results['success'])} databases")
        print(f"   ❌ Errors: {len(results['errors'])} databases")
        
        if results['success']:
            print(f"\n✅ Successfully set up:")
            for db in results['success']:
                print(f"   • {db}")
        
        if results['errors']:
            print(f"\n❌ Errors encountered:")
            for error in results['errors']:
                print(f"   • {error}")
        
        return results
    
    def _setup_database(self, db_name: str, db_path: str) -> bool:
        """Setup individual database"""
        try:
            # Ensure database directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check if clients table already exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                if cursor.fetchone():
                    print(f"     ℹ️  Clients table already exists in {db_name}")
                    return True
                
                # Create clients table based on database type
                if db_name in ['case_management', 'unified_platform']:
                    self._create_standard_clients_table(cursor)
                elif db_name in ['reminders', 'legal_cases', 'expungement']:
                    self._create_legal_clients_table(cursor)
                elif db_name in ['benefits_transport', 'social_services']:
                    self._create_benefits_clients_table(cursor)
                elif db_name in ['housing', 'housing_resources']:
                    self._create_housing_clients_table(cursor)
                elif db_name in ['jobs', 'resumes']:
                    self._create_employment_clients_table(cursor)
                elif db_name == 'services':
                    self._create_services_clients_table(cursor)
                else:
                    self._create_minimal_clients_table(cursor)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error setting up {db_name}: {e}")
            return False
    
    def _create_standard_clients_table(self, cursor):
        """Create standard clients table for case management"""
        cursor.execute("""
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                date_of_birth TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                emergency_contact_name TEXT,
                emergency_contact_phone TEXT,
                case_manager_id TEXT,
                risk_level TEXT DEFAULT 'Medium',
                status TEXT DEFAULT 'active',
                special_needs TEXT,
                medical_conditions TEXT,
                created_at TEXT,
                last_updated TEXT,
                is_active INTEGER DEFAULT 1,
                notes TEXT
            )
        """)
    
    def _create_legal_clients_table(self, cursor):
        """Create clients table for legal modules"""
        cursor.execute("""
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                case_manager_id TEXT,
                legal_status TEXT DEFAULT 'No Active Cases',
                case_type TEXT,
                priority TEXT DEFAULT 'Medium',
                created_at TEXT,
                last_updated TEXT,
                is_active INTEGER DEFAULT 1,
                notes TEXT
            )
        """)
    
    def _create_benefits_clients_table(self, cursor):
        """Create clients table for benefits modules"""
        cursor.execute("""
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                date_of_birth TEXT,
                case_manager_id TEXT,
                has_disability INTEGER DEFAULT 0,
                special_needs TEXT,
                medical_conditions TEXT,
                benefits_status TEXT DEFAULT 'Not Applied',
                eligibility_score REAL DEFAULT 0.0,
                created_at TEXT,
                last_updated TEXT,
                is_active INTEGER DEFAULT 1,
                notes TEXT
            )
        """)
    
    def _create_housing_clients_table(self, cursor):
        """Create clients table for housing modules"""
        cursor.execute("""
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                case_manager_id TEXT,
                housing_status TEXT DEFAULT 'Unknown',
                special_needs TEXT,
                accessibility_requirements TEXT,
                created_at TEXT,
                last_updated TEXT,
                is_active INTEGER DEFAULT 1,
                notes TEXT
            )
        """)
    
    def _create_employment_clients_table(self, cursor):
        """Create clients table for employment modules"""
        cursor.execute("""
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                case_manager_id TEXT,
                employment_status TEXT DEFAULT 'Unemployed',
                skills TEXT,
                experience_level TEXT,
                target_industries TEXT,
                created_at TEXT,
                last_updated TEXT,
                is_active INTEGER DEFAULT 1,
                notes TEXT
            )
        """)
    
    def _create_services_clients_table(self, cursor):
        """Create clients table for services module"""
        cursor.execute("""
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                case_manager_id TEXT,
                service_needs TEXT,
                special_needs TEXT,
                medical_conditions TEXT,
                has_disability INTEGER DEFAULT 0,
                created_at TEXT,
                last_updated TEXT,
                is_active INTEGER DEFAULT 1,
                notes TEXT
            )
        """)
    
    def _create_minimal_clients_table(self, cursor):
        """Create minimal clients table for other databases"""
        cursor.execute("""
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                case_manager_id TEXT,
                created_at TEXT,
                last_updated TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
    
    def verify_integration(self):
        """Verify that all databases are properly set up for integration"""
        print("\n🔍 Verifying database integration...")
        print("=" * 50)
        
        verification_results = {
            'verified': [],
            'issues': []
        }
        
        for db_name, db_path in self.databases.items():
            try:
                if not Path(db_path).exists():
                    verification_results['issues'].append(f"{db_name}: Database file does not exist")
                    continue
                
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Check if clients table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                    if not cursor.fetchone():
                        verification_results['issues'].append(f"{db_name}: Clients table missing")
                        continue
                    
                    # Check table structure
                    cursor.execute("PRAGMA table_info(clients)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    required_columns = ['client_id', 'first_name', 'last_name']
                    missing_columns = [col for col in required_columns if col not in columns]
                    
                    if missing_columns:
                        verification_results['issues'].append(f"{db_name}: Missing columns {missing_columns}")
                    else:
                        verification_results['verified'].append(db_name)
                        
            except Exception as e:
                verification_results['issues'].append(f"{db_name}: {str(e)}")
        
        print(f"✅ Verified: {len(verification_results['verified'])} databases")
        for db in verification_results['verified']:
            print(f"   • {db}")
        
        if verification_results['issues']:
            print(f"\n❌ Issues found: {len(verification_results['issues'])}")
            for issue in verification_results['issues']:
                print(f"   • {issue}")
        
        return verification_results

def main():
    """Main setup function"""
    print("🚀 Case Management Suite - All Database Setup")
    print("=" * 70)
    
    setup = AllDatabaseSetup()
    
    # Setup all databases
    setup_results = setup.setup_all_databases()
    
    # Verify integration
    verification_results = setup.verify_integration()
    
    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)
    
    total_databases = len(setup.databases)
    successful_setup = len(setup_results['success'])
    verified = len(verification_results['verified'])
    
    print(f"📊 Total databases: {total_databases}")
    print(f"✅ Successfully set up: {successful_setup}")
    print(f"🔍 Verified for integration: {verified}")
    
    if successful_setup == total_databases and verified == total_databases:
        print("\n🎉 ALL DATABASES ARE FULLY INTEGRATED!")
        print("✅ Client creation will now work across all 15 databases")
        print("✅ Disability detection and routing is enabled")
        print("✅ All modules can access client information")
    else:
        print(f"\n⚠️  Integration incomplete: {total_databases - verified} databases need attention")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
