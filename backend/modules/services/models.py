#!/usr/bin/env python3
"""
Social Services Database Models for Second Chance Jobs Platform
Professional-grade service provider database with comprehensive case management capabilities
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import os
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

class ServiceProvider:
    """Service provider data model for professional case management"""
    
    def __init__(self, **kwargs):
        # Basic Info
        self.id = kwargs.get('id')
        self.provider_id = kwargs.get('provider_id', str(uuid.uuid4()))
        self.name = kwargs.get('name', '')
        self.organization_type = kwargs.get('organization_type', '')  # Government, Nonprofit, Faith-based, Private, Community-based
        
        # Contact Information
        self.primary_contact = kwargs.get('primary_contact', '')
        self.referral_contact = kwargs.get('referral_contact', '')
        self.emergency_contact = kwargs.get('emergency_contact', '')
        self.address = kwargs.get('address', '')
        self.city = kwargs.get('city', '')
        self.county = kwargs.get('county', '')
        self.state = kwargs.get('state', 'CA')
        self.zip_code = kwargs.get('zip_code', '')
        
        # Communication
        self.phone_main = kwargs.get('phone_main', '')
        self.phone_referral = kwargs.get('phone_referral', '')
        self.fax = kwargs.get('fax', '')
        self.email = kwargs.get('email', '')
        self.website = kwargs.get('website', '')
        
        # Operational Details
        self.hours_operation = kwargs.get('hours_operation', '')
        self.appointment_types = kwargs.get('appointment_types', '')  # Walk-in, Scheduled, Emergency
        self.languages_offered = kwargs.get('languages_offered', '')
        self.accessibility_features = kwargs.get('accessibility_features', '')
        
        # Professional Information
        self.accreditation_status = kwargs.get('accreditation_status', '')
        self.license_number = kwargs.get('license_number', '')
        self.accepts_medicaid = kwargs.get('accepts_medicaid', True)
        self.sliding_scale_available = kwargs.get('sliding_scale_available', False)
        
        # Capacity and Availability
        self.current_capacity = kwargs.get('current_capacity', 0)
        self.total_capacity = kwargs.get('total_capacity', 0)
        self.waitlist_length = kwargs.get('waitlist_length', 0)
        self.avg_wait_time_days = kwargs.get('avg_wait_time_days', 0)
        
        # Background Check Policies
        self.background_check_policy = kwargs.get('background_check_policy', '')
        self.restricted_offenses = kwargs.get('restricted_offenses', '')
        self.case_by_case_review = kwargs.get('case_by_case_review', True)
        
        # Service Area
        self.service_radius_miles = kwargs.get('service_radius_miles', 0)
        self.provides_transportation = kwargs.get('provides_transportation', False)
        self.mobile_services = kwargs.get('mobile_services', False)
        self.telehealth_available = kwargs.get('telehealth_available', False)
        
        # Performance Metrics
        self.success_rate = kwargs.get('success_rate', 0.0)
        self.completion_rate = kwargs.get('completion_rate', 0.0)
        self.client_satisfaction = kwargs.get('client_satisfaction', 0.0)
        self.referral_volume_monthly = kwargs.get('referral_volume_monthly', 0)
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.is_active = kwargs.get('is_active', True)
        self.notes = kwargs.get('notes', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'name': self.name,
            'organization_type': self.organization_type,
            'primary_contact': self.primary_contact,
            'referral_contact': self.referral_contact,
            'emergency_contact': self.emergency_contact,
            'address': self.address,
            'city': self.city,
            'county': self.county,
            'state': self.state,
            'zip_code': self.zip_code,
            'phone_main': self.phone_main,
            'phone_referral': self.phone_referral,
            'fax': self.fax,
            'email': self.email,
            'website': self.website,
            'hours_operation': self.hours_operation,
            'appointment_types': self.appointment_types,
            'languages_offered': self.languages_offered,
            'accessibility_features': self.accessibility_features,
            'accreditation_status': self.accreditation_status,
            'license_number': self.license_number,
            'accepts_medicaid': self.accepts_medicaid,
            'sliding_scale_available': self.sliding_scale_available,
            'current_capacity': self.current_capacity,
            'total_capacity': self.total_capacity,
            'waitlist_length': self.waitlist_length,
            'avg_wait_time_days': self.avg_wait_time_days,
            'background_check_policy': self.background_check_policy,
            'restricted_offenses': self.restricted_offenses,
            'case_by_case_review': self.case_by_case_review,
            'service_radius_miles': self.service_radius_miles,
            'provides_transportation': self.provides_transportation,
            'mobile_services': self.mobile_services,
            'telehealth_available': self.telehealth_available,
            'success_rate': self.success_rate,
            'completion_rate': self.completion_rate,
            'client_satisfaction': self.client_satisfaction,
            'referral_volume_monthly': self.referral_volume_monthly,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'is_active': self.is_active,
            'notes': self.notes
        }


class SocialService:
    """Individual service offered by a provider"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.service_id = kwargs.get('service_id', str(uuid.uuid4()))
        self.provider_id = kwargs.get('provider_id', '')
        
        # Service Classification
        self.service_category = kwargs.get('service_category', '')  # Housing, Mental Health, Medical, etc.
        self.service_type = kwargs.get('service_type', '')  # Specific service within category
        self.service_level = kwargs.get('service_level', '')  # Emergency, Ongoing, Intensive, Maintenance
        
        # Service Details
        self.description = kwargs.get('description', '')
        self.eligibility_criteria = kwargs.get('eligibility_criteria', '')
        self.documentation_required = kwargs.get('documentation_required', '')
        self.referral_process = kwargs.get('referral_process', '')
        self.intake_requirements = kwargs.get('intake_requirements', '')
        
        # Restrictions and Requirements
        self.age_restrictions = kwargs.get('age_restrictions', '')
        self.gender_restrictions = kwargs.get('gender_restrictions', '')
        self.sobriety_required = kwargs.get('sobriety_required', False)
        self.insurance_required = kwargs.get('insurance_required', False)
        self.residency_required = kwargs.get('residency_required', False)
        
        # Special Populations
        self.serves_veterans = kwargs.get('serves_veterans', False)
        self.serves_disabled = kwargs.get('serves_disabled', False)
        self.serves_pregnant_women = kwargs.get('serves_pregnant_women', False)
        self.serves_lgbtq = kwargs.get('serves_lgbtq', False)
        self.serves_trafficking_survivors = kwargs.get('serves_trafficking_survivors', False)
        
        # Cost and Payment
        self.cost_structure = kwargs.get('cost_structure', '')
        self.insurance_accepted = kwargs.get('insurance_accepted', '')
        self.sliding_scale_fees = kwargs.get('sliding_scale_fees', False)
        self.free_services = kwargs.get('free_services', False)
        
        # Availability
        self.current_availability = kwargs.get('current_availability', '')  # Accepting, Waitlist, Closed
        self.waitlist_status = kwargs.get('waitlist_status', '')
        self.estimated_wait_time = kwargs.get('estimated_wait_time', '')
        
        # Performance
        self.success_rate = kwargs.get('success_rate', 0.0)
        self.completion_rate = kwargs.get('completion_rate', 0.0)
        self.avg_service_duration = kwargs.get('avg_service_duration', '')
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.is_active = kwargs.get('is_active', True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'service_id': self.service_id,
            'provider_id': self.provider_id,
            'service_category': self.service_category,
            'service_type': self.service_type,
            'service_level': self.service_level,
            'description': self.description,
            'eligibility_criteria': self.eligibility_criteria,
            'documentation_required': self.documentation_required,
            'referral_process': self.referral_process,
            'intake_requirements': self.intake_requirements,
            'age_restrictions': self.age_restrictions,
            'gender_restrictions': self.gender_restrictions,
            'sobriety_required': self.sobriety_required,
            'insurance_required': self.insurance_required,
            'residency_required': self.residency_required,
            'serves_veterans': self.serves_veterans,
            'serves_disabled': self.serves_disabled,
            'serves_pregnant_women': self.serves_pregnant_women,
            'serves_lgbtq': self.serves_lgbtq,
            'serves_trafficking_survivors': self.serves_trafficking_survivors,
            'cost_structure': self.cost_structure,
            'insurance_accepted': self.insurance_accepted,
            'sliding_scale_fees': self.sliding_scale_fees,
            'free_services': self.free_services,
            'current_availability': self.current_availability,
            'waitlist_status': self.waitlist_status,
            'estimated_wait_time': self.estimated_wait_time,
            'success_rate': self.success_rate,
            'completion_rate': self.completion_rate,
            'avg_service_duration': self.avg_service_duration,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'is_active': self.is_active
        }


