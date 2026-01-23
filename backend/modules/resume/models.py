# ================================================================
# @generated
# @preserve
# @readonly
# DO NOT MODIFY THIS FILE
# Purpose: This module/component/route is production-approved.
# Any changes must be approved by the lead developer.
#
# WARNING: Modifying this file may break the application.
# ================================================================

#!/usr/bin/env python3
"""
Resume Builder Models - Corrected Architecture
Aligned with 9-database architecture using employment.db and core_clients.db
"""

import sqlite3
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ClientEmploymentProfile:
    """Client employment profile model for employment.db"""
    profile_id: Optional[str] = None
    client_id: str = ""
    work_history: List[Dict[str, Any]] = None
    skills: List[Dict[str, Any]] = None
    education: List[Dict[str, Any]] = None
    certifications: List[Dict[str, Any]] = None
    professional_references: List[Dict[str, Any]] = None
    career_objective: str = ""
    preferred_industries: List[str] = None
    background_friendly_only: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize empty lists if None"""
        if self.work_history is None:
            self.work_history = []
        if self.skills is None:
            self.skills = []
        if self.education is None:
            self.education = []
        if self.certifications is None:
            self.certifications = []
        if self.professional_references is None:
            self.professional_references = []
        if self.preferred_industries is None:
            self.preferred_industries = []
        if self.profile_id is None:
            self.profile_id = str(uuid.uuid4())

@dataclass
class Resume:
    """Resume model for employment.db"""
    resume_id: Optional[str] = None
    client_id: str = ""
    profile_id: Optional[str] = None
    template_type: str = "classic"
    resume_title: str = ""
    content: str = ""  # JSON formatted resume data
    pdf_path: Optional[str] = None
    ats_score: Optional[int] = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.resume_id is None:
            self.resume_id = str(uuid.uuid4())

@dataclass
class JobApplication:
    """Job application model for employment.db"""
    application_id: Optional[str] = None
    client_id: str = ""
    resume_id: Optional[str] = None
    job_title: str = ""
    company_name: str = ""
    job_description: str = ""
    application_status: str = "draft"
    applied_date: Optional[str] = None
    follow_up_date: Optional[str] = None
    notes: str = ""
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.application_id is None:
            self.application_id = str(uuid.uuid4())

@dataclass
class ResumeTailoring:
    """Resume tailoring history model for employment.db"""
    tailoring_id: Optional[str] = None
    resume_id: str = ""
    job_application_id: Optional[str] = None
    original_content: str = ""
    tailored_content: str = ""
    optimization_type: str = "ats_optimization"
    match_score: Optional[float] = 0.0
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.tailoring_id is None:
            self.tailoring_id = str(uuid.uuid4())

@dataclass
class Client:
    """Client model from core_clients.db (read-only)"""
    client_id: str = ""
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    case_status: str = ""

class DatabaseManager:
    """Database manager for employment.db operations"""
    
    def __init__(self, db_path='databases/employment.db'):
        self.db_path = db_path
        self.connection = None
    
    def connect(self):
        """Connect to the database"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
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

