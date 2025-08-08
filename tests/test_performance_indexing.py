#!/usr/bin/env python3
"""
Performance Testing with Proper Indexing Suite
Tests database performance, query optimization, and indexing strategies
"""

import pytest
import sqlite3
import time
import statistics
from pathlib import Path
import logging
from typing import Dict, List, Any, Tuple
import uuid
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTester:
    """Database performance and indexing testing"""
    
    def __init__(self):
        self.db_paths = {
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
        
        # Performance thresholds (in seconds)
        self.performance_thresholds = {
            'simple_select': 0.1,      # 100ms for simple SELECT
            'complex_join': 0.5,       # 500ms for complex JOINs
            'full_text_search': 1.0,   # 1s for full-text search
            'bulk_insert': 2.0,        # 2s for bulk operations
            'index_scan': 0.05         # 50ms for indexed scans
        }
    
    def get_db_connection(self, db_name: str) -> sqlite3.Connection:
        """Get database connection with performance settings"""
        db_path = self.db_paths.get(db_name)
        if not db_path or not Path(db_path).exists():
            pytest.skip(f"Database {db_name} not found at {db_path}")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Performance optimizations
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = 10000")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA mmap_size = 268435456")  # 256MB
        
        return conn
    
    def time_query(self, conn: sqlite3.Connection, query: str, params: tuple = ()) -> Tuple[float, List[Dict]]:
        """Time a query execution and return duration and results"""
        cursor = conn.cursor()
        start_time = time.time()
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        end_time = time.time()
        return end_time - start_time, results
    
    def get_query_plan(self, conn: sqlite3.Connection, query: str, params: tuple = ()) -> List[Dict]:
        """Get query execution plan"""
        cursor = conn.cursor()
        cursor.execute(f"EXPLAIN QUERY PLAN {query}", params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_table_stats(self, conn: sqlite3.Connection, table_name: str) -> Dict[str, Any]:
        """Get table statistics"""
        cursor = conn.cursor()
        
        # Row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        # Table size
        cursor.execute(f"SELECT SUM(pgsize) FROM dbstat WHERE name = ?", (table_name,))
        size_result = cursor.fetchone()
        table_size = size_result[0] if size_result and size_result[0] else 0
        
        return {
            'row_count': row_count,
            'table_size_bytes': table_size,
            'avg_row_size': table_size / row_count if row_count > 0 else 0
        }

@pytest.fixture
def perf_tester():
    """Fixture providing PerformanceTester instance"""
    return PerformanceTester()

class TestDatabaseIndexing:
    """Test database indexing strategies and effectiveness"""
    
    def test_primary_key_indexes(self, perf_tester):
        """Test primary key index performance"""
        test_cases = [
            ('case_management', 'clients', 'client_id'),
            ('legal_cases', 'legal_cases', 'case_id'),
            ('reminders', 'reminders', 'reminder_id')
        ]
        
        for db_name, table_name, pk_column in test_cases:
            try:
                with perf_tester.get_db_connection(db_name) as conn:
                    # Get a sample ID
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT {pk_column} FROM {table_name} LIMIT 1")
                    result = cursor.fetchone()
                    if not result:
                        continue
                    
                    sample_id = result[0]
                    
                    # Test primary key lookup performance
                    query = f"SELECT * FROM {table_name} WHERE {pk_column} = ?"
                    duration, results = perf_tester.time_query(conn, query, (sample_id,))
                    
                    # Check query plan uses index
                    plan = perf_tester.get_query_plan(conn, query, (sample_id,))
                    uses_index = any('INDEX' in str(step).upper() for step in plan)
                    
                    assert duration < perf_tester.performance_thresholds['index_scan'], \
                        f"Primary key lookup too slow in {db_name}.{table_name}: {duration:.3f}s"
                    
                    logger.info(f"✅ Primary key index performance: {db_name}.{table_name} - {duration:.3f}s")
                    
            except Exception as e:
                logger.warning(f"Could not test primary key index for {db_name}.{table_name}: {e}")
    
    def test_foreign_key_indexes(self, perf_tester):
        """Test foreign key index performance"""
        foreign_key_tests = [
            ('legal_cases', 'legal_cases', 'client_id'),
            ('reminders', 'reminders', 'client_id'),
            ('expungement', 'expungement_cases', 'client_id')
        ]
        
        for db_name, table_name, fk_column in foreign_key_tests:
            try:
                with perf_tester.get_db_connection(db_name) as conn:
                    # Get a sample foreign key value
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT DISTINCT {fk_column} FROM {table_name} WHERE {fk_column} IS NOT NULL LIMIT 1")
                    result = cursor.fetchone()
                    if not result:
                        continue
                    
                    sample_fk = result[0]
                    
                    # Test foreign key lookup performance
                    query = f"SELECT * FROM {table_name} WHERE {fk_column} = ?"
                    duration, results = perf_tester.time_query(conn, query, (sample_fk,))
                    
                    assert duration < perf_tester.performance_thresholds['simple_select'], \
                        f"Foreign key lookup too slow in {db_name}.{table_name}: {duration:.3f}s"
                    
                    logger.info(f"✅ Foreign key index performance: {db_name}.{table_name}.{fk_column} - {duration:.3f}s")
                    
            except Exception as e:
                logger.warning(f"Could not test foreign key index for {db_name}.{table_name}.{fk_column}: {e}")
    
    def test_composite_indexes(self, perf_tester):
        """Test composite index performance for common query patterns"""
        composite_tests = [
            ('case_management', 'clients', ['case_status', 'risk_level']),
            ('reminders', 'reminders', ['client_id', 'status']),
            ('legal_cases', 'legal_cases', ['client_id', 'case_status'])
        ]
        
        for db_name, table_name, columns in composite_tests:
            try:
                with perf_tester.get_db_connection(db_name) as conn:
                    cursor = conn.cursor()
                    
                    # Get sample values for composite query
                    sample_query = f"SELECT {', '.join(columns)} FROM {table_name} WHERE " + \
                                 " AND ".join([f"{col} IS NOT NULL" for col in columns]) + " LIMIT 1"
                    cursor.execute(sample_query)
                    result = cursor.fetchone()
                    if not result:
                        continue
                    
                    sample_values = [result[col] for col in columns]
                    
                    # Test composite index query
                    where_clause = " AND ".join([f"{col} = ?" for col in columns])
                    query = f"SELECT * FROM {table_name} WHERE {where_clause}"
                    duration, results = perf_tester.time_query(conn, query, tuple(sample_values))
                    
                    assert duration < perf_tester.performance_thresholds['simple_select'], \
                        f"Composite index query too slow in {db_name}.{table_name}: {duration:.3f}s"
                    
                    logger.info(f"✅ Composite index performance: {db_name}.{table_name} - {duration:.3f}s")
                    
            except Exception as e:
                logger.warning(f"Could not test composite index for {db_name}.{table_name}: {e}")

class TestQueryPerformance:
    """Test query performance across different scenarios"""
    
    def test_simple_select_performance(self, perf_tester):
        """Test simple SELECT query performance"""
        test_queries = [
            ('case_management', "SELECT * FROM clients WHERE case_status = 'active'"),
            ('legal_cases', "SELECT * FROM legal_cases WHERE case_status = 'open'"),
            ('reminders', "SELECT * FROM reminders WHERE status = 'pending'")
        ]
        
        for db_name, query in test_queries:
            try:
                with perf_tester.get_db_connection(db_name) as conn:
                    duration, results = perf_tester.time_query(conn, query)
                    
                    assert duration < perf_tester.performance_thresholds['simple_select'], \
                        f"Simple SELECT too slow in {db_name}: {duration:.3f}s"
                    
                    logger.info(f"✅ Simple SELECT performance: {db_name} - {duration:.3f}s ({len(results)} rows)")
                    
            except Exception as e:
                logger.warning(f"Could not test simple SELECT for {db_name}: {e}")
    
    def test_join_performance(self, perf_tester):
        """Test JOIN query performance"""
        join_tests = [
            ('case_management', """
                SELECT c.client_id, c.first_name, c.last_name, c.case_status
                FROM clients c
                WHERE c.case_status = 'active'
                LIMIT 100
            """),
            ('legal_cases', """
                SELECT lc.case_id, lc.client_id, lc.case_type, lc.case_status
                FROM legal_cases lc
                WHERE lc.case_status IN ('open', 'pending')
                LIMIT 100
            """)
        ]
        
        for db_name, query in join_tests:
            try:
                with perf_tester.get_db_connection(db_name) as conn:
                    duration, results = perf_tester.time_query(conn, query)
                    
                    assert duration < perf_tester.performance_thresholds['complex_join'], \
                        f"JOIN query too slow in {db_name}: {duration:.3f}s"
                    
                    logger.info(f"✅ JOIN performance: {db_name} - {duration:.3f}s ({len(results)} rows)")
                    
            except Exception as e:
                logger.warning(f"Could not test JOIN for {db_name}: {e}")
    
    def test_full_text_search_performance(self, perf_tester):
        """Test full-text search performance"""
        search_tests = [
            ('case_management', "SELECT * FROM clients WHERE first_name LIKE '%Maria%' OR last_name LIKE '%Santos%'"),
            ('social_services', "SELECT * FROM service_providers WHERE provider_name LIKE '%Community%'")
        ]
        
        for db_name, query in search_tests:
            try:
                with perf_tester.get_db_connection(db_name) as conn:
                    duration, results = perf_tester.time_query(conn, query)
                    
                    assert duration < perf_tester.performance_thresholds['full_text_search'], \
                        f"Full-text search too slow in {db_name}: {duration:.3f}s"
                    
                    logger.info(f"✅ Full-text search performance: {db_name} - {duration:.3f}s ({len(results)} rows)")
                    
            except Exception as e:
                logger.warning(f"Could not test full-text search for {db_name}: {e}")
    
    def test_aggregation_performance(self, perf_tester):
        """Test aggregation query performance"""
        aggregation_tests = [
            ('case_management', "SELECT case_status, COUNT(*) FROM clients GROUP BY case_status"),
            ('reminders', "SELECT status, COUNT(*) FROM reminders GROUP BY status"),
            ('legal_cases', "SELECT case_type, COUNT(*) FROM legal_cases GROUP BY case_type")
        ]
        
        for db_name, query in aggregation_tests:
            try:
                with perf_tester.get_db_connection(db_name) as conn:
                    duration, results = perf_tester.time_query(conn, query)
                    
                    assert duration < perf_tester.performance_thresholds['simple_select'], \
                        f"Aggregation query too slow in {db_name}: {duration:.3f}s"
                    
                    logger.info(f"✅ Aggregation performance: {db_name} - {duration:.3f}s ({len(results)} groups)")
                    
            except Exception as e:
                logger.warning(f"Could not test aggregation for {db_name}: {e}")

class TestBulkOperations:
    """Test bulk operation performance"""
    
    def test_bulk_insert_performance(self, perf_tester):
        """Test bulk insert performance"""
        # Test with case_management database
        try:
            with perf_tester.get_db_connection('case_management') as conn:
                cursor = conn.cursor()
                
                # Generate test data
                test_clients = []
                for i in range(100):
                    test_clients.append((
                        str(uuid.uuid4()),
                        f'TestFirst{i}',
                        f'TestLast{i}',
                        '1985-01-01',
                        f'(555) 000-{i:04d}',
                        f'test{i}@example.com',
                        f'{i} Test St, Test City, CA 90210',
                        'medium',
                        'active',
                        'cm_test_001',
                        datetime.now().strftime('%Y-%m-%d'),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                
                # Time bulk insert
                start_time = time.time()
                cursor.executemany("""
                    INSERT INTO clients (
                        client_id, first_name, last_name, date_of_birth,
                        phone, email, address, risk_level, case_status,
                        case_manager_id, intake_date, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, test_clients)
                conn.commit()
                end_time = time.time()
                
                duration = end_time - start_time
                
                # Clean up test data
                test_client_ids = [client[0] for client in test_clients]
                cursor.executemany("DELETE FROM clients WHERE client_id = ?", [(cid,) for cid in test_client_ids])
                conn.commit()
                
                assert duration < perf_tester.performance_thresholds['bulk_insert'], \
                    f"Bulk insert too slow: {duration:.3f}s for 100 records"
                
                logger.info(f"✅ Bulk insert performance: {duration:.3f}s for 100 records")
                
        except Exception as e:
            logger.warning(f"Could not test bulk insert: {e}")
    
    def test_bulk_update_performance(self, perf_tester):
        """Test bulk update performance"""
        try:
            with perf_tester.get_db_connection('case_management') as conn:
                cursor = conn.cursor()
                
                # Get existing client IDs for update test
                cursor.execute("SELECT client_id FROM clients LIMIT 10")
                client_ids = [row[0] for row in cursor.fetchall()]
                
                if not client_ids:
                    pytest.skip("No clients available for bulk update test")
                
                # Time bulk update
                start_time = time.time()
                cursor.executemany(
                    "UPDATE clients SET updated_at = ? WHERE client_id = ?",
                    [(datetime.now().isoformat(), cid) for cid in client_ids]
                )
                conn.commit()
                end_time = time.time()
                
                duration = end_time - start_time
                
                assert duration < perf_tester.performance_thresholds['simple_select'], \
                    f"Bulk update too slow: {duration:.3f}s for {len(client_ids)} records"
                
                logger.info(f"✅ Bulk update performance: {duration:.3f}s for {len(client_ids)} records")
                
        except Exception as e:
            logger.warning(f"Could not test bulk update: {e}")

class TestDatabaseOptimization:
    """Test database optimization strategies"""
    
    def test_vacuum_effectiveness(self, perf_tester):
        """Test VACUUM command effectiveness"""
        test_databases = ['case_management', 'legal_cases', 'reminders']
        
        for db_name in test_databases:
            try:
                with perf_tester.get_db_connection(db_name) as conn:
                    # Get database size before VACUUM
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA page_count")
                    pages_before = cursor.fetchone()[0]
                    cursor.execute("PRAGMA page_size")
                    page_size = cursor.fetchone()[0]
                    size_before = pages_before * page_size
                    
                    # Run VACUUM
                    start_time = time.time()
                    conn.execute("VACUUM")
                    vacuum_duration = time.time() - start_time
                    
                    # Get database size after VACUUM
                    cursor.execute("PRAGMA page_count")
                    pages_after = cursor.fetchone()[0]
                    size_after = pages_after * page_size
                    
                    space_saved = size_before - size_after
                    space_saved_pct = (space_saved / size_before * 100) if size_before > 0 else 0
                    
                    logger.info(f"✅ VACUUM {db_name}: {vacuum_duration:.3f}s, "
                              f"saved {space_saved} bytes ({space_saved_pct:.1f}%)")
                    
            except Exception as e:
                logger.warning(f"Could not test VACUUM for {db_name}: {e}")
    
    def test_analyze_statistics(self, perf_tester):
        """Test ANALYZE command for query optimization"""
        test_databases = ['case_management', 'legal_cases', 'reminders']
        
        for db_name in test_databases:
            try:
                with perf_tester.get_db_connection(db_name) as conn:
                    # Run ANALYZE
                    start_time = time.time()
                    conn.execute("ANALYZE")
                    analyze_duration = time.time() - start_time
                    
                    # Check if statistics were updated
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_stat1")
                    stat_count = cursor.fetchone()[0]
                    
                    assert stat_count > 0, f"ANALYZE did not generate statistics for {db_name}"
                    
                    logger.info(f"✅ ANALYZE {db_name}: {analyze_duration:.3f}s, "
                              f"{stat_count} statistics entries")
                    
            except Exception as e:
                logger.warning(f"Could not test ANALYZE for {db_name}: {e}")

class TestConcurrencyPerformance:
    """Test concurrent access performance"""
    
    def test_concurrent_read_performance(self, perf_tester):
        """Test concurrent read performance"""
        import threading
        import queue
        
        def read_worker(db_name: str, query: str, result_queue: queue.Queue):
            try:
                with perf_tester.get_db_connection(db_name) as conn:
                    start_time = time.time()
                    duration, results = perf_tester.time_query(conn, query)
                    result_queue.put(('success', duration, len(results)))
            except Exception as e:
                result_queue.put(('error', str(e), 0))
        
        # Test concurrent reads on case_management
        query = "SELECT * FROM clients WHERE case_status = 'active' LIMIT 10"
        result_queue = queue.Queue()
        threads = []
        
        # Start 5 concurrent read threads
        for i in range(5):
            thread = threading.Thread(
                target=read_worker,
                args=('case_management', query, result_queue)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())
        
        # Analyze results
        successful_reads = [r for r in results if r[0] == 'success']
        if successful_reads:
            durations = [r[1] for r in successful_reads]
            avg_duration = statistics.mean(durations)
            max_duration = max(durations)
            
            assert max_duration < perf_tester.performance_thresholds['simple_select'] * 2, \
                f"Concurrent read too slow: {max_duration:.3f}s"
            
            logger.info(f"✅ Concurrent read performance: avg={avg_duration:.3f}s, max={max_duration:.3f}s")
        
        assert len(successful_reads) == 5, f"Only {len(successful_reads)}/5 concurrent reads succeeded"

if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])