#!/usr/bin/env python3
"""
Resume Generator with GPT-4o Integration
Creates ATS-compliant, humanized resumes from user data
"""

import json
import logging
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import asdict
import requests

try:
    from .models import ResumeData, Resume, ResumeDatabase
    from .utils import ResumeDataProcessor, ResumeTemplateHelper
except ImportError:
    # For direct execution
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from resume.models import ResumeData, Resume, ResumeDatabase
    from resume.utils import ResumeDataProcessor, ResumeTemplateHelper

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIClient:
    """OpenAI API client for resume generation"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or "REDACTED"
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(self, messages: List[Dict[str, str]], model: str = "gpt-4o", 
                       temperature: float = 0.7, max_tokens: int = 2000) -> Optional[str]:
        """Make a chat completion request to OpenAI"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return None

class ResumeGenerator:
    """Main resume generator class"""
    
    def __init__(self, openai_client: OpenAIClient = None):
        self.openai_client = openai_client or OpenAIClient()
        self.processor = ResumeDataProcessor()
        self.template_helper = ResumeTemplateHelper()
    
    def generate_base_resume(self, resume_data: ResumeData, 
                           target_industry: str = "general") -> Dict[str, Any]:
        """Generate a base ATS-compliant resume"""
        try:
            # Create the system prompt for resume generation
            system_prompt = self._create_system_prompt(target_industry)
            
            # Create the user prompt with resume data
            user_prompt = self._create_user_prompt(resume_data)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Generate the resume content
            generated_content = self.openai_client.chat_completion(
                messages=messages,
                model="gpt-4o",
                temperature=0.7,
                max_tokens=2500
            )
            
            if not generated_content:
                raise Exception("Failed to generate resume content")
            
            # Parse the generated content
            resume_sections = self._parse_generated_content(generated_content)
            
            # Create the final resume structure
            final_resume = self._create_final_resume_structure(resume_data, resume_sections)
            
            return {
                "success": True,
                "resume": final_resume,
                "raw_content": generated_content,
                "ats_score": self._calculate_initial_ats_score(final_resume)
            }
            
        except Exception as e:
            logger.error(f"Error generating base resume: {e}")
            return {
                "success": False,
                "error": str(e),
                "resume": None
            }
    
    def _create_system_prompt(self, target_industry: str) -> str:
        """Create the system prompt for resume generation"""
        return f"""You are an expert resume writer specializing in creating ATS-compliant, professional resumes for people seeking employment, including those with criminal backgrounds who deserve second chances.

Your task is to create a compelling, honest, and professional resume that:

1. **ATS Optimization**: Uses standard formatting, relevant keywords, and clear section headers
2. **Professional Tone**: Maintains a confident, positive tone throughout
3. **Skills-Focused**: Emphasizes transferable skills, accomplishments, and potential
4. **Background-Friendly**: Focuses on strengths without hiding gaps, using positive framing
5. **Industry-Relevant**: Tailored for the {target_industry} industry when applicable

**Key Guidelines:**
- Use action verbs and quantifiable achievements when possible
- Focus on skills, growth, and reliability rather than dwelling on past challenges
- Include relevant keywords for ATS systems
- Maintain honesty while presenting information in the most positive light
- Use standard resume formatting and section headers
- Keep descriptions concise but impactful
- Emphasize soft skills like reliability, teamwork, and work ethic

**Section Structure:**
1. Professional Summary (3-4 sentences highlighting key strengths)
2. Core Skills (mix of technical and soft skills)
3. Professional Experience (focus on accomplishments and responsibilities)
4. Education & Training
5. Additional Qualifications (certifications, volunteer work, etc.)

**Tone:** Professional, confident, and forward-looking. Focus on what the candidate can contribute to an employer.

Generate ONLY the resume content in a clear, structured format. Do not include explanations or meta-commentary."""

    def _create_user_prompt(self, resume_data: ResumeData) -> str:
        """Create the user prompt with resume data"""
        # Format work experience
        work_exp_text = ""
        for exp in resume_data.work_experience:
            end_date = exp.get('end_date', 'Present')
            if exp.get('current_job'):
                end_date = 'Present'
            
            work_exp_text += f"""
Company: {exp.get('company', '')}
Position: {exp.get('position', '')}
Duration: {exp.get('start_date', '')} - {end_date}
Location: {exp.get('location', '')}
Description: {exp.get('description', '')}
"""
        
        # Format education
        education_text = ""
        for edu in resume_data.education:
            education_text += f"""
Institution: {edu.get('institution', '')}
Degree/Program: {edu.get('degree', '')}
Field of Study: {edu.get('field_of_study', '')}
Graduation Year: {edu.get('graduation_year', '')}
Location: {edu.get('location', '')}
"""
        
        # Format skills
        all_skills = resume_data.technical_skills + resume_data.soft_skills
        skills_text = ", ".join([skill for skill in all_skills if skill.strip()])
        
        # Format certifications
        cert_text = ""
        for cert in resume_data.certifications:
            if cert.get('name'):
                cert_text += f"""
Certification: {cert.get('name', '')}
Issuer: {cert.get('issuer', '')}
Date: {cert.get('date_obtained', '')}
"""
        
        # Format volunteer experience
        volunteer_text = ""
        for vol in resume_data.volunteer_experience:
            if vol.get('organization'):
                volunteer_text += f"""
Organization: {vol.get('organization', '')}
Role: {vol.get('role', '')}
Description: {vol.get('description', '')}
"""
        
        # Format additional info
        additional_info = []
        if resume_data.languages:
            lang_list = [lang for lang in resume_data.languages if lang.strip()]
            if lang_list:
                additional_info.append(f"Languages: {', '.join(lang_list)}")
        
        if resume_data.achievements:
            ach_list = [ach for ach in resume_data.achievements if ach.strip()]
            if ach_list:
                additional_info.append(f"Achievements: {'; '.join(ach_list)}")
        
        additional_text = "\n".join(additional_info)
        
        prompt = f"""Please create a professional, ATS-compliant resume using the following information:

**Personal Information:**
Name: {resume_data.full_name}
Email: {resume_data.email}
Phone: {resume_data.phone}
Address: {resume_data.address}, {resume_data.city}, {resume_data.state} {resume_data.zip_code}

**Professional Summary (provided by candidate):**
{resume_data.professional_summary}

**Work Experience:**
{work_exp_text}

**Education:**
{education_text}

**Skills:**
{skills_text}

**Certifications:**
{cert_text}

**Volunteer Experience:**
{volunteer_text}

**Additional Information:**
{additional_text}

**Special Considerations:**
- This candidate is seeking a second chance and has demonstrated commitment to positive change
- Focus on transferable skills, reliability, and growth potential
- Emphasize accomplishments and contributions in each role
- Use positive, forward-looking language
- Include relevant keywords for ATS optimization

Please create a compelling resume that presents this candidate in the best possible light while maintaining honesty and professionalism."""

        return prompt
    
    def _parse_generated_content(self, content: str) -> Dict[str, str]:
        """Parse the generated resume content into sections"""
        sections = {}
        
        # Common section headers to look for
        section_patterns = {
            'summary': r'(?:PROFESSIONAL SUMMARY|SUMMARY|PROFILE|OBJECTIVE)[\s\n]*:?\s*\n(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)',
            'skills': r'(?:CORE SKILLS|SKILLS|TECHNICAL SKILLS|KEY SKILLS)[\s\n]*:?\s*\n(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)',
            'experience': r'(?:PROFESSIONAL EXPERIENCE|WORK EXPERIENCE|EXPERIENCE|EMPLOYMENT)[\s\n]*:?\s*\n(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)',
            'education': r'(?:EDUCATION|EDUCATION & TRAINING|ACADEMIC BACKGROUND)[\s\n]*:?\s*\n(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)',
            'additional': r'(?:ADDITIONAL QUALIFICATIONS|CERTIFICATIONS|VOLUNTEER EXPERIENCE|ADDITIONAL INFORMATION)[\s\n]*:?\s*\n(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)'
        }
        
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                sections[section_name] = match.group(1).strip()
        
        # If no sections found, treat entire content as raw resume
        if not sections:
            sections['raw'] = content
        
        return sections
    
    def _create_final_resume_structure(self, resume_data: ResumeData, 
                                     sections: Dict[str, str]) -> Dict[str, Any]:
        """Create the final structured resume"""
        return {
            "header": {
                "name": resume_data.full_name,
                "email": resume_data.email,
                "phone": resume_data.phone,
                "address": f"{resume_data.address}, {resume_data.city}, {resume_data.state} {resume_data.zip_code}".strip()
            },
            "sections": {
                "professional_summary": sections.get('summary', resume_data.professional_summary),
                "core_skills": sections.get('skills', ''),
                "professional_experience": sections.get('experience', ''),
                "education": sections.get('education', ''),
                "additional_qualifications": sections.get('additional', '')
            },
            "raw_content": sections.get('raw', ''),
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generator_version": "1.0",
                "target_industry": "general"
            }
        }
    
    def _calculate_initial_ats_score(self, resume: Dict[str, Any]) -> float:
        """Calculate an initial ATS score for the resume"""
        score = 0.0
        max_score = 100.0
        
        # Check for required sections (40 points)
        required_sections = ['professional_summary', 'professional_experience', 'education']
        for section in required_sections:
            if resume['sections'].get(section, '').strip():
                score += 13.33
        
        # Check for contact information (20 points)
        header = resume.get('header', {})
        contact_fields = ['name', 'email', 'phone']
        for field in contact_fields:
            if header.get(field, '').strip():
                score += 6.67
        
        # Check for skills section (15 points)
        if resume['sections'].get('core_skills', '').strip():
            score += 15
        
        # Check for additional qualifications (10 points)
        if resume['sections'].get('additional_qualifications', '').strip():
            score += 10
        
        # Check for action verbs and keywords (15 points)
        content = ' '.join(resume['sections'].values()).lower()
        action_verbs = ['achieved', 'managed', 'led', 'developed', 'improved', 'created', 'implemented']
        verb_count = sum(1 for verb in action_verbs if verb in content)
        score += min(verb_count * 2, 15)
        
        return min(score, max_score)

