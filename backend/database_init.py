#!/usr/bin/env python3
"""
Database Initialization - Initialize all 9 databases with required tables
Addresses potential table missing errors causing database failures
"""

import sqlite3
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def initialize_databases():
    """
    Initialize all 9 databases with required tables
    Addresses potential table missing errors
    """
    database_dir = Path("databases")
    database_dir.mkdir(exist_ok=True)
    
    # Core clients database schema
    core_clients_schema = """
    DROP TABLE IF EXISTS clients;
    CREATE TABLE clients (
        client_id TEXT PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        date_of_birth TEXT,
        case_manager_id TEXT NOT NULL,
        risk_level TEXT DEFAULT 'medium',
        intake_date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        housing_status TEXT DEFAULT 'unknown',
        employment_status TEXT DEFAULT 'unknown'
    );
    """
    
    # Module database schema (simplified for sync)
    module_schema = """
    DROP TABLE IF EXISTS clients;
    CREATE TABLE clients (
        client_id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        case_manager_id TEXT,
        intake_date TEXT,
        risk_level TEXT,
        synced_at TEXT
    );
    """
    
    # Case management database schema (includes dashboard_notes for case manager personal notes)
    case_management_schema = """
    DROP TABLE IF EXISTS clients;
    CREATE TABLE clients (
        client_id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        case_manager_id TEXT,
        intake_date TEXT,
        risk_level TEXT,
        synced_at TEXT
    );
    
    CREATE TABLE IF NOT EXISTS dashboard_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id TEXT UNIQUE NOT NULL,
        case_manager_id TEXT NOT NULL,
        content TEXT NOT NULL,
        pinned INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Enhanced reminders schema with task persistence
    reminders_schema = """
    CREATE TABLE IF NOT EXISTS clients (
        client_id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        case_manager_id TEXT,
        synced_at TEXT
    );
    
    CREATE TABLE IF NOT EXISTS intelligent_tasks (
        task_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        process_type TEXT,
        week_number INTEGER,
        due_date TEXT,
        priority TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'pending',
        dependencies TEXT,
        estimated_duration INTEGER DEFAULT 45,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY (client_id) REFERENCES clients(client_id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_tasks_client_id ON intelligent_tasks(client_id);
    CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON intelligent_tasks(due_date);
    CREATE INDEX IF NOT EXISTS idx_tasks_priority ON intelligent_tasks(priority);
    CREATE INDEX IF NOT EXISTS idx_tasks_status ON intelligent_tasks(status);
    """ + module_schema

    databases = [
        ("core_clients.db", core_clients_schema),
        ("case_management.db", case_management_schema),
        ("housing.db", module_schema),
        ("benefits.db", module_schema),
        ("legal.db", module_schema),
        ("employment.db", module_schema),
        ("services.db", module_schema),
        ("reminders.db", reminders_schema),
        ("ai_assistant.db", module_schema)
    ]
    
    for db_name, schema in databases:
        db_path = database_dir / db_name
        
        try:
            with sqlite3.connect(db_path) as conn:
                # Execute each statement separately
                statements = [stmt.strip() for stmt in schema.split(';') if stmt.strip()]
                for statement in statements:
                    conn.execute(statement)
                conn.commit()
                print(f"✅ Initialized {db_name}")
                logger.info(f"Initialized database: {db_name}")
        except Exception as e:
            print(f"❌ Failed to initialize {db_name}: {e}")
            logger.error(f"Failed to initialize {db_name}: {e}")
    
    print(f"✅ All 9 databases initialized successfully")
    logger.info("All 9 databases initialized successfully")

if __name__ == "__main__":
    initialize_databases()