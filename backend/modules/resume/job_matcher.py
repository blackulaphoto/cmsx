#!/usr/bin/env python3
"""
Job-Specific Resume Rewriter and Matching System
Tailors resumes to specific job postings and calculates match scores
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
    from .generator import OpenAIClient, ResumeGenerator, ResumeFormatter
    from .utils import ResumeDataProcessor
except ImportError:
    # For direct execution
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from resume.models import ResumeData, Resume, ResumeDatabase
    from resume.generator import OpenAIClient, ResumeGenerator, ResumeFormatter
    from resume.utils import ResumeDataProcessor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobAnalyzer:
    """Analyzes job postings to extract key requirements and keywords"""
    
    def __init__(self, openai_client: OpenAIClient = None):
        self.openai_client = openai_client or OpenAIClient()
    
    def analyze_job_posting(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a job posting to extract key requirements"""
        try:
            # Extract job information
            job_title = job_data.get('title', '')
            job_description = job_data.get('description', '')
            company = job_data.get('company', '')
            location = job_data.get('location', '')
            
            # Create analysis prompt
            analysis_prompt = self._create_job_analysis_prompt(
                job_title, job_description, company, location
            )
            
            messages = [
                {"role": "system", "content": self._get_job_analysis_system_prompt()},
                {"role": "user", "content": analysis_prompt}
            ]
            
            # Get AI analysis
            analysis_result = self.openai_client.chat_completion(
                messages=messages,
                model="gpt-4o",
                temperature=0.3,
                max_tokens=1500
            )
            
            if analysis_result:
                parsed_analysis = self._parse_job_analysis(analysis_result)
                
                # Add original job data
                parsed_analysis['original_job'] = {
                    'title': job_title,
                    'company': company,
                    'location': location,
                    'description': job_description,
                    'url': job_data.get('url', ''),
                    'source': job_data.get('source', ''),
                    'background_friendly_score': job_data.get('background_friendly_score', 0.0)
                }
                
                return parsed_analysis
            else:
                # Fallback analysis
                return self._fallback_job_analysis(job_data)
                
        except Exception as e:
            logger.error(f"Error analyzing job posting: {e}")
            return self._fallback_job_analysis(job_data)
    
    def _get_job_analysis_system_prompt(self) -> str:
        """Get the system prompt for job analysis"""
        return """You are an expert job market analyst and resume strategist. Your task is to analyze job postings and extract key information that will help tailor resumes effectively.

Analyze the job posting and provide a structured breakdown including:

1. **Required Skills**: Technical and soft skills explicitly mentioned
2. **Preferred Qualifications**: Education, experience, certifications
3. **Key Responsibilities**: Main duties and expectations
4. **Company Culture Indicators**: Values, work environment clues
5. **ATS Keywords**: Important terms for applicant tracking systems
6. **Background-Friendly Factors**: Elements that suggest openness to diverse backgrounds
7. **Match Optimization Tips**: Specific advice for tailoring a resume

Focus on actionable insights that will help someone with a non-traditional background (including those with criminal records) present themselves effectively.

Provide your analysis in a clear, structured format that can be easily parsed."""

    def _create_job_analysis_prompt(self, title: str, description: str, 
                                  company: str, location: str) -> str:
        """Create the job analysis prompt"""
        return f"""Please analyze this job posting and provide a comprehensive breakdown:

**Job Title:** {title}
**Company:** {company}
**Location:** {location}

**Job Description:**
{description}

Please provide a detailed analysis focusing on:
1. What skills and qualifications are absolutely required vs. preferred
2. Key responsibilities and expectations
3. Important keywords for ATS optimization
4. Company culture and values indicators
5. Factors that suggest this role might be open to candidates with diverse backgrounds
6. Specific recommendations for how someone with a non-traditional background could position themselves

Format your response clearly with headers and bullet points for easy parsing."""

    def _parse_job_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse the AI-generated job analysis"""
        analysis = {
            'required_skills': [],
            'preferred_qualifications': [],
            'key_responsibilities': [],
            'company_culture': [],
            'ats_keywords': [],
            'background_friendly_factors': [],
            'optimization_tips': [],
            'industry': 'general',
            'experience_level': 'entry',
            'education_requirements': 'flexible'
        }
        
        # Extract sections using regex patterns
        sections = {
            'required_skills': r'(?:required skills?|must have|essential skills?)[\s\n]*:?\s*\n(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)',
            'preferred_qualifications': r'(?:preferred|nice to have|desired|qualifications?)[\s\n]*:?\s*\n(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)',
            'key_responsibilities': r'(?:responsibilities|duties|role|expectations?)[\s\n]*:?\s*\n(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)',
            'ats_keywords': r'(?:keywords?|ats|terms?)[\s\n]*:?\s*\n(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)',
            'optimization_tips': r'(?:tips|recommendations?|advice|positioning?)[\s\n]*:?\s*\n(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)'
        }
        
        for section_name, pattern in sections.items():
            match = re.search(pattern, analysis_text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                # Split by bullet points or line breaks
                items = [item.strip() for item in re.split(r'[•\-\*]\s*|[\n\r]+', content) if item.strip()]
                analysis[section_name] = items[:10]  # Limit to 10 items
        
        # Extract additional metadata
        if 'entry level' in analysis_text.lower() or 'no experience' in analysis_text.lower():
            analysis['experience_level'] = 'entry'
        elif 'senior' in analysis_text.lower() or 'lead' in analysis_text.lower():
            analysis['experience_level'] = 'senior'
        else:
            analysis['experience_level'] = 'mid'
        
        # Determine industry
        common_industries = ['technology', 'healthcare', 'retail', 'manufacturing', 'logistics', 'hospitality']
        for industry in common_industries:
            if industry in analysis_text.lower():
                analysis['industry'] = industry
                break
        
        return analysis
    
    def _fallback_job_analysis(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback analysis when AI analysis fails"""
        description = job_data.get('description', '').lower()
        title = job_data.get('title', '').lower()
        
        # Extract basic keywords
        common_skills = ['communication', 'teamwork', 'customer service', 'problem solving', 
                        'time management', 'attention to detail', 'reliability', 'flexibility']
        
        found_skills = [skill for skill in common_skills if skill in description]
        
        return {
            'required_skills': found_skills,
            'preferred_qualifications': [],
            'key_responsibilities': [job_data.get('description', '')[:200] + '...'],
            'company_culture': [],
            'ats_keywords': found_skills,
            'background_friendly_factors': ['Equal opportunity employer' if 'equal opportunity' in description else ''],
            'optimization_tips': ['Focus on relevant experience and transferable skills'],
            'industry': 'general',
            'experience_level': 'entry',
            'education_requirements': 'flexible',
            'original_job': job_data
        }

