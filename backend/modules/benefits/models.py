#!/usr/bin/env python3
"""
Benefits Application Assistant Models for Second Chance Jobs Platform
Comprehensive benefits application tracking and assistance
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import uuid

logger = logging.getLogger(__name__)

class BenefitsApplication:
    """Benefits application tracking and assistance"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.application_id = kwargs.get('application_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        
        # Application Details
        self.benefit_type = kwargs.get('benefit_type', '')  # SNAP, Medicaid, SSI, SSDI, Housing Voucher, etc.
        self.application_status = kwargs.get('application_status', 'Not Started')
        self.application_date = kwargs.get('application_date', '')
        self.submitted_date = kwargs.get('submitted_date', '')
        self.decision_date = kwargs.get('decision_date', '')
        self.effective_date = kwargs.get('effective_date', '')
        
        # Application Progress
        self.completion_percentage = kwargs.get('completion_percentage', 0)
        self.current_step = kwargs.get('current_step', '')
        self.next_action_required = kwargs.get('next_action_required', '')
        self.estimated_completion_time = kwargs.get('estimated_completion_time', '')
        
        # Required Documents
        self.documents_required = kwargs.get('documents_required', '')  # JSON string
        self.documents_submitted = kwargs.get('documents_submitted', '')  # JSON string
        self.documents_missing = kwargs.get('documents_missing', '')  # JSON string
        
        # Application Details
        self.application_method = kwargs.get('application_method', 'Online')  # Online, In-Person, Phone, Mail
        self.assistance_received = kwargs.get('assistance_received', False)
        self.assistance_provider = kwargs.get('assistance_provider', '')
        self.case_worker_name = kwargs.get('case_worker_name', '')
        self.case_worker_phone = kwargs.get('case_worker_phone', '')
        self.case_worker_email = kwargs.get('case_worker_email', '')
        
        # Financial Information
        self.monthly_benefit_amount = kwargs.get('monthly_benefit_amount', 0.0)
        self.annual_benefit_amount = kwargs.get('annual_benefit_amount', 0.0)
        self.benefit_start_date = kwargs.get('benefit_start_date', '')
        self.benefit_end_date = kwargs.get('benefit_end_date', '')
        self.renewal_due_date = kwargs.get('renewal_due_date', '')
        
        # Decision and Appeals
        self.decision_outcome = kwargs.get('decision_outcome', '')  # Approved, Denied, Pending
        self.denial_reason = kwargs.get('denial_reason', '')
        self.appeal_filed = kwargs.get('appeal_filed', False)
        self.appeal_date = kwargs.get('appeal_date', '')
        self.appeal_status = kwargs.get('appeal_status', '')
        
        # Follow-up and Maintenance
        self.recertification_required = kwargs.get('recertification_required', False)
        self.recertification_due_date = kwargs.get('recertification_due_date', '')
        self.last_review_date = kwargs.get('last_review_date', '')
        self.next_review_date = kwargs.get('next_review_date', '')
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.created_by = kwargs.get('created_by', '')
        self.notes = kwargs.get('notes', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'application_id': self.application_id,
            'client_id': self.client_id,
            'benefit_type': self.benefit_type,
            'application_status': self.application_status,
            'application_date': self.application_date,
            'submitted_date': self.submitted_date,
            'decision_date': self.decision_date,
            'effective_date': self.effective_date,
            'completion_percentage': self.completion_percentage,
            'current_step': self.current_step,
            'next_action_required': self.next_action_required,
            'estimated_completion_time': self.estimated_completion_time,
            'documents_required': self.documents_required,
            'documents_submitted': self.documents_submitted,
            'documents_missing': self.documents_missing,
            'application_method': self.application_method,
            'assistance_received': self.assistance_received,
            'assistance_provider': self.assistance_provider,
            'case_worker_name': self.case_worker_name,
            'case_worker_phone': self.case_worker_phone,
            'case_worker_email': self.case_worker_email,
            'monthly_benefit_amount': self.monthly_benefit_amount,
            'annual_benefit_amount': self.annual_benefit_amount,
            'benefit_start_date': self.benefit_start_date,
            'benefit_end_date': self.benefit_end_date,
            'renewal_due_date': self.renewal_due_date,
            'decision_outcome': self.decision_outcome,
            'denial_reason': self.denial_reason,
            'appeal_filed': self.appeal_filed,
            'appeal_date': self.appeal_date,
            'appeal_status': self.appeal_status,
            'recertification_required': self.recertification_required,
            'recertification_due_date': self.recertification_due_date,
            'last_review_date': self.last_review_date,
            'next_review_date': self.next_review_date,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'created_by': self.created_by,
            'notes': self.notes
        }


