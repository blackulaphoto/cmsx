import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from pathlib import Path

# Try to import WeasyPrint, fallback if not available
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    logging.warning(f"WeasyPrint not available: {e}. PDFs will be generated as HTML files.")

from jinja2 import Environment, FileSystemLoader, Template

logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self):
        # More flexible path detection
        self.base_dir = self._find_base_dir()
        self.template_dir = self.base_dir / 'templates'
        self.output_dir = self.base_dir / 'output'
        self.styles_dir = self.template_dir / 'styles'
        
        self.ensure_directories()
        self.setup_templates()
    
    def _find_base_dir(self) -> Path:
        """Find the appropriate base directory"""
        current_file = Path(__file__).parent
        
        # Try different possible locations
        possible_paths = [
            current_file,
            current_file / 'resume',
            current_file.parent / 'static' / 'resumes',
            Path.cwd() / 'backend' / 'services',
            Path.cwd() / 'static' / 'resumes',
            Path.cwd() / 'temp' / 'resumes'
        ]
        
        for path in possible_paths:
            try:
                path.mkdir(parents=True, exist_ok=True)
                if os.access(path, os.W_OK):
                    logger.info(f"Using base directory: {path}")
                    return path
            except Exception as e:
                logger.debug(f"Cannot use path {path}: {e}")
                continue
        
        # Fallback to temp directory
        temp_path = Path.cwd() / 'temp' / 'pdf_service'
        temp_path.mkdir(parents=True, exist_ok=True)
        logger.warning(f"Using fallback temp directory: {temp_path}")
        return temp_path
    
    def ensure_directories(self):
        """Create necessary directories with better error handling"""
        directories = [self.template_dir, self.styles_dir, self.output_dir]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                # Test write permissions
                test_file = directory / '.write_test'
                test_file.touch()
                test_file.unlink()
                logger.debug(f"Directory ensured with write access: {directory}")
            except Exception as e:
                logger.error(f"Cannot create or write to directory {directory}: {e}")
                # Try alternative location
                alt_dir = Path.cwd() / 'temp' / directory.name
                try:
                    alt_dir.mkdir(parents=True, exist_ok=True)
                    if directory == self.template_dir:
                        self.template_dir = alt_dir
                    elif directory == self.output_dir:
                        self.output_dir = alt_dir
                    elif directory == self.styles_dir:
                        self.styles_dir = alt_dir
                    logger.warning(f"Using alternative directory: {alt_dir}")
                except Exception as e2:
                    logger.error(f"Failed to create alternative directory: {e2}")
    
    def setup_templates(self):
        """Create HTML templates if they don't exist with error handling"""
        templates = {
            'classic': self.get_classic_template(),
            'modern': self.get_modern_template(),
            'warehouse': self.get_warehouse_template(),
            'construction': self.get_construction_template(),
            'food_service': self.get_food_service_template(),
            'medical_social': self.get_medical_social_template()
        }
        
        for template_name, template_content in templates.items():
            template_path = self.template_dir / f"{template_name}.html"
            try:
                if not template_path.exists():
                    with open(template_path, 'w', encoding='utf-8') as f:
                        f.write(template_content)
                    logger.info(f"Created template: {template_path}")
                else:
                    logger.debug(f"Template already exists: {template_path}")
            except Exception as e:
                logger.error(f"Failed to create template {template_path}: {e}")
    
    async def generate_pdf(self, resume_data: Dict[str, Any], client_data: Dict[str, Any], 
                          template_type: str = 'classic') -> Optional[str]:
        """Generate PDF and return file path with enhanced error handling"""
        try:
            # Validate input data
            if not resume_data or not client_data:
                logger.error("Invalid input data for PDF generation")
                return None
            
            # Create client directory
            client_id = client_data.get('client_id', 'unknown')
            client_dir = self.output_dir / f"client_{client_id}"
            
            try:
                client_dir.mkdir(exist_ok=True)
            except Exception as e:
                logger.error(f"Cannot create client directory {client_dir}: {e}")
                # Use base output directory
                client_dir = self.output_dir
            
            # Generate HTML content
            try:
                html_content = await self.render_template(resume_data, client_data, template_type)
            except Exception as e:
                logger.error(f"Template rendering failed: {e}")
                html_content = self.get_basic_html_fallback(client_data, resume_data)
            
            # Generate PDF filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            resume_id = resume_data.get('resume_id', timestamp)
            safe_resume_id = str(resume_id).replace('/', '_').replace('\\', '_')
            
            # Try different file extensions
            for extension in ['.pdf', '.html']:
                try:
                    filename = f"resume_{safe_resume_id}{extension}"
                    file_path = client_dir / filename
                    
                    if extension == '.pdf' and WEASYPRINT_AVAILABLE:
                        success = await self.generate_weasyprint_pdf(html_content, file_path)
                        if success:
                            logger.info(f"PDF generated successfully: {file_path}")
                            return str(file_path)
                    elif extension == '.html':
                        success = await self.generate_html_fallback(html_content, file_path)
                        if success:
                            logger.info(f"HTML fallback generated successfully: {file_path}")
                            return str(file_path)
                except Exception as e:
                    logger.error(f"Failed to generate {extension} file: {e}")
                    continue
            
            logger.error("All file generation methods failed")
            return None
                
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            return None
    
    async def generate_weasyprint_pdf(self, html_content: str, pdf_path: Path) -> bool:
        """Generate PDF using WeasyPrint with better error handling"""
        if not WEASYPRINT_AVAILABLE:
            return False
            
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def generate_pdf_sync():
                try:
                    HTML(string=html_content, base_url=str(self.template_dir)).write_pdf(str(pdf_path))
                    return True
                except Exception as e:
                    logger.error(f"WeasyPrint PDF generation failed: {e}")
                    return False
            
            result = await loop.run_in_executor(None, generate_pdf_sync)
            return result
        except Exception as e:
            logger.error(f"WeasyPrint PDF generation error: {e}")
            return False
    
    async def generate_html_fallback(self, html_content: str, file_path: Path) -> bool:
        """Generate HTML file as PDF fallback with better error handling"""
        try:
            # Ensure the file has .html extension
            if file_path.suffix != '.html':
                file_path = file_path.with_suffix('.html')
            
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add some styling to make HTML look more like a PDF
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Resume</title>
                <style>
                    body {{ 
                        max-width: 8.5in; 
                        margin: 0 auto; 
                        padding: 20px; 
                        font-family: Arial, sans-serif;
                        background: white;
                        box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    }}
                    @media print {{
                        body {{ box-shadow: none; }}
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(styled_html)
            
            logger.info(f"Generated HTML fallback: {file_path}")
            return True
        except Exception as e:
            logger.error(f"HTML fallback generation failed: {e}")
            return False
    
    async def render_template(self, resume_data: Dict[str, Any], client_data: Dict[str, Any], 
                            template_type: str) -> str:
        """Render HTML template with better error handling"""
        try:
            # Check if template directory exists and is accessible
            if not self.template_dir.exists():
                logger.error(f"Template directory does not exist: {self.template_dir}")
                return self.get_basic_html_fallback(client_data, resume_data)
            
            try:
                env = Environment(loader=FileSystemLoader(str(self.template_dir)))
                template_filename = f"{template_type}.html"
                
                # Check if template file exists
                template_path = self.template_dir / template_filename
                if not template_path.exists():
                    logger.warning(f"Template {template_filename} not found, using classic")
                    template_filename = "classic.html"
                    template_path = self.template_dir / template_filename
                    
                    if not template_path.exists():
                        logger.error("Classic template also not found, using fallback")
                        return self.get_basic_html_fallback(client_data, resume_data)
                
                template = env.get_template(template_filename)
            except Exception as e:
                logger.error(f"Template loading failed: {e}")
                return self.get_basic_html_fallback(client_data, resume_data)
            
            # Prepare template context with safe defaults
            context = {
                'client': self._safe_client_data(client_data),
                'resume': self._safe_resume_data(resume_data),
                'template_type': template_type,
                'generation_date': datetime.now().strftime("%B %d, %Y"),
                'styles': self.get_template_styles(template_type)
            }
            
            try:
                rendered = template.render(**context)
                return rendered
            except Exception as e:
                logger.error(f"Template rendering failed: {e}")
                return self.get_basic_html_fallback(client_data, resume_data)
            
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return self.get_basic_html_fallback(client_data, resume_data)
    
    def get_template_styles(self, template_type: str) -> str:
        """Get CSS styles for template"""
        styles = {
            'classic': """
                body { font-family: 'Times New Roman', serif; color: #000; background: white; }
                .header { text-align: center; border-bottom: 2px solid #1e40af; padding-bottom: 10px; margin-bottom: 20px; }
                .name { font-size: 24px; font-weight: bold; color: #1e40af; text-transform: uppercase; }
                .contact { font-size: 12px; color: #666; margin-top: 5px; }
                .section-title { font-size: 14px; font-weight: bold; color: #1e40af; text-transform: uppercase; border-bottom: 1px solid #1e40af; padding-bottom: 2px; margin: 15px 0 8px 0; }
                .job-title { font-weight: bold; color: #1e40af; }
                .company { font-weight: bold; font-style: italic; }
                .dates { font-size: 11px; color: #666; font-style: italic; }
                ul { margin: 5px 0; padding-left: 20px; }
                li { margin-bottom: 3px; }
            """,
            'modern': """
                body { font-family: 'Arial', sans-serif; color: #000; background: white; }
                .header { text-align: center; background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; margin: -20px -20px 20px -20px; }
                .name { font-size: 26px; font-weight: bold; color: white; }
                .contact { font-size: 12px; color: rgba(255,255,255,0.9); margin-top: 5px; }
                .section-title { font-size: 14px; font-weight: bold; color: #7c3aed; text-transform: uppercase; border-bottom: 2px solid #7c3aed; padding-bottom: 2px; margin: 15px 0 8px 0; }
                .job-title { font-weight: bold; color: #8b5cf6; }
                .company { font-weight: bold; font-style: italic; }
                .dates { font-size: 11px; color: #666; font-style: italic; }
                ul { margin: 5px 0; padding-left: 20px; }
                li { margin-bottom: 3px; }
            """,
            'warehouse': """
                body { font-family: 'Arial', sans-serif; color: #000; background: white; }
                .header { text-align: center; border-bottom: 3px solid #f59e0b; padding-bottom: 10px; margin-bottom: 20px; }
                .name { font-size: 24px; font-weight: 900; color: #d97706; text-transform: uppercase; }
                .contact { font-size: 12px; color: #666; margin-top: 5px; }
                .section-title { font-size: 14px; font-weight: 900; color: #f59e0b; text-transform: uppercase; border-bottom: 2px solid #f59e0b; padding-bottom: 2px; margin: 15px 0 8px 0; }
                .job-title { font-weight: bold; color: #d97706; }
                .company { font-weight: bold; font-style: italic; }
                .dates { font-size: 11px; color: #666; font-style: italic; }
                ul { margin: 5px 0; padding-left: 20px; }
                li { margin-bottom: 3px; }
            """,
            'construction': """
                body { font-family: 'Arial', sans-serif; color: #000; background: white; }
                .header { text-align: center; border-bottom: 3px solid #dc2626; padding-bottom: 10px; margin-bottom: 20px; }
                .name { font-size: 24px; font-weight: 900; color: #991b1b; text-transform: uppercase; }
                .contact { font-size: 12px; color: #666; margin-top: 5px; }
                .section-title { font-size: 14px; font-weight: 900; color: #dc2626; text-transform: uppercase; border-bottom: 2px solid #dc2626; padding-bottom: 2px; margin: 15px 0 8px 0; }
                .job-title { font-weight: bold; color: #b91c1c; }
                .company { font-weight: bold; font-style: italic; }
                .dates { font-size: 11px; color: #666; font-style: italic; }
                ul { margin: 5px 0; padding-left: 20px; }
                li { margin-bottom: 3px; }
            """,
            'food_service': """
                body { font-family: 'Arial', sans-serif; color: #000; background: white; }
                .header { text-align: center; border-bottom: 3px solid #059669; padding-bottom: 10px; margin-bottom: 20px; }
                .name { font-size: 24px; font-weight: bold; color: #047857; text-transform: uppercase; }
                .contact { font-size: 12px; color: #666; margin-top: 5px; }
                .section-title { font-size: 14px; font-weight: bold; color: #059669; text-transform: uppercase; border-bottom: 2px solid #059669; padding-bottom: 2px; margin: 15px 0 8px 0; }
                .job-title { font-weight: bold; color: #065f46; }
                .company { font-weight: bold; font-style: italic; }
                .dates { font-size: 11px; color: #666; font-style: italic; }
                ul { margin: 5px 0; padding-left: 20px; }
                li { margin-bottom: 3px; }
            """,
            'medical_social': """
                body { font-family: 'Arial', sans-serif; color: #000; background: white; }
                .header { text-align: center; border-bottom: 3px solid #0891b2; padding-bottom: 10px; margin-bottom: 20px; }
                .name { font-size: 24px; font-weight: bold; color: #0e7490; text-transform: uppercase; }
                .contact { font-size: 12px; color: #666; margin-top: 5px; }
                .section-title { font-size: 14px; font-weight: bold; color: #0891b2; text-transform: uppercase; border-bottom: 2px solid #0891b2; padding-bottom: 2px; margin: 15px 0 8px 0; }
                .job-title { font-weight: bold; color: #0e7490; }
                .company { font-weight: bold; font-style: italic; }
                .dates { font-size: 11px; color: #666; font-style: italic; }
                ul { margin: 5px 0; padding-left: 20px; }
                li { margin-bottom: 3px; }
            """
        }
        return styles.get(template_type, styles['classic'])
    
    def get_classic_template(self) -> str:
        """Classic professional template"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume - {{ client.first_name }} {{ client.last_name }}</title>
    <style>
        {{ styles }}
        body { margin: 0; padding: 20px; line-height: 1.4; }
        .resume-container { max-width: 8.5in; margin: 0 auto; }
        .section { margin-bottom: 15px; }
        .job-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; }
        .skills-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .skill-category { margin-bottom: 10px; }
        .skill-title { font-weight: bold; font-size: 12px; margin-bottom: 3px; }
        .skill-list { font-size: 11px; }
    </style>
</head>
<body>
    <div class="resume-container">
        <header class="header">
            <div class="name">{{ client.first_name }} {{ client.last_name }}</div>
            <div class="contact">
                {{ client.phone }} • {{ client.email }}
                {% if client.address %} • {{ client.address }}{% endif %}
            </div>
        </header>

        {% if resume.career_objective %}
        <div class="section">
            <div class="section-title">OBJECTIVE</div>
            <p>{{ resume.career_objective }}</p>
        </div>
        {% endif %}

        {% if resume.work_history %}
        <div class="section">
            <div class="section-title">EXPERIENCE</div>
            {% for job in resume.work_history %}
            <div style="margin-bottom: 12px;">
                <div class="job-header">
                    <span class="job-title">{{ job.job_title or 'Job Title' }}</span>
                    <span class="company">{{ job.company or 'Company Name' }}</span>
                </div>
                {% if job.location or job.start_date or job.end_date %}
                <div class="dates">
                    {% if job.location %}{{ job.location }} • {% endif %}
                    {{ job.start_date or 'Start Date' }} - {{ job.end_date or 'Present' }}
                </div>
                {% endif %}
                {% if job.description %}
                <ul>
                    {% for line in job.description.split('\n') %}
                        {% if line.strip() %}
                        <li>{{ line.strip().replace('•', '').strip() }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if resume.skills %}
        <div class="section">
            <div class="section-title">SKILLS</div>
            <div class="skills-grid">
                {% for skill_cat in resume.skills %}
                <div class="skill-category">
                    <div class="skill-title">{{ skill_cat.category or 'Skills' }}</div>
                    <div class="skill-list">{{ (skill_cat.skill_list or []) | join(', ') }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if resume.education %}
        <div class="section">
            <div class="section-title">EDUCATION</div>
            {% for edu in resume.education %}
            <div style="margin-bottom: 8px;">
                <div class="job-title">{{ edu.degree or 'Degree' }}</div>
                <div class="company">{{ edu.institution or 'Institution' }}</div>
                <div class="dates">{{ edu.graduation_date or 'Year' }}</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if resume.certifications %}
        <div class="section">
            <div class="section-title">CERTIFICATIONS</div>
            {% for cert in resume.certifications %}
            <div style="margin-bottom: 8px;">
                <div class="job-title">{{ cert.name or 'Certification' }}</div>
                <div class="company">{{ cert.issuer or 'Issuer' }}</div>
                <div class="dates">{{ cert.date_obtained or 'Date' }}</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div style="margin-top: 30px; text-align: center; font-size: 10px; color: #666;">
            Generated on {{ generation_date }}
        </div>
    </div>
</body>
</html>
        """
    
    def get_modern_template(self) -> str:
        """Modern template with gradient header"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume - {{ client.first_name }} {{ client.last_name }}</title>
    <style>
        {{ styles }}
        body { margin: 0; padding: 20px; line-height: 1.4; }
        .resume-container { max-width: 8.5in; margin: 0 auto; }
        .section { margin-bottom: 15px; }
        .job-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; }
        .skills-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .skill-category { margin-bottom: 10px; }
        .skill-title { font-weight: bold; font-size: 12px; margin-bottom: 3px; color: #7c3aed; }
        .skill-list { font-size: 11px; }
    </style>
</head>
<body>
    <div class="resume-container">
        <header class="header">
            <div class="name">{{ client.first_name }} {{ client.last_name }}</div>
            <div class="contact">
                {{ client.phone }} • {{ client.email }}
                {% if client.address %} • {{ client.address }}{% endif %}
            </div>
        </header>

        {% if resume.career_objective %}
        <div class="section">
            <div class="section-title">PROFESSIONAL SUMMARY</div>
            <p>{{ resume.career_objective }}</p>
        </div>
        {% endif %}

        {% if resume.work_history %}
        <div class="section">
            <div class="section-title">EXPERIENCE</div>
            {% for job in resume.work_history %}
            <div style="margin-bottom: 12px;">
                <div class="job-header">
                    <span class="job-title">{{ job.job_title or 'Job Title' }}</span>
                    <span class="company">{{ job.company or 'Company Name' }}</span>
                </div>
                {% if job.location or job.start_date or job.end_date %}
                <div class="dates">
                    {% if job.location %}{{ job.location }} • {% endif %}
                    {{ job.start_date or 'Start Date' }} - {{ job.end_date or 'Present' }}
                </div>
                {% endif %}
                {% if job.description %}
                <ul>
                    {% for line in job.description.split('\n') %}
                        {% if line.strip() %}
                        <li>{{ line.strip().replace('•', '').strip() }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if resume.skills %}
        <div class="section">
            <div class="section-title">CORE COMPETENCIES</div>
            <div class="skills-grid">
                {% for skill_cat in resume.skills %}
                <div class="skill-category">
                    <div class="skill-title">{{ skill_cat.category or 'Skills' }}</div>
                    <div class="skill-list">{{ (skill_cat.skill_list or []) | join(', ') }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if resume.education %}
        <div class="section">
            <div class="section-title">EDUCATION</div>
            {% for edu in resume.education %}
            <div style="margin-bottom: 8px;">
                <div class="job-title">{{ edu.degree or 'Degree' }}</div>
                <div class="company">{{ edu.institution or 'Institution' }}</div>
                <div class="dates">{{ edu.graduation_date or 'Year' }}</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if resume.certifications %}
        <div class="section">
            <div class="section-title">CERTIFICATIONS</div>
            {% for cert in resume.certifications %}
            <div style="margin-bottom: 8px;">
                <div class="job-title">{{ cert.name or 'Certification' }}</div>
                <div class="company">{{ cert.issuer or 'Issuer' }}</div>
                <div class="dates">{{ cert.date_obtained or 'Date' }}</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div style="margin-top: 30px; text-align: center; font-size: 10px; color: #666;">
            Generated on {{ generation_date }}
        </div>
    </div>
</body>
</html>
        """
    
    def get_warehouse_template(self) -> str:
        """Warehouse/logistics focused template"""
        return self.get_classic_template().replace('OBJECTIVE', 'PROFESSIONAL SUMMARY').replace('EXPERIENCE', 'WORK EXPERIENCE').replace('SKILLS', 'KEY QUALIFICATIONS')
    
    def get_construction_template(self) -> str:
        """Construction focused template"""
        return self.get_classic_template().replace('OBJECTIVE', 'PROFESSIONAL SUMMARY').replace('SKILLS', 'TECHNICAL SKILLS')
    
    def get_food_service_template(self) -> str:
        """Food service focused template"""
        return self.get_classic_template().replace('OBJECTIVE', 'PROFESSIONAL SUMMARY').replace('SKILLS', 'SERVICE SKILLS')
    
    def get_medical_social_template(self) -> str:
        """Medical/social services focused template"""
        return self.get_classic_template().replace('OBJECTIVE', 'PROFESSIONAL SUMMARY').replace('SKILLS', 'PROFESSIONAL COMPETENCIES')
    
    def _safe_client_data(self, client_data: Dict[str, Any]) -> Dict[str, str]:
        """Safely extract client data with defaults"""
        return {
            'first_name': str(client_data.get('first_name', 'Unknown')),
            'last_name': str(client_data.get('last_name', 'Client')),
            'phone': str(client_data.get('phone', '')),
            'email': str(client_data.get('email', '')),
            'address': str(client_data.get('address', ''))
        }
    
    def _safe_resume_data(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Safely extract resume data with defaults"""
        return {
            'career_objective': str(resume_data.get('career_objective', '')),
            'work_history': resume_data.get('work_history', []),
            'skills': resume_data.get('skills', []),
            'education': resume_data.get('education', []),
            'certifications': resume_data.get('certifications', [])
        }
    
    def get_basic_html_fallback(self, client_data: Dict[str, Any], resume_data: Dict[str, Any]) -> str:
        """Enhanced basic HTML fallback"""
        client = self._safe_client_data(client_data)
        resume = self._safe_resume_data(resume_data)
        
        # Build HTML parts separately to avoid f-string nesting issues
        header_html = f"""
        <div class="header">
            <h1>{client['first_name']} {client['last_name']}</h1>
            <p>{client['phone']} • {client['email']}</p>
        """
        
        if client['address']:
            header_html += f"<p>{client['address']}</p>"
        header_html += "</div>"
        
        objective_html = ""
        if resume['career_objective']:
            objective_html = f"""
            <div class="section">
                <div class="section-title">OBJECTIVE</div>
                <p>{resume['career_objective']}</p>
            </div>
            """
        
        experience_html = ""
        if resume['work_history']:
            experience_html = '<div class="section"><div class="section-title">EXPERIENCE</div>'
            for job in resume['work_history']:
                job_title = job.get('job_title', 'Job Title')
                company = job.get('company', 'Company Name')
                start_date = job.get('start_date', 'Start Date')
                end_date = job.get('end_date', 'Present')
                description = job.get('description', '')
                
                experience_html += f"""
                <div class="work-item">
                    <div class="job-title">{job_title}</div>
                    <div class="company">{company}</div>
                    <div class="dates">{start_date} - {end_date}</div>
                """
                if description:
                    experience_html += f"<p>{description}</p>"
                experience_html += "</div>"
            experience_html += "</div>"
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Resume - {client['first_name']} {client['last_name']}</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            max-width: 8.5in; 
            margin: 0 auto; 
            padding: 20px;
            background: white;
        }}
        .header {{ 
            text-align: center; 
            border-bottom: 2px solid #333; 
            padding-bottom: 10px; 
            margin-bottom: 20px;
        }}
        .section {{ margin: 20px 0; }}
        .section-title {{ 
            font-weight: bold; 
            font-size: 16px; 
            color: #333; 
            border-bottom: 1px solid #ccc;
            padding-bottom: 5px;
            margin-bottom: 10px;
        }}
        .work-item {{ margin-bottom: 15px; }}
        .job-title {{ font-weight: bold; color: #1e40af; }}
        .company {{ font-style: italic; }}
        .dates {{ color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    {header_html}
    {objective_html}
    {experience_html}
    
    <div style="margin-top: 30px; text-align: center; font-size: 12px; color: #666;">
        Resume generated with basic template fallback
    </div>
</body>
</html>
        """

# Create global instance with error handling
try:
    pdf_service = PDFService()
    logger.info("PDF Service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize PDF Service: {e}")
    pdf_service = None