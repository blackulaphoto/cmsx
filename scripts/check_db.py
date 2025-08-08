#!/usr/bin/env python3
"""
Check existing database structure
"""

import sqlite3
import os

def check_database_structure():
    """Check the structure of existing databases"""
    
    # Check case_management.db
    if os.path.exists('databases/case_management.db'):
        print("=== Case Management Database ===")
        conn = sqlite3.connect('databases/case_management.db')
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables: {[t[0] for t in tables]}")
        
        # Show table structures
        for table in tables:
            table_name = table[0]
            print(f"\n--- {table_name} table ---")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        
        conn.close()
    else:
        print("Case management database does not exist")
    
    # Check reminders.db
    if os.path.exists('databases/reminders.db'):
        print("\n=== Reminders Database ===")
        conn = sqlite3.connect('databases/reminders.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables: {[t[0] for t in tables]}")
        
        # Show table structures
        for table in tables:
            table_name = table[0]
            print(f"\n--- {table_name} table ---")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        
        conn.close()
    else:
        print("Reminders database does not exist")

if __name__ == "__main__":
    check_database_structure()