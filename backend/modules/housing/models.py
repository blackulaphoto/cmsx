#!/usr/bin/env python3
"""
Housing Database Models for Second Chance Jobs Platform
SQLite-based housing resource database with comprehensive search capabilities
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class HousingResource:
    """Housing resource data model"""
    
    def __init__(self, **kwargs):
        # Basic Info
        self.id = kwargs.get('id')
        self.facility_name = kwargs.get('facility_name', '')
        self.physical_address = kwargs.get('physical_address', '')
        self.city = kwargs.get('city', '')
        self.state = kwargs.get('state', 'CA')
        self.zip_code = kwargs.get('zip_code', '')
        self.county = kwargs.get('county', '')
        
        # Contact Info
        self.primary_phone = kwargs.get('primary_phone', '')
        self.secondary_phone = kwargs.get('secondary_phone', '')
        self.website_url = kwargs.get('website_url', '')
        self.email_contact = kwargs.get('email_contact', '')
        
        # Program Details
        self.program_type = kwargs.get('program_type', '')
        self.target_population = kwargs.get('target_population', '')
        self.capacity = kwargs.get('capacity', '')
        self.length_of_stay = kwargs.get('length_of_stay', '')
        self.hours_of_operation = kwargs.get('hours_of_operation', '')
        
        # Eligibility & Requirements
        self.eligibility_criteria = kwargs.get('eligibility_criteria', '')
        self.required_documentation = kwargs.get('required_documentation', '')
        self.sobriety_requirements = kwargs.get('sobriety_requirements', '')
        self.criminal_background_restrictions = kwargs.get('criminal_background_restrictions', '')
        self.mental_health_requirements = kwargs.get('mental_health_requirements', '')
        self.medical_requirements = kwargs.get('medical_requirements', '')
        
        # Financial
        self.insurance_accepted = kwargs.get('insurance_accepted', '')
        self.private_pay_options = kwargs.get('private_pay_options', '')
        self.sliding_scale_fees = kwargs.get('sliding_scale_fees', '')
        self.financial_assistance_programs = kwargs.get('financial_assistance_programs', '')
        self.payment_plans_available = kwargs.get('payment_plans_available', '')
        
        # Process & Services
        self.referral_requirements = kwargs.get('referral_requirements', '')
        self.intake_process = kwargs.get('intake_process', '')
        self.wait_list_information = kwargs.get('wait_list_information', '')
        self.contact_person = kwargs.get('contact_person', '')
        self.clinical_services = kwargs.get('clinical_services', '')
        self.life_skills_training = kwargs.get('life_skills_training', '')
        self.job_placement_assistance = kwargs.get('job_placement_assistance', '')
        self.transportation_services = kwargs.get('transportation_services', '')
        self.medical_services = kwargs.get('medical_services', '')
        self.additional_support_services = kwargs.get('additional_support_services', '')
        
        # Metadata
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        
        # Derived/Computed fields for search
        self.background_friendly = self._is_background_friendly()
        self.price_range = self._extract_price_range()
        self.gender_restrictions = self._extract_gender_restrictions()
        self.pets_allowed = self._check_pets_allowed()
        self.couples_accepted = self._check_couples_accepted()
        
    def _is_background_friendly(self) -> bool:
        """Determine if facility is background-friendly"""
        restrictions = self.criminal_background_restrictions.lower()
        
        # Background-friendly indicators
        friendly_indicators = [
            'accepts individuals with criminal background',
            'case-by-case evaluation',
            'specifically serves justice-involved',
            'accepts criminal history',
            'background check may be required',
            'second chance friendly'
        ]
        
        # Non-background-friendly indicators
        unfriendly_indicators = [
            'no criminal background',
            'background check required',
            'clean criminal record',
            'no criminal history'
        ]
        
        for indicator in friendly_indicators:
            if indicator in restrictions:
                return True
                
        for indicator in unfriendly_indicators:
            if indicator in restrictions:
                return False
                
        # Default to neutral if unclear
        return True
    
    def _extract_price_range(self) -> Dict[str, Optional[float]]:
        """Extract price range from various payment fields"""
        price_text = f"{self.private_pay_options} {self.sliding_scale_fees}".lower()
        
        # Extract price ranges using regex patterns
        import re
        price_patterns = [
            r'\$(\d+)-\$?(\d+)',  # $500-$1000
            r'\$(\d+)/month',     # $500/month
            r'\$(\d+)',           # $500
            r'(\d+)% of income',  # 30% of income
        ]
        
        min_price = None
        max_price = None
        
        for pattern in price_patterns:
            matches = re.findall(pattern, price_text)
            if matches:
                if len(matches[0]) == 2:  # Range pattern
                    min_price = float(matches[0][0])
                    max_price = float(matches[0][1])
                else:  # Single price
                    min_price = float(matches[0])
                    max_price = min_price
                break
        
        return {'min': min_price, 'max': max_price}
    
    def _extract_gender_restrictions(self) -> str:
        """Extract gender restrictions from target population"""
        target = self.target_population.lower()
        
        if 'men' in target and 'women' not in target:
            return 'male_only'
        elif 'women' in target and 'men' not in target:
            return 'female_only'
        elif 'co-ed' in target:
            return 'co_ed'
        else:
            return 'all_genders'
    
    def _check_pets_allowed(self) -> bool:
        """Check if pets are allowed"""
        # This would need to be inferred from descriptions or added manually
        return False  # Default to not allowed unless specified
    
    def _check_couples_accepted(self) -> bool:
        """Check if couples are accepted"""
        target = self.target_population.lower()
        services = self.additional_support_services.lower()
        
        indicators = ['couples', 'families', 'family', 'married']
        return any(indicator in target or indicator in services for indicator in indicators)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'facility_name': self.facility_name,
            'physical_address': self.physical_address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'county': self.county,
            'primary_phone': self.primary_phone,
            'secondary_phone': self.secondary_phone,
            'website_url': self.website_url,
            'email_contact': self.email_contact,
            'program_type': self.program_type,
            'target_population': self.target_population,
            'capacity': self.capacity,
            'length_of_stay': self.length_of_stay,
            'hours_of_operation': self.hours_of_operation,
            'eligibility_criteria': self.eligibility_criteria,
            'required_documentation': self.required_documentation,
            'sobriety_requirements': self.sobriety_requirements,
            'criminal_background_restrictions': self.criminal_background_restrictions,
            'mental_health_requirements': self.mental_health_requirements,
            'medical_requirements': self.medical_requirements,
            'insurance_accepted': self.insurance_accepted,
            'private_pay_options': self.private_pay_options,
            'sliding_scale_fees': self.sliding_scale_fees,
            'financial_assistance_programs': self.financial_assistance_programs,
            'payment_plans_available': self.payment_plans_available,
            'referral_requirements': self.referral_requirements,
            'intake_process': self.intake_process,
            'wait_list_information': self.wait_list_information,
            'contact_person': self.contact_person,
            'clinical_services': self.clinical_services,
            'life_skills_training': self.life_skills_training,
            'job_placement_assistance': self.job_placement_assistance,
            'transportation_services': self.transportation_services,
            'medical_services': self.medical_services,
            'additional_support_services': self.additional_support_services,
            'last_updated': self.last_updated,
            'created_at': self.created_at,
            'background_friendly': self.background_friendly,
            'price_range': self.price_range,
            'gender_restrictions': self.gender_restrictions,
            'pets_allowed': self.pets_allowed,
            'couples_accepted': self.couples_accepted
        }


class HousingDatabase:
    """Housing database manager with comprehensive search capabilities"""
    
    def __init__(self, db_path: str = "databases/housing_resources.db"):
        self.db_path = db_path
        self.connection = None
        self.create_tables()
    
    def connect(self):
        """Connect to SQLite database"""
        try:
            # Use check_same_thread=False for Flask threading compatibility
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            logger.info(f"Connected to housing database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to housing database: {e}")
            raise
    
    def create_tables(self):
        """Create housing resources table with comprehensive schema"""
        if not self.connection:
            self.connect()
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS housing_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility_name TEXT NOT NULL,
            physical_address TEXT,
            city TEXT,
            state TEXT DEFAULT 'CA',
            zip_code TEXT,
            county TEXT,
            primary_phone TEXT,
            secondary_phone TEXT,
            website_url TEXT,
            email_contact TEXT,
            program_type TEXT,
            target_population TEXT,
            capacity TEXT,
            length_of_stay TEXT,
            hours_of_operation TEXT,
            eligibility_criteria TEXT,
            required_documentation TEXT,
            sobriety_requirements TEXT,
            criminal_background_restrictions TEXT,
            mental_health_requirements TEXT,
            medical_requirements TEXT,
            insurance_accepted TEXT,
            private_pay_options TEXT,
            sliding_scale_fees TEXT,
            financial_assistance_programs TEXT,
            payment_plans_available TEXT,
            referral_requirements TEXT,
            intake_process TEXT,
            wait_list_information TEXT,
            contact_person TEXT,
            clinical_services TEXT,
            life_skills_training TEXT,
            job_placement_assistance TEXT,
            transportation_services TEXT,
            medical_services TEXT,
            additional_support_services TEXT,
            last_updated TEXT,
            created_at TEXT,
            background_friendly INTEGER DEFAULT 1,
            price_min REAL,
            price_max REAL,
            gender_restrictions TEXT,
            pets_allowed INTEGER DEFAULT 0,
            couples_accepted INTEGER DEFAULT 0
        );
        """
        
        try:
            self.connection.execute(create_table_sql)
            self.connection.commit()
            logger.info("Housing resources table created successfully")
        except Exception as e:
            logger.error(f"Failed to create housing resources table: {e}")
            raise
    
    def save_housing_resource(self, resource: HousingResource) -> int:
        """Save a housing resource to the database"""
        if not self.connection:
            self.connect()
        
        insert_sql = """
        INSERT INTO housing_resources (
            facility_name, physical_address, city, state, zip_code, county,
            primary_phone, secondary_phone, website_url, email_contact,
            program_type, target_population, capacity, length_of_stay, hours_of_operation,
            eligibility_criteria, required_documentation, sobriety_requirements,
            criminal_background_restrictions, mental_health_requirements, medical_requirements,
            insurance_accepted, private_pay_options, sliding_scale_fees,
            financial_assistance_programs, payment_plans_available,
            referral_requirements, intake_process, wait_list_information, contact_person,
            clinical_services, life_skills_training, job_placement_assistance,
            transportation_services, medical_services, additional_support_services,
            last_updated, created_at, background_friendly, price_min, price_max,
            gender_restrictions, pets_allowed, couples_accepted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                resource.facility_name, resource.physical_address, resource.city,
                resource.state, resource.zip_code, resource.county,
                resource.primary_phone, resource.secondary_phone, resource.website_url,
                resource.email_contact, resource.program_type, resource.target_population,
                resource.capacity, resource.length_of_stay, resource.hours_of_operation,
                resource.eligibility_criteria, resource.required_documentation,
                resource.sobriety_requirements, resource.criminal_background_restrictions,
                resource.mental_health_requirements, resource.medical_requirements,
                resource.insurance_accepted, resource.private_pay_options,
                resource.sliding_scale_fees, resource.financial_assistance_programs,
                resource.payment_plans_available, resource.referral_requirements,
                resource.intake_process, resource.wait_list_information, resource.contact_person,
                resource.clinical_services, resource.life_skills_training,
                resource.job_placement_assistance, resource.transportation_services,
                resource.medical_services, resource.additional_support_services,
                resource.last_updated, resource.created_at, resource.background_friendly,
                resource.price_range['min'], resource.price_range['max'],
                resource.gender_restrictions, resource.pets_allowed, resource.couples_accepted
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save housing resource: {e}")
            raise
    
    def search_housing(self, filters: Dict[str, Any]) -> List[HousingResource]:
        """Search housing resources with comprehensive filtering"""
        if not self.connection:
            self.connect()
        
        # Build dynamic SQL query based on filters
        base_query = "SELECT * FROM housing_resources WHERE 1=1"
        params = []
        
        # Location filters
        if filters.get('city'):
            base_query += " AND city LIKE ?"
            params.append(f"%{filters['city']}%")
        
        if filters.get('county'):
            base_query += " AND county LIKE ?"
            params.append(f"%{filters['county']}%")
        
        if filters.get('zip_code'):
            base_query += " AND zip_code = ?"
            params.append(filters['zip_code'])
        
        # Housing type filters
        if filters.get('program_type'):
            base_query += " AND program_type LIKE ?"
            params.append(f"%{filters['program_type']}%")
        
        # Background check policy
        if filters.get('background_friendly'):
            base_query += " AND background_friendly = ?"
            params.append(1 if filters['background_friendly'] else 0)
        
        # Gender restrictions
        if filters.get('gender_restrictions'):
            base_query += " AND gender_restrictions = ?"
            params.append(filters['gender_restrictions'])
        
        # Sobriety requirements
        if filters.get('sobriety_required') is not None:
            if filters['sobriety_required']:
                base_query += " AND sobriety_requirements != ''"
            else:
                base_query += " AND sobriety_requirements = ''"
        
        # Price range
        if filters.get('price_min') is not None:
            base_query += " AND (price_min >= ? OR price_min IS NULL)"
            params.append(filters['price_min'])
        
        if filters.get('price_max') is not None:
            base_query += " AND (price_max <= ? OR price_max IS NULL)"
            params.append(filters['price_max'])
        
        # Couples and pets
        if filters.get('couples_accepted'):
            base_query += " AND couples_accepted = ?"
            params.append(1 if filters['couples_accepted'] else 0)
        
        if filters.get('pets_allowed'):
            base_query += " AND pets_allowed = ?"
            params.append(1 if filters['pets_allowed'] else 0)
        
        # Insurance accepted
        if filters.get('insurance_type'):
            base_query += " AND insurance_accepted LIKE ?"
            params.append(f"%{filters['insurance_type']}%")
        
        # Services offered
        if filters.get('services_needed'):
            for service in filters['services_needed']:
                base_query += " AND (clinical_services LIKE ? OR additional_support_services LIKE ? OR life_skills_training LIKE ? OR job_placement_assistance LIKE ? OR medical_services LIKE ?)"
                service_pattern = f"%{service}%"
                params.extend([service_pattern, service_pattern, service_pattern, service_pattern, service_pattern])
        
        # Level of care (inferred from program type and services)
        if filters.get('level_of_care'):
            level = filters['level_of_care'].lower()
            if level == 'independent':
                base_query += " AND (program_type LIKE '%SRO%' OR program_type LIKE '%Independent%')"
            elif level == 'supervised':
                base_query += " AND (program_type LIKE '%Transitional%' OR program_type LIKE '%Sober Living%')"
            elif level == '24/7':
                base_query += " AND hours_of_operation LIKE '%24/7%'"
            elif level == 'intensive':
                base_query += " AND (program_type LIKE '%PHP%' OR program_type LIKE '%IOP%')"
        
        # Wait list filter
        if filters.get('no_wait_list'):
            base_query += " AND (wait_list_information = '' OR wait_list_information IS NULL OR wait_list_information NOT LIKE '%wait%')"
        
        # Immediate availability
        if filters.get('immediate_availability'):
            base_query += " AND (wait_list_information LIKE '%immediate%' OR wait_list_information LIKE '%available%' OR wait_list_information = '')"
        
        # Ordering
        base_query += " ORDER BY facility_name"
        
        # Limit results
        if filters.get('limit'):
            base_query += f" LIMIT {filters['limit']}"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(base_query, params)
            rows = cursor.fetchall()
            
            # Convert rows to HousingResource objects
            resources = []
            for row in rows:
                resource_dict = dict(row)
                resource_dict['price_range'] = {
                    'min': resource_dict.get('price_min'),
                    'max': resource_dict.get('price_max')
                }
                resources.append(HousingResource(**resource_dict))
            
            return resources
        except Exception as e:
            logger.error(f"Failed to search housing resources: {e}")
            raise
    
    def get_housing_resource(self, resource_id: int) -> Optional[HousingResource]:
        """Get a specific housing resource by ID"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM housing_resources WHERE id = ?", (resource_id,))
            row = cursor.fetchone()
            
            if row:
                resource_dict = dict(row)
                resource_dict['price_range'] = {
                    'min': resource_dict.get('price_min'),
                    'max': resource_dict.get('price_max')
                }
                return HousingResource(**resource_dict)
            return None
        except Exception as e:
            logger.error(f"Failed to get housing resource: {e}")
            raise
    
    def get_all_housing_types(self) -> List[str]:
        """Get all distinct housing/program types"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT DISTINCT program_type FROM housing_resources WHERE program_type != ''")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get housing types: {e}")
            return []
    
    def get_all_counties(self) -> List[str]:
        """Get all distinct counties"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT DISTINCT county FROM housing_resources WHERE county != ''")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get counties: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get housing database statistics"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Total resources
            cursor.execute("SELECT COUNT(*) FROM housing_resources")
            total_resources = cursor.fetchone()[0]
            
            # Background-friendly count
            cursor.execute("SELECT COUNT(*) FROM housing_resources WHERE background_friendly = 1")
            background_friendly_count = cursor.fetchone()[0]
            
            # By program type
            cursor.execute("""
                SELECT program_type, COUNT(*) 
                FROM housing_resources 
                WHERE program_type != '' 
                GROUP BY program_type
            """)
            by_program_type = dict(cursor.fetchall())
            
            # By county
            cursor.execute("""
                SELECT county, COUNT(*) 
                FROM housing_resources 
                WHERE county != '' 
                GROUP BY county
            """)
            by_county = dict(cursor.fetchall())
            
            return {
                'total_resources': total_resources,
                'background_friendly_count': background_friendly_count,
                'background_friendly_percentage': (background_friendly_count / total_resources * 100) if total_resources > 0 else 0,
                'by_program_type': by_program_type,
                'by_county': by_county
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def get_resource_by_name(self, facility_name: str) -> Optional[HousingResource]:
        """Get a housing resource by facility name"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM housing_resources WHERE facility_name = ?", (facility_name,))
            row = cursor.fetchone()
            
            if row:
                resource_dict = dict(row)
                resource_dict['price_range'] = {
                    'min': resource_dict.get('price_min'),
                    'max': resource_dict.get('price_max')
                }
                return HousingResource(**resource_dict)
            return None
        except Exception as e:
            logger.error(f"Failed to get housing resource by name: {e}")
            return None
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Housing database connection closed")
    
    def search_housing_resources(self, filters: Dict[str, Any] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """Alias for search_housing method for FastAPI router compatibility"""
        if filters is None:
            filters = {}
        
        if max_results and max_results > 0:
            filters['limit'] = max_results
        
        try:
            housing_resources = self.search_housing(filters)
            # Convert HousingResource objects to dictionaries for JSON serialization
            return [
                {
                    'facility_name': resource.facility_name,
                    'physical_address': resource.physical_address,
                    'city': resource.city,
                    'state': resource.state,
                    'zip_code': resource.zip_code,
                    'county': resource.county,
                    'primary_phone': resource.primary_phone,
                    'program_type': resource.program_type,
                    'target_population': resource.target_population,
                    'capacity': resource.capacity,
                    'background_friendly': getattr(resource, 'background_friendly', True),
                    'website_url': resource.website_url,
                    'email_contact': resource.email_contact
                }
                for resource in housing_resources
            ]
        except Exception as e:
            logger.error(f"Error in search_housing_resources: {e}")
            return []
    
    def get_housing_types(self) -> List[str]:
        """Get distinct housing types for the router"""
        return self.get_all_housing_types()
    
    def get_counties(self) -> List[str]:
        """Get distinct counties for the router"""
        return self.get_all_counties()
    
    def get_cities(self) -> List[str]:
        """Get distinct cities for the router"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT DISTINCT city FROM housing_resources WHERE city IS NOT NULL AND city != '' ORDER BY city")
            cities = [row[0] for row in cursor.fetchall()]
            return cities
        except Exception as e:
            logger.error(f"Failed to get cities: {e}")
            return []
    
    def get_housing_resource(self, resource_id: str) -> Dict[str, Any]:
        """Get housing resource details for the router"""
        try:
            resource_id_int = int(resource_id) if resource_id.isdigit() else 1
            resource = self.get_housing_resource_by_id(resource_id_int)
            if resource:
                return {
                    'facility_name': resource.facility_name,
                    'physical_address': resource.physical_address,
                    'city': resource.city,
                    'state': resource.state,
                    'county': resource.county,
                    'primary_phone': resource.primary_phone,
                    'program_type': resource.program_type,
                    'target_population': resource.target_population,
                    'background_friendly': getattr(resource, 'background_friendly', True),
                    'website_url': resource.website_url,
                    'email_contact': resource.email_contact
                }
            return None
        except Exception as e:
            logger.error(f"Error getting housing resource: {e}")
            return None
    
    def get_housing_statistics(self) -> Dict[str, Any]:
        """Get housing resource statistics"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Total resources
            cursor.execute("SELECT COUNT(*) FROM housing_resources")
            total_resources = cursor.fetchone()[0]
            
            # Background-friendly count
            cursor.execute("SELECT COUNT(*) FROM housing_resources WHERE background_friendly = 1")
            background_friendly_count = cursor.fetchone()[0]
            
            # By program type
            cursor.execute("SELECT program_type, COUNT(*) FROM housing_resources GROUP BY program_type")
            by_program_type = dict(cursor.fetchall())
            
            return {
                'total_resources': total_resources,
                'background_friendly': background_friendly_count,
                'background_friendly_percentage': (background_friendly_count / total_resources * 100) if total_resources > 0 else 0,
                'by_program_type': by_program_type
            }
        except Exception as e:
            logger.error(f"Error getting housing statistics: {e}")
            return {
                'total_resources': 0,
                'background_friendly': 0,
                'background_friendly_percentage': 0,
                'by_program_type': {}
            }
    
    def create_housing_application(self, application_data: Dict[str, Any]) -> str:
        """Create a housing application record"""
        if not self.connection:
            self.connect()
        
        application_id = f"housing_app_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO housing_applications 
                (application_id, client_id, housing_resource_id, application_date, priority_level, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Submitted')
            """, (
                application_id,
                application_data.get('client_id'),
                application_data.get('housing_resource_id'),
                application_data.get('application_date', datetime.now().isoformat()),
                application_data.get('priority_level', 'Medium'),
                application_data.get('notes', '')
            ))
            self.connection.commit()
            return application_id
        except Exception as e:
            logger.error(f"Error creating housing application: {e}")
            return ""
    
    def get_client_housing_applications(self, client_id: str) -> List[Dict[str, Any]]:
        """Get housing applications for a client"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT ha.*, hr.facility_name 
                FROM housing_applications ha
                LEFT JOIN housing_resources hr ON ha.housing_resource_id = hr.id
                WHERE ha.client_id = ?
                ORDER BY ha.application_date DESC
            """, (client_id,))
            
            applications = []
            for row in cursor.fetchall():
                applications.append({
                    'application_id': row['application_id'],
                    'housing_resource_id': row['housing_resource_id'],
                    'facility_name': row['facility_name'],
                    'application_date': row['application_date'],
                    'status': row['status'],
                    'priority_level': row['priority_level'],
                    'notes': row['notes']
                })
            return applications
        except Exception as e:
            logger.error(f"Error getting client housing applications: {e}")
            return []