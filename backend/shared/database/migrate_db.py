"""
Database migration script to update existing database schema to match SQLAlchemy models
"""

import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def migrate_database():
    """Migrate the existing database to match SQLAlchemy models"""
    
    db_path = "databases/case_management.db"
    
    if not os.path.exists(db_path):
        logger.info("Database does not exist, creating new one")
        return
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if tasks table exists and has the old schema
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'task_id' in columns and 'id' not in columns:
                logger.info("Migrating tasks table schema...")
                
                # Create new tasks table with correct schema
                cursor.execute("""
                    CREATE TABLE tasks_new (
                        id TEXT PRIMARY KEY,
                        client_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        due_date DATETIME,
                        priority TEXT DEFAULT 'medium',
                        status TEXT DEFAULT 'pending',
                        category TEXT,
                        assigned_to TEXT,
                        created_by TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        task_type TEXT,
                        context_type TEXT,
                        context_id TEXT,
                        ai_generated BOOLEAN DEFAULT 0,
                        ai_priority_score REAL DEFAULT 0.0,
                        auto_generated BOOLEAN DEFAULT 0,
                        task_metadata TEXT,
                        completed_date DATETIME,
                        updated_by TEXT,
                        FOREIGN KEY (client_id) REFERENCES clients (id),
                        FOREIGN KEY (assigned_to) REFERENCES users (id),
                        FOREIGN KEY (created_by) REFERENCES users (id),
                        FOREIGN KEY (updated_by) REFERENCES users (id)
                    )
                """)
                
                # Copy data from old table to new table
                cursor.execute("""
                    INSERT INTO tasks_new (
                        id, client_id, title, description, due_date, priority, status, 
                        category, assigned_to, created_by, created_at, updated_at
                    )
                    SELECT 
                        task_id, client_id, task_description, task_description, due_date, 
                        'medium', status, 'general', NULL, NULL, created_at, created_at
                    FROM tasks
                """)
                
                # Drop old table and rename new table
                cursor.execute("DROP TABLE tasks")
                cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")
                
                logger.info("Tasks table migration completed")
            
            # Check if clients table needs migration
            cursor.execute("PRAGMA table_info(clients)")
            client_columns = [col[1] for col in cursor.fetchall()]
            
            if 'client_id' in client_columns and 'id' not in client_columns:
                logger.info("Migrating clients table schema...")
                
                # Create new clients table with correct schema
                cursor.execute("""
                    CREATE TABLE clients_new (
                        id TEXT PRIMARY KEY,
                        first_name TEXT NOT NULL,
                        last_name TEXT NOT NULL,
                        email TEXT UNIQUE,
                        phone TEXT,
                        status TEXT DEFAULT 'active',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Copy data from old table to new table
                cursor.execute("""
                    INSERT INTO clients_new (
                        id, first_name, last_name, email, phone, status, created_at, updated_at
                    )
                    SELECT 
                        client_id, first_name, last_name, email, phone, 
                        CASE WHEN is_active = 1 THEN 'active' ELSE 'inactive' END,
                        created_at, last_updated
                    FROM clients
                """)
                
                # Drop old table and rename new table
                cursor.execute("DROP TABLE clients")
                cursor.execute("ALTER TABLE clients_new RENAME TO clients")
                
                logger.info("Clients table migration completed")
            
            # Check if users table needs migration
            cursor.execute("PRAGMA table_info(users)")
            user_columns = [col[1] for col in cursor.fetchall()]
            
            if 'id' not in user_columns:
                logger.info("Creating users table...")
                
                cursor.execute("""
                    CREATE TABLE users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        role TEXT DEFAULT 'user',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert some default users
                cursor.execute("""
                    INSERT INTO users (id, username, email, role) VALUES 
                    ('default_manager', 'case_manager', 'manager@example.com', 'case_manager'),
                    ('default_user', 'user', 'user@example.com', 'user')
                """)
                
                logger.info("Users table created")
            
            # Ensure appointments table has correct schema
            cursor.execute("PRAGMA table_info(appointments)")
            appointment_columns = [col[1] for col in cursor.fetchall()]
            
            if 'id' not in appointment_columns:
                logger.info("Creating appointments table...")
                
                cursor.execute("""
                    CREATE TABLE appointments (
                        id TEXT PRIMARY KEY,
                        client_id TEXT NOT NULL,
                        case_manager_id TEXT,
                        appointment_type TEXT NOT NULL,
                        provider_name TEXT,
                        appointment_date DATETIME NOT NULL,
                        appointment_time TEXT,
                        location TEXT,
                        notes TEXT,
                        status TEXT DEFAULT 'scheduled',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (client_id) REFERENCES clients (id),
                        FOREIGN KEY (case_manager_id) REFERENCES users (id)
                    )
                """)
                
                logger.info("Appointments table created")
            
            # Ensure saved_jobs table has correct schema
            cursor.execute("PRAGMA table_info(saved_jobs)")
            job_columns = [col[1] for col in cursor.fetchall()]
            
            if 'id' not in job_columns:
                logger.info("Creating saved_jobs table...")
                
                cursor.execute("""
                    CREATE TABLE saved_jobs (
                        id TEXT PRIMARY KEY,
                        client_id TEXT NOT NULL,
                        job_title TEXT NOT NULL,
                        company TEXT NOT NULL,
                        location TEXT,
                        salary TEXT,
                        job_type TEXT,
                        background_friendly BOOLEAN DEFAULT 0,
                        description TEXT,
                        posted_date DATETIME,
                        source TEXT,
                        status TEXT DEFAULT 'saved',
                        application_date DATETIME,
                        saved_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (client_id) REFERENCES clients (id)
                    )
                """)
                
                logger.info("Saved_jobs table created")
            
            # Ensure resumes table has correct schema
            cursor.execute("PRAGMA table_info(resumes)")
            resume_columns = [col[1] for col in cursor.fetchall()]
            
            if 'id' not in resume_columns:
                logger.info("Creating resumes table...")
                
                cursor.execute("""
                    CREATE TABLE resumes (
                        id TEXT PRIMARY KEY,
                        client_id TEXT NOT NULL,
                        resume_name TEXT NOT NULL,
                        resume_data TEXT,
                        job_context TEXT,
                        template_used TEXT,
                        file_path TEXT,
                        download_url TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (client_id) REFERENCES clients (id)
                    )
                """)
                
                logger.info("Resumes table created")
            
            conn.commit()
            logger.info("Database migration completed successfully")
            
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_database()
