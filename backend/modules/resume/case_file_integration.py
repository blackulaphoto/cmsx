#!/usr/bin/env python3
"""
Case File Integration for Resume Management
Handles storing resume versions, tracking client progress, and case manager workflow
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import uuid
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ResumeVersion:
    """Resume version within a case file"""
    version_id: Optional[str] = None
    case_file_id: Optional[str] = None
    client_id: Optional[int] = None
    resume_data: Optional[Dict[str, Any]] = None
    template_id: str = 'classic'
    job_target: Optional[Dict[str, Any]] = None
    version_number: int = 1
    version_name: str = ""
    html_content: Optional[str] = None
    pdf_path: Optional[str] = None
    ats_score: Optional[float] = None
    match_score: Optional[float] = None
    status: str = 'draft'  # draft, reviewed, approved, sent
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    notes: Optional[str] = None
    tailoring_recommendations: Optional[List[Dict[str, Any]]] = None

@dataclass
class CaseFile:
    """Case file for client resume management"""
    case_file_id: Optional[str] = None
    client_id: Optional[int] = None
    client_name: str = ""
    client_email: Optional[str] = None
    case_manager: Optional[str] = None
    status: str = 'active'  # active, paused, completed, archived
    priority: str = 'medium'  # low, medium, high, urgent
    goal: Optional[str] = None
    background_notes: Optional[str] = None
    employment_goals: Optional[List[str]] = None
    target_industries: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    resume_versions: Optional[List[ResumeVersion]] = None
    total_applications: int = 0
    interviews_scheduled: int = 0
    job_offers: int = 0

    def __post_init__(self):
        """Initialize empty lists if None"""
        if self.employment_goals is None:
            self.employment_goals = []
        if self.target_industries is None:
            self.target_industries = []
        if self.resume_versions is None:
            self.resume_versions = []

@dataclass
class ClientProgress:
    """Client progress tracking"""
    client_id: int
    case_file_id: str
    total_resumes: int = 0
    active_applications: int = 0
    interviews_this_month: int = 0
    last_resume_update: Optional[datetime] = None
    success_metrics: Optional[Dict[str, Any]] = None
    risk_level: str = 'low'  # low, medium, high
    case_manager_notes: Optional[str] = None

class CaseFileDatabase:
    """Database operations for case file resume management"""
    
    def __init__(self, db_path='jobs.db'):
        self.db_path = db_path
        self.connection = None
    
    def connect(self):
        """Connect to the database"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self._create_tables()
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def _create_tables(self):
        """Create case file tables if they don't exist"""
        # Case files table
        case_files_sql = """
        CREATE TABLE IF NOT EXISTS case_files (
            case_file_id TEXT PRIMARY KEY,
            client_id INTEGER NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT,
            case_manager TEXT,
            status TEXT DEFAULT 'active',
            priority TEXT DEFAULT 'medium',
            goal TEXT,
            background_notes TEXT,
            employment_goals TEXT,
            target_industries TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_activity TEXT,
            total_applications INTEGER DEFAULT 0,
            interviews_scheduled INTEGER DEFAULT 0,
            job_offers INTEGER DEFAULT 0,
            FOREIGN KEY (client_id) REFERENCES clients(client_id)
        );
        """
        
        # Resume versions table
        resume_versions_sql = """
        CREATE TABLE IF NOT EXISTS resume_versions (
            version_id TEXT PRIMARY KEY,
            case_file_id TEXT NOT NULL,
            client_id INTEGER NOT NULL,
            resume_data TEXT,
            template_id TEXT DEFAULT 'classic',
            job_target TEXT,
            version_number INTEGER NOT NULL,
            version_name TEXT NOT NULL,
            html_content TEXT,
            pdf_path TEXT,
            ats_score REAL,
            match_score REAL,
            status TEXT DEFAULT 'draft',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            notes TEXT,
            tailoring_recommendations TEXT,
            FOREIGN KEY (case_file_id) REFERENCES case_files(case_file_id),
            FOREIGN KEY (client_id) REFERENCES clients(client_id)
        );
        """
        
        # Client progress tracking table
        client_progress_sql = """
        CREATE TABLE IF NOT EXISTS client_progress (
            client_id INTEGER PRIMARY KEY,
            case_file_id TEXT NOT NULL,
            total_resumes INTEGER DEFAULT 0,
            active_applications INTEGER DEFAULT 0,
            interviews_this_month INTEGER DEFAULT 0,
            last_resume_update TEXT,
            success_metrics TEXT,
            risk_level TEXT DEFAULT 'low',
            case_manager_notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (case_file_id) REFERENCES case_files(case_file_id),
            FOREIGN KEY (client_id) REFERENCES clients(client_id)
        );
        """
        
        # Case file activities table for audit trail
        case_activities_sql = """
        CREATE TABLE IF NOT EXISTS case_activities (
            activity_id TEXT PRIMARY KEY,
            case_file_id TEXT NOT NULL,
            client_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            description TEXT NOT NULL,
            created_by TEXT,
            created_at TEXT NOT NULL,
            metadata TEXT,
            FOREIGN KEY (case_file_id) REFERENCES case_files(case_file_id),
            FOREIGN KEY (client_id) REFERENCES clients(client_id)
        );
        """
        
        try:
            self.connection.execute(case_files_sql)
            self.connection.execute(resume_versions_sql)
            self.connection.execute(client_progress_sql)
            self.connection.execute(case_activities_sql)
            self.connection.commit()
            logger.info("Case file tables created successfully")
        except Exception as e:
            logger.error(f"Error creating case file tables: {e}")
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[sqlite3.Cursor]:
        """Execute a database query"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            return cursor
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            self.connection.rollback()
            return None
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[sqlite3.Row]:
        """Fetch one row from database"""
        cursor = self.execute_query(query, params)
        return cursor.fetchone() if cursor else None
    
    def fetch_all(self, query: str, params: tuple = None) -> List[sqlite3.Row]:
        """Fetch all rows from database"""
        cursor = self.execute_query(query, params)
        return cursor.fetchall() if cursor else []

class CaseFileManager:
    """Case file management operations"""
    
    def __init__(self, db: CaseFileDatabase):
        self.db = db
    
    def create_case_file(self, case_file: CaseFile) -> Optional[str]:
        """Create a new case file"""
        case_file_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        query = """
        INSERT INTO case_files (
            case_file_id, client_id, client_name, client_email, case_manager,
            status, priority, goal, background_notes, employment_goals,
            target_industries, created_at, updated_at, last_activity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            case_file_id, case_file.client_id, case_file.client_name,
            case_file.client_email, case_file.case_manager, case_file.status,
            case_file.priority, case_file.goal, case_file.background_notes,
            json.dumps(case_file.employment_goals),
            json.dumps(case_file.target_industries),
            now, now, now
        )
        
        cursor = self.db.execute_query(query, params)
        if cursor:
            # Log activity
            self._log_activity(case_file_id, case_file.client_id, 
                             'case_created', 'Case file created', case_file.case_manager)
            return case_file_id
        return None
    
    def get_case_file(self, case_file_id: str) -> Optional[CaseFile]:
        """Get case file by ID"""
        query = "SELECT * FROM case_files WHERE case_file_id = ?"
        row = self.db.fetch_one(query, (case_file_id,))
        
        if row:
            case_file = CaseFile(
                case_file_id=row['case_file_id'],
                client_id=row['client_id'],
                client_name=row['client_name'],
                client_email=row['client_email'],
                case_manager=row['case_manager'],
                status=row['status'],
                priority=row['priority'],
                goal=row['goal'],
                background_notes=row['background_notes'],
                employment_goals=json.loads(row['employment_goals']) if row['employment_goals'] else [],
                target_industries=json.loads(row['target_industries']) if row['target_industries'] else [],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
                last_activity=datetime.fromisoformat(row['last_activity']) if row['last_activity'] else None,
                total_applications=row['total_applications'],
                interviews_scheduled=row['interviews_scheduled'],
                job_offers=row['job_offers']
            )
            
            # Load resume versions
            case_file.resume_versions = self.get_resume_versions(case_file_id)
            return case_file
        return None
    
    def get_case_files_by_client(self, client_id: int) -> List[CaseFile]:
        """Get all case files for a client"""
        query = """
        SELECT * FROM case_files 
        WHERE client_id = ? 
        ORDER BY last_activity DESC
        """
        rows = self.db.fetch_all(query, (client_id,))
        
        case_files = []
        for row in rows:
            case_file = CaseFile(
                case_file_id=row['case_file_id'],
                client_id=row['client_id'],
                client_name=row['client_name'],
                client_email=row['client_email'],
                case_manager=row['case_manager'],
                status=row['status'],
                priority=row['priority'],
                goal=row['goal'],
                background_notes=row['background_notes'],
                employment_goals=json.loads(row['employment_goals']) if row['employment_goals'] else [],
                target_industries=json.loads(row['target_industries']) if row['target_industries'] else [],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
                last_activity=datetime.fromisoformat(row['last_activity']) if row['last_activity'] else None,
                total_applications=row['total_applications'],
                interviews_scheduled=row['interviews_scheduled'],
                job_offers=row['job_offers']
            )
            case_files.append(case_file)
        
        return case_files
    
    def get_all_case_files(self, case_manager: str = None, status: str = None) -> List[CaseFile]:
        """Get all case files with optional filtering"""
        query = "SELECT * FROM case_files WHERE 1=1"
        params = []
        
        if case_manager:
            query += " AND case_manager = ?"
            params.append(case_manager)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY last_activity DESC"
        
        rows = self.db.fetch_all(query, tuple(params))
        
        case_files = []
        for row in rows:
            case_file = CaseFile(
                case_file_id=row['case_file_id'],
                client_id=row['client_id'],
                client_name=row['client_name'],
                client_email=row['client_email'],
                case_manager=row['case_manager'],
                status=row['status'],
                priority=row['priority'],
                goal=row['goal'],
                background_notes=row['background_notes'],
                employment_goals=json.loads(row['employment_goals']) if row['employment_goals'] else [],
                target_industries=json.loads(row['target_industries']) if row['target_industries'] else [],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
                last_activity=datetime.fromisoformat(row['last_activity']) if row['last_activity'] else None,
                total_applications=row['total_applications'],
                interviews_scheduled=row['interviews_scheduled'],
                job_offers=row['job_offers']
            )
            case_files.append(case_file)
        
        return case_files
    
    def update_case_file(self, case_file: CaseFile) -> bool:
        """Update case file"""
        query = """
        UPDATE case_files SET
            client_name = ?, client_email = ?, case_manager = ?, status = ?,
            priority = ?, goal = ?, background_notes = ?, employment_goals = ?,
            target_industries = ?, updated_at = ?, last_activity = ?,
            total_applications = ?, interviews_scheduled = ?, job_offers = ?
        WHERE case_file_id = ?
        """
        
        now = datetime.now().isoformat()
        params = (
            case_file.client_name, case_file.client_email, case_file.case_manager,
            case_file.status, case_file.priority, case_file.goal,
            case_file.background_notes, json.dumps(case_file.employment_goals),
            json.dumps(case_file.target_industries), now, now,
            case_file.total_applications, case_file.interviews_scheduled,
            case_file.job_offers, case_file.case_file_id
        )
        
        cursor = self.db.execute_query(query, params)
        if cursor:
            self._log_activity(case_file.case_file_id, case_file.client_id,
                             'case_updated', 'Case file updated', case_file.case_manager)
            return True
        return False
    
    def _log_activity(self, case_file_id: str, client_id: int, activity_type: str, 
                     description: str, created_by: str = None, metadata: Dict[str, Any] = None):
        """Log case file activity"""
        activity_id = str(uuid.uuid4())
        query = """
        INSERT INTO case_activities (
            activity_id, case_file_id, client_id, activity_type,
            description, created_by, created_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            activity_id, case_file_id, client_id, activity_type,
            description, created_by, datetime.now().isoformat(),
            json.dumps(metadata) if metadata else None
        )
        
        self.db.execute_query(query, params)

class ResumeVersionManager:
    """Resume version management operations"""
    
    def __init__(self, db: CaseFileDatabase):
        self.db = db
    
    def save_resume_version(self, resume_version: ResumeVersion) -> Optional[str]:
        """Save a new resume version"""
        version_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        query = """
        INSERT INTO resume_versions (
            version_id, case_file_id, client_id, resume_data, template_id,
            job_target, version_number, version_name, html_content, pdf_path,
            ats_score, match_score, status, created_by, created_at, updated_at,
            notes, tailoring_recommendations
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            version_id, resume_version.case_file_id, resume_version.client_id,
            json.dumps(resume_version.resume_data) if resume_version.resume_data else None,
            resume_version.template_id,
            json.dumps(resume_version.job_target) if resume_version.job_target else None,
            resume_version.version_number, resume_version.version_name,
            resume_version.html_content, resume_version.pdf_path,
            resume_version.ats_score, resume_version.match_score,
            resume_version.status, resume_version.created_by, now, now,
            resume_version.notes,
            json.dumps(resume_version.tailoring_recommendations) if resume_version.tailoring_recommendations else None
        )
        
        cursor = self.db.execute_query(query, params)
        if cursor:
            # Update case file activity
            case_manager = CaseFileManager(self.db)
            case_manager._log_activity(
                resume_version.case_file_id, resume_version.client_id,
                'resume_created', f'Resume version "{resume_version.version_name}" created',
                resume_version.created_by
            )
            return version_id
        return None
    
    def get_resume_versions(self, case_file_id: str) -> List[ResumeVersion]:
        """Get all resume versions for a case file"""
        query = """
        SELECT * FROM resume_versions 
        WHERE case_file_id = ? 
        ORDER BY version_number DESC, created_at DESC
        """
        rows = self.db.fetch_all(query, (case_file_id,))
        
        versions = []
        for row in rows:
            version = ResumeVersion(
                version_id=row['version_id'],
                case_file_id=row['case_file_id'],
                client_id=row['client_id'],
                resume_data=json.loads(row['resume_data']) if row['resume_data'] else None,
                template_id=row['template_id'],
                job_target=json.loads(row['job_target']) if row['job_target'] else None,
                version_number=row['version_number'],
                version_name=row['version_name'],
                html_content=row['html_content'],
                pdf_path=row['pdf_path'],
                ats_score=row['ats_score'],
                match_score=row['match_score'],
                status=row['status'],
                created_by=row['created_by'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
                notes=row['notes'],
                tailoring_recommendations=json.loads(row['tailoring_recommendations']) if row['tailoring_recommendations'] else None
            )
            versions.append(version)
        
        return versions
    
    def get_resume_version(self, version_id: str) -> Optional[ResumeVersion]:
        """Get specific resume version"""
        query = "SELECT * FROM resume_versions WHERE version_id = ?"
        row = self.db.fetch_one(query, (version_id,))
        
        if row:
            return ResumeVersion(
                version_id=row['version_id'],
                case_file_id=row['case_file_id'],
                client_id=row['client_id'],
                resume_data=json.loads(row['resume_data']) if row['resume_data'] else None,
                template_id=row['template_id'],
                job_target=json.loads(row['job_target']) if row['job_target'] else None,
                version_number=row['version_number'],
                version_name=row['version_name'],
                html_content=row['html_content'],
                pdf_path=row['pdf_path'],
                ats_score=row['ats_score'],
                match_score=row['match_score'],
                status=row['status'],
                created_by=row['created_by'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
                notes=row['notes'],
                tailoring_recommendations=json.loads(row['tailoring_recommendations']) if row['tailoring_recommendations'] else None
            )
        return None
    
    def update_resume_version(self, resume_version: ResumeVersion) -> bool:
        """Update resume version"""
        query = """
        UPDATE resume_versions SET
            resume_data = ?, template_id = ?, job_target = ?, version_name = ?,
            html_content = ?, pdf_path = ?, ats_score = ?, match_score = ?,
            status = ?, updated_at = ?, notes = ?, tailoring_recommendations = ?
        WHERE version_id = ?
        """
        
        params = (
            json.dumps(resume_version.resume_data) if resume_version.resume_data else None,
            resume_version.template_id,
            json.dumps(resume_version.job_target) if resume_version.job_target else None,
            resume_version.version_name, resume_version.html_content,
            resume_version.pdf_path, resume_version.ats_score,
            resume_version.match_score, resume_version.status,
            datetime.now().isoformat(), resume_version.notes,
            json.dumps(resume_version.tailoring_recommendations) if resume_version.tailoring_recommendations else None,
            resume_version.version_id
        )
        
        cursor = self.db.execute_query(query, params)
        return cursor is not None
    
    def get_next_version_number(self, case_file_id: str) -> int:
        """Get next version number for case file"""
        query = """
        SELECT MAX(version_number) as max_version 
        FROM resume_versions 
        WHERE case_file_id = ?
        """
        row = self.db.fetch_one(query, (case_file_id,))
        
        if row and row['max_version']:
            return row['max_version'] + 1
        return 1

class CaseFileResumeIntegration:
    """Main integration class for case file resume management"""
    
    def __init__(self, db_path='jobs.db'):
        self.db = CaseFileDatabase(db_path)
        self.case_manager = CaseFileManager(self.db)
        self.version_manager = ResumeVersionManager(self.db)
    
    def connect(self):
        """Connect to database"""
        return self.db.connect()
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def create_client_case(self, client_id: int, client_name: str, client_email: str = None,
                          case_manager: str = None, goal: str = None) -> Optional[str]:
        """Create a new case file for a client"""
        case_file = CaseFile(
            client_id=client_id,
            client_name=client_name,
            client_email=client_email,
            case_manager=case_manager,
            goal=goal or "Develop professional resume and secure employment"
        )
        
        return self.case_manager.create_case_file(case_file)
    
    def save_resume_to_case(self, case_file_id: str, client_id: int, resume_data: Dict[str, Any],
                           template_id: str, job_target: Dict[str, Any] = None,
                           html_content: str = None, pdf_path: str = None,
                           version_name: str = None, created_by: str = None) -> Optional[str]:
        """Save a resume version to a case file"""
        
        # Get next version number
        version_number = self.version_manager.get_next_version_number(case_file_id)
        
        # Generate version name if not provided
        if not version_name:
            if job_target and job_target.get('title'):
                version_name = f"Resume v{version_number} - {job_target['title']}"
            else:
                version_name = f"Resume v{version_number}"
        
        resume_version = ResumeVersion(
            case_file_id=case_file_id,
            client_id=client_id,
            resume_data=resume_data,
            template_id=template_id,
            job_target=job_target,
            version_number=version_number,
            version_name=version_name,
            html_content=html_content,
            pdf_path=pdf_path,
            created_by=created_by,
            status='draft'
        )
        
        return self.version_manager.save_resume_version(resume_version)
    
    def get_client_resume_history(self, client_id: int) -> List[Dict[str, Any]]:
        """Get complete resume history for a client"""
        case_files = self.case_manager.get_case_files_by_client(client_id)
        
        history = []
        for case_file in case_files:
            versions = self.version_manager.get_resume_versions(case_file.case_file_id)
            
            case_data = {
                'case_file': asdict(case_file),
                'resume_versions': [asdict(version) for version in versions]
            }
            history.append(case_data)
        
        return history
    
    def get_case_manager_dashboard_data(self, case_manager: str = None) -> Dict[str, Any]:
        """Get dashboard data for case manager"""
        case_files = self.case_manager.get_all_case_files(case_manager=case_manager)
        
        # Calculate summary metrics
        total_cases = len(case_files)
        active_cases = len([cf for cf in case_files if cf.status == 'active'])
        high_priority = len([cf for cf in case_files if cf.priority == 'high'])
        
        # Recent activity
        recent_activity = []
        for case_file in case_files[:10]:  # Top 10 most recent
            versions = self.version_manager.get_resume_versions(case_file.case_file_id)
            if versions:
                recent_activity.append({
                    'case_file_id': case_file.case_file_id,
                    'client_name': case_file.client_name,
                    'last_activity': case_file.last_activity,
                    'latest_version': versions[0].version_name if versions else None
                })
        
        return {
            'summary': {
                'total_cases': total_cases,
                'active_cases': active_cases,
                'high_priority_cases': high_priority,
                'completed_cases': len([cf for cf in case_files if cf.status == 'completed'])
            },
            'case_files': [asdict(cf) for cf in case_files],
            'recent_activity': recent_activity
        }
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

# Example usage and testing
if __name__ == "__main__":
    # Test the case file integration
    with CaseFileResumeIntegration() as case_integration:
        
        print("Testing Case File Resume Integration...")
        
        # Create a test case file
        case_file_id = case_integration.create_client_case(
            client_id=1,
            client_name="John Smith",
            client_email="john.smith@email.com",
            case_manager="Case Manager A",
            goal="Secure warehouse employment with background-friendly employer"
        )
        
        if case_file_id:
            print(f"✅ Created case file: {case_file_id}")
            
            # Save test resume version
            test_resume_data = {
                'full_name': 'John Smith',
                'email': 'john.smith@email.com',
                'phone': '555-123-4567',
                'summary': 'Reliable warehouse worker seeking stable employment',
                'work_experience': [
                    {
                        'title': 'Warehouse Associate',
                        'company': 'ABC Logistics',
                        'start_date': '2020-01',
                        'end_date': '2022-12',
                        'description': 'Handled inventory and shipping operations'
                    }
                ],
                'technical_skills': ['Forklift Operation', 'Inventory Management'],
                'soft_skills': ['Teamwork', 'Reliability']
            }
            
            test_job_target = {
                'title': 'Warehouse Worker',
                'company': 'XYZ Distribution',
                'industry': 'warehouse'
            }
            
            version_id = case_integration.save_resume_to_case(
                case_file_id=case_file_id,
                client_id=1,
                resume_data=test_resume_data,
                template_id='warehouse',
                job_target=test_job_target,
                version_name="Warehouse Position - XYZ Distribution",
                created_by="Case Manager A"
            )
            
            if version_id:
                print(f"✅ Saved resume version: {version_id}")
                
                # Test getting client history
                history = case_integration.get_client_resume_history(1)
                print(f"✅ Retrieved client history: {len(history)} case files")
                
                # Test dashboard data
                dashboard_data = case_integration.get_case_manager_dashboard_data("Case Manager A")
                print(f"✅ Dashboard data: {dashboard_data['summary']['total_cases']} total cases")
                
                print("✅ Case File Resume Integration working correctly!")
            else:
                print("❌ Failed to save resume version")
        else:
            print("❌ Failed to create case file")