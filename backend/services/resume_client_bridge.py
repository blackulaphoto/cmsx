#!/usr/bin/env python3
"""
Resume Client Bridge Service
Bridges the resume system to the main client database without modifying protected resume routes
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import sys

# Add paths for imports
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

# Import the main database access layer
from shared.database.new_access_layer import (
    db_access, 
    core_clients_service
)

logger = logging.getLogger(__name__)


def _parse_json_field(value, default):
    """Parse JSON-backed columns while tolerating legacy plain-text values."""
    if value in (None, ""):
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default

class ResumeClientBridge:
    """
    Bridge service that provides resume-compatible client access using the main database
    """
    
    def __init__(self):
        self.core_clients = core_clients_service
        self.module = 'employment'  # Resume system uses employment module permissions
        
    def get_available_clients(self):
        """Get all clients in resume-compatible format"""
        try:
            # Get clients from main database
            clients = self.core_clients.get_all_clients(self.module)
            
            # Convert to resume-compatible format
            resume_clients = []
            for client in clients:
                resume_client = type('Client', (), {
                    'client_id': client.get('client_id'),
                    'first_name': client.get('first_name', ''),
                    'last_name': client.get('last_name', ''),
                    'phone': client.get('phone', ''),
                    'email': client.get('email', ''),
                    'address': client.get('address', '')
                })()
                resume_clients.append(resume_client)
                
            logger.info("Retrieved %s clients from main database", len(resume_clients))
            return resume_clients
            
        except Exception as e:
            logger.error("Failed to get clients from main database: %s", e)
            # Return empty list instead of crashing
            return []
    
    def get_client_by_id(self, client_id: str):
        """Get specific client by ID in resume-compatible format"""
        try:
            # Get client from main database
            client = self.core_clients.get_client(client_id, self.module)
            
            if not client:
                return None
                
            # Convert to resume-compatible format
            resume_client = type('Client', (), {
                'client_id': client.get('client_id'),
                'first_name': client.get('first_name', ''),
                'last_name': client.get('last_name', ''),
                'phone': client.get('phone', ''),
                'email': client.get('email', ''),
                'address': client.get('address', '')
            })()
            
            logger.info("Retrieved client %s from main database", client_id)
            return resume_client
            
        except Exception as e:
            logger.error("Failed to get client %s from main database: %s", client_id, e)
            return None

class ResumeDatabase:
    """
    Resume database that uses the main client database for client data
    and employment database for resume-specific functionality
    """
    
    def __init__(self):
        self.core_clients = ResumeClientBridge()
        self.profiles = ResumeProfiles(db_access)
        self.resumes = ResumeStorage(db_access)
        self.applications = ResumeApplications(db_access)
        
    def connect(self):
        """Connection method for compatibility"""
        logger.info("Resume database connected to main client database and employment database")

# Resume-specific data classes (using employment database for resume storage)
class ResumeProfiles:
    """Resume profiles using employment database"""
    
    def __init__(self, db_access):
        self.db = db_access
        self.module = 'employment'
    
    def get_profile_by_client(self, client_id):
        """Get employment profile for client"""
        try:
            with self.db.get_connection('employment', self.module) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM client_employment_profiles WHERE client_id = ?', (client_id,))
                row = cursor.fetchone()
                
                if row:
                    profile_data = dict(row)
                    return type('Profile', (), {
                        'profile_id': profile_data.get('profile_id'),
                        'client_id': client_id,
                        'career_objective': profile_data.get('career_objective', ''),
                        'work_history': _parse_json_field(profile_data.get('work_history'), []),
                        'skills': _parse_json_field(profile_data.get('skills'), []),
                        'education': _parse_json_field(profile_data.get('education'), []),
                        'certifications': _parse_json_field(profile_data.get('certifications'), []),
                        'professional_references': _parse_json_field(profile_data.get('professional_references'), []),
                        'preferred_industries': _parse_json_field(profile_data.get('preferred_industries'), []),
                    })()
                else:
                    # No stored profile: return None so writers take the CREATE
                    # branch (an UPDATE against a phantom profile_id matches zero
                    # rows and silently drops the data) and so reads never serve
                    # fabricated placeholder resume content.
                    return None
        except Exception as e:
            logger.error(f"Error getting profile for {client_id}: {e}")
            return None
    
    def create_profile(self, profile):
        """Create employment profile"""
        profile_id = getattr(profile, 'profile_id', None) or f'profile-{profile.client_id}'
        current_time = datetime.now().isoformat()
        try:
            with self.db.get_connection('employment', self.module) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO client_employment_profiles (
                        profile_id, client_id, work_history, skills, education,
                        preferred_industries, background_friendly_only, created_at,
                        certifications, career_objective, updated_at, professional_references
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        profile_id,
                        profile.client_id,
                        json.dumps(getattr(profile, 'work_history', []) or []),
                        json.dumps(getattr(profile, 'skills', []) or []),
                        json.dumps(getattr(profile, 'education', []) or []),
                        json.dumps(getattr(profile, 'preferred_industries', []) or []),
                        int(bool(getattr(profile, 'background_friendly_only', True))),
                        current_time,
                        json.dumps(getattr(profile, 'certifications', []) or []),
                        getattr(profile, 'career_objective', ''),
                        current_time,
                        json.dumps(getattr(profile, 'professional_references', []) or []),
                    ),
                )
                conn.commit()
            return profile_id
        except Exception as e:
            logger.error("Error creating profile for %s: %s", profile.client_id, e)
            return None
    
    def update_profile(self, profile):
        """Update employment profile"""
        profile_id = getattr(profile, 'profile_id', None) or f'profile-{profile.client_id}'
        current_time = datetime.now().isoformat()
        try:
            with self.db.get_connection('employment', self.module) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    UPDATE client_employment_profiles
                    SET work_history = ?, skills = ?, education = ?, preferred_industries = ?,
                        background_friendly_only = ?, certifications = ?, career_objective = ?,
                        updated_at = ?, professional_references = ?
                    WHERE profile_id = ? AND client_id = ?
                    ''',
                    (
                        json.dumps(getattr(profile, 'work_history', []) or []),
                        json.dumps(getattr(profile, 'skills', []) or []),
                        json.dumps(getattr(profile, 'education', []) or []),
                        json.dumps(getattr(profile, 'preferred_industries', []) or []),
                        int(bool(getattr(profile, 'background_friendly_only', True))),
                        json.dumps(getattr(profile, 'certifications', []) or []),
                        getattr(profile, 'career_objective', ''),
                        current_time,
                        json.dumps(getattr(profile, 'professional_references', []) or []),
                        profile_id,
                        profile.client_id,
                    ),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error("Error updating profile for %s: %s", profile.client_id, e)
            return False

class ResumeStorage:
    """Resume storage using employment database"""
    
    def __init__(self, db_access):
        self.db = db_access
        self.module = 'employment'
    
    def get_resumes_by_client(self, client_id):
        """Get resumes for client from employment database"""
        try:
            with self.db.get_connection('employment', self.module) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM resumes WHERE client_id = ?', (client_id,))
                rows = cursor.fetchall()
                
                resumes = []
                for row in rows:
                    resume_data = dict(row)
                    resume = type('Resume', (), {
                        'resume_id': resume_data.get('resume_id'),
                        'client_id': client_id,
                        'resume_title': resume_data.get('resume_title', 'Professional Resume'),
                        'template_type': resume_data.get('template_type', 'classic'),
                        'content': resume_data.get('content', '{}'),
                        'ats_score': resume_data.get('ats_score', 75),
                        'created_at': resume_data.get('created_at', '2024-01-01T00:00:00'),
                        'updated_at': resume_data.get('updated_at', resume_data.get('created_at', '2024-01-01T00:00:00')),
                        'is_active': bool(resume_data.get('is_active', True)),
                        'pdf_path': resume_data.get('pdf_path')
                    })()
                    resumes.append(resume)
                return resumes
                
        except Exception as e:
            logger.error(f"Error getting resumes for {client_id}: {e}")
            return []
    
    def get_resume_by_id(self, resume_id):
        """Get specific resume by ID"""
        try:
            with self.db.get_connection('employment', self.module) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM resumes WHERE resume_id = ?', (resume_id,))
                row = cursor.fetchone()
                
                if row:
                    resume_data = dict(row)
                    return type('Resume', (), {
                        'resume_id': resume_data.get('resume_id'),
                        'client_id': resume_data.get('client_id'),
                        'resume_title': resume_data.get('resume_title', 'Professional Resume'),
                        'template_type': resume_data.get('template_type', 'classic'),
                        'content': resume_data.get('content', '{}'),
                        'ats_score': resume_data.get('ats_score', 75),
                        'created_at': resume_data.get('created_at', '2024-01-01T00:00:00'),
                        'updated_at': resume_data.get('updated_at', resume_data.get('created_at', '2024-01-01T00:00:00')),
                        'is_active': bool(resume_data.get('is_active', True)),
                        'pdf_path': resume_data.get('pdf_path')
                    })()
                return None
                    
        except Exception as e:
            logger.error(f"Error getting resume {resume_id}: {e}")
            return None
    
    def create_resume(self, resume):
        """Create new resume"""
        resume_id = getattr(resume, 'resume_id', None) or f'resume-{resume.client_id}-{int(datetime.now().timestamp())}'
        current_time = datetime.now().isoformat()
        try:
            with self.db.get_connection('employment', self.module) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO resumes (
                        resume_id, client_id, template_type, content, pdf_path,
                        created_at, profile_id, resume_title, ats_score, is_active, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        resume_id,
                        resume.client_id,
                        getattr(resume, 'template_type', 'classic'),
                        getattr(resume, 'content', '{}'),
                        getattr(resume, 'pdf_path', None),
                        current_time,
                        getattr(resume, 'profile_id', None),
                        getattr(resume, 'resume_title', 'Professional Resume'),
                        getattr(resume, 'ats_score', 75),
                        int(bool(getattr(resume, 'is_active', True))),
                        current_time,
                    ),
                )
                conn.commit()
            return resume_id
        except Exception as e:
            logger.error("Error creating resume for %s: %s", resume.client_id, e)
            return None
    
    def update_resume(self, resume):
        """Update existing resume"""
        current_time = datetime.now().isoformat()
        try:
            with self.db.get_connection('employment', self.module) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    UPDATE resumes
                    SET template_type = ?, content = ?, pdf_path = ?, profile_id = ?,
                        resume_title = ?, ats_score = ?, is_active = ?, updated_at = ?
                    WHERE resume_id = ? AND client_id = ?
                    ''',
                    (
                        getattr(resume, 'template_type', 'classic'),
                        getattr(resume, 'content', '{}'),
                        getattr(resume, 'pdf_path', None),
                        getattr(resume, 'profile_id', None),
                        getattr(resume, 'resume_title', 'Professional Resume'),
                        getattr(resume, 'ats_score', 75),
                        int(bool(getattr(resume, 'is_active', True))),
                        current_time,
                        resume.resume_id,
                        resume.client_id,
                    ),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error("Error updating resume %s: %s", getattr(resume, 'resume_id', 'unknown'), e)
            return False

class ResumeApplications:
    """Resume applications using employment database"""
    
    def __init__(self, db_access):
        self.db = db_access
        self.module = 'employment'
    
    def get_applications_by_client(self, client_id):
        """Get job applications for client"""
        try:
            with self.db.get_connection('employment', self.module) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM job_applications WHERE client_id = ?', (client_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting applications for {client_id}: {e}")
            return []
    
    def create_application(self, application):
        """Create job application"""
        application_id = getattr(application, 'application_id', None) or f'app-{application.client_id}-{int(datetime.now().timestamp())}'
        current_time = datetime.now().isoformat()
        try:
            with self.db.get_connection('employment', self.module) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO job_applications (
                        application_id, client_id, resume_id, job_title, company_name,
                        job_description, application_status, applied_date, follow_up_date, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        application_id,
                        getattr(application, 'client_id', ''),
                        getattr(application, 'resume_id', None),
                        getattr(application, 'job_title', ''),
                        getattr(application, 'company_name', ''),
                        getattr(application, 'job_description', ''),
                        getattr(application, 'application_status', 'submitted'),
                        getattr(application, 'applied_date', current_time[:10]),
                        getattr(application, 'follow_up_date', None),
                        getattr(application, 'notes', None),
                        current_time,
                    ),
                )
                conn.commit()
                return application_id
        except Exception as e:
            logger.error("Error creating job application for %s: %s", getattr(application, 'client_id', 'unknown'), e)
            return None

# Global instance
resume_database = ResumeDatabase()

def get_resume_database():
    """Get the resume database instance that uses main client database"""
    return resume_database
