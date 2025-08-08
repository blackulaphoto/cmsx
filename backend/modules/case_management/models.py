"""
Case Management Models
Data models for client management, case notes, and referrals
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
import uuid
import json


class Client:
    """Client model with comprehensive intake information"""
    
    def __init__(self, **kwargs):
        # Core identification
        self.client_id = kwargs.get('client_id', f"client_{str(uuid.uuid4())[:8]}")
        
        # Personal Information
        self.first_name = kwargs.get('first_name', '')
        self.last_name = kwargs.get('last_name', '')
        self.date_of_birth = kwargs.get('date_of_birth', '')
        self.phone = kwargs.get('phone', '')
        self.email = kwargs.get('email', '')
        
        # Address Information
        self.address = kwargs.get('address', '')
        self.city = kwargs.get('city', '')
        self.state = kwargs.get('state', 'CA')
        self.zip_code = kwargs.get('zip_code', '')
        
        # Emergency Contact
        self.emergency_contact_name = kwargs.get('emergency_contact_name', '')
        self.emergency_contact_phone = kwargs.get('emergency_contact_phone', '')
        self.emergency_contact_relationship = kwargs.get('emergency_contact_relationship', '')
        
        # Case Management
        self.case_manager_id = kwargs.get('case_manager_id', '')
        self.risk_level = kwargs.get('risk_level', 'Medium')  # Low, Medium, High
        self.case_status = kwargs.get('case_status', 'Active')  # Active, Inactive, Closed
        
        # Service Status
        self.housing_status = kwargs.get('housing_status', 'Unknown')
        self.employment_status = kwargs.get('employment_status', 'Unemployed')
        self.benefits_status = kwargs.get('benefits_status', 'Not Applied')
        self.legal_status = kwargs.get('legal_status', 'No Active Cases')
        
        # Program Information
        self.program_type = kwargs.get('program_type', 'Reentry')
        self.referral_source = kwargs.get('referral_source', '')
        self.intake_date = kwargs.get('intake_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Background Assessment
        self.prior_convictions = kwargs.get('prior_convictions', '')
        self.substance_abuse_history = kwargs.get('substance_abuse_history', 'No')
        self.mental_health_status = kwargs.get('mental_health_status', 'Stable')
        
        # Support & Resources
        self.transportation = kwargs.get('transportation', 'None')
        self.medical_conditions = kwargs.get('medical_conditions', '')
        self.special_needs = kwargs.get('special_needs', '')
        
        # Goals & Planning
        self.goals = kwargs.get('goals', '')
        self.barriers = kwargs.get('barriers', '')
        self.needs = kwargs.get('needs', [])  # List of service needs
        
        # Progress Tracking
        self.progress = kwargs.get('progress', 0)  # 0-100 percentage
        self.last_contact = kwargs.get('last_contact', '')
        self.next_followup = kwargs.get('next_followup', '')
        
        # Metadata
        self.notes = kwargs.get('notes', '')
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
        self.is_active = kwargs.get('is_active', True)
    
    @property
    def full_name(self) -> str:
        """Get client's full name"""
        first = self.first_name or ""
        last = self.last_name or ""
        return f"{first} {last}".strip()
    
    @property
    def age(self) -> Optional[int]:
        """Calculate client's age from date of birth"""
        if not self.date_of_birth:
            return None
        try:
            birth_date = datetime.strptime(self.date_of_birth, '%Y-%m-%d').date()
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            return age
        except (ValueError, TypeError):
            return None
    
    @property
    def full_address(self) -> str:
        """Get formatted full address"""
        address_parts = [self.address, self.city, self.state, self.zip_code]
        return ', '.join([part for part in address_parts if part and part.strip()])
    
    @property
    def risk_score(self) -> float:
        """Calculate numerical risk score"""
        score = 0.0
        
        # Base risk level
        risk_scores = {'Low': 1.0, 'Medium': 2.0, 'High': 3.0}
        score += risk_scores.get(self.risk_level, 2.0)
        
        # Housing status impact
        if self.housing_status in ['Homeless', 'At Risk']:
            score += 1.0
        elif self.housing_status == 'Transitional':
            score += 0.5
        
        # Employment status impact
        if self.employment_status == 'Unemployed':
            score += 0.5
        
        # Legal status impact
        if self.legal_status in ['Probation', 'Parole', 'Pending Court']:
            score += 0.5
        
        # Substance abuse history
        if self.substance_abuse_history in ['Recent', 'Needs Treatment']:
            score += 1.0
        elif self.substance_abuse_history == 'Active Treatment':
            score += 0.5
        
        # Mental health status
        if self.mental_health_status in ['Crisis Support', 'Needs Assessment']:
            score += 0.5
        
        return min(score, 5.0)  # Cap at 5.0
    
    def calculate_priority_score(self) -> int:
        """Calculate priority score for task/reminder generation"""
        score = 0
        
        # Risk level impact
        risk_scores = {'High': 40, 'Medium': 20, 'Low': 10}
        score += risk_scores.get(self.risk_level, 20)
        
        # Housing urgency
        if self.housing_status in ['Homeless', 'At Risk']:
            score += 30
        elif self.housing_status == 'Transitional':
            score += 15
        
        # Employment needs
        if self.employment_status == 'Unemployed':
            score += 15
        
        # Legal urgency
        if self.legal_status in ['Pending Court', 'Probation', 'Parole']:
            score += 20
        
        # Service needs count
        score += len(self.needs) * 5
        
        return min(score, 100)  # Cap at 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert client to dictionary for JSON serialization"""
        return {
            'client_id': self.client_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'date_of_birth': self.date_of_birth,
            'age': self.age,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'full_address': self.full_address,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone': self.emergency_contact_phone,
            'emergency_contact_relationship': self.emergency_contact_relationship,
            'case_manager_id': self.case_manager_id,
            'risk_level': self.risk_level,
            'risk_score': self.risk_score,
            'case_status': self.case_status,
            'housing_status': self.housing_status,
            'employment_status': self.employment_status,
            'benefits_status': self.benefits_status,
            'legal_status': self.legal_status,
            'program_type': self.program_type,
            'referral_source': self.referral_source,
            'intake_date': self.intake_date,
            'prior_convictions': self.prior_convictions,
            'substance_abuse_history': self.substance_abuse_history,
            'mental_health_status': self.mental_health_status,
            'transportation': self.transportation,
            'medical_conditions': self.medical_conditions,
            'special_needs': self.special_needs,
            'goals': self.goals,
            'barriers': self.barriers,
            'needs': self.needs,
            'progress': self.progress,
            'priority_score': self.calculate_priority_score(),
            'last_contact': self.last_contact,
            'next_followup': self.next_followup,
            'notes': self.notes,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'is_active': self.is_active
        }


