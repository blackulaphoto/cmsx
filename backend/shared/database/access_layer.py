#!/usr/bin/env python3
"""
Database Access Layer - Centralized database access with permissions and optimization
This layer provides secure, optimized access to all databases in the system
"""

import sqlite3
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class PermissionLevel(Enum):
    """Permission levels for database access"""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"

class DatabaseType(Enum):
    """Database types in the system"""
    CORE_CLIENTS = "core_clients"
    CASE_MANAGEMENT = "case_management"
    REMINDERS = "reminders"
    LEGAL_CASES = "legal_cases"
    EXPUNGEMENT = "expungement"
    BENEFITS_TRANSPORT = "benefits_transport"
    HOUSING = "housing"
    HOUSING_RESOURCES = "housing_resources"
    JOBS = "jobs"
    RESUMES = "resumes"
    SERVICES = "services"
    SOCIAL_SERVICES = "social_services"
    UNIFIED_PLATFORM = "unified_platform"
    CASE_MANAGER = "case_manager"

class DatabaseAccessLayer:
    """Centralized database access layer with permissions and optimization"""
    
    def __init__(self):
        self.databases = {
            DatabaseType.CORE_CLIENTS: "databases/core_clients.db",
            DatabaseType.CASE_MANAGEMENT: "databases/case_management.db",
            DatabaseType.REMINDERS: "databases/reminders.db",
            DatabaseType.LEGAL_CASES: "databases/legal_cases.db",
            DatabaseType.EXPUNGEMENT: "databases/expungement.db",
            DatabaseType.BENEFITS_TRANSPORT: "databases/benefits_transport.db",
            DatabaseType.HOUSING: "databases/housing.db",
            DatabaseType.HOUSING_RESOURCES: "databases/housing_resources.db",
            DatabaseType.JOBS: "databases/jobs.db",
            DatabaseType.RESUMES: "databases/resumes.db",
            DatabaseType.SERVICES: "databases/services.db",
            DatabaseType.SOCIAL_SERVICES: "databases/social_services.db",
            DatabaseType.UNIFIED_PLATFORM: "databases/unified_platform.db",
            DatabaseType.CASE_MANAGER: "databases/case_manager.db"
        }
        
        # Permission matrix - defines what each module can access
        self.permissions = {
            # Core clients database - only Case Management and AI can write
            DatabaseType.CORE_CLIENTS: {
                "case_management": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN,
                "reminders": PermissionLevel.READ_ONLY,
                "legal_cases": PermissionLevel.READ_ONLY,
                "expungement": PermissionLevel.READ_ONLY,
                "benefits_transport": PermissionLevel.READ_ONLY,
                "housing": PermissionLevel.READ_ONLY,
                "housing_resources": PermissionLevel.READ_ONLY,
                "jobs": PermissionLevel.READ_ONLY,
                "resumes": PermissionLevel.READ_ONLY,
                "services": PermissionLevel.READ_ONLY,
                "social_services": PermissionLevel.READ_ONLY,
                "unified_platform": PermissionLevel.READ_ONLY,
                "case_manager": PermissionLevel.READ_ONLY
            },
            # Module databases - each module has full access to its own database
            DatabaseType.CASE_MANAGEMENT: {
                "case_management": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.REMINDERS: {
                "reminders": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.LEGAL_CASES: {
                "legal_cases": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.EXPUNGEMENT: {
                "expungement": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.BENEFITS_TRANSPORT: {
                "benefits_transport": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.HOUSING: {
                "housing": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.HOUSING_RESOURCES: {
                "housing_resources": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.JOBS: {
                "jobs": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.RESUMES: {
                "resumes": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.SERVICES: {
                "services": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.SOCIAL_SERVICES: {
                "social_services": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.UNIFIED_PLATFORM: {
                "unified_platform": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            },
            DatabaseType.CASE_MANAGER: {
                "case_manager": PermissionLevel.ADMIN,
                "ai_assistant": PermissionLevel.ADMIN
            }
        }
        
        # Connection pool for optimization
        self._connections = {}
    
    def check_permission(self, module: str, database_type: DatabaseType, operation: str) -> bool:
        """Check if a module has permission to perform an operation on a database"""
        
        if database_type not in self.permissions:
            return False
        
        module_permissions = self.permissions[database_type]
        
        if module not in module_permissions:
            return False
        
        permission_level = module_permissions[module]
        
        # Determine if operation is allowed based on permission level
        if operation in ['SELECT', 'READ']:
            return True  # All permission levels can read
        elif operation in ['INSERT', 'UPDATE', 'DELETE', 'WRITE']:
            return permission_level in [PermissionLevel.READ_WRITE, PermissionLevel.ADMIN]
        elif operation in ['CREATE', 'DROP', 'ALTER', 'ADMIN']:
            return permission_level == PermissionLevel.ADMIN
        
        return False
    
    def get_connection(self, database_type: DatabaseType) -> sqlite3.Connection:
        """Get a database connection with optimization"""
        
        db_path = self.databases.get(database_type)
        if not db_path or not Path(db_path).exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        # Create connection with optimizations
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA synchronous = NORMAL")  # Balance between safety and performance
        conn.execute("PRAGMA cache_size = 10000")  # Increase cache size
        conn.execute("PRAGMA temp_store = MEMORY")  # Store temp tables in memory
        
        return conn
    
    def execute_query(self, module: str, database_type: DatabaseType, query: str, 
                     params: tuple = (), operation: str = "SELECT") -> List[Dict[str, Any]]:
        """Execute a query with permission checking and optimization"""
        
        # Check permissions
        if not self.check_permission(module, database_type, operation):
            raise PermissionError(f"Module {module} does not have {operation} permission on {database_type.value}")
        
        try:
            with self.get_connection(database_type) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                if operation == "SELECT":
                    # Get column names
                    columns = [description[0] for description in cursor.description]
                    rows = cursor.fetchall()
                    
                    # Convert to list of dictionaries
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    conn.commit()
                    return [{"affected_rows": cursor.rowcount}]
                    
        except Exception as e:
            logger.error(f"Error executing query on {database_type.value}: {e}")
            raise
    
    def get_client_data(self, module: str, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client data from core database with permission checking"""
        
        try:
            results = self.execute_query(
                module=module,
                database_type=DatabaseType.CORE_CLIENTS,
                query="SELECT * FROM clients WHERE client_id = ?",
                params=(client_id,),
                operation="SELECT"
            )
            
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error getting client data: {e}")
            return None
    
    def cross_database_query(self, module: str, client_id: str) -> Dict[str, Any]:
        """Perform optimized cross-database query for a client"""
        
        try:
            # Get client data from core database
            client_data = self.get_client_data(module, client_id)
            if not client_data:
                return {"error": "Client not found"}
            
            # Initialize result structure
            result = {
                "client": client_data,
                "module_data": {}
            }
            
            # Query each module database for client-specific data
            for db_type in DatabaseType:
                if db_type == DatabaseType.CORE_CLIENTS:
                    continue  # Skip core database as we already have client data
                
                try:
                    # Check if module has read permission
                    if not self.check_permission(module, db_type, "SELECT"):
                        continue
                    
                    # Get tables that might contain client data
                    with self.get_connection(db_type) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = [row[0] for row in cursor.fetchall()]
                        
                        module_data = {}
                        
                        # Query each table for client_id
                        for table in tables:
                            try:
                                # Check if table has client_id column
                                cursor.execute(f"PRAGMA table_info({table})")
                                columns = [col[1] for col in cursor.fetchall()]
                                
                                if 'client_id' in columns:
                                    cursor.execute(f"SELECT * FROM {table} WHERE client_id = ?", (client_id,))
                                    rows = cursor.fetchall()
                                    
                                    if rows:
                                        # Get column names
                                        cursor.execute(f"PRAGMA table_info({table})")
                                        table_columns = [col[1] for col in cursor.fetchall()]
                                        module_data[table] = [dict(zip(table_columns, row)) for row in rows]
                                        
                            except Exception as e:
                                logger.warning(f"Error querying table {table} in {db_type.value}: {e}")
                                continue
                        
                        if module_data:
                            result["module_data"][db_type.value] = module_data
                            
                except Exception as e:
                    logger.warning(f"Error querying database {db_type.value}: {e}")
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"Error in cross-database query: {e}")
            return {"error": str(e)}
    
    def get_database_stats(self, module: str) -> Dict[str, Any]:
        """Get statistics for all databases the module has access to"""
        
        stats = {}
        
        for db_type in DatabaseType:
            try:
                if not self.check_permission(module, db_type, "SELECT"):
                    continue
                
                with self.get_connection(db_type) as conn:
                    cursor = conn.cursor()
                    
                    # Get table count
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    table_count = cursor.fetchone()[0]
                    
                    # Get total row count across all tables
                    total_rows = 0
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    for table in tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            row_count = cursor.fetchone()[0]
                            total_rows += row_count
                        except:
                            continue
                    
                    stats[db_type.value] = {
                        "table_count": table_count,
                        "total_rows": total_rows,
                        "database_path": self.databases[db_type]
                    }
                    
            except Exception as e:
                logger.warning(f"Error getting stats for {db_type.value}: {e}")
                continue
        
        return stats
    
    def optimize_queries(self, module: str, client_id: str) -> Dict[str, Any]:
        """Optimize queries for a specific client across all databases"""
        
        try:
            # Use cross-database query with optimization
            result = self.cross_database_query(module, client_id)
            
            # Add optimization metadata
            result["optimization"] = {
                "timestamp": datetime.now().isoformat(),
                "module": module,
                "client_id": client_id,
                "databases_queried": len(result.get("module_data", {})),
                "total_records": sum(
                    len(table_data) 
                    for db_data in result.get("module_data", {}).values() 
                    for table_data in db_data.values()
                )
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing queries: {e}")
            return {"error": str(e)}