class TransportationRequest:
    """Transportation coordination and assistance"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.request_id = kwargs.get('request_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        
        # Request Details
        self.transportation_type = kwargs.get('transportation_type', '')  # Bus Pass, Medical Transport, Ride Share, etc.
        self.request_status = kwargs.get('request_status', 'Pending')
        self.request_date = kwargs.get('request_date', datetime.now().isoformat())
        self.needed_date = kwargs.get('needed_date', '')
        self.fulfilled_date = kwargs.get('fulfilled_date', '')
        
        # Transportation Details
        self.purpose = kwargs.get('purpose', '')  # Medical, Court, Employment, Services, etc.
        self.destination_name = kwargs.get('destination_name', '')
        self.destination_address = kwargs.get('destination_address', '')
        self.pickup_location = kwargs.get('pickup_location', '')
        self.appointment_time = kwargs.get('appointment_time', '')
        self.return_trip_needed = kwargs.get('return_trip_needed', False)
        
        # Provider Information
        self.transportation_provider = kwargs.get('transportation_provider', '')
        self.provider_contact = kwargs.get('provider_contact', '')
        self.provider_phone = kwargs.get('provider_phone', '')
        self.confirmation_number = kwargs.get('confirmation_number', '')
        
        # Cost and Payment
        self.estimated_cost = kwargs.get('estimated_cost', 0.0)
        self.actual_cost = kwargs.get('actual_cost', 0.0)
        self.payment_method = kwargs.get('payment_method', '')
        self.cost_covered_by = kwargs.get('cost_covered_by', '')  # Client, Insurance, Program, etc.
        
        # Special Requirements
        self.wheelchair_accessible = kwargs.get('wheelchair_accessible', False)
        self.special_needs = kwargs.get('special_needs', '')
        self.language_requirements = kwargs.get('language_requirements', '')
        
        # Status and Tracking
        self.assigned_driver = kwargs.get('assigned_driver', '')
        self.vehicle_info = kwargs.get('vehicle_info', '')
        self.pickup_time = kwargs.get('pickup_time', '')
        self.dropoff_time = kwargs.get('dropoff_time', '')
        self.trip_completed = kwargs.get('trip_completed', False)
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.created_by = kwargs.get('created_by', '')
        self.notes = kwargs.get('notes', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'request_id': self.request_id,
            'client_id': self.client_id,
            'transportation_type': self.transportation_type,
            'request_status': self.request_status,
            'request_date': self.request_date,
            'needed_date': self.needed_date,
            'fulfilled_date': self.fulfilled_date,
            'purpose': self.purpose,
            'destination_name': self.destination_name,
            'destination_address': self.destination_address,
            'pickup_location': self.pickup_location,
            'appointment_time': self.appointment_time,
            'return_trip_needed': self.return_trip_needed,
            'transportation_provider': self.transportation_provider,
            'provider_contact': self.provider_contact,
            'provider_phone': self.provider_phone,
            'confirmation_number': self.confirmation_number,
            'estimated_cost': self.estimated_cost,
            'actual_cost': self.actual_cost,
            'payment_method': self.payment_method,
            'cost_covered_by': self.cost_covered_by,
            'wheelchair_accessible': self.wheelchair_accessible,
            'special_needs': self.special_needs,
            'language_requirements': self.language_requirements,
            'assigned_driver': self.assigned_driver,
            'vehicle_info': self.vehicle_info,
            'pickup_time': self.pickup_time,
            'dropoff_time': self.dropoff_time,
            'trip_completed': self.trip_completed,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'created_by': self.created_by,
            'notes': self.notes
        }


class BenefitsDatabase:
    """Benefits and transportation coordination database"""
    
    def __init__(self, db_path: str = "benefits_transport.db"):
        self.db_path = db_path
        self.connection = None
        self.create_tables()
    
    def connect(self):
        """Connect to SQLite database"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to benefits database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to benefits database: {e}")
            raise
    
    def create_tables(self):
        """Create benefits and transportation tables"""
        if not self.connection:
            self.connect()
        
        # Benefits applications table
        create_benefits_sql = """
        CREATE TABLE IF NOT EXISTS benefits_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            benefit_type TEXT NOT NULL,
            application_status TEXT DEFAULT 'Not Started',
            application_date TEXT,
            submitted_date TEXT,
            decision_date TEXT,
            effective_date TEXT,
            completion_percentage INTEGER DEFAULT 0,
            current_step TEXT,
            next_action_required TEXT,
            estimated_completion_time TEXT,
            documents_required TEXT,
            documents_submitted TEXT,
            documents_missing TEXT,
            application_method TEXT DEFAULT 'Online',
            assistance_received INTEGER DEFAULT 0,
            assistance_provider TEXT,
            case_worker_name TEXT,
            case_worker_phone TEXT,
            case_worker_email TEXT,
            monthly_benefit_amount REAL DEFAULT 0.0,
            annual_benefit_amount REAL DEFAULT 0.0,
            benefit_start_date TEXT,
            benefit_end_date TEXT,
            renewal_due_date TEXT,
            decision_outcome TEXT,
            denial_reason TEXT,
            appeal_filed INTEGER DEFAULT 0,
            appeal_date TEXT,
            appeal_status TEXT,
            recertification_required INTEGER DEFAULT 0,
            recertification_due_date TEXT,
            last_review_date TEXT,
            next_review_date TEXT,
            created_at TEXT,
            last_updated TEXT,
            created_by TEXT,
            notes TEXT
        );
        """
        
        # Transportation requests table
        create_transport_sql = """
        CREATE TABLE IF NOT EXISTS transportation_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            transportation_type TEXT NOT NULL,
            request_status TEXT DEFAULT 'Pending',
            request_date TEXT,
            needed_date TEXT,
            fulfilled_date TEXT,
            purpose TEXT,
            destination_name TEXT,
            destination_address TEXT,
            pickup_location TEXT,
            appointment_time TEXT,
            return_trip_needed INTEGER DEFAULT 0,
            transportation_provider TEXT,
            provider_contact TEXT,
            provider_phone TEXT,
            confirmation_number TEXT,
            estimated_cost REAL DEFAULT 0.0,
            actual_cost REAL DEFAULT 0.0,
            payment_method TEXT,
            cost_covered_by TEXT,
            wheelchair_accessible INTEGER DEFAULT 0,
            special_needs TEXT,
            language_requirements TEXT,
            assigned_driver TEXT,
            vehicle_info TEXT,
            pickup_time TEXT,
            dropoff_time TEXT,
            trip_completed INTEGER DEFAULT 0,
            created_at TEXT,
            last_updated TEXT,
            created_by TEXT,
            notes TEXT
        );
        """
        
        try:
            self.connection.execute(create_benefits_sql)
            self.connection.execute(create_transport_sql)
            self.connection.commit()
            logger.info("Benefits and transportation tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create benefits tables: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Benefits database connection closed")