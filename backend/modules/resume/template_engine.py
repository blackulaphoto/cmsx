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
Resume Template Engine for Dynamic Content Integration
Handles template rendering, PDF generation, and template management
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import tempfile
import uuid
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dataclasses import dataclass, asdict

# PDF generation libraries
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    # Handle both import errors and OSError for missing system libraries
    WEASYPRINT_AVAILABLE = False
    HTML = None
    CSS = None

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TemplateInfo:
    """Resume template information"""
    id: str
    name: str
    category: str
    description: str
    file_path: str
    preview_image: Optional[str]
    features: List[str]
    is_ats_friendly: bool
    background_friendly: bool
    industry_focus: List[str]

@dataclass
class ResumeRenderResult:
    """Result of resume rendering"""
    success: bool
    html_content: str
    pdf_path: Optional[str]
    template_used: str
    render_timestamp: str
    file_size_bytes: int
    error_message: Optional[str]

class ResumeTemplateManager:
    """Manages resume templates and their metadata"""
    
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.ensure_template_directory()
        self.templates = self._load_template_metadata()
    
    def ensure_template_directory(self):
        """Ensure template directory exists"""
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir, exist_ok=True)
            logger.info(f"Created template directory: {self.template_dir}")
    
    def _load_template_metadata(self) -> Dict[str, TemplateInfo]:
        """Load template metadata and discover available templates"""
        templates = {}
        
        # Define built-in templates with enhanced metadata
        builtin_templates = [
            {
                'id': 'classic',
                'name': 'Classic Professional',
                'category': 'traditional',
                'description': 'Clean, traditional layout perfect for corporate environments',
                'file_path': 'classic_template.html',
                'features': ['ATS-Friendly', 'Clean Layout', 'Professional'],
                'is_ats_friendly': True,
                'background_friendly': True,
                'industry_focus': ['office', 'retail', 'general']
            },
            {
                'id': 'modern',
                'name': 'Modern Professional',
                'category': 'contemporary',
                'description': 'Contemporary design with subtle colors and modern typography',
                'file_path': 'modern_template.html',
                'features': ['Modern Design', 'Color Accents', 'ATS-Friendly'],
                'is_ats_friendly': True,
                'background_friendly': True,
                'industry_focus': ['healthcare', 'office', 'retail']
            },
            {
                'id': 'warehouse',
                'name': 'Warehouse Worker',
                'category': 'industry_specific',
                'description': 'Optimized for warehouse, logistics, and manual labor positions',
                'file_path': 'warehouse_template.html',
                'features': ['Background-Friendly', 'Skills-Focused', 'Entry-Level'],
                'is_ats_friendly': True,
                'background_friendly': True,
                'industry_focus': ['warehouse', 'manufacturing', 'logistics']
            },
            {
                'id': 'construction',
                'name': 'Construction & Trades',
                'category': 'industry_specific',
                'description': 'Designed for construction, maintenance, and trade positions',
                'file_path': 'construction_template.html',
                'features': ['Skills-Focused', 'Certification Highlight', 'Safety-Aware'],
                'is_ats_friendly': True,
                'background_friendly': True,
                'industry_focus': ['construction', 'maintenance', 'manufacturing']
            },
            {
                'id': 'food_service',
                'name': 'Food Service',
                'category': 'industry_specific',
                'description': 'Perfect for restaurant, kitchen, and food service roles',
                'file_path': 'food_service_template.html',
                'features': ['Fast-Paced Focus', 'Team-Oriented', 'Customer Service'],
                'is_ats_friendly': True,
                'background_friendly': True,
                'industry_focus': ['food_service', 'retail', 'customer_service']
            },
            {
                'id': 'medical_social_worker',
                'name': 'Medical Social Worker',
                'category': 'professional',
                'description': 'Professional template for healthcare and social work positions',
                'file_path': 'medical_social_worker_template.html',
                'features': ['Professional', 'Healthcare-Focused', 'Credential Highlight'],
                'is_ats_friendly': True,
                'background_friendly': False,
                'industry_focus': ['healthcare', 'social_work', 'office']
            }
        ]
        
        # Create TemplateInfo objects
        for template_data in builtin_templates:
            template_info = TemplateInfo(
                id=template_data['id'],
                name=template_data['name'],
                category=template_data['category'],
                description=template_data['description'],
                file_path=template_data['file_path'],
                preview_image=f"{template_data['id']}_preview.png",
                features=template_data['features'],
                is_ats_friendly=template_data['is_ats_friendly'],
                background_friendly=template_data['background_friendly'],
                industry_focus=template_data['industry_focus']
            )
            templates[template_data['id']] = template_info
        
        logger.info(f"Loaded {len(templates)} resume templates")
        return templates
    
    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        """Get template information by ID"""
        return self.templates.get(template_id)
    
    def get_templates_by_category(self, category: str) -> List[TemplateInfo]:
        """Get templates filtered by category"""
        return [t for t in self.templates.values() if t.category == category]
    
    def get_background_friendly_templates(self) -> List[TemplateInfo]:
        """Get templates suitable for people with backgrounds"""
        return [t for t in self.templates.values() if t.background_friendly]
    
    def get_templates_for_industry(self, industry: str) -> List[TemplateInfo]:
        """Get templates optimized for specific industry"""
        return [t for t in self.templates.values() if industry in t.industry_focus]
    
    def list_all_templates(self) -> List[TemplateInfo]:
        """Get all available templates"""
        return list(self.templates.values())

