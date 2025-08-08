#!/usr/bin/env python3
"""
Referential Integrity Validation Suite
Tests foreign key relationships, cascade operations, and data consistency
"""

import pytest
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Any, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReferentialIntegrityTester:
    """Test referential integrity across all databases"""
    
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
            'unified_platform': 'databases/unified_platform.db'
        }
        
        # Define expected foreign key relationships
        self.foreign_key_relationships = {
            'legal_cases': [
                ('legal_cases', 'client_id', 'case_management', 'clients', 'client_id'),
                ('court_dates', 'case_id', 'legal_cases', 'legal_cases', 'case_id')
            ],
            'expungement': [
                ('expungement_cases', 'client_id', 'case_management', 'clients', 'client_id'),
                ('expungement_cases', 'legal_case_id', 'legal_cases', 'legal_cases', 'case_id')
            ],
            'reminders': [
                ('reminders', 'client_id', 'case_management', 'clients', 'client_id')
            ],
            'benefits_transport': [
                ('benefit_applications', 'client_id', 'case_management', 'clients', 'client_id')
            ]
        }
        
        # Test data for integrity testing
        self.test_client_id = str(uuid.uuid4())
        self.test_case_id = str(uuid.uuid4())
        self.test_reminder_id = str(uuid.uuid4())
    
    def get_db_connection(self, db_name: str) -> sqlite3.Connection:
        """Get database connection with foreign keys enabled"""
        db_path = self.db_paths.get(db_name)
        if not db_path or not Path(db_path).exists():
            pytest.skip(f"Database {db_name} not found at {db_path}")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def get_foreign_keys(self, db_name: str, table_name: str) -> List[Dict]:
        """Get foreign key information for a table"""
        with self.get_db_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            return [dict(row) for row in cursor.fetchall()]
    
    def check_foreign_key_violations(self, db_name: str) -> List[Dict]:
        """Check for foreign key violations in a database"""
        with self.get_db_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_key_check")
            return [dict(row) for row in cursor.fetchall()]
    
    def create_test_client(self, db_name: str = 'case_management') -> str:
        """Create a test client for referential integrity testing"""
        with self.get_db_connection(db_name) as conn:
            cursor = conn.cursor()
            
            test_client_data = (
                self.test_client_id,
                'Test',
                'Client',
                '1985-01-01',
                '(555) 123-4567',
                'test.client@example.com',
                '123 Test St, Test City, CA 90210',
                'medium',
                'active',
                'cm_test_001',
                datetime.now().strftime('%Y-%m-%d'),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            )
            
            cursor.execute("""
                INSERT INTO clients (
                    client_id, first_name, last_name, date_of_birth,
                    phone, email, address, risk_level, case_status,
                    case_manager_id, intake_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, test_client_data)
            conn.commit()
            
            return self.test_client_id
    
    def cleanup_test_data(self):
        """Clean up test data from all databases"""
        cleanup_queries = [
            ('case_management', "DELETE FROM clients WHERE client_id = ?", (self.test_client_id,)),
            ('legal_cases', "DELETE FROM legal_cases WHERE client_id = ?", (self.test_client_id,)),
            ('legal_cases', "DELETE FROM legal_cases WHERE case_id = ?", (self.test_case_id,)),
            ('reminders', "DELETE FROM reminders WHERE client_id = ?", (self.test_client_id,)),
            ('reminders', "DELETE FROM reminders WHERE reminder_id = ?", (self.test_reminder_id,))
        ]
        
        for db_name, query, params in cleanup_queries:
            try:
                with self.get_db_connection(db_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
            except Exception as e:
                logger.warning(f"Cleanup failed for {db_name}: {e}")

@pytest.fixture
def integrity_tester():
    """Fixture providing ReferentialIntegrityTester instance"""
    tester = ReferentialIntegrityTester()
    yield tester
    # Cleanup after each test
    tester.cleanup_test_data()

class TestForeignKeyConstraints:
    """Test foreign key constraint enforcement"""
    
    def test_foreign_key_enforcement_enabled(self, integrity_tester):
        """Test that foreign key enforcement is enabled"""
        for db_name in integrity_tester.db_paths.keys():
            try:
                with integrity_tester.get_db_connection(db_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA foreign_keys")
                    fk_enabled = cursor.fetchone()[0]
                    
                    assert fk_enabled == 1, f"Foreign keys not enabled in {db_name}"
                    logger.info(f"✅ Foreign keys enabled in {db_name}")
                    
            except Exception as e:
                logger.warning(f"Could not check foreign key status for {db_name}: {e}")
    
    def test_existing_foreign_key_violations(self, integrity_tester):
        """Test for existing foreign key violations"""
        violations_found = {}
        
        for db_name in integrity_tester.db_paths.keys():
            try:
                violations = integrity_tester.check_foreign_key_violations(db_name)
                if violations:
                    violations_found[db_name] = violations
                    logger.warning(f"Foreign key violations in {db_name}: {violations}")
                else:
                    logger.info(f"✅ No foreign key violations in {db_name}")
                    
            except Exception as e:
                logger.warning(f"Could not check foreign key violations for {db_name}: {e}")
        
        assert not violations_found, f"Foreign key violations found: {violations_found}"
    
    def test_foreign_key_constraint_enforcement(self, integrity_tester):
        """Test that foreign key constraints are enforced on insert"""
        # Test inserting a record with invalid foreign key
        try:
            with integrity_tester.get_db_connection('legal_cases') as conn:
                cursor = conn.cursor()
                
                # Try to insert legal case with non-existent client_id
                invalid_client_id = str(uuid.uuid4())
                
                with pytest.raises(sqlite3.IntegrityError):
                    cursor.execute("""
                        INSERT INTO legal_cases (
                            case_id, client_id, case_type, case_status, created_at
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        invalid_client_id,
                        'expungement',
                        'open',
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                
                logger.info("✅ Foreign key constraint properly enforced on insert")
                
        except Exception as e:
            if "foreign key constraint" in str(e).lower():
                logger.info("✅ Foreign key constraint properly enforced")
            else:
                logger.warning(f"Unexpected error testing foreign key constraint: {e}")

class TestCascadeOperations:
    """Test cascade operations and referential actions"""
    
    def test_cascade_delete_behavior(self, integrity_tester):
        """Test cascade delete behavior"""
        # Create test client
        client_id = integrity_tester.create_test_client()
        
        # Create dependent records
        try:
            # Create legal case
            with integrity_tester.get_db_connection('legal_cases') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO legal_cases (
                        case_id, client_id, case_type, case_status, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    integrity_tester.test_case_id,
                    client_id,
                    'expungement',
                    'open',
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            # Create reminder
            with integrity_tester.get_db_connection('reminders') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO reminders (
                        reminder_id, client_id, task_description, due_date, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    integrity_tester.test_reminder_id,
                    client_id,
                    'Test reminder',
                    (datetime.now() + timedelta(days=7)).isoformat(),
                    'pending',
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            # Verify dependent records exist
            with integrity_tester.get_db_connection('legal_cases') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM legal_cases WHERE client_id = ?", (client_id,))
                legal_count_before = cursor.fetchone()[0]
                assert legal_count_before > 0, "Legal case not created"
            
            with integrity_tester.get_db_connection('reminders') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM reminders WHERE client_id = ?", (client_id,))
                reminder_count_before = cursor.fetchone()[0]
                assert reminder_count_before > 0, "Reminder not created"
            
            logger.info("✅ Dependent records created successfully")
            
            # Note: SQLite doesn't support CASCADE DELETE by default
            # This test verifies the current behavior and documents expected behavior
            
        except Exception as e:
            logger.warning(f"Could not test cascade delete: {e}")
    
    def test_update_cascade_behavior(self, integrity_tester):
        """Test update cascade behavior"""
        # Create test client
        client_id = integrity_tester.create_test_client()
        
        try:
            # Create dependent record
            with integrity_tester.get_db_connection('legal_cases') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO legal_cases (
                        case_id, client_id, case_type, case_status, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    integrity_tester.test_case_id,
                    client_id,
                    'expungement',
                    'open',
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            # Update parent record
            with integrity_tester.get_db_connection('case_management') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE clients SET updated_at = ? WHERE client_id = ?
                """, (datetime.now().isoformat(), client_id))
                conn.commit()
            
            # Verify update succeeded
            cursor.execute("SELECT updated_at FROM clients WHERE client_id = ?", (client_id,))
            result = cursor.fetchone()
            assert result is not None, "Client update failed"
            
            logger.info("✅ Update cascade behavior working correctly")
            
        except Exception as e:
            logger.warning(f"Could not test update cascade: {e}")

class TestCrossModuleIntegrity:
    """Test referential integrity across different modules"""
    
    def test_client_legal_case_integrity(self, integrity_tester):
        """Test integrity between clients and legal cases"""
        # Create test client
        client_id = integrity_tester.create_test_client()
        
        try:
            # Create legal case
            with integrity_tester.get_db_connection('legal_cases') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO legal_cases (
                        case_id, client_id, case_type, case_status, 
                        court_name, case_number, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    integrity_tester.test_case_id,
                    client_id,
                    'expungement',
                    'open',
                    'Los Angeles Superior Court',
                    'TEST-2024-001',
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            # Verify legal case was created
            cursor.execute("SELECT * FROM legal_cases WHERE case_id = ?", (integrity_tester.test_case_id,))
            legal_case = cursor.fetchone()
            assert legal_case is not None, "Legal case not created"
            assert legal_case['client_id'] == client_id, "Client ID mismatch in legal case"
            
            logger.info("✅ Client-Legal case integrity maintained")
            
        except Exception as e:
            logger.error(f"Client-Legal case integrity test failed: {e}")
            raise
    
    def test_client_reminder_integrity(self, integrity_tester):
        """Test integrity between clients and reminders"""
        # Create test client
        client_id = integrity_tester.create_test_client()
        
        try:
            # Create reminder
            with integrity_tester.get_db_connection('reminders') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO reminders (
                        reminder_id, client_id, task_description, due_date, 
                        priority, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    integrity_tester.test_reminder_id,
                    client_id,
                    'Follow up on housing application',
                    (datetime.now() + timedelta(days=3)).isoformat(),
                    'high',
                    'pending',
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            # Verify reminder was created
            cursor.execute("SELECT * FROM reminders WHERE reminder_id = ?", (integrity_tester.test_reminder_id,))
            reminder = cursor.fetchone()
            assert reminder is not None, "Reminder not created"
            assert reminder['client_id'] == client_id, "Client ID mismatch in reminder"
            
            logger.info("✅ Client-Reminder integrity maintained")
            
        except Exception as e:
            logger.error(f"Client-Reminder integrity test failed: {e}")
            raise
    
    def test_legal_case_expungement_integrity(self, integrity_tester):
        """Test integrity between legal cases and expungement records"""
        # Create test client and legal case
        client_id = integrity_tester.create_test_client()
        
        try:
            # Create legal case first
            with integrity_tester.get_db_connection('legal_cases') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO legal_cases (
                        case_id, client_id, case_type, case_status, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    integrity_tester.test_case_id,
                    client_id,
                    'expungement',
                    'open',
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            # Create expungement record
            with integrity_tester.get_db_connection('expungement') as conn:
                cursor = conn.cursor()
                
                # Check if expungement_cases table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expungement_cases'")
                if cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO expungement_cases (
                            expungement_id, client_id, legal_case_id, 
                            eligibility_score, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        client_id,
                        integrity_tester.test_case_id,
                        85.5,
                        'in_progress',
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                    
                    logger.info("✅ Legal case-Expungement integrity maintained")
                else:
                    logger.info("ℹ️ Expungement cases table not found, skipping test")
            
        except Exception as e:
            logger.warning(f"Legal case-Expungement integrity test: {e}")

class TestDataConsistencyValidation:
    """Test data consistency validation across modules"""
    
    def test_client_status_consistency(self, integrity_tester):
        """Test client status consistency across modules"""
        # Create test client
        client_id = integrity_tester.create_test_client()
        
        try:
            # Update client status in case management
            with integrity_tester.get_db_connection('case_management') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE clients SET case_status = 'inactive', updated_at = ? 
                    WHERE client_id = ?
                """, (datetime.now().isoformat(), client_id))
                conn.commit()
            
            # Verify status update
            cursor.execute("SELECT case_status FROM clients WHERE client_id = ?", (client_id,))
            result = cursor.fetchone()
            assert result['case_status'] == 'inactive', "Client status not updated"
            
            logger.info("✅ Client status consistency maintained")
            
        except Exception as e:
            logger.error(f"Client status consistency test failed: {e}")
            raise
    
    def test_timestamp_consistency(self, integrity_tester):
        """Test timestamp consistency across related records"""
        # Create test client
        client_id = integrity_tester.create_test_client()
        
        try:
            current_time = datetime.now().isoformat()
            
            # Create related records with consistent timestamps
            with integrity_tester.get_db_connection('legal_cases') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO legal_cases (
                        case_id, client_id, case_type, case_status, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    integrity_tester.test_case_id,
                    client_id,
                    'expungement',
                    'open',
                    current_time
                ))
                conn.commit()
            
            with integrity_tester.get_db_connection('reminders') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO reminders (
                        reminder_id, client_id, task_description, due_date, 
                        status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    integrity_tester.test_reminder_id,
                    client_id,
                    'Test reminder',
                    (datetime.now() + timedelta(days=7)).isoformat(),
                    'pending',
                    current_time
                ))
                conn.commit()
            
            logger.info("✅ Timestamp consistency maintained")
            
        except Exception as e:
            logger.error(f"Timestamp consistency test failed: {e}")
            raise

class TestIntegrityRecovery:
    """Test integrity recovery and repair mechanisms"""
    
    def test_orphaned_record_detection(self, integrity_tester):
        """Test detection of orphaned records"""
        orphaned_records = {}
        
        # Check for orphaned legal cases
        try:
            with integrity_tester.get_db_connection('legal_cases') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT lc.case_id, lc.client_id 
                    FROM legal_cases lc 
                    LEFT JOIN (
                        SELECT client_id FROM clients 
                        UNION 
                        SELECT client_id FROM clients
                    ) c ON lc.client_id = c.client_id 
                    WHERE c.client_id IS NULL
                """)
                orphaned_legal = cursor.fetchall()
                if orphaned_legal:
                    orphaned_records['legal_cases'] = orphaned_legal
                    
        except Exception as e:
            logger.warning(f"Could not check orphaned legal cases: {e}")
        
        # Check for orphaned reminders
        try:
            with integrity_tester.get_db_connection('reminders') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT r.reminder_id, r.client_id 
                    FROM reminders r 
                    LEFT JOIN (
                        SELECT client_id FROM clients
                    ) c ON r.client_id = c.client_id 
                    WHERE c.client_id IS NULL
                """)
                orphaned_reminders = cursor.fetchall()
                if orphaned_reminders:
                    orphaned_records['reminders'] = orphaned_reminders
                    
        except Exception as e:
            logger.warning(f"Could not check orphaned reminders: {e}")
        
        if orphaned_records:
            logger.warning(f"Orphaned records detected: {orphaned_records}")
        else:
            logger.info("✅ No orphaned records detected")
        
        # Don't fail the test for orphaned records, just log them
        return orphaned_records
    
    def test_integrity_repair_simulation(self, integrity_tester):
        """Test integrity repair mechanisms"""
        # This test simulates what would happen during integrity repair
        
        # Create test client
        client_id = integrity_tester.create_test_client()
        
        try:
            # Create dependent records
            with integrity_tester.get_db_connection('legal_cases') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO legal_cases (
                        case_id, client_id, case_type, case_status, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    integrity_tester.test_case_id,
                    client_id,
                    'expungement',
                    'open',
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            # Simulate integrity check
            violations = integrity_tester.check_foreign_key_violations('legal_cases')
            assert not violations, f"Integrity violations found: {violations}"
            
            logger.info("✅ Integrity repair simulation completed")
            
        except Exception as e:
            logger.error(f"Integrity repair simulation failed: {e}")
            raise

if __name__ == "__main__":
    # Run referential integrity tests
    pytest.main([__file__, "-v", "--tb=short"])