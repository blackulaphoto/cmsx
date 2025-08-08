"""
Database utilities for Case Management Suite
"""

import sqlite3
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper row factory"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an update/insert query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
        """
        results = self.execute_query(query, (table_name,))
        return len(results) > 0

# Database instances
def get_case_management_db() -> DatabaseManager:
    """Get case management database instance"""
    from config.config import config
    return DatabaseManager(config.CASE_MANAGEMENT_DB)

def get_housing_db() -> DatabaseManager:
    """Get housing database instance"""
    from config.config import config
    return DatabaseManager(config.HOUSING_DB)

def get_services_db() -> DatabaseManager:
    """Get services database instance"""
    from config.config import config
    return DatabaseManager(config.SERVICES_DB) 