class CoreClientsManager:
    """Manager for reading from core_clients.db"""
    
    def __init__(self, db_path='databases/core_clients.db'):
        self.db_path = db_path
    
    def get_available_clients(self) -> List[Client]:
        """Get all active clients from core_clients.db with resume counts"""
        try:
            # First get clients from core_clients.db
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
            SELECT client_id, first_name, last_name, phone, email, address, case_status
            FROM clients 
            WHERE case_status = 'active'
            ORDER BY last_name, first_name
            """
            
            rows = cursor.execute(query).fetchall()
            conn.close()
            
            # Now get resume counts from employment.db
            employment_conn = sqlite3.connect('databases/employment.db')
            employment_cursor = employment_conn.cursor()
            
            clients = []
            for row in rows:
                # Get resume count for this client
                resume_count_query = """
                SELECT COUNT(*) as resume_count 
                FROM resumes 
                WHERE client_id = ? AND is_active = 1
                """
                resume_count = employment_cursor.execute(resume_count_query, (row['client_id'],)).fetchone()[0]
                
                client = Client(
                    client_id=row['client_id'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    phone=row['phone'] or '',
                    email=row['email'] or '',
                    address=row['address'] or '',
                    case_status=row['case_status']
                )
                # Add resume count as additional attribute
                client.active_resumes = resume_count
                client.has_resume = resume_count > 0
                
                clients.append(client)
            
            employment_conn.close()
            return clients
            
        except Exception as e:
            logger.error(f"Error getting clients with resume counts: {e}")
            return []
    
    def get_client_by_id(self, client_id: str) -> Optional[Client]:
        """Get specific client from core_clients.db"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
            SELECT client_id, first_name, last_name, phone, email, address, case_status
            FROM clients 
            WHERE client_id = ?
            """
            
            row = cursor.execute(query, (client_id,)).fetchone()
            conn.close()
            
            if row:
                return Client(
                    client_id=row['client_id'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    phone=row['phone'] or '',
                    email=row['email'] or '',
                    address=row['address'] or '',
                    case_status=row['case_status']
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting client {client_id} from core_clients.db: {e}")
            return None

class EmploymentProfileManager:
    """Manager for client employment profiles in employment.db"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_profile(self, profile: ClientEmploymentProfile) -> Optional[str]:
        """Create a new employment profile"""
        query = """
        INSERT INTO client_employment_profiles 
        (profile_id, client_id, work_history, skills, education, certifications, 
         professional_references, career_objective, preferred_industries, background_friendly_only, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        now = datetime.now()
        params = (
            profile.profile_id,
            profile.client_id,
            json.dumps(profile.work_history),
            json.dumps(profile.skills),
            json.dumps(profile.education),
            json.dumps(profile.certifications),
            json.dumps(profile.professional_references),
            profile.career_objective,
            json.dumps(profile.preferred_industries),
            profile.background_friendly_only,
            now,
            now
        )
        
        cursor = self.db.execute_query(query, params)
        return profile.profile_id if cursor else None
    
    def get_profile_by_client(self, client_id: str) -> Optional[ClientEmploymentProfile]:
        """Get employment profile by client ID"""
        query = """
        SELECT * FROM client_employment_profiles 
        WHERE client_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        row = self.db.fetch_one(query, (client_id,))
        
        if row:
            return ClientEmploymentProfile(
                profile_id=row['profile_id'],
                client_id=row['client_id'],
                work_history=json.loads(row['work_history']) if row['work_history'] else [],
                skills=json.loads(row['skills']) if row['skills'] else [],
                education=json.loads(row['education']) if row['education'] else [],
                certifications=json.loads(row['certifications']) if row['certifications'] else [],
                professional_references=json.loads(row['professional_references']) if row['professional_references'] else [],
                career_objective=row['career_objective'] or '',
                preferred_industries=json.loads(row['preferred_industries']) if row['preferred_industries'] else [],
                background_friendly_only=bool(row['background_friendly_only']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        return None
    
    def update_profile(self, profile: ClientEmploymentProfile) -> bool:
        """Update employment profile"""
        query = """
        UPDATE client_employment_profiles 
        SET work_history = ?, skills = ?, education = ?, certifications = ?, professional_references = ?,
            career_objective = ?, preferred_industries = ?, background_friendly_only = ?,
            updated_at = ?
        WHERE profile_id = ?
        """
        
        params = (
            json.dumps(profile.work_history),
            json.dumps(profile.skills),
            json.dumps(profile.education),
            json.dumps(profile.certifications),
            json.dumps(profile.professional_references),
            profile.career_objective,
            json.dumps(profile.preferred_industries),
            profile.background_friendly_only,
            datetime.now(),
            profile.profile_id
        )
        
        cursor = self.db.execute_query(query, params)
        return cursor is not None

class ResumeManager:
    """Manager for resumes in employment.db"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_resume(self, resume: Resume) -> Optional[str]:
        """Create a new resume"""
        query = """
        INSERT INTO resumes 
        (resume_id, client_id, profile_id, template_type, resume_title, 
         content, pdf_path, ats_score, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        now = datetime.now()
        params = (
            resume.resume_id,
            resume.client_id,
            resume.profile_id,
            resume.template_type,
            resume.resume_title,
            resume.content,
            resume.pdf_path,
            resume.ats_score,
            resume.is_active,
            now,
            now
        )
        
        cursor = self.db.execute_query(query, params)
        return resume.resume_id if cursor else None
    
    def get_resume_by_id(self, resume_id: str) -> Optional[Resume]:
        """Get resume by ID"""
        query = "SELECT * FROM resumes WHERE resume_id = ?"
        row = self.db.fetch_one(query, (resume_id,))
        
        if row:
            return Resume(
                resume_id=row['resume_id'],
                client_id=row['client_id'],
                profile_id=row['profile_id'],
                template_type=row['template_type'],
                resume_title=row['resume_title'],
                content=row['content'],
                pdf_path=row['pdf_path'],
                ats_score=row['ats_score'],
                is_active=bool(row['is_active']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        return None
    
    def get_resumes_by_client(self, client_id: str) -> List[Resume]:
        """Get all resumes for a client"""
        query = """
        SELECT * FROM resumes 
        WHERE client_id = ? AND is_active = 1
        ORDER BY created_at DESC
        """
        
        rows = self.db.fetch_all(query, (client_id,))
        resumes = []
        
        for row in rows:
            resumes.append(Resume(
                resume_id=row['resume_id'],
                client_id=row['client_id'],
                profile_id=row['profile_id'],
                template_type=row['template_type'],
                resume_title=row['resume_title'],
                content=row['content'],
                pdf_path=row['pdf_path'],
                ats_score=row['ats_score'],
                is_active=bool(row['is_active']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ))
        
        return resumes
    
    def update_resume(self, resume: Resume) -> bool:
        """Update resume"""
        query = """
        UPDATE resumes 
        SET profile_id = ?, template_type = ?, resume_title = ?, content = ?,
            pdf_path = ?, ats_score = ?, updated_at = ?
        WHERE resume_id = ?
        """
        
        params = (
            resume.profile_id,
            resume.template_type,
            resume.resume_title,
            resume.content,
            resume.pdf_path,
            resume.ats_score,
            datetime.now(),
            resume.resume_id
        )
        
        cursor = self.db.execute_query(query, params)
        return cursor is not None
    
    def delete_resume(self, resume_id: str) -> bool:
        """Soft delete resume (set is_active = 0)"""
        query = "UPDATE resumes SET is_active = 0, updated_at = ? WHERE resume_id = ?"
        cursor = self.db.execute_query(query, (datetime.now(), resume_id))
        return cursor is not None

class JobApplicationManager:
    """Manager for job applications in employment.db"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_application(self, application: JobApplication) -> Optional[str]:
        """Create a new job application"""
        query = """
        INSERT INTO job_applications 
        (application_id, client_id, resume_id, job_title, company_name, 
         job_description, application_status, applied_date, follow_up_date, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            application.application_id,
            application.client_id,
            application.resume_id,
            application.job_title,
            application.company_name,
            application.job_description,
            application.application_status,
            application.applied_date,
            application.follow_up_date,
            application.notes,
            datetime.now()
        )
        
        cursor = self.db.execute_query(query, params)
        return application.application_id if cursor else None
    
    def get_applications_by_client(self, client_id: str) -> List[JobApplication]:
        """Get all job applications for a client"""
        query = """
        SELECT * FROM job_applications 
        WHERE client_id = ?
        ORDER BY created_at DESC
        """
        
        rows = self.db.fetch_all(query, (client_id,))
        applications = []
        
        for row in rows:
            applications.append(JobApplication(
                application_id=row['application_id'],
                client_id=row['client_id'],
                resume_id=row['resume_id'],
                job_title=row['job_title'],
                company_name=row['company_name'],
                job_description=row['job_description'],
                application_status=row['application_status'],
                applied_date=row['applied_date'],
                follow_up_date=row['follow_up_date'],
                notes=row['notes'],
                created_at=row['created_at']
            ))
        
        return applications

# Main database interface
class EmploymentDatabase:
    """Main database interface for Resume Builder functionality"""
    
    def __init__(self, employment_db_path='databases/employment.db', core_clients_db_path='databases/core_clients.db'):
        self.db_manager = DatabaseManager(employment_db_path)
        self.core_clients = CoreClientsManager(core_clients_db_path)
        self.profiles = EmploymentProfileManager(self.db_manager)
        self.resumes = ResumeManager(self.db_manager)
        self.applications = JobApplicationManager(self.db_manager)
    
    def connect(self):
        """Connect to employment database"""
        return self.db_manager.connect()
    
    def close(self):
        """Close database connection"""
        self.db_manager.close()
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

# Example usage and testing
if __name__ == "__main__":
    # Test the corrected database models
    with EmploymentDatabase() as db:
        # Test client retrieval from core_clients.db
        clients = db.core_clients.get_available_clients()
        print(f"Found {len(clients)} active clients")
        
        if clients:
            test_client = clients[0]
            print(f"Test client: {test_client.first_name} {test_client.last_name}")
            
            # Test employment profile creation
            profile = ClientEmploymentProfile(
                client_id=test_client.client_id,
                career_objective="Seeking employment in warehouse operations",
                work_history=[
                    {
                        "job_title": "Warehouse Associate",
                        "company": "ABC Logistics",
                        "start_date": "2020-01",
                        "end_date": "2022-12",
                        "description": "Managed inventory and shipping operations"
                    }
                ],
                skills=[
                    {
                        "category": "Technical Skills",
                        "skill_list": ["Forklift Operation", "Inventory Management", "Shipping Software"]
                    }
                ]
            )
            
            profile_id = db.profiles.create_profile(profile)
            print(f"Created employment profile: {profile_id}")
            
            # Test resume creation
            resume = Resume(
                client_id=test_client.client_id,
                profile_id=profile_id,
                template_type="warehouse",
                resume_title="Warehouse Operations Resume",
                content=json.dumps({"test": "content"}),
                ats_score=75
            )
            
            resume_id = db.resumes.create_resume(resume)
            print(f"Created resume: {resume_id}")
            
            print("✅ Corrected Resume Builder models working correctly!")