class ResumeTemplateRenderer:
    """Renders resume templates with dynamic content"""
    
    def __init__(self):
        self.template_manager = ResumeTemplateManager()
        self.jinja_env = self._setup_jinja_environment()
        self.output_dir = os.path.join(os.path.dirname(__file__), 'output')
        self.ensure_output_directory()
    
    def ensure_output_directory(self):
        """Ensure output directory exists"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info(f"Created output directory: {self.output_dir}")
    
    def _setup_jinja_environment(self) -> Environment:
        """Set up Jinja2 template environment"""
        env = Environment(
            loader=FileSystemLoader(self.template_manager.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        env.filters['format_date'] = self._format_date_filter
        env.filters['format_phone'] = self._format_phone_filter
        env.filters['format_skills'] = self._format_skills_filter
        env.filters['nl2br'] = self._nl2br_filter
        env.filters['truncate_words'] = self._truncate_words_filter
        
        return env
    
    def _format_date_filter(self, date_str: str) -> str:
        """Format date for display"""
        if not date_str:
            return ""
        
        if date_str.lower() == 'present':
            return 'Present'
        
        # Handle YYYY-MM format
        if re.match(r'^\d{4}-\d{2}$', date_str):
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
        
        return date_str
    
    def _format_phone_filter(self, phone: str) -> str:
        """Format phone number"""
        if not phone:
            return ""
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        if len(digits_only) == 10:
            return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
        
        return phone
    
    def _format_skills_filter(self, skills: List[str], separator: str = ", ") -> str:
        """Format skills list"""
        if not skills:
            return ""
        return separator.join(skills)
    
    def _nl2br_filter(self, text: str) -> str:
        """Convert newlines to HTML breaks"""
        if not text:
            return ""
        return text.replace('\n', '<br>')
    
    def _truncate_words_filter(self, text: str, length: int = 50) -> str:
        """Truncate text to specified word count"""
        if not text:
            return ""
        words = text.split()
        if len(words) <= length:
            return text
        return ' '.join(words[:length]) + '...'
    
    def render_resume_html(self, resume_data: Dict[str, Any], template_id: str = 'classic') -> Tuple[bool, str, str]:
        """Render resume to HTML"""
        try:
            # Get template info
            template_info = self.template_manager.get_template(template_id)
            if not template_info:
                return False, "", f"Template '{template_id}' not found"
            
            # Try to load the template
            try:
                template = self.jinja_env.get_template(template_info.file_path)
            except Exception as e:
                # Fallback to built-in template
                logger.warning(f"Template file not found, using built-in template: {e}")
                template_html = self._get_builtin_template(template_id)
                template = self.jinja_env.from_string(template_html)
            
            # Prepare template context
            context = self._prepare_template_context(resume_data, template_info)
            
            # Render template
            html_content = template.render(**context)
            
            logger.info(f"Resume HTML rendered successfully using template: {template_id}")
            return True, html_content, ""
            
        except Exception as e:
            logger.error(f"Error rendering resume HTML: {e}")
            return False, "", str(e)
    
    def _get_builtin_template(self, template_id: str) -> str:
        """Get built-in template HTML when template file is missing"""
        templates = {
            'classic': self._get_classic_template(),
            'modern': self._get_modern_template(),
            'warehouse': self._get_warehouse_template(),
            'construction': self._get_construction_template(),
            'food_service': self._get_food_service_template()
        }
        
        return templates.get(template_id, templates['classic'])
    
    def _get_classic_template(self) -> str:
        """Built-in classic template"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ full_name }} - Resume</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; color: #333; }
        .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 20px; }
        .name { font-size: 2.5em; font-weight: bold; margin-bottom: 10px; }
        .contact { font-size: 1.1em; color: #666; }
        .section { margin-bottom: 25px; }
        .section-title { font-size: 1.4em; font-weight: bold; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-bottom: 15px; }
        .job-entry { margin-bottom: 20px; }
        .job-title { font-weight: bold; font-size: 1.1em; }
        .job-company { font-style: italic; color: #666; }
        .job-dates { color: #888; font-size: 0.9em; }
        .skills { display: flex; flex-wrap: wrap; gap: 10px; }
        .skill { background: #f0f0f0; padding: 5px 10px; border-radius: 3px; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <div class="name">{{ full_name }}</div>
        <div class="contact">
            {% if email %}{{ email }}{% endif %}
            {% if phone and email %} • {% endif %}
            {% if phone %}{{ phone | format_phone }}{% endif %}
            {% if location and (email or phone) %} • {% endif %}
            {% if location %}{{ location }}{% endif %}
        </div>
    </div>
    
    {% if summary %}
    <div class="section">
        <div class="section-title">Professional Summary</div>
        <p>{{ summary | nl2br }}</p>
    </div>
    {% endif %}
    
    {% if work_experience %}
    <div class="section">
        <div class="section-title">Work Experience</div>
        {% for job in work_experience %}
        <div class="job-entry">
            <div class="job-title">{{ job.title or job.position }}</div>
            <div class="job-company">{{ job.company }}</div>
            {% if job.start_date or job.end_date %}
            <div class="job-dates">
                {{ job.start_date | format_date }}{% if job.start_date %} - {% endif %}{{ job.end_date | format_date or 'Present' }}
            </div>
            {% endif %}
            {% if job.description %}
            <p>{{ job.description | nl2br }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    {% if education %}
    <div class="section">
        <div class="section-title">Education</div>
        {% for edu in education %}
        <div class="job-entry">
            <div class="job-title">{{ edu.degree }}</div>
            <div class="job-company">{{ edu.institution }}</div>
            {% if edu.graduation_year %}
            <div class="job-dates">{{ edu.graduation_year }}</div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    {% if technical_skills or soft_skills %}
    <div class="section">
        <div class="section-title">Skills</div>
        {% if technical_skills %}
        <p><strong>Technical Skills:</strong> {{ technical_skills | format_skills }}</p>
        {% endif %}
        {% if soft_skills %}
        <p><strong>Soft Skills:</strong> {{ soft_skills | format_skills }}</p>
        {% endif %}
    </div>
    {% endif %}
</body>
</html>
        '''
    
    def _get_modern_template(self) -> str:
        """Built-in modern template"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ full_name }} - Resume</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; margin: 0; color: #333; }
        .container { max-width: 800px; margin: 0 auto; background: white; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }
        .name { font-size: 2.8em; font-weight: 300; margin-bottom: 10px; }
        .contact { font-size: 1.1em; opacity: 0.9; }
        .content { padding: 40px; }
        .section { margin-bottom: 30px; }
        .section-title { font-size: 1.5em; font-weight: 600; color: #667eea; margin-bottom: 20px; position: relative; }
        .section-title::after { content: ''; position: absolute; bottom: -5px; left: 0; width: 50px; height: 3px; background: #667eea; }
        .job-entry { margin-bottom: 25px; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea; }
        .job-title { font-weight: 600; font-size: 1.2em; color: #333; }
        .job-company { color: #667eea; font-weight: 500; margin: 5px 0; }
        .job-dates { color: #6c757d; font-size: 0.9em; margin-bottom: 10px; }
        .skills { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
        .skill-category { background: #f8f9fa; padding: 15px; border-radius: 8px; }
        .skill-category h4 { margin: 0 0 10px 0; color: #667eea; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="name">{{ full_name }}</div>
            <div class="contact">
                {% if email %}{{ email }}{% endif %}
                {% if phone and email %} • {% endif %}
                {% if phone %}{{ phone | format_phone }}{% endif %}
                {% if location and (email or phone) %} • {% endif %}
                {% if location %}{{ location }}{% endif %}
            </div>
        </div>
        
        <div class="content">
            {% if summary %}
            <div class="section">
                <div class="section-title">Professional Summary</div>
                <p style="font-size: 1.1em; line-height: 1.7;">{{ summary | nl2br }}</p>
            </div>
            {% endif %}
            
            {% if work_experience %}
            <div class="section">
                <div class="section-title">Work Experience</div>
                {% for job in work_experience %}
                <div class="job-entry">
                    <div class="job-title">{{ job.title or job.position }}</div>
                    <div class="job-company">{{ job.company }}</div>
                    {% if job.start_date or job.end_date %}
                    <div class="job-dates">
                        {{ job.start_date | format_date }}{% if job.start_date %} - {% endif %}{{ job.end_date | format_date or 'Present' }}
                    </div>
                    {% endif %}
                    {% if job.description %}
                    <p>{{ job.description | nl2br }}</p>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if education %}
            <div class="section">
                <div class="section-title">Education</div>
                {% for edu in education %}
                <div class="job-entry">
                    <div class="job-title">{{ edu.degree }}</div>
                    <div class="job-company">{{ edu.institution }}</div>
                    {% if edu.graduation_year %}
                    <div class="job-dates">{{ edu.graduation_year }}</div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if technical_skills or soft_skills %}
            <div class="section">
                <div class="section-title">Skills</div>
                <div class="skills">
                    {% if technical_skills %}
                    <div class="skill-category">
                        <h4>Technical Skills</h4>
                        <p>{{ technical_skills | format_skills }}</p>
                    </div>
                    {% endif %}
                    {% if soft_skills %}
                    <div class="skill-category">
                        <h4>Soft Skills</h4>
                        <p>{{ soft_skills | format_skills }}</p>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
        '''
    
    def _get_warehouse_template(self) -> str:
        """Built-in warehouse-specific template"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ full_name }} - Warehouse Resume</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 30px; color: #333; }
        .header { border: 3px solid #2c5282; padding: 20px; margin-bottom: 25px; background: #f7fafc; }
        .name { font-size: 2.2em; font-weight: bold; color: #2c5282; margin-bottom: 10px; }
        .contact { font-size: 1.1em; color: #4a5568; }
        .availability { background: #2c5282; color: white; padding: 10px; margin-top: 10px; text-align: center; font-weight: bold; }
        .section { margin-bottom: 25px; }
        .section-title { font-size: 1.3em; font-weight: bold; color: #2c5282; background: #edf2f7; padding: 10px; margin-bottom: 15px; }
        .highlight-box { background: #e6fffa; border: 2px solid #38b2ac; padding: 15px; margin: 15px 0; border-radius: 5px; }
        .skills-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .skill-item { background: #f0fff4; padding: 10px; border-left: 4px solid #38a169; }
        .job-entry { border-left: 4px solid #2c5282; padding-left: 15px; margin-bottom: 20px; }
        .safety-note { background: #fed7d7; border: 2px solid #e53e3e; padding: 10px; color: #742a2a; font-weight: bold; text-align: center; }
    </style>
</head>
<body>
    <div class="header">
        <div class="name">{{ full_name }}</div>
        <div class="contact">
            {% if email %}{{ email }}{% endif %}
            {% if phone and email %} • {% endif %}
            {% if phone %}{{ phone | format_phone }}{% endif %}
            {% if location and (email or phone) %} • {% endif %}
            {% if location %}{{ location }}{% endif %}
        </div>
        <div class="availability">AVAILABLE FOR IMMEDIATE START • RELIABLE TRANSPORTATION</div>
    </div>
    
    <div class="safety-note">
        SAFETY-CONSCIOUS • OSHA AWARE • COMMITTED TO WORKPLACE SAFETY
    </div>
    
    {% if summary %}
    <div class="section">
        <div class="section-title">🎯 PROFESSIONAL OBJECTIVE</div>
        <div class="highlight-box">
            {{ summary | nl2br }}
        </div>
    </div>
    {% endif %}
    
    {% if technical_skills or soft_skills %}
    <div class="section">
        <div class="section-title">🔧 KEY SKILLS & ABILITIES</div>
        <div class="skills-grid">
            {% if technical_skills %}
            {% for skill in technical_skills %}
            <div class="skill-item">✓ {{ skill }}</div>
            {% endfor %}
            {% endif %}
            {% if soft_skills %}
            {% for skill in soft_skills %}
            <div class="skill-item">✓ {{ skill }}</div>
            {% endfor %}
            {% endif %}
        </div>
    </div>
    {% endif %}
    
    {% if work_experience %}
    <div class="section">
        <div class="section-title">💼 WORK EXPERIENCE</div>
        {% for job in work_experience %}
        <div class="job-entry">
            <div style="font-weight: bold; font-size: 1.1em;">{{ job.title or job.position }}</div>
            <div style="color: #2c5282; font-weight: bold;">{{ job.company }}</div>
            {% if job.start_date or job.end_date %}
            <div style="color: #666; font-style: italic;">
                {{ job.start_date | format_date }}{% if job.start_date %} - {% endif %}{{ job.end_date | format_date or 'Present' }}
            </div>
            {% endif %}
            {% if job.description %}
            <p>{{ job.description | nl2br }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    {% if education %}
    <div class="section">
        <div class="section-title">🎓 EDUCATION & TRAINING</div>
        {% for edu in education %}
        <div class="job-entry">
            <div style="font-weight: bold;">{{ edu.degree }}</div>
            <div style="color: #2c5282;">{{ edu.institution }}</div>
            {% if edu.graduation_year %}
            <div style="color: #666;">{{ edu.graduation_year }}</div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <div class="highlight-box" style="text-align: center; margin-top: 30px;">
        <strong>READY TO WORK HARD • LEARN FAST • CONTRIBUTE TO TEAM SUCCESS</strong>
    </div>
</body>
</html>
        '''
    
    def _get_construction_template(self) -> str:
        """Built-in construction-specific template"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ full_name }} - Construction Resume</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 30px; color: #333; background: #f8f9fa; }
        .container { background: white; padding: 30px; border: 3px solid #fd7e14; }
        .header { background: #fd7e14; color: white; padding: 25px; margin: -30px -30px 25px -30px; }
        .name { font-size: 2.3em; font-weight: bold; margin-bottom: 8px; }
        .contact { font-size: 1.1em; opacity: 0.95; }
        .trade-skills { background: #fff3cd; border: 2px solid #ffc107; padding: 15px; margin: 20px 0; text-align: center; }
        .section { margin-bottom: 25px; }
        .section-title { font-size: 1.3em; font-weight: bold; color: #fd7e14; background: #f8f9fa; padding: 10px; border-left: 5px solid #fd7e14; }
        .certifications { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .cert-item { background: #d4edda; border: 1px solid #28a745; padding: 10px; text-align: center; font-weight: bold; }
        .job-entry { background: #f8f9fa; padding: 15px; margin-bottom: 15px; border-left: 5px solid #fd7e14; }
        .safety-first { background: #dc3545; color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 1.1em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="name">{{ full_name }}</div>
            <div class="contact">
                {% if email %}📧 {{ email }}{% endif %}
                {% if phone and email %} • {% endif %}
                {% if phone %}📞 {{ phone | format_phone }}{% endif %}
                {% if location and (email or phone) %} • {% endif %}
                {% if location %}📍 {{ location }}{% endif %}
            </div>
        </div>
        
        <div class="safety-first">
            🛡️ SAFETY FIRST • OSHA TRAINED • ZERO ACCIDENTS COMMITMENT 🛡️
        </div>
        
        {% if summary %}
        <div class="section">
            <div class="section-title">🎯 PROFESSIONAL PROFILE</div>
            <p style="font-size: 1.1em; background: #e9ecef; padding: 15px; border-radius: 5px;">{{ summary | nl2br }}</p>
        </div>
        {% endif %}
        
        {% if technical_skills %}
        <div class="section">
            <div class="section-title">🔨 TRADE SKILLS & TOOLS</div>
            <div class="trade-skills">
                <strong>EXPERIENCED WITH:</strong><br>
                {{ technical_skills | format_skills(" • ") }}
            </div>
        </div>
        {% endif %}
        
        {% if soft_skills %}
        <div class="section">
            <div class="section-title">👥 WORK QUALITIES</div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                {% for skill in soft_skills %}
                <div style="background: #e2e3e5; padding: 8px; text-align: center; border-radius: 3px;">✓ {{ skill }}</div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        {% if work_experience %}
        <div class="section">
            <div class="section-title">🏗️ WORK EXPERIENCE</div>
            {% for job in work_experience %}
            <div class="job-entry">
                <div style="font-weight: bold; font-size: 1.2em; color: #fd7e14;">{{ job.title or job.position }}</div>
                <div style="font-weight: bold; color: #495057;">{{ job.company }}</div>
                {% if job.start_date or job.end_date %}
                <div style="color: #6c757d; margin: 5px 0;">
                    📅 {{ job.start_date | format_date }}{% if job.start_date %} - {% endif %}{{ job.end_date | format_date or 'Present' }}
                </div>
                {% endif %}
                {% if job.description %}
                <p style="margin-top: 10px;">{{ job.description | nl2br }}</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        {% if education %}
        <div class="section">
            <div class="section-title">🎓 EDUCATION & CERTIFICATIONS</div>
            <div class="certifications">
                {% for edu in education %}
                <div class="cert-item">
                    {{ edu.degree }}<br>
                    <small>{{ edu.institution }}</small><br>
                    {% if edu.graduation_year %}<small>{{ edu.graduation_year }}</small>{% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <div style="background: #28a745; color: white; padding: 15px; text-align: center; margin-top: 25px; font-weight: bold;">
            ✅ RELIABLE • PUNCTUAL • READY TO START IMMEDIATELY ✅
        </div>
    </div>
</body>
</html>
        '''
    
    def _get_food_service_template(self) -> str:
        """Built-in food service template"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ full_name }} - Food Service Resume</title>
    <style>
        body { font-family: 'Trebuchet MS', Arial, sans-serif; line-height: 1.6; margin: 25px; color: #333; }
        .header { background: linear-gradient(45deg, #e53e3e, #fd7e14); color: white; padding: 25px; border-radius: 10px; text-align: center; margin-bottom: 25px; }
        .name { font-size: 2.4em; font-weight: bold; margin-bottom: 8px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .contact { font-size: 1.1em; opacity: 0.95; }
        .availability { background: #38a169; color: white; padding: 12px; margin: 15px 0; text-align: center; font-weight: bold; border-radius: 5px; }
        .section { margin-bottom: 25px; }
        .section-title { font-size: 1.3em; font-weight: bold; color: #e53e3e; background: #fed7d7; padding: 12px; border-radius: 5px; border-left: 5px solid #e53e3e; }
        .food-service-skills { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 15px 0; }
        .skill-badge { background: #fef5e7; border: 2px solid #fd7e14; padding: 10px; text-align: center; border-radius: 8px; font-weight: bold; color: #c05621; }
        .job-entry { background: #f7fafc; padding: 18px; margin-bottom: 15px; border-radius: 8px; border-left: 5px solid #e53e3e; }
        .fast-paced { background: #bee3f8; border: 2px solid #3182ce; padding: 12px; text-align: center; color: #2c5282; font-weight: bold; }
        .customer-focus { background: #c6f6d5; border: 2px solid #38a169; padding: 15px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="name">{{ full_name }}</div>
        <div class="contact">
            {% if email %}📧 {{ email }}{% endif %}
            {% if phone and email %} • {% endif %}
            {% if phone %}📞 {{ phone | format_phone }}{% endif %}
            {% if location and (email or phone) %} • {% endif %}
            {% if location %}📍 {{ location }}{% endif %}
        </div>
    </div>
    
    <div class="availability">
        🕐 FLEXIBLE SCHEDULE • WEEKENDS • HOLIDAYS • IMMEDIATE START AVAILABLE 🕐
    </div>
    
    {% if summary %}
    <div class="section">
        <div class="section-title">🎯 PROFESSIONAL SUMMARY</div>
        <div class="customer-focus">
            <strong>Customer Service Focused Professional</strong><br>
            {{ summary | nl2br }}
        </div>
    </div>
    {% endif %}
    
    {% if technical_skills or soft_skills %}
    <div class="section">
        <div class="section-title">🍽️ FOOD SERVICE SKILLS</div>
        <div class="food-service-skills">
            {% if technical_skills %}
                {% for skill in technical_skills %}
                <div class="skill-badge">🔧 {{ skill }}</div>
                {% endfor %}
            {% endif %}
            {% if soft_skills %}
                {% for skill in soft_skills %}
                <div class="skill-badge">👥 {{ skill }}</div>
                {% endfor %}
            {% endif %}
        </div>
    </div>
    {% endif %}
    
    <div class="fast-paced">
        ⚡ THRIVES IN FAST-PACED ENVIRONMENTS • MULTITASKING EXPERT • TEAM PLAYER ⚡
    </div>
    
    {% if work_experience %}
    <div class="section">
        <div class="section-title">👨‍🍳 WORK EXPERIENCE</div>
        {% for job in work_experience %}
        <div class="job-entry">
            <div style="font-weight: bold; font-size: 1.2em; color: #e53e3e;">{{ job.title or job.position }}</div>
            <div style="font-weight: bold; color: #2d3748;">{{ job.company }}</div>
            {% if job.start_date or job.end_date %}
            <div style="color: #718096; margin: 5px 0;">
                📅 {{ job.start_date | format_date }}{% if job.start_date %} - {% endif %}{{ job.end_date | format_date or 'Present' }}
            </div>
            {% endif %}
            {% if job.description %}
            <p style="margin-top: 10px;">{{ job.description | nl2br }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    {% if education %}
    <div class="section">
        <div class="section-title">🎓 EDUCATION & CERTIFICATIONS</div>
        {% for edu in education %}
        <div class="job-entry">
            <div style="font-weight: bold; color: #e53e3e;">{{ edu.degree }}</div>
            <div style="color: #2d3748;">{{ edu.institution }}</div>
            {% if edu.graduation_year %}
            <div style="color: #718096;">{{ edu.graduation_year }}</div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <div style="background: linear-gradient(45deg, #38a169, #68d391); color: white; padding: 18px; text-align: center; border-radius: 10px; font-weight: bold; font-size: 1.1em;">
        🌟 FOOD SAFE CERTIFIED • CUSTOMER SERVICE EXCELLENCE • READY TO SERVE 🌟
    </div>
</body>
</html>
        '''
    
    def _prepare_template_context(self, resume_data: Dict[str, Any], template_info: TemplateInfo) -> Dict[str, Any]:
        """Prepare context variables for template rendering"""
        context = resume_data.copy()
        
        # Add template metadata
        context['template_info'] = asdict(template_info)
        context['render_timestamp'] = datetime.utcnow().isoformat()
        
        # Ensure required fields have defaults
        context.setdefault('full_name', 'Your Name')
        context.setdefault('email', '')
        context.setdefault('phone', '')
        context.setdefault('location', '')
        context.setdefault('summary', '')
        context.setdefault('work_experience', [])
        context.setdefault('education', [])
        context.setdefault('technical_skills', [])
        context.setdefault('soft_skills', [])
        
        # Process work experience to ensure consistent field names
        if context['work_experience']:
            for exp in context['work_experience']:
                if 'position' not in exp and 'title' in exp:
                    exp['position'] = exp['title']
                elif 'title' not in exp and 'position' in exp:
                    exp['title'] = exp['position']
        
        return context

class ResumePDFGenerator:
    """Generates PDF files from resume HTML"""
    
    def __init__(self):
        self.output_dir = os.path.join(os.path.dirname(__file__), 'output')
        self.pdf_options = self._get_pdf_options()
    
    def _get_pdf_options(self) -> Dict[str, Any]:
        """Get PDF generation options"""
        return {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None
        }
    
    def generate_pdf_from_html(self, html_content: str, filename: str = None) -> Tuple[bool, str, str]:
        """Generate PDF from HTML content"""
        if not filename:
            filename = f"resume_{uuid.uuid4().hex[:8]}.pdf"
        
        pdf_path = os.path.join(self.output_dir, filename)
        
        # Try different PDF generation methods
        methods = [
            ('weasyprint', self._generate_with_weasyprint),
            ('pdfkit', self._generate_with_pdfkit),
            ('reportlab', self._generate_with_reportlab_fallback)
        ]
        
        for method_name, method_func in methods:
            try:
                success, error_msg = method_func(html_content, pdf_path)
                if success:
                    file_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
                    logger.info(f"PDF generated successfully using {method_name}: {pdf_path}")
                    return True, pdf_path, ""
                else:
                    logger.warning(f"PDF generation failed with {method_name}: {error_msg}")
            except Exception as e:
                logger.warning(f"PDF generation method {method_name} failed: {e}")
                continue
        
        return False, "", "All PDF generation methods failed"
    
    def _generate_with_weasyprint(self, html_content: str, pdf_path: str) -> Tuple[bool, str]:
        """Generate PDF using WeasyPrint"""
        if not WEASYPRINT_AVAILABLE:
            return False, "WeasyPrint not available"
        
        try:
            # Import at method level to avoid module-level import issues
            from weasyprint import HTML
            HTML(string=html_content, base_url='.').write_pdf(pdf_path)
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def _generate_with_pdfkit(self, html_content: str, pdf_path: str) -> Tuple[bool, str]:
        """Generate PDF using pdfkit (wkhtmltopdf)"""
        if not PDFKIT_AVAILABLE:
            return False, "pdfkit not available"
        
        try:
            pdfkit.from_string(html_content, pdf_path, options=self.pdf_options)
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def _generate_with_reportlab_fallback(self, html_content: str, pdf_path: str) -> Tuple[bool, str]:
        """Generate basic PDF using ReportLab as fallback"""
        if not REPORTLAB_AVAILABLE:
            return False, "ReportLab not available"
        
        try:
            # This is a very basic fallback - just extracts text and creates simple PDF
            from html import unescape
            import re
            
            # Extract text content from HTML
            text_content = re.sub(r'<[^>]+>', '\n', html_content)
            text_content = unescape(text_content)
            text_content = re.sub(r'\n+', '\n', text_content).strip()
            
            # Create PDF
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Split content into paragraphs
            paragraphs = text_content.split('\n')
            for para in paragraphs:
                if para.strip():
                    p = Paragraph(para.strip(), styles['Normal'])
                    story.append(p)
                    story.append(Spacer(1, 12))
            
            doc.build(story)
            return True, ""
            
        except Exception as e:
            return False, str(e)

class ResumeTemplateEngine:
    """Main template engine for resume generation"""
    
    def __init__(self):
        self.template_manager = ResumeTemplateManager()
        self.renderer = ResumeTemplateRenderer()
        self.pdf_generator = ResumePDFGenerator()
    
    def render_resume(self, resume_data: Dict[str, Any], template_id: str = 'classic', 
                     generate_pdf: bool = True) -> ResumeRenderResult:
        """Render resume with specified template"""
        try:
            # Render HTML
            success, html_content, error_msg = self.renderer.render_resume_html(resume_data, template_id)
            
            if not success:
                return ResumeRenderResult(
                    success=False,
                    html_content="",
                    pdf_path=None,
                    template_used=template_id,
                    render_timestamp=datetime.utcnow().isoformat(),
                    file_size_bytes=0,
                    error_message=error_msg
                )
            
            # Generate PDF if requested
            pdf_path = None
            if generate_pdf:
                pdf_success, pdf_path, pdf_error = self.pdf_generator.generate_pdf_from_html(
                    html_content, f"resume_{template_id}_{uuid.uuid4().hex[:8]}.pdf"
                )
                if not pdf_success:
                    logger.warning(f"PDF generation failed: {pdf_error}")
            
            # Calculate file size
            file_size = 0
            if pdf_path and os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
            else:
                file_size = len(html_content.encode('utf-8'))
            
            return ResumeRenderResult(
                success=True,
                html_content=html_content,
                pdf_path=pdf_path,
                template_used=template_id,
                render_timestamp=datetime.utcnow().isoformat(),
                file_size_bytes=file_size,
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Error rendering resume: {e}")
            return ResumeRenderResult(
                success=False,
                html_content="",
                pdf_path=None,
                template_used=template_id,
                render_timestamp=datetime.utcnow().isoformat(),
                file_size_bytes=0,
                error_message=str(e)
            )
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available templates"""
        templates = self.template_manager.list_all_templates()
        return [asdict(template) for template in templates]
    
    def get_templates_for_job(self, job_analysis: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get templates recommended for specific job"""
        if not job_analysis:
            return self.get_available_templates()
        
        industry = job_analysis.get('industry', 'general')
        is_entry_level = job_analysis.get('experience_level') == 'entry_level'
        
        # Get industry-specific templates
        industry_templates = self.template_manager.get_templates_for_industry(industry)
        
        # Get background-friendly templates
        bg_friendly_templates = self.template_manager.get_background_friendly_templates()
        
        # Combine and deduplicate
        recommended = {}
        for template in industry_templates + bg_friendly_templates:
            recommended[template.id] = template
        
        # Convert to dict format
        return [asdict(template) for template in recommended.values()]

# Example usage and testing
if __name__ == "__main__":
    engine = ResumeTemplateEngine()
    
    # Test resume data
    test_resume = {
        'full_name': 'John Smith',
        'email': 'john.smith@email.com',
        'phone': '5551234567',
        'location': 'Los Angeles, CA',
        'summary': 'Hardworking individual with experience in warehouse operations and team collaboration.',
        'work_experience': [
            {
                'title': 'Warehouse Associate',
                'company': 'ABC Logistics',
                'start_date': '2022-01',
                'end_date': '2023-12',
                'description': 'Managed inventory, operated forklifts, and maintained safety standards.'
            }
        ],
        'education': [
            {
                'degree': 'High School Diploma',
                'institution': 'Central High School',
                'graduation_year': '2020'
            }
        ],
        'technical_skills': ['Forklift Operation', 'Inventory Management', 'Microsoft Office'],
        'soft_skills': ['Teamwork', 'Reliability', 'Communication']
    }
    
    # Test template rendering
    result = engine.render_resume(test_resume, 'warehouse', generate_pdf=True)
    
    print(f"✅ Resume Template Engine Test Complete!")
    print(f"Success: {result.success}")
    print(f"Template Used: {result.template_used}")
    print(f"HTML Length: {len(result.html_content)}")
    print(f"PDF Path: {result.pdf_path}")
    print(f"File Size: {result.file_size_bytes} bytes")
    print(f"Available Templates: {len(engine.get_available_templates())}")