class CaseNote:
    """Case note model for tracking interactions and progress"""
    
    def __init__(self, **kwargs):
        self.note_id = kwargs.get('note_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        self.case_manager_id = kwargs.get('case_manager_id', '')
        
        # Note content
        self.note_type = kwargs.get('note_type', 'General')  # General, Contact, Assessment, Progress
        self.title = kwargs.get('title', '')
        self.content = kwargs.get('content', '')
        
        # Context
        self.contact_method = kwargs.get('contact_method', '')  # Phone, In-Person, Email, etc.
        self.duration_minutes = kwargs.get('duration_minutes', 0)
        self.location = kwargs.get('location', '')
        
        # Assessment
        self.client_mood = kwargs.get('client_mood', '')  # Positive, Neutral, Negative, Crisis
        self.progress_rating = kwargs.get('progress_rating', 0)  # 1-5 rating
        self.barriers_identified = kwargs.get('barriers_identified', '')
        self.action_items = kwargs.get('action_items', '')
        
        # Follow-up
        self.next_contact_needed = kwargs.get('next_contact_needed', '')
        self.referrals_made = kwargs.get('referrals_made', '')
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.is_confidential = kwargs.get('is_confidential', False)
        self.tags = kwargs.get('tags', [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert case note to dictionary"""
        return {
            'note_id': self.note_id,
            'client_id': self.client_id,
            'case_manager_id': self.case_manager_id,
            'note_type': self.note_type,
            'title': self.title,
            'content': self.content,
            'contact_method': self.contact_method,
            'duration_minutes': self.duration_minutes,
            'location': self.location,
            'client_mood': self.client_mood,
            'progress_rating': self.progress_rating,
            'barriers_identified': self.barriers_identified,
            'action_items': self.action_items,
            'next_contact_needed': self.next_contact_needed,
            'referrals_made': self.referrals_made,
            'created_at': self.created_at,
            'is_confidential': self.is_confidential,
            'tags': self.tags
        }


class Referral:
    """Service referral model"""
    
    def __init__(self, **kwargs):
        self.referral_id = kwargs.get('referral_id', str(uuid.uuid4()))
        self.client_id = kwargs.get('client_id', '')
        self.case_manager_id = kwargs.get('case_manager_id', '')
        
        # Referral details
        self.service_type = kwargs.get('service_type', '')  # housing, employment, legal, etc.
        self.provider_name = kwargs.get('provider_name', '')
        self.provider_contact = kwargs.get('provider_contact', '')
        
        # Status tracking
        self.status = kwargs.get('status', 'Pending')  # Pending, Active, Completed, Cancelled
        self.priority = kwargs.get('priority', 'Medium')  # Low, Medium, High, Urgent
        
        # Dates
        self.referral_date = kwargs.get('referral_date', datetime.now().strftime('%Y-%m-%d'))
        self.expected_contact_date = kwargs.get('expected_contact_date', '')
        self.actual_contact_date = kwargs.get('actual_contact_date', '')
        self.completion_date = kwargs.get('completion_date', '')
        
        # Outcome
        self.outcome = kwargs.get('outcome', '')
        self.notes = kwargs.get('notes', '')
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.last_updated = kwargs.get('last_updated', datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert referral to dictionary"""
        return {
            'referral_id': self.referral_id,
            'client_id': self.client_id,
            'case_manager_id': self.case_manager_id,
            'service_type': self.service_type,
            'provider_name': self.provider_name,
            'provider_contact': self.provider_contact,
            'status': self.status,
            'priority': self.priority,
            'referral_date': self.referral_date,
            'expected_contact_date': self.expected_contact_date,
            'actual_contact_date': self.actual_contact_date,
            'completion_date': self.completion_date,
            'outcome': self.outcome,
            'notes': self.notes,
            'created_at': self.created_at,
            'last_updated': self.last_updated
        }