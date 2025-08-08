"""
Case Management Database Layer
Handles client data persistence and database operations
"""

import sqlite3
import logging
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import Client, CaseNote, Referral

logger = logging.getLogger(__name__)


class CaseManagementDatabase:
    """Database interface for case management operations"""
    
    def __init__(self, db_path: str = 'databases/case_management.db'):
        self.db_path = db_path
        self.connection = None
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self.setup_database()
    
    def connect(self):
        """Connect to SQLite database"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def setup_database(self):
        """Create database tables if they don't exist"""
        if not self.connect():
            return False
        
        # Check if we need to migrate the clients table
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA table_info(clients)")
        columns = cursor.fetchall()
        
        # If table exists but has wrong schema, drop and recreate
        if columns and len(columns) < 39:  # Expected 39 columns
            logger.info("Clients table has outdated schema, recreating...")
            cursor.execute("DROP TABLE IF EXISTS clients")
            self.connection.commit()
        
        # Check if case_notes table needs migration
        cursor.execute("PRAGMA table_info(case_notes)")
        case_notes_columns = cursor.fetchall()
        
        # If case_notes table exists but has wrong schema (old schema had only 4 columns), drop and recreate
        if case_notes_columns and len(case_notes_columns) < 15:  # Expected 15+ columns
            logger.info("Case notes table has outdated schema, recreating...")
            cursor.execute("DROP TABLE IF EXISTS case_notes")
            self.connection.commit()
        
        tables = [
            # Clients table with comprehensive fields
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                
                -- Personal Information
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth TEXT,
                phone TEXT,
                email TEXT,
                
                -- Address Information
                address TEXT,
                city TEXT,
                state TEXT DEFAULT 'CA',
                zip_code TEXT,
                
                -- Emergency Contact
                emergency_contact_name TEXT,
                emergency_contact_phone TEXT,
                emergency_contact_relationship TEXT,
                
                -- Case Management
                case_manager_id TEXT NOT NULL,
                risk_level TEXT DEFAULT 'Medium',
                case_status TEXT DEFAULT 'Active',
                
                -- Service Status
                housing_status TEXT DEFAULT 'Unknown',
                employment_status TEXT DEFAULT 'Unemployed',
                benefits_status TEXT DEFAULT 'Not Applied',
                legal_status TEXT DEFAULT 'No Active Cases',
                
                -- Program Information
                program_type TEXT DEFAULT 'Reentry',
                referral_source TEXT,
                intake_date TEXT,
                
                -- Background Assessment
                prior_convictions TEXT,
                substance_abuse_history TEXT DEFAULT 'No',
                mental_health_status TEXT DEFAULT 'Stable',
                
                -- Support & Resources
                transportation TEXT DEFAULT 'None',
                medical_conditions TEXT,
                special_needs TEXT,
                
                -- Goals & Planning
                goals TEXT,
                barriers TEXT,
                needs TEXT,  -- JSON array of service needs
                
                -- Progress Tracking
                progress INTEGER DEFAULT 0,
                last_contact TEXT,
                next_followup TEXT,
                
                -- Metadata
                notes TEXT,
                created_at TEXT,
                last_updated TEXT,
                is_active INTEGER DEFAULT 1
            )
            """,
            
            # Case Notes table
            """
            CREATE TABLE IF NOT EXISTS case_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                
                -- Note content
                note_type TEXT DEFAULT 'General',
                title TEXT,
                content TEXT NOT NULL,
                
                -- Context
                contact_method TEXT,
                duration_minutes INTEGER DEFAULT 0,
                location TEXT,
                
                -- Assessment
                client_mood TEXT,
                progress_rating INTEGER DEFAULT 0,
                barriers_identified TEXT,
                action_items TEXT,
                
                -- Follow-up
                next_contact_needed TEXT,
                referrals_made TEXT,
                
                -- Metadata
                created_at TEXT,
                is_confidential INTEGER DEFAULT 0,
                tags TEXT,  -- JSON array
                
                FOREIGN KEY (client_id) REFERENCES clients (client_id)
            )
            """,
            
            # Referrals table
            """
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referral_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                
                -- Referral details
                service_type TEXT NOT NULL,
                provider_name TEXT,
                provider_contact TEXT,
                
                -- Status tracking
                status TEXT DEFAULT 'Pending',
                priority TEXT DEFAULT 'Medium',
                
                -- Dates
                referral_date TEXT,
                expected_contact_date TEXT,
                actual_contact_date TEXT,
                completion_date TEXT,
                
                -- Outcome
                outcome TEXT,
                notes TEXT,
                
                -- Metadata
                created_at TEXT,
                last_updated TEXT,
                
                FOREIGN KEY (client_id) REFERENCES clients (client_id)
            )
            """
        ]
        
        try:
            for table_sql in tables:
                self.connection.execute(table_sql)
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_clients_case_manager ON clients(case_manager_id)",
                "CREATE INDEX IF NOT EXISTS idx_clients_risk_level ON clients(risk_level)",
                "CREATE INDEX IF NOT EXISTS idx_clients_active ON clients(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_case_notes_client ON case_notes(client_id)",
                "CREATE INDEX IF NOT EXISTS idx_referrals_client ON referrals(client_id)",
                "CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals(status)"
            ]
            
            for index_sql in indexes:
                self.connection.execute(index_sql)
            
            self.connection.commit()
            logger.info("Case management database tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            return False
    
    def create_client(self, client: Client) -> bool:
        """Create a new client record"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            
            # Convert needs list to JSON string
            needs_json = json.dumps(client.needs) if client.needs else '[]'
            
            cursor.execute("""
                INSERT INTO clients (
                    client_id, first_name, last_name, date_of_birth, phone, email,
                    address, city, state, zip_code,
                    emergency_contact_name, emergency_contact_phone, emergency_contact_relationship,
                    case_manager_id, risk_level, case_status,
                    housing_status, employment_status, benefits_status, legal_status,
                    program_type, referral_source, intake_date,
                    prior_convictions, substance_abuse_history, mental_health_status,
                    transportation, medical_conditions, special_needs,
                    goals, barriers, needs,
                    progress, last_contact, next_followup,
                    notes, created_at, last_updated, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client.client_id, client.first_name, client.last_name, client.date_of_birth, client.phone, client.email,
                client.address, client.city, client.state, client.zip_code,
                client.emergency_contact_name, client.emergency_contact_phone, client.emergency_contact_relationship,
                client.case_manager_id, client.risk_level, client.case_status,
                client.housing_status, client.employment_status, client.benefits_status, client.legal_status,
                client.program_type, client.referral_source, client.intake_date,
                client.prior_convictions, client.substance_abuse_history, client.mental_health_status,
                client.transportation, client.medical_conditions, client.special_needs,
                client.goals, client.barriers, needs_json,
                client.progress, client.last_contact, client.next_followup,
                client.notes, client.created_at, client.last_updated, client.is_active
            ))
            
            self.connection.commit()
            logger.info(f"Created client: {client.client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_client(self, client_id: str) -> Optional[Client]:
        """Get a client by ID"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM clients WHERE client_id = ? AND is_active = 1", (client_id,))
            
            row = cursor.fetchone()
            if row:
                client_data = dict(row)
                
                # Parse JSON fields
                if client_data.get('needs'):
                    try:
                        client_data['needs'] = json.loads(client_data['needs'])
                    except (json.JSONDecodeError, TypeError):
                        client_data['needs'] = []
                
                return Client(**client_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting client: {e}")
            return None
    
    def get_clients_by_case_manager(self, case_manager_id: str, filters: Dict[str, Any] = None) -> List[Client]:
        """Get all clients for a case manager with optional filters"""
        try:
            if not self.connection:
                self.connect()
            
            # Handle None or empty case_manager_id
            if not case_manager_id:
                logger.warning("None case_manager_id provided")
                return []
            
            case_manager_id = str(case_manager_id).strip()
            if not case_manager_id:
                logger.warning("Empty case_manager_id provided")
                return []
            
            cursor = self.connection.cursor()
            
            # Build query with filters
            where_conditions = ["case_manager_id = ? AND is_active = 1"]
            params = [case_manager_id]
            
            if filters:
                if filters.get('risk_level'):
                    where_conditions.append("risk_level = ?")
                    params.append(filters['risk_level'])
                
                if filters.get('housing_status'):
                    where_conditions.append("housing_status = ?")
                    params.append(filters['housing_status'])
                
                if filters.get('search'):
                    where_conditions.append("(first_name LIKE ? OR last_name LIKE ?)")
                    search_term = f"%{filters['search']}%"
                    params.extend([search_term, search_term])
            
            query = f"SELECT * FROM clients WHERE {' AND '.join(where_conditions)} ORDER BY last_updated DESC"
            cursor.execute(query, params)
            
            clients = []
            for row in cursor.fetchall():
                client_data = dict(row)
                
                # Parse JSON fields
                if client_data.get('needs'):
                    try:
                        client_data['needs'] = json.loads(client_data['needs'])
                    except (json.JSONDecodeError, TypeError):
                        client_data['needs'] = []
                
                clients.append(Client(**client_data))
            
            return clients
            
        except Exception as e:
            logger.error(f"Error getting clients: {e}")
            return []
    
    def update_client(self, client: Client) -> bool:
        """Update an existing client record"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            
            # Update timestamp
            client.last_updated = datetime.now().isoformat()
            needs_json = json.dumps(client.needs) if client.needs else '[]'
            
            cursor.execute("""
                UPDATE clients SET
                    first_name = ?, last_name = ?, date_of_birth = ?, phone = ?, email = ?,
                    address = ?, city = ?, state = ?, zip_code = ?,
                    emergency_contact_name = ?, emergency_contact_phone = ?, emergency_contact_relationship = ?,
                    risk_level = ?, case_status = ?,
                    housing_status = ?, employment_status = ?, benefits_status = ?, legal_status = ?,
                    program_type = ?, referral_source = ?,
                    prior_convictions = ?, substance_abuse_history = ?, mental_health_status = ?,
                    transportation = ?, medical_conditions = ?, special_needs = ?,
                    goals = ?, barriers = ?, needs = ?,
                    progress = ?, last_contact = ?, next_followup = ?,
                    notes = ?, last_updated = ?
                WHERE client_id = ?
            """, (
                client.first_name, client.last_name, client.date_of_birth, client.phone, client.email,
                client.address, client.city, client.state, client.zip_code,
                client.emergency_contact_name, client.emergency_contact_phone, client.emergency_contact_relationship,
                client.risk_level, client.case_status,
                client.housing_status, client.employment_status, client.benefits_status, client.legal_status,
                client.program_type, client.referral_source,
                client.prior_convictions, client.substance_abuse_history, client.mental_health_status,
                client.transportation, client.medical_conditions, client.special_needs,
                client.goals, client.barriers, needs_json,
                client.progress, client.last_contact, client.next_followup,
                client.notes, client.last_updated,
                client.client_id
            ))
            
            self.connection.commit()
            logger.info(f"Updated client: {client.client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating client: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def delete_client(self, client_id: str) -> bool:
        """Soft delete a client (set is_active = 0)"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            cursor.execute("UPDATE clients SET is_active = 0 WHERE client_id = ?", (client_id,))
            
            self.connection.commit()
            logger.info(f"Deleted client: {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting client: {e}")
            return False
    
    def create_case_note(self, case_note: CaseNote) -> bool:
        """Create a new case note"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            tags_json = json.dumps(case_note.tags) if case_note.tags else '[]'
            
            cursor.execute("""
                INSERT INTO case_notes (
                    note_id, client_id, case_manager_id,
                    note_type, title, content,
                    contact_method, duration_minutes, location,
                    client_mood, progress_rating, barriers_identified, action_items,
                    next_contact_needed, referrals_made,
                    created_at, is_confidential, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case_note.note_id, case_note.client_id, case_note.case_manager_id,
                case_note.note_type, case_note.title, case_note.content,
                case_note.contact_method, case_note.duration_minutes, case_note.location,
                case_note.client_mood, case_note.progress_rating, case_note.barriers_identified, case_note.action_items,
                case_note.next_contact_needed, case_note.referrals_made,
                case_note.created_at, case_note.is_confidential, tags_json
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error creating case note: {e}")
            return False
    
    def get_client_notes(self, client_id: str) -> List[CaseNote]:
        """Get all case notes for a client"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT * FROM case_notes WHERE client_id = ? ORDER BY created_at DESC",
                (client_id,)
            )
            
            notes = []
            for row in cursor.fetchall():
                note_data = dict(row)
                
                # Parse JSON fields
                if note_data.get('tags'):
                    try:
                        note_data['tags'] = json.loads(note_data['tags'])
                    except (json.JSONDecodeError, TypeError):
                        note_data['tags'] = []
                
                notes.append(CaseNote(**note_data))
            
            return notes
            
        except Exception as e:
            logger.error(f"Error getting case notes: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None