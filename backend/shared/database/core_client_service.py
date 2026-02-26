#!/usr/bin/env python3
"""
Core Client Service - Centralized client management for core_clients.db
This service handles all client CRUD operations as the single source of truth
"""

import sqlite3
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from backend.shared.database.railway_postgres import upsert_client_to_postgres

logger = logging.getLogger(__name__)

class CoreClientService:
    """Centralized service for managing clients in core_clients.db"""
    
    def __init__(self):
        self.db_path = "databases/core_clients.db"
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Ensure the core_clients.db database exists"""
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Core clients database not found: {self.db_path}")

    def _sync_client_to_postgres(self, client_data: Dict[str, Any], operation: str) -> str:
        """Dual-write mirror into Railway Postgres without blocking SQLite path."""
        return upsert_client_to_postgres(
            client_data=client_data,
            integration_results={"source": "core_client_service", "operation": operation},
        )
    
    def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new client in core_clients.db"""
        
        try:
            # Generate unique client_id if not provided
            if not client_data.get('client_id'):
                client_data['client_id'] = str(uuid.uuid4())
            
            # Set default values
            client_data.setdefault('created_at', datetime.now().isoformat())
            client_data.setdefault('updated_at', datetime.now().isoformat())
            client_data.setdefault('intake_date', datetime.now().strftime('%Y-%m-%d'))
            client_data.setdefault('case_status', 'active')
            client_data.setdefault('risk_level', 'medium')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if client already exists
                cursor.execute("SELECT client_id FROM clients WHERE client_id = ?", (client_data['client_id'],))
                if cursor.fetchone():
                    raise ValueError(f"Client with ID {client_data['client_id']} already exists")
                
                # Insert new client
                columns = ', '.join(client_data.keys())
                placeholders = ', '.join(['?' for _ in client_data])
                values = list(client_data.values())
                
                cursor.execute(f"INSERT INTO clients ({columns}) VALUES ({placeholders})", values)
                conn.commit()
                postgres_sync = self._sync_client_to_postgres(client_data, "create")
                
                logger.info(f"Created client: {client_data['first_name']} {client_data['last_name']} (ID: {client_data['client_id']})")
                
                return {
                    'success': True,
                    'client_id': client_data['client_id'],
                    'message': f"Client {client_data['first_name']} {client_data['last_name']} created successfully",
                    'postgres_sync': postgres_sync,
                }
                
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get a client by ID"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
                row = cursor.fetchone()
                
                if row:
                    # Get column names
                    cursor.execute("PRAGMA table_info(clients)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"Error getting client {client_id}: {e}")
            return None
    
    def get_all_clients(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all clients with pagination"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM clients ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute("PRAGMA table_info(clients)")
                columns = [col[1] for col in cursor.fetchall()]
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting all clients: {e}")
            return []
    
    def update_client(self, client_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a client"""
        
        try:
            update_data['updated_at'] = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if client exists
                cursor.execute("SELECT client_id FROM clients WHERE client_id = ?", (client_id,))
                if not cursor.fetchone():
                    raise ValueError(f"Client with ID {client_id} not found")
                
                # Build update query
                set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
                values = list(update_data.values()) + [client_id]
                
                cursor.execute(f"UPDATE clients SET {set_clause} WHERE client_id = ?", values)
                conn.commit()
                latest = self.get_client(client_id) or {"client_id": client_id, **update_data}
                postgres_sync = self._sync_client_to_postgres(latest, "update")
                
                logger.info(f"Updated client: {client_id}")
                
                return {
                    'success': True,
                    'client_id': client_id,
                    'message': f"Client {client_id} updated successfully",
                    'postgres_sync': postgres_sync,
                }
                
        except Exception as e:
            logger.error(f"Error updating client {client_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_client(self, client_id: str) -> Dict[str, Any]:
        """Delete a client (soft delete by setting status to inactive)"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if client exists
                cursor.execute("SELECT client_id FROM clients WHERE client_id = ?", (client_id,))
                if not cursor.fetchone():
                    raise ValueError(f"Client with ID {client_id} not found")
                
                # Soft delete by setting status to inactive
                cursor.execute(
                    "UPDATE clients SET case_status = 'inactive', updated_at = ? WHERE client_id = ?",
                    (datetime.now().isoformat(), client_id)
                )
                conn.commit()
                latest = self.get_client(client_id)
                postgres_sync = (
                    self._sync_client_to_postgres(latest, "delete-soft")
                    if latest
                    else "skipped:no-client"
                )
                
                logger.info(f"Soft deleted client: {client_id}")
                
                return {
                    'success': True,
                    'client_id': client_id,
                    'message': f"Client {client_id} marked as inactive",
                    'postgres_sync': postgres_sync,
                }
                
        except Exception as e:
            logger.error(f"Error deleting client {client_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_clients(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search clients by name, email, or phone"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                search_pattern = f"%{search_term}%"
                cursor.execute("""
                    SELECT * FROM clients 
                    WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (search_pattern, search_pattern, search_pattern, search_pattern, limit))
                
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute("PRAGMA table_info(clients)")
                columns = [col[1] for col in cursor.fetchall()]
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logger.error(f"Error searching clients: {e}")
            return []
    
    def get_clients_by_case_manager(self, case_manager_id: str) -> List[Dict[str, Any]]:
        """Get all clients assigned to a specific case manager"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM clients WHERE case_manager_id = ? ORDER BY created_at DESC",
                    (case_manager_id,)
                )
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute("PRAGMA table_info(clients)")
                columns = [col[1] for col in cursor.fetchall()]
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting clients for case manager {case_manager_id}: {e}")
            return []
    
    def get_client_count(self) -> int:
        """Get total number of active clients"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM clients WHERE case_status = 'active'")
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Error getting client count: {e}")
            return 0
