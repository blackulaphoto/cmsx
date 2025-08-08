#!/usr/bin/env python3
"""
Employment Database Migration Script
Updates employment.db to match the corrected Resume Builder architecture
"""
import sqlite3
import os
from datetime import datetime

def migrate_employment_database():
    db_path = "databases/employment.db"
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Starting employment.db migration...")
        
        # 1. Update client_employment_profiles table
        print("📝 Updating client_employment_profiles table...")
        
        # Add missing columns to client_employment_profiles
        missing_profile_columns = [
            ("certifications", "TEXT"),
            ("professional_references", "TEXT"),  # Renamed to avoid SQL reserved word
            ("career_objective", "TEXT"),
            ("updated_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
        ]
        
        for column_name, column_type in missing_profile_columns:
            try:
                cursor.execute(f"ALTER TABLE client_employment_profiles ADD COLUMN {column_name} {column_type}")
                print(f"  ✅ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"  ⚠️  Column already exists: {column_name}")
                else:
                    print(f"  ❌ Error adding column {column_name}: {e}")
        
        # 2. Update resumes table
        print("📝 Updating resumes table...")
        
        # Add missing columns to resumes
        missing_resume_columns = [
            ("profile_id", "TEXT"),
            ("resume_title", "TEXT"),
            ("ats_score", "INTEGER CHECK (ats_score BETWEEN 0 AND 100)"),
            ("is_active", "BOOLEAN DEFAULT 1"),
            ("updated_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
        ]
        
        for column_name, column_type in missing_resume_columns:
            try:
                cursor.execute(f"ALTER TABLE resumes ADD COLUMN {column_name} {column_type}")
                print(f"  ✅ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"  ⚠️  Column already exists: {column_name}")
                else:
                    print(f"  ❌ Error adding column {column_name}: {e}")
        
        # 3. Update job_applications table
        print("📝 Updating job_applications table...")
        
        # Add missing columns to job_applications
        missing_app_columns = [
            ("resume_id", "TEXT"),
            ("job_description", "TEXT"),
            ("follow_up_date", "DATE"),
            ("notes", "TEXT"),
            ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
        ]
        
        for column_name, column_type in missing_app_columns:
            try:
                cursor.execute(f"ALTER TABLE job_applications ADD COLUMN {column_name} {column_type}")
                print(f"  ✅ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"  ⚠️  Column already exists: {column_name}")
                else:
                    print(f"  ❌ Error adding column {column_name}: {e}")
        
        # 4. Create resume_tailoring table if it doesn't exist
        print("📝 Creating resume_tailoring table...")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_tailoring (
            tailoring_id TEXT PRIMARY KEY,
            resume_id TEXT NOT NULL,
            job_application_id TEXT,
            original_content TEXT,
            tailored_content TEXT,
            optimization_type TEXT,
            match_score DECIMAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resume_id) REFERENCES resumes(resume_id),
            FOREIGN KEY (job_application_id) REFERENCES job_applications(application_id)
        )
        """)
        print("  ✅ Created resume_tailoring table")
        
        # 5. Create indexes for performance
        print("📝 Creating indexes...")
        
        indexes = [
            ("idx_profiles_client", "client_employment_profiles", "client_id"),
            ("idx_resumes_client", "resumes", "client_id"),
            ("idx_resumes_profile", "resumes", "profile_id"),
            ("idx_applications_client", "job_applications", "client_id"),
            ("idx_applications_resume", "job_applications", "resume_id"),
            ("idx_tailoring_resume", "resume_tailoring", "resume_id")
        ]
        
        for index_name, table_name, column_name in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})")
                print(f"  ✅ Created index: {index_name}")
            except sqlite3.OperationalError as e:
                print(f"  ⚠️  Index creation warning for {index_name}: {e}")
        
        # 6. Update existing records with default values
        print("📝 Updating existing records...")
        
        # Set default values for new columns
        cursor.execute("UPDATE client_employment_profiles SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        cursor.execute("UPDATE resumes SET is_active = 1 WHERE is_active IS NULL")
        cursor.execute("UPDATE resumes SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        cursor.execute("UPDATE job_applications SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        
        print("  ✅ Updated existing records with default values")
        
        # Commit all changes
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # 7. Verify the updated structure
        print("\n📊 Updated database structure:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            print(f"\n--- {table_name} ---")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                nullable = "NOT NULL" if col[3] else "NULL"
                primary_key = "PRIMARY KEY" if col[5] else ""
                print(f"  {col[1]} {col[2]} {nullable} {primary_key}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_employment_database()
    if success:
        print("\n🎉 Employment database migration completed successfully!")
    else:
        print("\n💥 Employment database migration failed!")