class SocialServicesDatabase:
    """Professional social services database for case management"""
    
    def __init__(self, db_path: str = "social_services.db"):
        self.db_path = db_path
        self.connection = None
        self.create_tables()
    
    def connect(self):
        """Connect to SQLite database"""
        try:
            # Use check_same_thread=False for Flask threading compatibility
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to social services database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to social services database: {e}")
            raise
    
    def create_tables(self):
        """Create comprehensive social services database schema"""
        if not self.connection:
            self.connect()
        
        # Service Providers table
        create_providers_sql = """
        CREATE TABLE IF NOT EXISTS service_providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            organization_type TEXT,
            primary_contact TEXT,
            referral_contact TEXT,
            emergency_contact TEXT,
            address TEXT,
            city TEXT,
            county TEXT,
            state TEXT DEFAULT 'CA',
            zip_code TEXT,
            phone_main TEXT,
            phone_referral TEXT,
            fax TEXT,
            email TEXT,
            website TEXT,
            hours_operation TEXT,
            appointment_types TEXT,
            languages_offered TEXT,
            accessibility_features TEXT,
            accreditation_status TEXT,
            license_number TEXT,
            accepts_medicaid INTEGER DEFAULT 1,
            sliding_scale_available INTEGER DEFAULT 0,
            current_capacity INTEGER DEFAULT 0,
            total_capacity INTEGER DEFAULT 0,
            waitlist_length INTEGER DEFAULT 0,
            avg_wait_time_days INTEGER DEFAULT 0,
            background_check_policy TEXT,
            restricted_offenses TEXT,
            case_by_case_review INTEGER DEFAULT 1,
            service_radius_miles INTEGER DEFAULT 0,
            provides_transportation INTEGER DEFAULT 0,
            mobile_services INTEGER DEFAULT 0,
            telehealth_available INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,
            completion_rate REAL DEFAULT 0.0,
            client_satisfaction REAL DEFAULT 0.0,
            referral_volume_monthly INTEGER DEFAULT 0,
            created_at TEXT,
            last_updated TEXT,
            is_active INTEGER DEFAULT 1,
            notes TEXT
        );
        """
        
        # Services table
        create_services_sql = """
        CREATE TABLE IF NOT EXISTS social_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id TEXT UNIQUE NOT NULL,
            provider_id TEXT NOT NULL,
            service_category TEXT NOT NULL,
            service_type TEXT,
            service_level TEXT,
            description TEXT,
            eligibility_criteria TEXT,
            documentation_required TEXT,
            referral_process TEXT,
            intake_requirements TEXT,
            age_restrictions TEXT,
            gender_restrictions TEXT,
            sobriety_required INTEGER DEFAULT 0,
            insurance_required INTEGER DEFAULT 0,
            residency_required INTEGER DEFAULT 0,
            serves_veterans INTEGER DEFAULT 0,
            serves_disabled INTEGER DEFAULT 0,
            serves_pregnant_women INTEGER DEFAULT 0,
            serves_lgbtq INTEGER DEFAULT 0,
            serves_trafficking_survivors INTEGER DEFAULT 0,
            cost_structure TEXT,
            insurance_accepted TEXT,
            sliding_scale_fees INTEGER DEFAULT 0,
            free_services INTEGER DEFAULT 0,
            current_availability TEXT,
            waitlist_status TEXT,
            estimated_wait_time TEXT,
            success_rate REAL DEFAULT 0.0,
            completion_rate REAL DEFAULT 0.0,
            avg_service_duration TEXT,
            created_at TEXT,
            last_updated TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (provider_id) REFERENCES service_providers (provider_id)
        );
        """
        
        # Case management tables
        create_clients_sql = """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL,
            case_manager_id TEXT,
            first_name TEXT,
            last_name TEXT,
            date_of_birth TEXT,
            gender TEXT,
            primary_phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT,
            county TEXT,
            zip_code TEXT,
            emergency_contact TEXT,
            emergency_phone TEXT,
            is_veteran INTEGER DEFAULT 0,
            has_disability INTEGER DEFAULT 0,
            special_populations TEXT,
            background_summary TEXT,
            sobriety_status TEXT,
            insurance_status TEXT,
            housing_status TEXT,
            employment_status TEXT,
            service_priorities TEXT,
            created_at TEXT,
            last_updated TEXT,
            is_active INTEGER DEFAULT 1
        );
        """
        
        create_referrals_sql = """
        CREATE TABLE IF NOT EXISTS service_referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referral_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            case_manager_id TEXT NOT NULL,
            provider_id TEXT NOT NULL,
            service_id TEXT NOT NULL,
            referral_date TEXT,
            priority_level TEXT,
            status TEXT,
            expected_start_date TEXT,
            actual_start_date TEXT,
            completion_date TEXT,
            notes TEXT,
            barriers_encountered TEXT,
            outcome TEXT,
            satisfaction_rating INTEGER,
            created_at TEXT,
            last_updated TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (client_id),
            FOREIGN KEY (provider_id) REFERENCES service_providers (provider_id),
            FOREIGN KEY (service_id) REFERENCES social_services (service_id)
        );
        """
        
        create_tasks_sql = """
        CREATE TABLE IF NOT EXISTS case_management_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            case_manager_id TEXT NOT NULL,
            client_id TEXT,
            referral_id TEXT,
            task_type TEXT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT,
            due_date TEXT,
            status TEXT,
            assigned_to TEXT,
            completed_date TEXT,
            completion_notes TEXT,
            created_at TEXT,
            last_updated TEXT
        );
        """
        
        try:
            self.connection.execute(create_providers_sql)
            self.connection.execute(create_services_sql)
            self.connection.execute(create_clients_sql)
            self.connection.execute(create_referrals_sql)
            self.connection.execute(create_tasks_sql)
            self.connection.commit()
            logger.info("Social services database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create social services tables: {e}")
            raise
    
    def save_service_provider(self, provider: ServiceProvider) -> int:
        """Save a service provider to the database"""
        if not self.connection:
            self.connect()
        
        insert_sql = """
        INSERT INTO service_providers (
            provider_id, name, organization_type, primary_contact, referral_contact, emergency_contact,
            address, city, county, state, zip_code, phone_main, phone_referral, fax, email, website,
            hours_operation, appointment_types, languages_offered, accessibility_features,
            accreditation_status, license_number, accepts_medicaid, sliding_scale_available,
            current_capacity, total_capacity, waitlist_length, avg_wait_time_days,
            background_check_policy, restricted_offenses, case_by_case_review,
            service_radius_miles, provides_transportation, mobile_services, telehealth_available,
            success_rate, completion_rate, client_satisfaction, referral_volume_monthly,
            created_at, last_updated, is_active, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                provider.provider_id, provider.name, provider.organization_type,
                provider.primary_contact, provider.referral_contact, provider.emergency_contact,
                provider.address, provider.city, provider.county, provider.state, provider.zip_code,
                provider.phone_main, provider.phone_referral, provider.fax, provider.email, provider.website,
                provider.hours_operation, provider.appointment_types, provider.languages_offered,
                provider.accessibility_features, provider.accreditation_status, provider.license_number,
                provider.accepts_medicaid, provider.sliding_scale_available,
                provider.current_capacity, provider.total_capacity, provider.waitlist_length,
                provider.avg_wait_time_days, provider.background_check_policy, provider.restricted_offenses,
                provider.case_by_case_review, provider.service_radius_miles, provider.provides_transportation,
                provider.mobile_services, provider.telehealth_available, provider.success_rate,
                provider.completion_rate, provider.client_satisfaction, provider.referral_volume_monthly,
                provider.created_at, provider.last_updated, provider.is_active, provider.notes
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save service provider: {e}")
            raise
    
    def save_social_service(self, service: SocialService) -> int:
        """Save a social service to the database"""
        if not self.connection:
            self.connect()
        
        insert_sql = """
        INSERT INTO social_services (
            service_id, provider_id, service_category, service_type, service_level,
            description, eligibility_criteria, documentation_required, referral_process, intake_requirements,
            age_restrictions, gender_restrictions, sobriety_required, insurance_required, residency_required,
            serves_veterans, serves_disabled, serves_pregnant_women, serves_lgbtq, serves_trafficking_survivors,
            cost_structure, insurance_accepted, sliding_scale_fees, free_services,
            current_availability, waitlist_status, estimated_wait_time,
            success_rate, completion_rate, avg_service_duration,
            created_at, last_updated, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                service.service_id, service.provider_id, service.service_category, service.service_type,
                service.service_level, service.description, service.eligibility_criteria,
                service.documentation_required, service.referral_process, service.intake_requirements,
                service.age_restrictions, service.gender_restrictions, service.sobriety_required,
                service.insurance_required, service.residency_required, service.serves_veterans,
                service.serves_disabled, service.serves_pregnant_women, service.serves_lgbtq,
                service.serves_trafficking_survivors, service.cost_structure, service.insurance_accepted,
                service.sliding_scale_fees, service.free_services, service.current_availability,
                service.waitlist_status, service.estimated_wait_time, service.success_rate,
                service.completion_rate, service.avg_service_duration, service.created_at,
                service.last_updated, service.is_active
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save social service: {e}")
            raise
    
    def search_services(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search social services with professional filtering"""
        if not self.connection:
            self.connect()
        
        # Build dynamic SQL query
        base_query = """
        SELECT p.*, s.*,
               p.name as provider_name,
               s.service_category,
               s.service_type,
               s.description as service_description
        FROM service_providers p
        LEFT JOIN social_services s ON p.provider_id = s.provider_id
        WHERE p.is_active = 1 AND (s.is_active = 1 OR s.is_active IS NULL)
        """
        params = []
        
        # Text search filter - CRITICAL FIX for "dentist" searches
        if filters.get('keywords'):
            keywords = filters['keywords'].lower()
            base_query += """ AND (
                LOWER(p.name) LIKE ? OR
                LOWER(s.service_category) LIKE ? OR
                LOWER(s.service_type) LIKE ? OR
                LOWER(s.description) LIKE ?
            )"""
            keyword_param = f"%{keywords}%"
            params.extend([keyword_param, keyword_param, keyword_param, keyword_param])
        
        # Service category filter
        if filters.get('service_category'):
            base_query += " AND s.service_category = ?"
            params.append(filters['service_category'])
        
        # Location filters
        if filters.get('city'):
            base_query += " AND p.city LIKE ?"
            params.append(f"%{filters['city']}%")
        
        if filters.get('county'):
            base_query += " AND p.county = ?"
            params.append(filters['county'])
        
        # Organization type
        if filters.get('organization_type'):
            base_query += " AND p.organization_type = ?"
            params.append(filters['organization_type'])
        
        # Background check policy
        if filters.get('background_friendly'):
            base_query += " AND (p.background_check_policy LIKE '%background-friendly%' OR p.case_by_case_review = 1)"
        
        # Insurance
        if filters.get('accepts_medicaid'):
            base_query += " AND p.accepts_medicaid = 1"
        
        if filters.get('sliding_scale'):
            base_query += " AND (p.sliding_scale_available = 1 OR s.sliding_scale_fees = 1)"
        
        # Special populations
        if filters.get('serves_veterans'):
            base_query += " AND s.serves_veterans = 1"
        
        if filters.get('serves_disabled'):
            base_query += " AND s.serves_disabled = 1"
        
        # Availability
        if filters.get('current_availability'):
            base_query += " AND s.current_availability = ?"
            params.append(filters['current_availability'])
        
        # Service level
        if filters.get('service_level'):
            base_query += " AND s.service_level = ?"
            params.append(filters['service_level'])
        
        # Sobriety requirements
        if filters.get('sobriety_required') is not None:
            base_query += " AND s.sobriety_required = ?"
            params.append(1 if filters['sobriety_required'] else 0)
        
        # Gender restrictions
        if filters.get('gender_restrictions'):
            base_query += " AND (s.gender_restrictions = ? OR s.gender_restrictions = '' OR s.gender_restrictions IS NULL)"
            params.append(filters['gender_restrictions'])
        
        # Transportation
        if filters.get('provides_transportation'):
            base_query += " AND p.provides_transportation = 1"
        
        if filters.get('mobile_services'):
            base_query += " AND p.mobile_services = 1"
        
        if filters.get('telehealth_available'):
            base_query += " AND p.telehealth_available = 1"
        
        # Ordering and limiting
        base_query += " ORDER BY p.name, s.service_category"
        
        if filters.get('limit'):
            base_query += f" LIMIT {filters['limit']}"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(base_query, params)
            rows = cursor.fetchall()
            
            # Convert to dictionaries
            results = []
            for row in rows:
                result_dict = dict(row)
                results.append(result_dict)
            
            return results
        except Exception as e:
            logger.error(f"Failed to search social services: {e}")
            raise
    
    def get_service_categories(self) -> List[str]:
        """Get all available service categories"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT DISTINCT service_category FROM social_services WHERE service_category != '' AND is_active = 1")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get service categories: {e}")
            return []
    
    def get_provider_statistics(self) -> Dict[str, Any]:
        """Get comprehensive provider network statistics"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Total providers
            cursor.execute("SELECT COUNT(*) FROM service_providers WHERE is_active = 1")
            total_providers = cursor.fetchone()[0]
            
            # Total services
            cursor.execute("SELECT COUNT(*) FROM social_services WHERE is_active = 1")
            total_services = cursor.fetchone()[0]
            
            # Background-friendly providers
            cursor.execute("""
                SELECT COUNT(*) FROM service_providers 
                WHERE is_active = 1 AND (background_check_policy LIKE '%background-friendly%' OR case_by_case_review = 1)
            """)
            background_friendly_providers = cursor.fetchone()[0]
            
            # By organization type
            cursor.execute("""
                SELECT organization_type, COUNT(*) 
                FROM service_providers 
                WHERE is_active = 1 AND organization_type != '' 
                GROUP BY organization_type
            """)
            by_org_type = dict(cursor.fetchall())
            
            # By service category
            cursor.execute("""
                SELECT service_category, COUNT(*) 
                FROM social_services 
                WHERE is_active = 1 AND service_category != '' 
                GROUP BY service_category
            """)
            by_service_category = dict(cursor.fetchall())
            
            # By county
            cursor.execute("""
                SELECT county, COUNT(*) 
                FROM service_providers 
                WHERE is_active = 1 AND county != '' 
                GROUP BY county
            """)
            by_county = dict(cursor.fetchall())
            
            # Average capacity utilization
            cursor.execute("""
                SELECT AVG(CASE WHEN total_capacity > 0 THEN (current_capacity * 100.0 / total_capacity) ELSE 0 END)
                FROM service_providers 
                WHERE is_active = 1 AND total_capacity > 0
            """)
            avg_capacity_utilization = cursor.fetchone()[0] or 0
            
            return {
                'total_providers': total_providers,
                'total_services': total_services,
                'background_friendly_providers': background_friendly_providers,
                'background_friendly_percentage': (background_friendly_providers / total_providers * 100) if total_providers > 0 else 0,
                'by_organization_type': by_org_type,
                'by_service_category': by_service_category,
                'by_county': by_county,
                'avg_capacity_utilization': avg_capacity_utilization
            }
        except Exception as e:
            logger.error(f"Failed to get provider statistics: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Social services database connection closed")