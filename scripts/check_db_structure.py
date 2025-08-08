#!/usr/bin/env python3
"""
Quick script to check database structure
"""
import sqlite3
import os

def check_database_tables(db_path, db_name):
    """Check what tables exist in a database"""
    if not os.path.exists(db_path):
        print(f"❌ {db_name}: Database file does not exist")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"✅ {db_name}: {len(tables)} tables")
        for table in tables:
            print(f"   - {table}")
        print()
    except Exception as e:
        print(f"❌ {db_name}: Error - {e}")

# Check key databases
databases = [
    ("databases/unified_platform.db", "Unified Platform"),
    ("databases/case_management.db", "Case Management"),
    ("databases/core_clients.db", "Core Clients"),
    ("databases/benefits_transport.db", "Benefits Transport")
]

print("🔍 Database Structure Check")
print("=" * 50)

for db_path, db_name in databases:
    check_database_tables(db_path, db_name)