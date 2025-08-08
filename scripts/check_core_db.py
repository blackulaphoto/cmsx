#!/usr/bin/env python3
import sqlite3
import os

db_path = "databases/core_clients.db"

if os.path.exists(db_path):
    print(f"=== Core Clients Database ===")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables: {[t[0] for t in tables]}")
    
    # Show structure of each table
    for table in tables:
        table_name = table[0]
        print(f"\n--- {table_name} table ---")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    
    conn.close()
else:
    print(f"Core clients database not found at: {db_path}")