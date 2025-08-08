#!/usr/bin/env python3
"""
Step 1: Create new core_clients.db with master clients table
This creates the single source of truth for all client data
"""

import sqlite3
import os
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_core_clients_database():
    """Create the master core_clients.db database"""
    
    print("🔧 Step 1: Creating core_clients.db - Master Client Database")
    print("=" * 60)
    
    # Ensure databases directory exists
    db_path = "databases/core_clients.db"
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Create MASTER CLIENTS TABLE
            print("📊 Creating master clients table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    client_id TEXT PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL, 
                    date_of_birth DATE,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    emergency_contact_name TEXT,
                    emergency_contact_phone TEXT,
                    risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high')),
                    case_status TEXT CHECK (case_status IN ('active', 'inactive', 'completed')),
                    case_manager_id TEXT,
                    intake_date DATE DEFAULT CURRENT_DATE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create CLIENT GOALS TABLE
            print("📋 Creating client_goals table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS client_goals (
                    goal_id TEXT PRIMARY KEY,
                    client_id TEXT REFERENCES clients(client_id),
                    goal_type TEXT, -- 'housing', 'employment', 'legal', 'benefits'
                    description TEXT,
                    status TEXT CHECK (status IN ('pending', 'in_progress', 'completed')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create CLIENT BARRIERS TABLE
            print("🚧 Creating client_barriers table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS client_barriers (
                    barrier_id TEXT PRIMARY KEY,
                    client_id TEXT REFERENCES clients(client_id),
                    barrier_type TEXT,
                    description TEXT,
                    severity TEXT CHECK (severity IN ('low', 'medium', 'high')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create CASE NOTES TABLE
            print("📝 Creating case_notes table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS case_notes (
                    note_id TEXT PRIMARY KEY,
                    client_id TEXT REFERENCES clients(client_id),
                    note_type TEXT,
                    content TEXT,
                    created_by TEXT, -- case_manager_id
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            print("⚡ Creating indexes...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_case_manager ON clients(case_manager_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(case_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_client ON client_goals(client_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_barriers_client ON client_barriers(client_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_client ON case_notes(client_id)")
            
            conn.commit()
            
            # Verify tables were created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"✅ Successfully created core_clients.db")
            print(f"📊 Tables created: {', '.join(tables)}")
            
            # Show table schemas
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print(f"\n📋 {table} table structure:")
                for col in columns:
                    print(f"   • {col[1]} ({col[2]}) - {'PK' if col[5] else 'FK' if 'REFERENCES' in str(col) else ''}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error creating core_clients.db: {e}")
        print(f"❌ Failed to create core_clients.db: {e}")
        return False

if __name__ == "__main__":
    success = create_core_clients_database()
    if success:
        print("\n🎉 Step 1 Complete: core_clients.db created successfully!")
        print("📁 Database location: databases/core_clients.db")
    else:
        print("\n❌ Step 1 Failed: Could not create core_clients.db")
