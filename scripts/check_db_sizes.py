#!/usr/bin/env python3
"""
Quick database size and structure check
"""

import os
import sqlite3
from pathlib import Path

def check_databases():
    """Check all database sizes and basic structure"""
    databases_dir = Path("databases")
    
    if not databases_dir.exists():
        print("❌ Databases directory not found")
        return
    
    print("📊 Database Status Report")
    print("=" * 50)
    
    total_size = 0
    db_count = 0
    
    for db_file in databases_dir.glob("*.db"):
        try:
            size_kb = db_file.stat().st_size / 1024
            total_size += size_kb
            db_count += 1
            
            # Check if database is accessible
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Get table count
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_count = len(tables)
            
            conn.close()
            
            print(f"✅ {db_file.name}: {size_kb:.1f}KB ({table_count} tables)")
            
        except Exception as e:
            print(f"❌ {db_file.name}: Error - {e}")
    
    print("=" * 50)
    print(f"📈 Total: {db_count} databases, {total_size:.1f}KB")
    
    # Check for backup files
    backup_files = list(databases_dir.glob("*.db.backup*"))
    if backup_files:
        print(f"💾 {len(backup_files)} backup files found")

if __name__ == "__main__":
    check_databases()
