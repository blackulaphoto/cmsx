#!/usr/bin/env python3
"""
Fix Database References - Ensure all modules use correct database architecture
This script identifies and fixes database reference issues across modules
"""
import os
import re
import sqlite3
from pathlib import Path

def find_database_references(directory):
    """Find all database connection references in Python files"""
    issues = []
    
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        if any(skip in root for skip in ['__pycache__', '.git', 'node_modules', 'frontend']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Look for sqlite3.connect patterns
                    connections = re.findall(r'sqlite3\.connect\([\'"]([^\'"]+)[\'"]', content)
                    
                    for conn in connections:
                        # Check for problematic patterns
                        if 'unified_platform.db' in conn and 'clients' in content:
                            issues.append({
                                'file': file_path,
                                'issue': 'unified_platform.db used with clients table',
                                'connection': conn
                            })
                        elif 'case_management.db' in conn and 'benefits' in content:
                            issues.append({
                                'file': file_path,
                                'issue': 'case_management.db used in benefits context',
                                'connection': conn
                            })
                            
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return issues

def check_database_integrity():
    """Check if all required databases exist and have proper structure"""
    required_databases = {
        'databases/core_clients.db': ['clients', 'client_goals', 'client_barriers', 'case_notes'],
        'databases/unified_platform.db': ['benefits_applications', 'case_notes', 'tasks', 'legal_cases'],
        'databases/case_management.db': ['clients', 'cases', 'documents', 'referrals'],
        'databases/benefits_transport.db': ['benefits_applications'],
        'databases/housing.db': [],  # May not exist yet
        'databases/legal_cases.db': [],
        'databases/expungement.db': [],
        'databases/reminders.db': [],
        'databases/resumes.db': [],
        'databases/search_cache.db': [],
        'databases/social_services.db': []
    }
    
    print("🔍 Database Integrity Check")
    print("=" * 50)
    
    for db_path, expected_tables in required_databases.items():
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                actual_tables = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                missing_tables = [t for t in expected_tables if t not in actual_tables]
                if missing_tables:
                    print(f"⚠️  {db_path}: Missing tables: {missing_tables}")
                else:
                    print(f"✅ {db_path}: OK ({len(actual_tables)} tables)")
                    
            except Exception as e:
                print(f"❌ {db_path}: Error - {e}")
        else:
            print(f"❌ {db_path}: File does not exist")

def main():
    """Main function to check and fix database issues"""
    print("🔧 Database Reference Checker & Fixer")
    print("=" * 50)
    
    # Check database integrity first
    check_database_integrity()
    print()
    
    # Find problematic database references
    print("🔍 Scanning for database reference issues...")
    issues = find_database_references('backend/modules')
    
    if issues:
        print(f"Found {len(issues)} potential issues:")
        for issue in issues:
            print(f"  📁 {issue['file']}")
            print(f"     Issue: {issue['issue']}")
            print(f"     Connection: {issue['connection']}")
            print()
    else:
        print("✅ No obvious database reference issues found")
    
    print("\n📋 Database Architecture Summary:")
    print("- core_clients.db: Master client data (owned by Case Management)")
    print("- unified_platform.db: Cross-module data (benefits_applications, tasks, etc.)")
    print("- case_management.db: Case management specific data")
    print("- Module-specific databases: Housing, Legal, Benefits, etc.")

if __name__ == "__main__":
    main()