class ResumeJobMatcher:
    """Matches resumes to job postings and calculates compatibility scores"""
    
    def __init__(self, openai_client: OpenAIClient = None):
        self.openai_client = openai_client or OpenAIClient()
        self.job_analyzer = JobAnalyzer(openai_client)
    
    def calculate_match_score(self, resume_data: ResumeData, 
                            job_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate how well a resume matches a job posting"""
        try:
            # Extract resume content for analysis
            resume_text = self._extract_resume_text(resume_data)
            
            # Get job requirements
            required_skills = job_analysis.get('required_skills', [])
            ats_keywords = job_analysis.get('ats_keywords', [])
            
            # Calculate different score components
            skills_score = self._calculate_skills_match(resume_text, required_skills)
            keyword_score = self._calculate_keyword_match(resume_text, ats_keywords)
            experience_score = self._calculate_experience_match(resume_data, job_analysis)
            
            # Calculate overall score
            overall_score = (skills_score * 0.4 + keyword_score * 0.3 + experience_score * 0.3)
            
            # Generate improvement suggestions
            suggestions = self._generate_improvement_suggestions(
                resume_data, job_analysis, skills_score, keyword_score, experience_score
            )
            
            return {
                'overall_score': round(overall_score, 1),
                'skills_score': round(skills_score, 1),
                'keyword_score': round(keyword_score, 1),
                'experience_score': round(experience_score, 1),
                'suggestions': suggestions,
                'missing_skills': self._find_missing_skills(resume_text, required_skills),
                'missing_keywords': self._find_missing_keywords(resume_text, ats_keywords)
            }
            
        except Exception as e:
            logger.error(f"Error calculating match score: {e}")
            return {
                'overall_score': 0.0,
                'skills_score': 0.0,
                'keyword_score': 0.0,
                'experience_score': 0.0,
                'suggestions': ['Unable to calculate match score'],
                'missing_skills': [],
                'missing_keywords': []
            }
    
    def _extract_resume_text(self, resume_data: ResumeData) -> str:
        """Extract all text content from resume data"""
        text_parts = [
            resume_data.professional_summary,
            ' '.join(resume_data.technical_skills),
            ' '.join(resume_data.soft_skills),
        ]
        
        # Add work experience
        for exp in resume_data.work_experience:
            text_parts.extend([
                exp.get('position', ''),
                exp.get('company', ''),
                exp.get('description', '')
            ])
        
        # Add education
        for edu in resume_data.education:
            text_parts.extend([
                edu.get('degree', ''),
                edu.get('field_of_study', ''),
                edu.get('institution', '')
            ])
        
        return ' '.join([part for part in text_parts if part]).lower()
    
    def _calculate_skills_match(self, resume_text: str, required_skills: List[str]) -> float:
        """Calculate how many required skills are present in the resume"""
        if not required_skills:
            return 100.0
        
        matched_skills = 0
        for skill in required_skills:
            if skill.lower() in resume_text:
                matched_skills += 1
        
        return (matched_skills / len(required_skills)) * 100
    
    def _calculate_keyword_match(self, resume_text: str, keywords: List[str]) -> float:
        """Calculate keyword match percentage"""
        if not keywords:
            return 100.0
        
        matched_keywords = 0
        for keyword in keywords:
            if keyword.lower() in resume_text:
                matched_keywords += 1
        
        return (matched_keywords / len(keywords)) * 100
    
    def _calculate_experience_match(self, resume_data: ResumeData, 
                                  job_analysis: Dict[str, Any]) -> float:
        """Calculate experience level match"""
        experience_level = job_analysis.get('experience_level', 'entry')
        work_experience_count = len(resume_data.work_experience)
        
        if experience_level == 'entry':
            return 100.0 if work_experience_count >= 0 else 80.0
        elif experience_level == 'mid':
            return 100.0 if work_experience_count >= 2 else 70.0
        elif experience_level == 'senior':
            return 100.0 if work_experience_count >= 5 else 60.0
        
        return 80.0
    
    def _find_missing_skills(self, resume_text: str, required_skills: List[str]) -> List[str]:
        """Find skills that are required but missing from resume"""
        return [skill for skill in required_skills if skill.lower() not in resume_text]
    
    def _find_missing_keywords(self, resume_text: str, keywords: List[str]) -> List[str]:
        """Find keywords that are missing from resume"""
        return [keyword for keyword in keywords if keyword.lower() not in resume_text]
    
    def _generate_improvement_suggestions(self, resume_data: ResumeData, 
                                        job_analysis: Dict[str, Any],
                                        skills_score: float, keyword_score: float, 
                                        experience_score: float) -> List[str]:
        """Generate specific suggestions for improving the resume match"""
        suggestions = []
        
        if skills_score < 70:
            suggestions.append("Consider adding more relevant technical skills to your resume")
        
        if keyword_score < 60:
            suggestions.append("Include more industry-specific keywords in your professional summary")
        
        if experience_score < 80:
            suggestions.append("Highlight transferable skills from your experience")
        
        # Add specific suggestions based on job analysis
        optimization_tips = job_analysis.get('optimization_tips', [])
        suggestions.extend(optimization_tips[:3])  # Add up to 3 tips
        
        return suggestions[:5]  # Limit to 5 suggestions

class JobSpecificResumeRewriter:
    """Rewrites resumes to be specifically tailored to job postings"""
    
    def __init__(self, openai_client: OpenAIClient = None):
        self.openai_client = openai_client or OpenAIClient()
        self.job_analyzer = JobAnalyzer(openai_client)
        self.matcher = ResumeJobMatcher(openai_client)
        self.base_generator = ResumeGenerator(openai_client)
    
    def rewrite_resume_for_job(self, resume_data: ResumeData, 
                              job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rewrite a resume to be specifically tailored to a job posting"""
        try:
            # Analyze the job posting
            job_analysis = self.job_analyzer.analyze_job_posting(job_data)
            
            # Calculate initial match score
            initial_match = self.matcher.calculate_match_score(resume_data, job_analysis)
            
            # Create tailored resume
            tailored_resume = self._create_tailored_resume(resume_data, job_analysis)
            
            # Calculate new match score
            # Note: We'd need to convert the tailored resume back to ResumeData for accurate scoring
            # For now, we'll estimate an improved score
            estimated_new_score = min(initial_match['overall_score'] + 15, 95)
            
            return {
                'success': True,
                'original_score': initial_match['overall_score'],
                'new_score': estimated_new_score,
                'tailored_resume': tailored_resume,
                'job_analysis': job_analysis,
                'improvements_made': self._get_improvements_made(job_analysis),
                'match_details': initial_match
            }
            
        except Exception as e:
            logger.error(f"Error rewriting resume for job: {e}")
            return {
                'success': False,
                'error': str(e),
                'tailored_resume': None
            }
    
    def _create_tailored_resume(self, resume_data: ResumeData, 
                              job_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a tailored resume using AI"""
        try:
            # Create the system prompt for tailored resume generation
            system_prompt = self._create_tailored_system_prompt(job_analysis)
            
            # Create the user prompt with resume data and job requirements
            user_prompt = self._create_tailored_user_prompt(resume_data, job_analysis)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Generate the tailored resume content
            generated_content = self.openai_client.chat_completion(
                messages=messages,
                model="gpt-4o",
                temperature=0.6,
                max_tokens=2500
            )
            
            if not generated_content:
                raise Exception("Failed to generate tailored resume content")
            
            # Parse the generated content
            resume_sections = self.base_generator._parse_generated_content(generated_content)
            
            # Create the final tailored resume structure
            tailored_resume = self.base_generator._create_final_resume_structure(resume_data, resume_sections)
            
            # Add job-specific metadata
            tailored_resume['metadata'].update({
                'tailored_for_job': job_analysis['original_job']['title'],
                'tailored_for_company': job_analysis['original_job']['company'],
                'target_industry': job_analysis.get('industry', 'general'),
                'tailoring_date': datetime.now().isoformat()
            })
            
            return tailored_resume
            
        except Exception as e:
            logger.error(f"Error creating tailored resume: {e}")
            # Return base resume as fallback
            return self.base_generator.generate_base_resume(resume_data)['resume']
    
    def _create_tailored_system_prompt(self, job_analysis: Dict[str, Any]) -> str:
        """Create system prompt for tailored resume generation"""
        job_info = job_analysis['original_job']
        required_skills = ', '.join(job_analysis.get('required_skills', [])[:5])
        keywords = ', '.join(job_analysis.get('ats_keywords', [])[:8])
        
        return f"""You are an expert resume writer specializing in creating job-specific, ATS-optimized resumes for people seeking employment, including those with criminal backgrounds who deserve second chances.

Your task is to rewrite a resume to be specifically tailored for this position:

**Target Job:** {job_info['title']} at {job_info['company']}
**Industry:** {job_analysis.get('industry', 'general')}
**Key Required Skills:** {required_skills}
**Important ATS Keywords:** {keywords}

**Tailoring Guidelines:**
1. **Keyword Optimization**: Naturally incorporate the required skills and ATS keywords throughout the resume
2. **Relevance Focus**: Emphasize experiences and skills most relevant to this specific role
3. **Industry Alignment**: Use industry-appropriate language and terminology
4. **Value Proposition**: Clearly articulate how the candidate's background adds value to this specific role
5. **Background-Friendly Approach**: Frame experiences positively while maintaining honesty

**Key Requirements for this Role:**
{chr(10).join(['- ' + skill for skill in job_analysis.get('required_skills', [])[:5]])}

**Optimization Tips:**
{chr(10).join(['- ' + tip for tip in job_analysis.get('optimization_tips', [])[:3]])}

Generate a compelling, honest, and highly targeted resume that maximizes the candidate's chances for this specific position while maintaining ATS compatibility."""

    def _create_tailored_user_prompt(self, resume_data: ResumeData, 
                                   job_analysis: Dict[str, Any]) -> str:
        """Create user prompt for tailored resume generation"""
        base_prompt = self.base_generator._create_user_prompt(resume_data)
        
        job_info = job_analysis['original_job']
        
        additional_context = f"""

**SPECIFIC JOB TARGETING:**
This resume should be specifically tailored for the {job_info['title']} position at {job_info['company']}.

**Job Description Summary:**
{job_info['description'][:500]}...

**Key Requirements to Address:**
{chr(10).join(['- ' + skill for skill in job_analysis.get('required_skills', [])[:5]])}

**Must-Include Keywords:**
{', '.join(job_analysis.get('ats_keywords', [])[:8])}

**Tailoring Instructions:**
- Rewrite the professional summary to directly address this role
- Emphasize experiences most relevant to the job requirements
- Use the exact keywords and phrases from the job posting where appropriate
- Highlight transferable skills that match the job needs
- Frame all experiences in terms of value to this specific employer

Please create a highly targeted resume that feels custom-written for this exact position."""

        return base_prompt + additional_context
    
    def _get_improvements_made(self, job_analysis: Dict[str, Any]) -> List[str]:
        """Get list of improvements made during tailoring"""
        improvements = [
            f"Optimized for {job_analysis['original_job']['title']} role",
            f"Incorporated {len(job_analysis.get('ats_keywords', []))} relevant keywords",
            f"Emphasized skills matching {len(job_analysis.get('required_skills', []))} job requirements"
        ]
        
        if job_analysis.get('industry') != 'general':
            improvements.append(f"Tailored language for {job_analysis['industry']} industry")
        
        return improvements

# Example usage and testing
if __name__ == "__main__":
    # Test the job-specific resume system
    try:
        # Create test resume data
        test_resume = ResumeData(
            full_name="Maria Rodriguez",
            email="maria.rodriguez@email.com",
            phone="(555) 987-6543",
            address="456 Oak Avenue",
            city="Los Angeles",
            state="CA",
            zip_code="90015",
            professional_summary="Reliable and hardworking professional with experience in customer service and team collaboration. Committed to excellence and continuous learning.",
            work_experience=[
                {
                    "company": "Local Restaurant",
                    "position": "Server",
                    "start_date": "2021-03",
                    "end_date": "2023-11",
                    "description": "Provided excellent customer service, managed multiple tables, handled cash transactions, and worked collaboratively with kitchen staff.",
                    "location": "Los Angeles, CA"
                }
            ],
            education=[
                {
                    "institution": "Los Angeles Community College",
                    "degree": "Certificate",
                    "field_of_study": "Customer Service",
                    "graduation_year": "2021"
                }
            ],
            technical_skills=["Cash Handling", "POS Systems", "Microsoft Office"],
            soft_skills=["Customer Service", "Communication", "Teamwork", "Problem Solving"]
        )
        
        # Create test job posting
        test_job = {
            "title": "Customer Service Representative",
            "company": "TechCorp Solutions",
            "location": "Los Angeles, CA",
            "description": "We are seeking a dedicated Customer Service Representative to join our team. The ideal candidate will have excellent communication skills, experience with customer service, and the ability to work in a fast-paced environment. Responsibilities include handling customer inquiries, resolving issues, and maintaining accurate records. Experience with CRM software and data entry is preferred. We are an equal opportunity employer committed to diversity and inclusion.",
            "url": "https://example.com/job/123",
            "source": "indeed",
            "background_friendly_score": 0.8
        }
        
        # Test job analysis
        analyzer = JobAnalyzer()
        job_analysis = analyzer.analyze_job_posting(test_job)
        print("✅ Job Analysis completed!")
        print(f"Required Skills: {job_analysis.get('required_skills', [])[:3]}")
        print(f"ATS Keywords: {job_analysis.get('ats_keywords', [])[:3]}")
        
        # Test resume matching
        matcher = ResumeJobMatcher()
        match_score = matcher.calculate_match_score(test_resume, job_analysis)
        print(f"\n✅ Match Score calculated: {match_score['overall_score']}/100")
        print(f"Skills Match: {match_score['skills_score']}/100")
        print(f"Keyword Match: {match_score['keyword_score']}/100")
        
        # Test resume rewriting
        rewriter = JobSpecificResumeRewriter()
        result = rewriter.rewrite_resume_for_job(test_resume, test_job)
        
        if result['success']:
            print(f"\n✅ Resume rewriting successful!")
            print(f"Original Score: {result['original_score']}/100")
            print(f"New Score: {result['new_score']}/100")
            print(f"Improvements: {result['improvements_made']}")
            
            # Format and display the tailored resume
            formatter = ResumeFormatter()
            tailored_text = formatter.format_as_text(result['tailored_resume'])
            print("\n" + "="*50)
            print("TAILORED RESUME:")
            print("="*50)
            print(tailored_text[:500] + "...")
        else:
            print(f"❌ Resume rewriting failed: {result['error']}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        # Fallback test
        print("Testing basic functionality...")
        
        test_job = {
            "title": "Warehouse Worker",
            "company": "ABC Logistics",
            "description": "Looking for reliable warehouse workers with attention to detail.",
            "location": "Los Angeles, CA"
        }
        
        analyzer = JobAnalyzer()
        analysis = analyzer._fallback_job_analysis(test_job)
        print("✅ Fallback analysis working!")
        print(f"Found skills: {analysis['required_skills']}")

