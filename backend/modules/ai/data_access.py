"""
Platform Data Access Layer for AI Assistant
Provides unified access to all platform data sources
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os

logger = logging.getLogger(__name__)

class PlatformDataAccess:
    """Unified data access layer for AI assistant"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.databases = {
            'case_management': os.path.join(self.base_dir, 'databases', 'case_manager.db'),
            'services': os.path.join(self.base_dir, 'databases', 'services.db'),
            'housing': os.path.join(self.base_dir, 'databases', 'housing_resources.db'),
            'jobs': os.path.join(self.base_dir, 'databases', 'case_manager.db'),  # Jobs likely in main DB
            'resumes': os.path.join(self.base_dir, 'databases', 'resumes.db')
        }
        
        # Initialize database connections
        self._init_databases()
    
    def _init_databases(self):
        """Initialize database connections and create tables if needed"""
        try:
            # Ensure databases directory exists
            db_dir = os.path.join(self.base_dir, 'databases')
            os.makedirs(db_dir, exist_ok=True)
            
            # Test connections
            for db_name, db_path in self.databases.items():
                try:
                    conn = sqlite3.connect(db_path)
                    conn.close()
                    logger.info(f"Database connection verified: {db_name}")
                except Exception as e:
                    logger.warning(f"Database connection issue for {db_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error initializing databases: {e}")
    
    def _execute_query(self, db_name: str, query: str, params: tuple = ()) -> List[Dict]:
        """Execute query on specified database"""
        try:
            db_path = self.databases.get(db_name)
            if not db_path or not os.path.exists(db_path):
                logger.warning(f"Database not found: {db_name}")
                return []
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            cursor = conn.cursor()
            
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Database query error in {db_name}: {e}")
            return []
    
    # Client Information Methods
    def get_client_info(self, client_identifier: str) -> Dict[str, Any]:
        """Get comprehensive client information"""
        try:
            # Search by name or ID
            query = """
                SELECT * FROM clients 
                WHERE id = ? OR name LIKE ? OR email LIKE ?
                LIMIT 1
            """
            
            results = self._execute_query(
                'case_management', 
                query, 
                (client_identifier, f'%{client_identifier}%', f'%{client_identifier}%')
            )
            
            if not results:
                return {'error': f'Client not found: {client_identifier}'}
            
            client = results[0]
            
            # Get related data
            client_data = {
                'basic_info': client,
                'referrals': self.get_client_referrals(client['id']),
                'tasks': self.get_client_tasks(client['id']),
                'appointments': self.get_client_appointments(client['id']),
                'documents': self.get_client_documents(client['id']),
                'notes': self.get_client_notes(client['id']),
                'resumes': self.get_client_resumes(client['id'])
            }
            
            return client_data
            
        except Exception as e:
            logger.error(f"Error getting client info: {e}")
            return {'error': f'Failed to retrieve client information: {str(e)}'}
    
    def get_client_referrals(self, client_id: str) -> List[Dict]:
        """Get client referrals"""
        query = """
            SELECT * FROM referrals 
            WHERE client_id = ? 
            ORDER BY created_date DESC
        """
        return self._execute_query('case_management', query, (client_id,))
    
    def get_client_tasks(self, client_id: str) -> List[Dict]:
        """Get client tasks"""
        query = """
            SELECT * FROM tasks 
            WHERE client_id = ? 
            ORDER BY due_date ASC
        """
        return self._execute_query('case_management', query, (client_id,))
    
    def get_client_appointments(self, client_id: str) -> List[Dict]:
        """Get client appointments"""
        query = """
            SELECT * FROM appointments 
            WHERE client_id = ? 
            ORDER BY appointment_date DESC
        """
        return self._execute_query('case_management', query, (client_id,))
    
    def get_client_documents(self, client_id: str) -> List[Dict]:
        """Get client documents"""
        query = """
            SELECT * FROM documents 
            WHERE client_id = ? 
            ORDER BY upload_date DESC
        """
        return self._execute_query('case_management', query, (client_id,))
    
    def get_client_notes(self, client_id: str) -> List[Dict]:
        """Get client case notes"""
        query = """
            SELECT * FROM case_notes 
            WHERE client_id = ? 
            ORDER BY created_date DESC
            LIMIT 10
        """
        return self._execute_query('case_management', query, (client_id,))
    
    def get_client_resumes(self, client_id: str) -> List[Dict]:
        """Get client resumes"""
        query = """
            SELECT * FROM resumes 
            WHERE user_id = ? 
            ORDER BY created_date DESC
        """
        return self._execute_query('resumes', query, (client_id,))
    
    # Court and Legal Methods
    def get_court_dates(self, client_id: str) -> List[Dict]:
        """Get upcoming court dates for client"""
        try:
            # Look for court-related tasks
            query = """
                SELECT * FROM tasks 
                WHERE client_id = ? 
                AND (
                    LOWER(title) LIKE '%court%' OR 
                    LOWER(title) LIKE '%hearing%' OR 
                    LOWER(title) LIKE '%legal%' OR
                    LOWER(description) LIKE '%court%'
                )
                AND due_date >= date('now')
                ORDER BY due_date ASC
            """
            
            court_tasks = self._execute_query('case_management', query, (client_id,))
            
            # Format for AI response
            court_dates = []
            for task in court_tasks:
                court_dates.append({
                    'date': task.get('due_date'),
                    'type': task.get('title', 'Court Appearance'),
                    'description': task.get('description', ''),
                    'status': task.get('status', 'pending'),
                    'location': task.get('location', 'TBD')
                })
            
            return court_dates
            
        except Exception as e:
            logger.error(f"Error getting court dates: {e}")
            return []
    
    # Service Provider Methods
    def search_providers(self, service_type: str, location: str = None) -> List[Dict]:
        """Search service providers"""
        try:
            # First search service_providers table  
            query = """
                SELECT * FROM service_providers 
                WHERE LOWER(organization_type) LIKE ? OR LOWER(name) LIKE ?
            """
            params = [f'%{service_type.lower()}%', f'%{service_type.lower()}%']
            
            if location:
                query += " AND (LOWER(address) LIKE ?)"
                params.extend([f'%{location.lower()}%'])
            
            query += " ORDER BY name LIMIT 20"
            
            results = self._execute_query('services', query, tuple(params))
            
            # Also search social_services table if we need more results
            if len(results) < 20:
                social_query = """
                    SELECT * FROM social_services 
                    WHERE LOWER(service_type) LIKE ? OR LOWER(service_category) LIKE ? OR LOWER(description) LIKE ?
                """
                social_params = [f'%{service_type.lower()}%', f'%{service_type.lower()}%', f'%{service_type.lower()}%']
                
                # Note: social_services table doesn't have address field
                # Location filtering would need to be done via provider_id join if needed
                
                social_query += " ORDER BY service_type LIMIT ?"
                social_params.append(20 - len(results))
                
                social_results = self._execute_query('services', social_query, tuple(social_params))
                results.extend(social_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching providers: {e}")
            return []
    
    # Housing Methods
    def search_housing(self, location: str = None, housing_type: str = None, background_friendly: bool = True) -> List[Dict]:
        """Search housing resources"""
        try:
            query = "SELECT * FROM housing WHERE 1=1"
            params = []
            
            if location:
                query += " AND (LOWER(city) LIKE ? OR LOWER(address) LIKE ?)"
                params.extend([f'%{location.lower()}%', f'%{location.lower()}%'])
            
            if housing_type:
                query += " AND LOWER(housing_type) LIKE ?"
                params.append(f'%{housing_type.lower()}%')
            
            if background_friendly:
                query += " AND (background_friendly = 1 OR background_friendly = 'true')"
            
            query += " ORDER BY name LIMIT 20"
            
            return self._execute_query('housing', query, tuple(params))
            
        except Exception as e:
            logger.error(f"Error searching housing: {e}")
            return []
    
    # Job Methods
    def get_job_matches(self, client_id: str, keywords: str = None, location: str = None) -> List[Dict]:
        """Get job matches for client"""
        try:
            # Get client profile first
            client_info = self.get_client_info(client_id)
            if 'error' in client_info:
                return []
            
            # Search jobs
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []
            
            if keywords:
                query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ?)"
                params.extend([f'%{keywords.lower()}%', f'%{keywords.lower()}%'])
            
            if location:
                query += " AND LOWER(location) LIKE ?"
                params.append(f'%{location.lower()}%')
            
            # Prioritize background-friendly jobs
            query += " ORDER BY background_friendly_score DESC, scraped_date DESC LIMIT 20"
            
            return self._execute_query('jobs', query, tuple(params))
            
        except Exception as e:
            logger.error(f"Error getting job matches: {e}")
            return []
    
    def search_jobs(self, keywords: str, location: str = None, client_id: str = None) -> List[Dict]:
        """Search for job opportunities"""
        try:
            query = """
                SELECT * FROM jobs 
                WHERE LOWER(title) LIKE ? OR LOWER(description) LIKE ?
            """
            params = [f'%{keywords.lower()}%', f'%{keywords.lower()}%']
            
            if location:
                query += " AND LOWER(location) LIKE ?"
                params.append(f'%{location.lower()}%')
            
            query += " ORDER BY background_friendly_score DESC, scraped_date DESC LIMIT 20"
            
            return self._execute_query('jobs', query, tuple(params))
            
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return []
    
    # Referral Methods
    def get_referral_status(self, client_id: str, referral_id: str = None) -> List[Dict]:
        """Check status of service referrals"""
        try:
            query = "SELECT * FROM referrals WHERE client_id = ?"
            params = [client_id]
            
            if referral_id:
                query += " AND id = ?"
                params.append(referral_id)
            
            query += " ORDER BY created_date DESC"
            
            return self._execute_query('case_management', query, tuple(params))
            
        except Exception as e:
            logger.error(f"Error getting referral status: {e}")
            return []
    
    # Statistics and Summary Methods
    def get_client_summary(self, client_id: str) -> Dict[str, Any]:
        """Get client summary statistics"""
        try:
            summary = {
                'total_referrals': len(self.get_client_referrals(client_id)),
                'pending_tasks': len([t for t in self.get_client_tasks(client_id) if t.get('status') == 'pending']),
                'upcoming_appointments': len([a for a in self.get_client_appointments(client_id) 
                                            if a.get('appointment_date', '') >= datetime.now().strftime('%Y-%m-%d')]),
                'total_documents': len(self.get_client_documents(client_id)),
                'recent_notes': len(self.get_client_notes(client_id)),
                'resumes_created': len(self.get_client_resumes(client_id))
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting client summary: {e}")
            return {}
    
    def get_platform_stats(self) -> Dict[str, Any]:
        """Get overall platform statistics"""
        try:
            stats = {}
            
            # Client stats
            clients = self._execute_query('case_management', "SELECT COUNT(*) as count FROM clients")
            stats['total_clients'] = clients[0]['count'] if clients else 0
            
            # Job stats
            jobs = self._execute_query('jobs', "SELECT COUNT(*) as count FROM jobs")
            stats['total_jobs'] = jobs[0]['count'] if jobs else 0
            
            # Housing stats
            housing = self._execute_query('housing', "SELECT COUNT(*) as count FROM housing")
            stats['total_housing'] = housing[0]['count'] if housing else 0
            
            # Service stats (count from both tables)
            providers = self._execute_query('services', "SELECT COUNT(*) as count FROM service_providers")
            social_services = self._execute_query('services', "SELECT COUNT(*) as count FROM social_services")
            provider_count = providers[0]['count'] if providers else 0
            social_count = social_services[0]['count'] if social_services else 0
            stats['total_services'] = provider_count + social_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting platform stats: {e}")
            return {}
    
    # Search Methods
    def search_all(self, query: str, limit: int = 10) -> Dict[str, List[Dict]]:
        """Search across all platform data"""
        try:
            results = {
                'clients': [],
                'jobs': [],
                'housing': [],
                'services': []
            }
            
            # Search clients
            client_query = """
                SELECT * FROM clients 
                WHERE LOWER(name) LIKE ? OR LOWER(email) LIKE ?
                LIMIT ?
            """
            results['clients'] = self._execute_query(
                'case_management', 
                client_query, 
                (f'%{query.lower()}%', f'%{query.lower()}%', limit)
            )
            
            # Search jobs
            job_query = """
                SELECT * FROM jobs 
                WHERE LOWER(title) LIKE ? OR LOWER(company) LIKE ?
                ORDER BY background_friendly_score DESC
                LIMIT ?
            """
            results['jobs'] = self._execute_query(
                'jobs', 
                job_query, 
                (f'%{query.lower()}%', f'%{query.lower()}%', limit)
            )
            
            # Search housing
            housing_query = """
                SELECT * FROM housing 
                WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ?
                LIMIT ?
            """
            results['housing'] = self._execute_query(
                'housing', 
                housing_query, 
                (f'%{query.lower()}%', f'%{query.lower()}%', limit)
            )
            
            # Search services (search both tables)
            service_query = """
                SELECT * FROM service_providers 
                WHERE LOWER(name) LIKE ? OR LOWER(organization_type) LIKE ?
                LIMIT ?
            """
            provider_results = self._execute_query(
                'services', 
                service_query, 
                (f'%{query.lower()}%', f'%{query.lower()}%', limit)
            )
            
            # Also search social services
            social_query = """
                SELECT * FROM social_services 
                WHERE LOWER(service_type) LIKE ? OR LOWER(service_category) LIKE ? OR LOWER(description) LIKE ?
                LIMIT ?
            """
            social_results = self._execute_query(
                'services', 
                social_query, 
                (f'%{query.lower()}%', f'%{query.lower()}%', f'%{query.lower()}%', limit)
            )
            
            # Combine results
            all_services = provider_results + social_results
            results['services'] = all_services[:limit]
            
            return results
            
        except Exception as e:
            logger.error(f"Error in universal search: {e}")
            return {'clients': [], 'jobs': [], 'housing': [], 'services': []}