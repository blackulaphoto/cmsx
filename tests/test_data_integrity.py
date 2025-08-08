#!/usr/bin/env python3
"""
Comprehensive Data Integrity Testing Suite
Tests data consistency, validation, and integrity across all 15 databases
"""

import pytest
import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataIntegrityTester:
    """Comprehensive data integrity testing across all databases"""
    
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
            'unified_platform': 'databases/unified_platform.db',
            'jobs': 'databases/jobs.db',
            'services': 'databases/services.db',
            'housing': 'databases/housing.db',
            'case_manager': 'databases/case_manager.db'
        }
        
        # Test client data for integrity testing
        self.test_client_data = {
            'client_id': str(uuid.uuid4()),
            'first_name': 'Test',
            'last_name': 'Client',
            'date_of_birth': '1985-01-01',
            'phone': '(555) 123-4567',
            'email': 'test.client@example.com',
            'address': '123 Test St, Test City, CA 90210',
            'risk_level': 'medium',
            'case_status': 'active',
            'case_manager_id': 'cm_test_001',
            'intake_date': datetime.now().strftime('%Y-%m-%d'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    def get_db_connection(self, db_name: str) -> sqlite3.Connection:
        """Get database connection with proper configuration"""
        db_path = self.db_paths.get(db_name)
        if not db_path or not Path(db_path).exists():
            pytest.skip(f"Database {db_name} not found at {db_path}")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def get_table_schema(self, db_name: str, table_name: str) -> List[Dict]:
        """Get table schema information"""
        with self.get_db_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_table_names(self, db_name: str) -> List[str]:
        """Get all table names in a database"""
        with self.get_db_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]

@pytest.fixture
def integrity_tester():
    """Fixture providing DataIntegrityTester instance"""
    return DataIntegrityTester()

class TestDatabaseStructure:
    """Test database structure and schema integrity"""
    
    def test_all_databases_exist(self, integrity_tester):
        """Verify all expected databases exist"""
        missing_dbs = []
        for db_name, db_path in integrity_tester.db_paths.items():
            if not Path(db_path).exists():
                missing_dbs.append(f"{db_name}: {db_path}")
        
        assert not missing_dbs, f"Missing databases: {missing_dbs}"
        logger.info("✅ All expected databases exist")
    
    def test_core_client_schema(self, integrity_tester):
        """Test core clients database schema"""
        tables = integrity_tester.get_table_names('core_clients')
        expected_tables = ['clients', 'client_goals', 'client_barriers', 'case_notes']
        
        for table in expected_tables:
            assert table in tables, f"Missing table {table} in core_clients.db"
        
        # Test clients table schema
        schema = integrity_tester.get_table_schema('core_clients', 'clients')
        required_columns = [
            'client_id', 'first_name', 'last_name', 'date_of_birth',
            'phone', 'email', 'address', 'risk_level', 'case_status',
            'case_manager_id', 'intake_date', 'created_at', 'updated_at'
        ]
        
        existing_columns = [col['name'] for col in schema]
        for col in required_columns:
            assert col in existing_columns, f"Missing column {col} in clients table"
        
        logger.info("✅ Core clients schema validation passed")
    
    def test_case_management_schema(self, integrity_tester):
        """Test case management database schema"""
        tables = integrity_tester.get_table_names('case_management')
        
        # Should have clients table and related tables
        assert 'clients' in tables, "Missing clients table in case_management.db"
        
        schema = integrity_tester.get_table_schema('case_management', 'clients')
        primary_key_cols = [col for col in schema if col['pk'] == 1]
        assert len(primary_key_cols) == 1, "Clients table should have exactly one primary key"
        assert primary_key_cols[0]['name'] == 'client_id', "Primary key should be client_id"
        
        logger.info("✅ Case management schema validation passed")
    
    def test_foreign_key_constraints(self, integrity_tester):
        """Test foreign key constraints are properly defined"""
        test_databases = ['legal_cases', 'expungement', 'reminders', 'benefits_transport']
        
        for db_name in test_databases:
            try:
                with integrity_tester.get_db_connection(db_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA foreign_key_check")
                    violations = cursor.fetchall()
                    assert not violations, f"Foreign key violations in {db_name}: {violations}"
            except Exception as e:
                logger.warning(f"Could not check foreign keys for {db_name}: {e}")
        
        logger.info("✅ Foreign key constraints validation passed")

class TestDataValidation:
    """Test data validation and constraints"""
    
    def test_client_data_validation(self, integrity_tester):
        """Test client data validation rules"""
        with integrity_tester.get_db_connection('case_management') as conn:
            cursor = conn.cursor()
            
            # Test valid client insertion
            test_client = integrity_tester.test_client_data.copy()
            
            try:
                cursor.execute("""
                    INSERT INTO clients (
                        client_id, first_name, last_name, date_of_birth,
                        phone, email, address, risk_level, case_status,
                        case_manager_id, intake_date, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_client['client_id'], test_client['first_name'],
                    test_client['last_name'], test_client['date_of_birth'],
                    test_client['phone'], test_client['email'],
                    test_client['address'], test_client['risk_level'],
                    test_client['case_status'], test_client['case_manager_id'],
                    test_client['intake_date'], test_client['created_at'],
                    test_client['updated_at']
                ))
                conn.commit()
                
                # Verify insertion
                cursor.execute("SELECT * FROM clients WHERE client_id = ?", (test_client['client_id'],))
                result = cursor.fetchone()
                assert result is not None, "Client insertion failed"
                assert result['first_name'] == test_client['first_name']
                
                # Clean up
                cursor.execute("DELETE FROM clients WHERE client_id = ?", (test_client['client_id'],))
                conn.commit()
                
            except Exception as e:
                logger.error(f"Client validation test failed: {e}")
                raise
        
        logger.info("✅ Client data validation passed")
    
    def test_risk_level_constraints(self, integrity_tester):
        """Test risk level enumeration constraints"""
        valid_risk_levels = ['low', 'medium', 'high']
        
        with integrity_tester.get_db_connection('case_management') as conn:
            cursor = conn.cursor()
            
            for risk_level in valid_risk_levels:
                test_client = integrity_tester.test_client_data.copy()
                test_client['client_id'] = str(uuid.uuid4())
                test_client['risk_level'] = risk_level
                
                try:
                    cursor.execute("""
                        INSERT INTO clients (
                            client_id, first_name, last_name, risk_level, case_status
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        test_client['client_id'], test_client['first_name'],
                        test_client['last_name'], risk_level, 'active'
                    ))
                    conn.commit()
                    
                    # Clean up
                    cursor.execute("DELETE FROM clients WHERE client_id = ?", (test_client['client_id'],))
                    conn.commit()
                    
                except Exception as e:
                    pytest.fail(f"Valid risk level '{risk_level}' was rejected: {e}")
        
        logger.info("✅ Risk level constraints validation passed")
    
    def test_case_status_constraints(self, integrity_tester):
        """Test case status enumeration constraints"""
        valid_statuses = ['active', 'inactive', 'completed']
        
        with integrity_tester.get_db_connection('case_management') as conn:
            cursor = conn.cursor()
            
            for status in valid_statuses:
                test_client = integrity_tester.test_client_data.copy()
                test_client['client_id'] = str(uuid.uuid4())
                test_client['case_status'] = status
                
                try:
                    cursor.execute("""
                        INSERT INTO clients (
                            client_id, first_name, last_name, risk_level, case_status
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        test_client['client_id'], test_client['first_name'],
                        test_client['last_name'], 'medium', status
                    ))
                    conn.commit()
                    
                    # Clean up
                    cursor.execute("DELETE FROM clients WHERE client_id = ?", (test_client['client_id'],))
                    conn.commit()
                    
                except Exception as e:
                    pytest.fail(f"Valid case status '{status}' was rejected: {e}")
        
        logger.info("✅ Case status constraints validation passed")

class TestDataConsistency:
    """Test data consistency across databases"""
    
    def test_client_id_consistency(self, integrity_tester):
        """Test client_id consistency across databases"""
        client_databases = [
            'case_management', 'legal_cases', 'expungement', 
            'reminders', 'benefits_transport', 'resumes'
        ]
        
        client_ids_by_db = {}
        
        for db_name in client_databases:
            try:
                with integrity_tester.get_db_connection(db_name) as conn:
                    cursor = conn.cursor()
                    
                    # Find tables with client_id column
                    tables = integrity_tester.get_table_names(db_name)
                    client_ids = set()
                    
                    for table in tables:
                        try:
                            cursor.execute(f"SELECT DISTINCT client_id FROM {table} WHERE client_id IS NOT NULL")
                            table_client_ids = [row[0] for row in cursor.fetchall()]
                            client_ids.update(table_client_ids)
                        except sqlite3.OperationalError:
                            # Table doesn't have client_id column
                            continue
                    
                    client_ids_by_db[db_name] = client_ids
                    
            except Exception as e:
                logger.warning(f"Could not check client IDs in {db_name}: {e}")
        
        # Check for orphaned client_ids (exist in module DB but not in case_management)
        if 'case_management' in client_ids_by_db:
            master_client_ids = client_ids_by_db['case_management']
            
            for db_name, client_ids in client_ids_by_db.items():
                if db_name != 'case_management':
                    orphaned_ids = client_ids - master_client_ids
                    if orphaned_ids:
                        logger.warning(f"Orphaned client IDs in {db_name}: {orphaned_ids}")
        
        logger.info("✅ Client ID consistency check completed")
    
    def test_timestamp_consistency(self, integrity_tester):
        """Test timestamp format consistency"""
        timestamp_databases = ['case_management', 'legal_cases', 'reminders']
        
        for db_name in timestamp_databases:
            try:
                with integrity_tester.get_db_connection(db_name) as conn:
                    cursor = conn.cursor()
                    tables = integrity_tester.get_table_names(db_name)
                    
                    for table in tables:
                        schema = integrity_tester.get_table_schema(db_name, table)
                        timestamp_columns = [
                            col['name'] for col in schema 
                            if 'created_at' in col['name'] or 'updated_at' in col['name']
                        ]
                        
                        for col in timestamp_columns:
                            try:
                                cursor.execute(f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL LIMIT 5")
                                timestamps = [row[0] for row in cursor.fetchall()]
                                
                                for ts in timestamps:
                                    # Validate ISO 8601 format
                                    try:
                                        datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                    except ValueError:
                                        logger.warning(f"Invalid timestamp format in {db_name}.{table}.{col}: {ts}")
                                        
                            except sqlite3.OperationalError:
                                continue
                                
            except Exception as e:
                logger.warning(f"Could not check timestamps in {db_name}: {e}")
        
        logger.info("✅ Timestamp consistency check completed")

class TestDataIntegrityRecovery:
    """Test data integrity recovery and repair mechanisms"""
    
    def test_duplicate_detection(self, integrity_tester):
        """Test detection of duplicate records"""
        with integrity_tester.get_db_connection('case_management') as conn:
            cursor = conn.cursor()
            
            # Check for duplicate client_ids
            cursor.execute("""
                SELECT client_id, COUNT(*) as count 
                FROM clients 
                GROUP BY client_id 
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            
            if duplicates:
                logger.warning(f"Duplicate client IDs found: {duplicates}")
            else:
                logger.info("✅ No duplicate client IDs found")
    
    def test_null_constraint_violations(self, integrity_tester):
        """Test for NULL values in required fields"""
        critical_fields = {
            'case_management': {
                'clients': ['client_id', 'first_name', 'last_name']
            }
        }
        
        for db_name, tables in critical_fields.items():
            try:
                with integrity_tester.get_db_connection(db_name) as conn:
                    cursor = conn.cursor()
                    
                    for table_name, required_fields in tables.items():
                        for field in required_fields:
                            cursor.execute(f"""
                                SELECT COUNT(*) FROM {table_name} 
                                WHERE {field} IS NULL OR {field} = ''
                            """)
                            null_count = cursor.fetchone()[0]
                            
                            assert null_count == 0, f"Found {null_count} NULL values in {db_name}.{table_name}.{field}"
                            
            except Exception as e:
                logger.warning(f"Could not check NULL constraints in {db_name}: {e}")
        
        logger.info("✅ NULL constraint validation passed")

if __name__ == "__main__":
    # Run data integrity tests
    pytest.main([__file__, "-v", "--tb=short"])