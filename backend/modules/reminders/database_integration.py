#!/usr/bin/env python3
"""
Authentication Database Layer
User storage and retrieval using SQLite
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import os

from .models import User, UserInDB, UserCreate, UserRole, UserStatus
from .security import get_password_hash

logger = logging.getLogger(__name__)

class AuthDatabase:
    """Database manager for authentication"""
    
    def __init__(self, db_path: str = "databases/auth.db"):
        self.db_path = db_path
        self.ensure_database_exists()
        self.init_tables()
    
    def ensure_database_exists(self):
        """Ensure database directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_tables(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    department TEXT,
                    supervisor_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            # User sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users (user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users (role)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions (user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions (token_hash)")
            
            conn.commit()
            logger.info("Authentication database tables initialized")
    
    def create_user(self, user_data: UserCreate) -> Optional[User]:
        """Create a new user"""
        try:
            with self.get_connection() as conn:
                # Check if user already exists
                existing = conn.execute(
                    "SELECT id FROM users WHERE email = ? OR username = ?",
                    (user_data.email, user_data.username)
                ).fetchone()
                
                if existing:
                    logger.warning(f"User creation failed: email or username already exists")
                    return None
                
                # Hash password
                hashed_password = get_password_hash(user_data.password)
                
                # Generate user ID
                import uuid
                user_id = str(uuid.uuid4())
                
                # Insert user
                cursor = conn.execute("""
                    INSERT INTO users (
                        user_id, email, username, hashed_password, full_name,
                        role, department, supervisor_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, user_data.email, user_data.username, hashed_password,
                    user_data.full_name, user_data.role.value, user_data.department,
                    user_data.supervisor_id
                ))
                
                conn.commit()
                
                # Return created user
                return self.get_user_by_id(user_id)
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username"""
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ? AND is_active = 1",
                    (username,)
                ).fetchone()
                
                if row:
                    return self._row_to_user_in_db(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email"""
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE email = ? AND is_active = 1",
                    (email,)
                ).fetchone()
                
                if row:
                    return self._row_to_user_in_db(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE user_id = ? AND is_active = 1",
                    (user_id,)
                ).fetchone()
                
                if row:
                    return self._row_to_user(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
    
    def get_users_by_role(self, role: UserRole) -> List[User]:
        """Get all users with specific role"""
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM users WHERE role = ? AND is_active = 1 ORDER BY full_name",
                    (role.value,)
                ).fetchall()
                
                return [self._row_to_user(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting users by role: {e}")
            return []
    
    def get_team_members(self, supervisor_id: str) -> List[User]:
        """Get team members for a supervisor"""
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM users WHERE supervisor_id = ? AND is_active = 1 ORDER BY full_name",
                    (supervisor_id,)
                ).fetchall()
                
                return [self._row_to_user(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting team members: {e}")
            return []
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE users SET is_active = 0, status = 'inactive' WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            return False
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert database row to User model"""
        return User(
            id=str(row['id']),
            user_id=row['user_id'],
            email=row['email'],
            username=row['username'],
            full_name=row['full_name'],
            role=UserRole(row['role']),
            status=UserStatus(row['status']),
            department=row['department'],
            supervisor_id=row['supervisor_id'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None,
            is_active=bool(row['is_active'])
        )
    
    def _row_to_user_in_db(self, row: sqlite3.Row) -> UserInDB:
        """Convert database row to UserInDB model"""
        user = self._row_to_user(row)
        return UserInDB(
            **user.dict(),
            hashed_password=row['hashed_password']
        )
    
    def seed_initial_users(self):
        """Seed initial case manager and supervisor accounts"""
        try:
            # Check if users already exist
            with self.get_connection() as conn:
                existing_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
                
                if existing_count > 0:
                    logger.info("Users already exist, skipping seed")
                    return
            
            # Create supervisor account
            supervisor_data = UserCreate(
                email="supervisor@casemanager.com",
                username="supervisor",
                password="SupervisorPass123!",
                full_name="Sarah Johnson",
                role=UserRole.SUPERVISOR,
                department="Case Management"
            )
            
            supervisor = self.create_user(supervisor_data)
            if supervisor:
                logger.info(f"Created supervisor account: {supervisor.username}")
            
            # Create case manager account
            case_manager_data = UserCreate(
                email="casemanager@casemanager.com",
                username="casemanager",
                password="CaseManagerPass123!",
                full_name="Michael Rodriguez",
                role=UserRole.CASE_MANAGER,
                department="Case Management",
                supervisor_id=supervisor.user_id if supervisor else None
            )
            
            case_manager = self.create_user(case_manager_data)
            if case_manager:
                logger.info(f"Created case manager account: {case_manager.username}")
            
            # Create admin account
            admin_data = UserCreate(
                email="admin@casemanager.com",
                username="admin",
                password="AdminPass123!",
                full_name="Administrator",
                role=UserRole.ADMIN,
                department="IT"
            )
            
            admin = self.create_user(admin_data)
            if admin:
                logger.info(f"Created admin account: {admin.username}")
            
            logger.info("Initial user accounts seeded successfully")
            
        except Exception as e:
            logger.error(f"Error seeding initial users: {e}")
    
    def get_all_users(self) -> List[User]:
        """Get all active users"""
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM users WHERE is_active = 1 ORDER BY full_name"
                ).fetchall()
                
                return [self._row_to_user(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

