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
Resume utilities for form handling, data processing, and validation
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import asdict

try:
    from .models import ResumeData, User
except ImportError:
    # For direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from resume.models import ResumeData, User

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResumeFormValidator:
    """Validates resume form data"""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validate email format"""
        if not email:
            return False, "Email is required"
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format"
        
        return True, ""
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """Validate phone number format"""
        if not phone:
            return False, "Phone number is required"
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        if len(digits_only) != 10:
            return False, "Phone number must be 10 digits"
        
        return True, ""
    
    @staticmethod
    def validate_required_field(value: str, field_name: str) -> Tuple[bool, str]:
        """Validate required text field"""
        if not value or not value.strip():
            return False, f"{field_name} is required"
        
        return True, ""
    
    @staticmethod
    def validate_work_experience(work_exp: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate work experience entries"""
        errors = []
        
        if not work_exp:
            errors.append("At least one work experience entry is required")
            return False, errors
        
        for i, exp in enumerate(work_exp):
            if not exp.get('company', '').strip():
                errors.append(f"Company name is required for experience {i+1}")
            
            if not exp.get('position', '').strip():
                errors.append(f"Position title is required for experience {i+1}")
            
            if not exp.get('start_date', '').strip():
                errors.append(f"Start date is required for experience {i+1}")
            
            # Validate date format (YYYY-MM)
            start_date = exp.get('start_date', '')
            if start_date and not re.match(r'^\d{4}-\d{2}$', start_date):
                errors.append(f"Start date must be in YYYY-MM format for experience {i+1}")
            
            end_date = exp.get('end_date', '')
            if end_date and end_date != 'Present' and not re.match(r'^\d{4}-\d{2}$', end_date):
                errors.append(f"End date must be in YYYY-MM format or 'Present' for experience {i+1}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_education(education: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate education entries"""
        errors = []
        
        if not education:
            errors.append("At least one education entry is required")
            return False, errors
        
        for i, edu in enumerate(education):
            if not edu.get('institution', '').strip():
                errors.append(f"Institution name is required for education {i+1}")
            
            if not edu.get('degree', '').strip():
                errors.append(f"Degree/Program is required for education {i+1}")
            
            if not edu.get('graduation_year', '').strip():
                errors.append(f"Graduation year is required for education {i+1}")
            
            # Validate graduation year
            grad_year = edu.get('graduation_year', '')
            if grad_year and not re.match(r'^\d{4}$', grad_year):
                errors.append(f"Graduation year must be a 4-digit year for education {i+1}")
        
        return len(errors) == 0, errors
    
    def validate_resume_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate complete resume data"""
        errors = []
        
        # Validate required personal information
        valid, error = self.validate_required_field(data.get('full_name', ''), 'Full name')
        if not valid:
            errors.append(error)
        
        valid, error = self.validate_email(data.get('email', ''))
        if not valid:
            errors.append(error)
        
        valid, error = self.validate_phone(data.get('phone', ''))
        if not valid:
            errors.append(error)
        
        valid, error = self.validate_required_field(data.get('address', ''), 'Address')
        if not valid:
            errors.append(error)
        
        valid, error = self.validate_required_field(data.get('city', ''), 'City')
        if not valid:
            errors.append(error)
        
        valid, error = self.validate_required_field(data.get('state', ''), 'State')
        if not valid:
            errors.append(error)
        
        # Validate professional summary
        valid, error = self.validate_required_field(data.get('professional_summary', ''), 'Professional summary')
        if not valid:
            errors.append(error)
        
        # Validate work experience
        work_exp = data.get('work_experience', [])
        valid, work_errors = self.validate_work_experience(work_exp)
        if not valid:
            errors.extend(work_errors)
        
        # Validate education
        education = data.get('education', [])
        valid, edu_errors = self.validate_education(education)
        if not valid:
            errors.extend(edu_errors)
        
        # Validate skills (at least some skills required)
        tech_skills = data.get('technical_skills', [])
        soft_skills = data.get('soft_skills', [])
        if not tech_skills and not soft_skills:
            errors.append("At least some technical or soft skills are required")
        
        return len(errors) == 0, errors

class ResumeDataProcessor:
    """Processes and formats resume data"""
    
    @staticmethod
    def format_phone_number(phone: str) -> str:
        """Format phone number to (XXX) XXX-XXXX"""
        if not phone:
            return ""
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        if len(digits_only) == 10:
            return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
        
        return phone  # Return original if not 10 digits
    
    @staticmethod
    def format_date_range(start_date: str, end_date: str) -> str:
        """Format date range for display"""
        if not start_date:
            return ""
        
        formatted_start = ResumeDataProcessor.format_date(start_date)
        
        if not end_date or end_date.lower() == 'present':
            return f"{formatted_start} - Present"
        
        formatted_end = ResumeDataProcessor.format_date(end_date)
        return f"{formatted_start} - {formatted_end}"
    
    @staticmethod
    def format_date(date_str: str) -> str:
        """Format YYYY-MM to Month YYYY"""
        if not date_str or not re.match(r'^\d{4}-\d{2}$', date_str):
            return date_str
        
        try:
            year, month = date_str.split('-')
            month_names = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
            month_name = month_names[int(month) - 1]
            return f"{month_name} {year}"
        except (ValueError, IndexError):
            return date_str
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and format text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize line breaks
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text
    
    @staticmethod
    def extract_keywords_from_text(text: str) -> List[str]:
        """Extract potential keywords from text"""
        if not text:
            return []
        
        # Common stop words to exclude
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'
        }
        
        # Extract words (alphanumeric + some special chars)
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9+#.-]*\b', text.lower())
        
        # Filter out stop words and short words
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Remove duplicates while preserving order
        unique_keywords = []
        seen = set()
        for keyword in keywords:
            if keyword not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword)
        
        return unique_keywords[:50]  # Limit to top 50 keywords
    
    def process_form_data(self, form_data: Dict[str, Any]) -> ResumeData:
        """Process raw form data into ResumeData object"""
        # Clean and format personal information
        processed_data = {
            'full_name': self.clean_text(form_data.get('full_name', '')),
            'email': form_data.get('email', '').strip().lower(),
            'phone': self.format_phone_number(form_data.get('phone', '')),
            'address': self.clean_text(form_data.get('address', '')),
            'city': self.clean_text(form_data.get('city', '')),
            'state': self.clean_text(form_data.get('state', '')),
            'zip_code': form_data.get('zip_code', '').strip(),
            'professional_summary': self.clean_text(form_data.get('professional_summary', ''))
        }
        
        # Process work experience
        work_experience = []
        for exp in form_data.get('work_experience', []):
            if exp.get('company') or exp.get('position'):  # Only include if has content
                work_experience.append({
                    'company': self.clean_text(exp.get('company', '')),
                    'position': self.clean_text(exp.get('position', '')),
                    'start_date': exp.get('start_date', '').strip(),
                    'end_date': exp.get('end_date', '').strip(),
                    'description': self.clean_text(exp.get('description', '')),
                    'location': self.clean_text(exp.get('location', ''))
                })
        processed_data['work_experience'] = work_experience
        
        # Process education
        education = []
        for edu in form_data.get('education', []):
            if edu.get('institution') or edu.get('degree'):  # Only include if has content
                education.append({
                    'institution': self.clean_text(edu.get('institution', '')),
                    'degree': self.clean_text(edu.get('degree', '')),
                    'field_of_study': self.clean_text(edu.get('field_of_study', '')),
                    'graduation_year': edu.get('graduation_year', '').strip(),
                    'gpa': edu.get('gpa', '').strip(),
                    'location': self.clean_text(edu.get('location', ''))
                })
        processed_data['education'] = education
        
        # Process skills (clean and deduplicate)
        tech_skills = []
        for skill in form_data.get('technical_skills', []):
            cleaned_skill = self.clean_text(skill)
            if cleaned_skill and cleaned_skill not in tech_skills:
                tech_skills.append(cleaned_skill)
        processed_data['technical_skills'] = tech_skills
        
        soft_skills = []
        for skill in form_data.get('soft_skills', []):
            cleaned_skill = self.clean_text(skill)
            if cleaned_skill and cleaned_skill not in soft_skills:
                soft_skills.append(cleaned_skill)
        processed_data['soft_skills'] = soft_skills
        
        # Process certifications
        certifications = []
        for cert in form_data.get('certifications', []):
            if cert.get('name'):  # Only include if has content
                certifications.append({
                    'name': self.clean_text(cert.get('name', '')),
                    'issuer': self.clean_text(cert.get('issuer', '')),
                    'date_obtained': cert.get('date_obtained', '').strip(),
                    'expiry_date': cert.get('expiry_date', '').strip(),
                    'credential_id': cert.get('credential_id', '').strip()
                })
        processed_data['certifications'] = certifications
        
        # Process additional information
        languages = []
        for lang in form_data.get('languages', []):
            cleaned_lang = self.clean_text(lang)
            if cleaned_lang and cleaned_lang not in languages:
                languages.append(cleaned_lang)
        processed_data['languages'] = languages
        
        volunteer_experience = []
        for vol in form_data.get('volunteer_experience', []):
            if vol.get('organization'):  # Only include if has content
                volunteer_experience.append({
                    'organization': self.clean_text(vol.get('organization', '')),
                    'role': self.clean_text(vol.get('role', '')),
                    'start_date': vol.get('start_date', '').strip(),
                    'end_date': vol.get('end_date', '').strip(),
                    'description': self.clean_text(vol.get('description', ''))
                })
        processed_data['volunteer_experience'] = volunteer_experience
        
        achievements = []
        for achievement in form_data.get('achievements', []):
            cleaned_achievement = self.clean_text(achievement)
            if cleaned_achievement and cleaned_achievement not in achievements:
                achievements.append(cleaned_achievement)
        processed_data['achievements'] = achievements
        
        # Process background-friendly specific fields
        processed_data['background_explanation'] = self.clean_text(form_data.get('background_explanation', ''))
        processed_data['rehabilitation_efforts'] = self.clean_text(form_data.get('rehabilitation_efforts', ''))
        processed_data['community_service'] = self.clean_text(form_data.get('community_service', ''))
        
        return ResumeData(**processed_data)

class ResumeTemplateHelper:
    """Helper for resume template generation"""
    
    @staticmethod
    def get_default_template_structure() -> Dict[str, Any]:
        """Get default resume template structure"""
        return {
            'sections': [
                {
                    'name': 'header',
                    'title': 'Contact Information',
                    'required': True,
                    'fields': ['full_name', 'email', 'phone', 'address']
                },
                {
                    'name': 'summary',
                    'title': 'Professional Summary',
                    'required': True,
                    'fields': ['professional_summary']
                },
                {
                    'name': 'experience',
                    'title': 'Work Experience',
                    'required': True,
                    'fields': ['work_experience']
                },
                {
                    'name': 'education',
                    'title': 'Education',
                    'required': True,
                    'fields': ['education']
                },
                {
                    'name': 'skills',
                    'title': 'Skills',
                    'required': True,
                    'fields': ['technical_skills', 'soft_skills']
                },
                {
                    'name': 'certifications',
                    'title': 'Certifications',
                    'required': False,
                    'fields': ['certifications']
                },
                {
                    'name': 'additional',
                    'title': 'Additional Information',
                    'required': False,
                    'fields': ['languages', 'volunteer_experience', 'achievements']
                }
            ],
            'style': {
                'font_family': 'Arial, sans-serif',
                'font_size': '11pt',
                'line_height': '1.2',
                'margins': '0.75in',
                'section_spacing': '12pt'
            }
        }
    
    @staticmethod
    def get_ats_friendly_keywords() -> List[str]:
        """Get list of ATS-friendly keywords by category"""
        return {
            'action_verbs': [
                'achieved', 'administered', 'analyzed', 'collaborated', 'coordinated',
                'created', 'developed', 'executed', 'implemented', 'improved',
                'increased', 'led', 'managed', 'optimized', 'organized',
                'planned', 'produced', 'reduced', 'resolved', 'streamlined'
            ],
            'technical_skills': [
                'microsoft office', 'excel', 'powerpoint', 'word', 'outlook',
                'google workspace', 'project management', 'data analysis',
                'customer service', 'sales', 'marketing', 'accounting',
                'inventory management', 'quality control', 'safety protocols'
            ],
            'soft_skills': [
                'communication', 'teamwork', 'leadership', 'problem-solving',
                'time management', 'attention to detail', 'adaptability',
                'reliability', 'work ethic', 'customer focus', 'initiative'
            ]
        }

# Example usage and testing
if __name__ == "__main__":
    # Test form validation
    validator = ResumeFormValidator()
    processor = ResumeDataProcessor()
    
    # Test data
    test_data = {
        'full_name': 'John Doe',
        'email': 'john.doe@example.com',
        'phone': '5551234567',
        'address': '123 Main St',
        'city': 'Los Angeles',
        'state': 'CA',
        'professional_summary': 'Experienced professional seeking new opportunities',
        'work_experience': [
            {
                'company': 'Test Company',
                'position': 'Test Position',
                'start_date': '2020-01',
                'end_date': '2023-12',
                'description': 'Performed various duties'
            }
        ],
        'education': [
            {
                'institution': 'Test University',
                'degree': 'Bachelor of Science',
                'graduation_year': '2020'
            }
        ],
        'technical_skills': ['Microsoft Office', 'Customer Service'],
        'soft_skills': ['Communication', 'Teamwork']
    }
    
    # Test validation
    is_valid, errors = validator.validate_resume_data(test_data)
    print(f"Validation result: {is_valid}")
    if errors:
        print(f"Errors: {errors}")
    
    # Test processing
    resume_data = processor.process_form_data(test_data)
    print(f"Processed resume for: {resume_data.full_name}")
    print(f"Formatted phone: {resume_data.phone}")
    
    print("✅ Resume utilities working correctly!")