class ResumeFormatter:
    """Formats resume content for different output formats"""
    
    def __init__(self):
        self.template_helper = ResumeTemplateHelper()
    
    def format_as_html(self, resume: Dict[str, Any]) -> str:
        """Format resume as HTML"""
        header = resume.get('header', {})
        sections = resume.get('sections', {})
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{header.get('name', 'Resume')}</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #2c3e50;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            color: #2c3e50;
            font-weight: bold;
        }}
        .contact-info {{
            margin-top: 10px;
            font-size: 1.1em;
            color: #555;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .section h2 {{
            color: #2c3e50;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
            margin-bottom: 15px;
            font-size: 1.4em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .section-content {{
            margin-left: 10px;
            line-height: 1.7;
        }}
        .experience-item {{
            margin-bottom: 20px;
        }}
        .job-title {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 1.1em;
        }}
        .company {{
            font-style: italic;
            color: #7f8c8d;
        }}
        .date-range {{
            float: right;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .skills-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .skill-item {{
            background: #ecf0f1;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.9em;
            color: #2c3e50;
        }}
        @media print {{
            body {{ margin: 0; padding: 15px; }}
            .header h1 {{ font-size: 2em; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{header.get('name', '')}</h1>
        <div class="contact-info">
            {header.get('email', '')} | {header.get('phone', '')} | {header.get('address', '')}
        </div>
    </div>
"""
        
        # Add sections
        section_order = [
            ('professional_summary', 'Professional Summary'),
            ('core_skills', 'Core Skills'),
            ('professional_experience', 'Professional Experience'),
            ('education', 'Education'),
            ('additional_qualifications', 'Additional Qualifications')
        ]
        
        for section_key, section_title in section_order:
            content = sections.get(section_key, '').strip()
            if content:
                html += f"""
    <div class="section">
        <h2>{section_title}</h2>
        <div class="section-content">
            {self._format_section_content(content, section_key)}
        </div>
    </div>
"""
        
        html += """
</body>
</html>
"""
        return html
    
    def _format_section_content(self, content: str, section_type: str) -> str:
        """Format section content based on type"""
        if section_type == 'core_skills':
            # Format skills as tags
            skills = [skill.strip() for skill in content.replace(',', '\n').split('\n') if skill.strip()]
            if skills:
                return '<div class="skills-list">' + ''.join([f'<span class="skill-item">{skill}</span>' for skill in skills]) + '</div>'
        
        # For other sections, convert line breaks to HTML
        formatted = content.replace('\n\n', '</p><p>').replace('\n', '<br>')
        return f'<p>{formatted}</p>'
    
    def format_as_text(self, resume: Dict[str, Any]) -> str:
        """Format resume as plain text"""
        header = resume.get('header', {})
        sections = resume.get('sections', {})
        
        text = f"""
{header.get('name', '').upper()}
{header.get('email', '')} | {header.get('phone', '')}
{header.get('address', '')}

"""
        
        section_order = [
            ('professional_summary', 'PROFESSIONAL SUMMARY'),
            ('core_skills', 'CORE SKILLS'),
            ('professional_experience', 'PROFESSIONAL EXPERIENCE'),
            ('education', 'EDUCATION'),
            ('additional_qualifications', 'ADDITIONAL QUALIFICATIONS')
        ]
        
        for section_key, section_title in section_order:
            content = sections.get(section_key, '').strip()
            if content:
                text += f"{section_title}\n{'=' * len(section_title)}\n{content}\n\n"
        
        return text.strip()

# Example usage and testing
if __name__ == "__main__":
    # Test the resume generator
    try:
        # Create test resume data
        test_data = ResumeData(
            full_name="John Smith",
            email="john.smith@email.com",
            phone="(555) 123-4567",
            address="123 Main Street",
            city="Los Angeles",
            state="CA",
            zip_code="90210",
            professional_summary="Dedicated professional with strong work ethic and proven ability to contribute to team success. Experienced in customer service, problem-solving, and maintaining high standards of quality.",
            work_experience=[
                {
                    "company": "ABC Warehouse",
                    "position": "Warehouse Associate",
                    "start_date": "2020-01",
                    "end_date": "2023-12",
                    "description": "Managed inventory, operated forklifts, and ensured accurate order fulfillment. Maintained safety standards and collaborated with team members.",
                    "location": "Los Angeles, CA"
                }
            ],
            education=[
                {
                    "institution": "Los Angeles Community College",
                    "degree": "High School Diploma",
                    "graduation_year": "2019"
                }
            ],
            technical_skills=["Forklift Operation", "Inventory Management", "Microsoft Office"],
            soft_skills=["Teamwork", "Communication", "Problem Solving"]
        )
        
        # Generate resume
        generator = ResumeGenerator()
        result = generator.generate_base_resume(test_data)
        
        if result['success']:
            print("✅ Resume generated successfully!")
            print(f"ATS Score: {result['ats_score']:.1f}/100")
            
            # Format as text
            formatter = ResumeFormatter()
            text_resume = formatter.format_as_text(result['resume'])
            print("\n" + "="*50)
            print("GENERATED RESUME:")
            print("="*50)
            print(text_resume)
        else:
            print(f"❌ Resume generation failed: {result['error']}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        # Fallback test without OpenAI
        print("Testing without OpenAI integration...")
        
        test_data = ResumeData(
            full_name="Test User",
            email="test@example.com",
            phone="(555) 123-4567",
            professional_summary="Test summary"
        )
        
        formatter = ResumeFormatter()
        test_resume = {
            "header": {
                "name": test_data.full_name,
                "email": test_data.email,
                "phone": test_data.phone,
                "address": "Test Address"
            },
            "sections": {
                "professional_summary": test_data.professional_summary,
                "core_skills": "Test Skills",
                "professional_experience": "Test Experience",
                "education": "Test Education",
                "additional_qualifications": "Test Additional"
            }
        }
        
        text_output = formatter.format_as_text(test_resume)
        print("✅ Formatter working correctly!")
        print(text_output[:200] + "...")

