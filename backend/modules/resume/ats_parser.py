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
ATS Parser and Scoring System
Analyzes resumes for ATS compatibility and provides detailed feedback
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

class ATSAnalyzer:
    """Analyzes resumes for ATS (Applicant Tracking System) compatibility"""
    
    def __init__(self, openai_client: OpenAIClient = None):
        self.openai_client = openai_client or OpenAIClient()
        
        # ATS scoring criteria weights
        self.scoring_weights = {
            'format_compatibility': 0.25,
            'keyword_optimization': 0.20,
            'section_structure': 0.15,
            'contact_information': 0.10,
            'work_experience': 0.15,
            'skills_presentation': 0.10,
            'readability': 0.05
        }
        
        # Common ATS-friendly formats and requirements
        self.ats_requirements = {
            'preferred_formats': ['docx', 'pdf', 'txt'],
            'required_sections': ['contact', 'experience', 'education', 'skills'],
            'recommended_sections': ['summary', 'achievements', 'certifications'],
            'avoid_elements': ['tables', 'images', 'graphics', 'headers', 'footers'],
            'font_requirements': ['standard fonts', 'readable size', 'consistent formatting']
        }
    
    def analyze_resume(self, resume_data: ResumeData, 
                      resume_text: str = None) -> Dict[str, Any]:
        """Perform comprehensive ATS analysis of a resume"""
        try:
            # Validate input parameters
            if not resume_data:
                logger.error("ResumeData object is None")
                return {
                    'overall_score': 0.0,
                    'grade': 'F',
                    'error': 'No resume data provided for analysis',
                    'recommendations': ['Please provide valid resume data for analysis.']
                }
            
            # Generate resume text if not provided
            if not resume_text:
                try:
                    generator = ResumeGenerator(self.openai_client)
                    formatter = ResumeFormatter()
                    base_resume = generator.generate_base_resume(resume_data)
                    
                    # Check if resume generation was successful
                    if not base_resume or not base_resume.get('success'):
                        error_msg = base_resume.get('error', 'Resume generation failed') if base_resume else 'Resume generation returned None'
                        logger.error(f"Resume generation failed: {error_msg}")
                        return {
                            'overall_score': 0.0,
                            'grade': 'F',
                            'error': f'Resume generation failed: {error_msg}',
                            'recommendations': ['Unable to generate resume for analysis. Please check your input data and try again.']
                        }
                    
                    # Extract resume content safely
                    resume_content = base_resume.get('resume')
                    if not resume_content:
                        logger.error("Resume content is empty or None")
                        return {
                            'overall_score': 0.0,
                            'grade': 'F',
                            'error': 'Resume content is empty',
                            'recommendations': ['Unable to analyze empty resume. Please provide resume content.']
                        }
                    
                    resume_text = formatter.format_as_text(resume_content)
                    
                    # Validate resume text
                    if not resume_text or len(resume_text.strip()) < 50:
                        logger.error("Generated resume text is too short or empty")
                        return {
                            'overall_score': 0.0,
                            'grade': 'F',
                            'error': 'Generated resume text is insufficient for analysis',
                            'recommendations': ['Please provide more detailed information to generate a proper resume for analysis.']
                        }
                except Exception as e:
                    logger.error(f"Error generating resume text: {e}")
                    return {
                        'overall_score': 0.0,
                        'grade': 'F',
                        'error': f'Resume generation error: {str(e)}',
                        'recommendations': ['Unable to generate resume for analysis. Please check your input data and try again.']
                    }
            else:
                # If resume_text is provided, validate and process it
                try:
                    if isinstance(resume_text, dict):
                        # It's a resume structure, format it as text
                        formatter = ResumeFormatter()
                        resume_text = formatter.format_as_text(resume_text)
                    elif not isinstance(resume_text, str):
                        # Convert to string if it's neither dict nor string
                        resume_text = str(resume_text)
                    
                    # Validate the processed resume text
                    if not resume_text or len(resume_text.strip()) < 20:
                        logger.error("Provided resume text is too short or empty")
                        return {
                            'overall_score': 0.0,
                            'grade': 'F',
                            'error': 'Provided resume text is insufficient for analysis',
                            'recommendations': ['Please provide more detailed resume content for analysis.']
                        }
                except Exception as e:
                    logger.error(f"Error processing provided resume text: {e}")
                    return {
                        'overall_score': 0.0,
                        'grade': 'F',
                        'error': f'Resume text processing error: {str(e)}',
                        'recommendations': ['Unable to process resume text. Please check the format and try again.']
                    }
            
            # Perform individual analyses with error handling
            try:
                format_score = self._analyze_format_compatibility(resume_text)
            except Exception as e:
                logger.error(f"Error in format analysis: {e}")
                format_score = {'score': 50.0, 'issues': ['Format analysis failed'], 'recommendations': ['Check resume format'], 'details': 'Format analysis error'}
            
            try:
                keyword_score = self._analyze_keyword_optimization(resume_text)
            except Exception as e:
                logger.error(f"Error in keyword analysis: {e}")
                keyword_score = {'score': 50.0, 'issues': ['Keyword analysis failed'], 'recommendations': ['Check keyword usage'], 'details': 'Keyword analysis error'}
            
            try:
                structure_score = self._analyze_section_structure(resume_data, resume_text)
            except Exception as e:
                logger.error(f"Error in structure analysis: {e}")
                structure_score = {'score': 50.0, 'issues': ['Structure analysis failed'], 'recommendations': ['Check resume structure'], 'details': 'Structure analysis error'}
            
            try:
                contact_score = self._analyze_contact_information(resume_data)
            except Exception as e:
                logger.error(f"Error in contact analysis: {e}")
                contact_score = {'score': 50.0, 'issues': ['Contact analysis failed'], 'recommendations': ['Check contact information'], 'details': 'Contact analysis error'}
            
            try:
                experience_score = self._analyze_work_experience(resume_data)
            except Exception as e:
                logger.error(f"Error in experience analysis: {e}")
                experience_score = {'score': 50.0, 'issues': ['Experience analysis failed'], 'recommendations': ['Check work experience'], 'details': 'Experience analysis error'}
            
            try:
                skills_score = self._analyze_skills_presentation(resume_data)
            except Exception as e:
                logger.error(f"Error in skills analysis: {e}")
                skills_score = {'score': 50.0, 'issues': ['Skills analysis failed'], 'recommendations': ['Check skills section'], 'details': 'Skills analysis error'}
            
            try:
                readability_score = self._analyze_readability(resume_text)
            except Exception as e:
                logger.error(f"Error in readability analysis: {e}")
                readability_score = {'score': 50.0, 'issues': ['Readability analysis failed'], 'recommendations': ['Check readability'], 'details': 'Readability analysis error'}
            
            # Calculate overall ATS score
            try:
                overall_score = self._calculate_overall_score({
                    'format_compatibility': format_score['score'],
                    'keyword_optimization': keyword_score['score'],
                    'section_structure': structure_score['score'],
                    'contact_information': contact_score['score'],
                    'work_experience': experience_score['score'],
                    'skills_presentation': skills_score['score'],
                    'readability': readability_score['score']
                })
            except Exception as e:
                logger.error(f"Error calculating overall score: {e}")
                overall_score = 50.0
            
            # Generate comprehensive recommendations
            try:
                recommendations = self._generate_recommendations({
                    'format': format_score,
                    'keywords': keyword_score,
                    'structure': structure_score,
                    'contact': contact_score,
                    'experience': experience_score,
                    'skills': skills_score,
                    'readability': readability_score
                })
            except Exception as e:
                logger.error(f"Error generating recommendations: {e}")
                recommendations = ['Unable to generate specific recommendations. Please review your resume for ATS compatibility.']
            
            # Create detailed analysis report
            analysis_report = {
                'overall_score': overall_score,
                'grade': self._get_score_grade(overall_score),
                'category_scores': {
                    'format_compatibility': format_score,
                    'keyword_optimization': keyword_score,
                    'section_structure': structure_score,
                    'contact_information': contact_score,
                    'work_experience': experience_score,
                    'skills_presentation': skills_score,
                    'readability': readability_score
                },
                'recommendations': recommendations,
                'ats_compatibility_level': self._get_compatibility_level(overall_score),
                'analysis_date': datetime.now().isoformat(),
                'resume_length': len(resume_text.split()) if resume_text else 0,
                'estimated_ats_pass_rate': self._estimate_ats_pass_rate(overall_score)
            }
            
            return analysis_report
            
        except Exception as e:
            logger.error(f"Unexpected error analyzing resume for ATS compatibility: {e}")
            return {
                'overall_score': 0.0,
                'grade': 'F',
                'error': f'Unexpected analysis error: {str(e)}',
                'recommendations': ['Unable to analyze resume due to unexpected error. Please check format and try again.']
            }
    
    def _analyze_format_compatibility(self, resume_text: str) -> Dict[str, Any]:
        """Analyze format compatibility with ATS systems"""
        score = 100.0
        issues = []
        recommendations = []
        
        # Check for problematic formatting
        if re.search(r'\|{2,}', resume_text):  # Multiple pipes (table indicators)
            score -= 15
            issues.append("Contains table-like formatting that may confuse ATS")
            recommendations.append("Remove tables and use simple bullet points instead")
        
        if re.search(r'[^\x00-\x7F]', resume_text):  # Non-ASCII characters
            score -= 10
            issues.append("Contains special characters that may not parse correctly")
            recommendations.append("Replace special characters with standard alternatives")
        
        # Check for excessive formatting
        if len(re.findall(r'[A-Z]{3,}', resume_text)) > 10:  # Too many all-caps words
            score -= 8
            issues.append("Excessive use of all-caps text")
            recommendations.append("Use standard capitalization for better readability")
        
        # Check for proper spacing
        if resume_text.count('\n\n') < 3:  # Not enough section breaks
            score -= 5
            issues.append("Insufficient spacing between sections")
            recommendations.append("Add clear spacing between resume sections")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': recommendations,
            'details': 'Format compatibility analysis for ATS parsing'
        }
    
    def _analyze_keyword_optimization(self, resume_text: str) -> Dict[str, Any]:
        """Analyze keyword optimization and density"""
        score = 100.0
        issues = []
        recommendations = []
        
        # Common industry keywords that should appear
        important_keywords = [
            'experience', 'skills', 'management', 'team', 'project',
            'customer', 'service', 'communication', 'problem solving',
            'leadership', 'training', 'development', 'results'
        ]
        
        text_lower = resume_text.lower()
        keyword_count = sum(1 for keyword in important_keywords if keyword in text_lower)
        keyword_percentage = (keyword_count / len(important_keywords)) * 100
        
        if keyword_percentage < 30:
            score -= 25
            issues.append("Low keyword density for common job-related terms")
            recommendations.append("Include more industry-relevant keywords naturally throughout your resume")
        elif keyword_percentage < 50:
            score -= 10
            issues.append("Moderate keyword density - could be improved")
            recommendations.append("Consider adding more relevant keywords to strengthen your resume")
        
        # Check for keyword stuffing
        words = resume_text.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 3:  # Only count meaningful words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Flag if any word appears too frequently
        total_words = len(words)
        for word, count in word_freq.items():
            if count > total_words * 0.03:  # More than 3% of total words
                score -= 15
                issues.append(f"Potential keyword stuffing detected with '{word}'")
                recommendations.append("Vary your language to avoid repetitive keywords")
                break
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': recommendations,
            'keyword_percentage': keyword_percentage,
            'details': f'Found {keyword_count}/{len(important_keywords)} important keywords'
        }
    
    def _analyze_section_structure(self, resume_data: ResumeData, 
                                 resume_text: str) -> Dict[str, Any]:
        """Analyze resume section structure and organization"""
        score = 100.0
        issues = []
        recommendations = []
        
        # Check for required sections
        required_sections = ['contact', 'experience', 'education', 'skills']
        text_lower = resume_text.lower()
        
        missing_sections = []
        for section in required_sections:
            if section not in text_lower and section.replace('_', ' ') not in text_lower:
                missing_sections.append(section)
        
        if missing_sections:
            score -= len(missing_sections) * 15
            issues.append(f"Missing required sections: {', '.join(missing_sections)}")
            recommendations.append("Add all required resume sections for complete ATS parsing")
        
        # Check section order (contact should be first)
        if not resume_text.strip().startswith(resume_data.full_name):
            score -= 10
            issues.append("Contact information should appear at the top")
            recommendations.append("Place your name and contact details at the very beginning")
        
        # Check for professional summary
        if not resume_data.professional_summary or len(resume_data.professional_summary) < 50:
            score -= 8
            issues.append("Missing or insufficient professional summary")
            recommendations.append("Add a compelling professional summary at the top of your resume")
        
        # Check work experience structure
        if len(resume_data.work_experience) == 0:
            score -= 20
            issues.append("No work experience listed")
            recommendations.append("Include relevant work experience with clear job titles and descriptions")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': recommendations,
            'missing_sections': missing_sections,
            'details': 'Section structure and organization analysis'
        }
    
    def _analyze_contact_information(self, resume_data: ResumeData) -> Dict[str, Any]:
        """Analyze contact information completeness and format"""
        score = 100.0
        issues = []
        recommendations = []
        
        # Check required contact fields
        if not resume_data.full_name or len(resume_data.full_name.strip()) < 2:
            score -= 25
            issues.append("Missing or incomplete full name")
            recommendations.append("Provide your complete full name")
        
        if not resume_data.email or '@' not in resume_data.email:
            score -= 25
            issues.append("Missing or invalid email address")
            recommendations.append("Include a professional email address")
        
        if not resume_data.phone or len(re.sub(r'[^\d]', '', resume_data.phone)) < 10:
            score -= 20
            issues.append("Missing or incomplete phone number")
            recommendations.append("Include a complete phone number with area code")
        
        # Check email professionalism
        if resume_data.email and any(word in resume_data.email.lower() for word in 
                                   ['sexy', 'hot', 'cool', 'party', '69', '420']):
            score -= 15
            issues.append("Email address may not appear professional")
            recommendations.append("Consider using a more professional email address")
        
        # Check for location information
        if not resume_data.city or not resume_data.state:
            score -= 10
            issues.append("Missing location information")
            recommendations.append("Include your city and state for location-based job matching")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': recommendations,
            'details': 'Contact information completeness and professionalism'
        }
    
    def _analyze_work_experience(self, resume_data: ResumeData) -> Dict[str, Any]:
        """Analyze work experience section quality"""
        score = 100.0
        issues = []
        recommendations = []
        
        if not resume_data.work_experience:
            score = 0
            issues.append("No work experience provided")
            recommendations.append("Add relevant work experience with detailed descriptions")
            return {
                'score': score,
                'issues': issues,
                'recommendations': recommendations,
                'details': 'No work experience to analyze'
            }
        
        # Check each work experience entry
        for i, exp in enumerate(resume_data.work_experience):
            exp_issues = []
            
            # Check required fields
            if not exp.get('position'):
                exp_issues.append("Missing job title")
            if not exp.get('company'):
                exp_issues.append("Missing company name")
            if not exp.get('description') or len(exp.get('description', '')) < 50:
                exp_issues.append("Missing or insufficient job description")
            
            # Check date format
            if not exp.get('start_date') or not exp.get('end_date'):
                exp_issues.append("Missing employment dates")
            
            if exp_issues:
                score -= len(exp_issues) * 5
                issues.extend([f"Experience {i+1}: {issue}" for issue in exp_issues])
        
        # Check for quantifiable achievements
        total_descriptions = ' '.join([exp.get('description', '') for exp in resume_data.work_experience])
        if not re.search(r'\d+%|\$\d+|\d+\+|increased|decreased|improved|reduced', total_descriptions.lower()):
            score -= 15
            issues.append("No quantifiable achievements mentioned")
            recommendations.append("Include specific numbers and achievements in your job descriptions")
        
        # Check for action verbs
        action_verbs = ['managed', 'led', 'developed', 'created', 'implemented', 'achieved', 'improved']
        if not any(verb in total_descriptions.lower() for verb in action_verbs):
            score -= 10
            issues.append("Limited use of strong action verbs")
            recommendations.append("Start bullet points with strong action verbs")
        
        if not issues:
            recommendations.append("Work experience section looks good!")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': recommendations,
            'experience_count': len(resume_data.work_experience),
            'details': 'Work experience quality and completeness analysis'
        }
    
    def _analyze_skills_presentation(self, resume_data: ResumeData) -> Dict[str, Any]:
        """Analyze skills section presentation and relevance"""
        score = 100.0
        issues = []
        recommendations = []
        
        total_skills = len(resume_data.technical_skills) + len(resume_data.soft_skills)
        
        if total_skills == 0:
            score = 0
            issues.append("No skills listed")
            recommendations.append("Add both technical and soft skills relevant to your target jobs")
            return {
                'score': score,
                'issues': issues,
                'recommendations': recommendations,
                'details': 'No skills to analyze'
            }
        
        # Check skill count
        if total_skills < 5:
            score -= 20
            issues.append("Too few skills listed")
            recommendations.append("Include 8-12 relevant skills for better keyword matching")
        elif total_skills > 20:
            score -= 10
            issues.append("Too many skills listed")
            recommendations.append("Focus on your most relevant and strongest skills")
        
        # Check for balance between technical and soft skills
        if len(resume_data.technical_skills) == 0:
            score -= 15
            issues.append("No technical skills listed")
            recommendations.append("Include relevant technical skills for your industry")
        
        if len(resume_data.soft_skills) == 0:
            score -= 10
            issues.append("No soft skills listed")
            recommendations.append("Include important soft skills like communication and teamwork")
        
        # Check for generic skills
        generic_skills = ['microsoft office', 'computer skills', 'people skills', 'hard worker']
        all_skills = resume_data.technical_skills + resume_data.soft_skills
        generic_count = sum(1 for skill in all_skills if skill.lower() in generic_skills)
        
        if generic_count > 2:
            score -= 12
            issues.append("Too many generic skills")
            recommendations.append("Replace generic skills with specific, relevant abilities")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': recommendations,
            'total_skills': total_skills,
            'technical_skills': len(resume_data.technical_skills),
            'soft_skills': len(resume_data.soft_skills),
            'details': 'Skills section analysis for ATS optimization'
        }
    
    def _analyze_readability(self, resume_text: str) -> Dict[str, Any]:
        """Analyze resume readability and clarity"""
        score = 100.0
        issues = []
        recommendations = []
        
        # Check resume length
        word_count = len(resume_text.split())
        if word_count < 200:
            score -= 20
            issues.append("Resume is too short")
            recommendations.append("Expand your resume with more detailed descriptions")
        elif word_count > 800:
            score -= 15
            issues.append("Resume may be too long")
            recommendations.append("Consider condensing content to 1-2 pages")
        
        # Check sentence length
        sentences = re.split(r'[.!?]+', resume_text)
        long_sentences = [s for s in sentences if len(s.split()) > 25]
        if len(long_sentences) > 3:
            score -= 10
            issues.append("Some sentences are too long")
            recommendations.append("Break up long sentences for better readability")
        
        # Check for bullet points
        bullet_count = resume_text.count('•') + resume_text.count('-') + resume_text.count('*')
        if bullet_count < 5:
            score -= 8
            issues.append("Limited use of bullet points")
            recommendations.append("Use bullet points to organize information clearly")
        
        # Check for consistent formatting
        if len(set(re.findall(r'\n([A-Z][A-Z\s]+)\n', resume_text))) < 3:
            score -= 5
            issues.append("Inconsistent section headers")
            recommendations.append("Use consistent formatting for section headers")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': recommendations,
            'word_count': word_count,
            'bullet_points': bullet_count,
            'details': 'Readability and formatting analysis'
        }
    
    def _calculate_overall_score(self, category_scores: Dict[str, float]) -> float:
        """Calculate weighted overall ATS score"""
        total_score = 0.0
        for category, score in category_scores.items():
            weight = self.scoring_weights.get(category, 0)
            total_score += score * weight
        
        return round(total_score, 1)
    
    def _get_score_grade(self, score: float) -> str:
        """Convert numerical score to letter grade"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _get_compatibility_level(self, score: float) -> str:
        """Get ATS compatibility level description"""
        if score >= 85:
            return 'Excellent - Highly likely to pass ATS screening'
        elif score >= 75:
            return 'Good - Should pass most ATS systems'
        elif score >= 65:
            return 'Fair - May have issues with some ATS systems'
        elif score >= 50:
            return 'Poor - Likely to have ATS parsing problems'
        else:
            return 'Very Poor - Major ATS compatibility issues'
    
    def _estimate_ats_pass_rate(self, score: float) -> str:
        """Estimate the percentage of ATS systems that would successfully parse this resume"""
        if score >= 90:
            return '95-100%'
        elif score >= 80:
            return '85-95%'
        elif score >= 70:
            return '70-85%'
        elif score >= 60:
            return '50-70%'
        elif score >= 50:
            return '30-50%'
        else:
            return '10-30%'
    
    def _generate_recommendations(self, analysis_results: Dict[str, Dict]) -> List[str]:
        """Generate prioritized recommendations based on analysis results"""
        all_recommendations = []
        
        # Collect all recommendations with their category scores
        for category, result in analysis_results.items():
            if result['score'] < 80:  # Only include recommendations for low-scoring categories
                category_recs = [(rec, result['score']) for rec in result.get('recommendations', [])]
                all_recommendations.extend(category_recs)
        
        # Sort by score (lowest first) and remove duplicates
        all_recommendations.sort(key=lambda x: x[1])
        unique_recommendations = []
        seen = set()
        
        for rec, score in all_recommendations:
            if rec not in seen:
                unique_recommendations.append(rec)
                seen.add(rec)
        
        # Return top 8 recommendations
        return unique_recommendations[:8]

class ATSOptimizer:
    """Provides specific optimization suggestions for ATS compatibility"""
    
    def __init__(self, openai_client: OpenAIClient = None):
        self.openai_client = openai_client or OpenAIClient()
        self.analyzer = ATSAnalyzer(openai_client)
    
    def optimize_resume_for_ats(self, resume_data: ResumeData) -> Dict[str, Any]:
        """Generate ATS-optimized version of resume with specific improvements"""
        try:
            # First, analyze current resume
            analysis = self.analyzer.analyze_resume(resume_data)
            
            # Generate optimized resume content
            optimized_resume = self._create_ats_optimized_resume(resume_data, analysis)
            
            # Analyze the optimized version
            optimized_analysis = self.analyzer.analyze_resume(resume_data, optimized_resume['content'])
            
            return {
                'success': True,
                'original_score': analysis['overall_score'],
                'optimized_score': optimized_analysis['overall_score'],
                'improvement': optimized_analysis['overall_score'] - analysis['overall_score'],
                'optimized_resume': optimized_resume,
                'optimization_summary': self._create_optimization_summary(analysis, optimized_analysis),
                'original_analysis': analysis,
                'optimized_analysis': optimized_analysis
            }
            
        except Exception as e:
            logger.error(f"Error optimizing resume for ATS: {e}")
            return {
                'success': False,
                'error': str(e),
                'optimized_resume': None
            }
    
    def _create_ats_optimized_resume(self, resume_data: ResumeData, 
                                   analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create an ATS-optimized version of the resume"""
        try:
            # Create optimization prompt based on analysis
            optimization_prompt = self._create_optimization_prompt(resume_data, analysis)
            
            messages = [
                {"role": "system", "content": self._get_ats_optimization_system_prompt()},
                {"role": "user", "content": optimization_prompt}
            ]
            
            # Generate optimized content
            optimized_content = self.openai_client.chat_completion(
                messages=messages,
                model="gpt-4o",
                temperature=0.4,
                max_tokens=2000
            )
            
            if not optimized_content:
                raise Exception("Failed to generate ATS-optimized resume")
            
            return {
                'content': optimized_content,
                'optimization_date': datetime.now().isoformat(),
                'optimizations_applied': self._extract_optimizations_applied(analysis)
            }
            
        except Exception as e:
            logger.error(f"Error creating ATS-optimized resume: {e}")
            # Return basic formatted resume as fallback
            generator = ResumeGenerator(self.openai_client)
            formatter = ResumeFormatter()
            base_resume = generator.generate_base_resume(resume_data)
            return {
                'content': formatter.format_as_text(base_resume['resume']),
                'optimization_date': datetime.now().isoformat(),
                'optimizations_applied': ['Basic formatting applied']
            }
    
    def _get_ats_optimization_system_prompt(self) -> str:
        """Get system prompt for ATS optimization"""
        return """You are an expert ATS (Applicant Tracking System) optimization specialist. Your task is to rewrite resumes to maximize their compatibility with ATS systems while maintaining readability and impact.

**ATS Optimization Principles:**
1. **Simple Formatting**: Use standard fonts, clear section headers, and consistent spacing
2. **Keyword Integration**: Naturally incorporate relevant keywords throughout
3. **Standard Sections**: Include Contact, Professional Summary, Experience, Education, Skills
4. **Bullet Points**: Use simple bullet points (•) for easy parsing
5. **Quantifiable Results**: Include specific numbers and achievements
6. **Action Verbs**: Start descriptions with strong action verbs
7. **No Graphics**: Avoid tables, images, or complex formatting
8. **Standard Dates**: Use consistent date formats (MM/YYYY)

**Background-Friendly Approach:**
- Frame experiences positively while maintaining honesty
- Emphasize transferable skills and growth
- Focus on achievements and value delivered
- Use inclusive, professional language

Generate a clean, ATS-optimized resume that maximizes parsing success while presenting the candidate in the best possible light."""

    def _create_optimization_prompt(self, resume_data: ResumeData, 
                                  analysis: Dict[str, Any]) -> str:
        """Create optimization prompt based on analysis results"""
        # Extract key issues from analysis
        major_issues = []
        for category, result in analysis['category_scores'].items():
            if result['score'] < 70:
                major_issues.extend(result.get('issues', []))
        
        # Create base resume content
        base_content = f"""
**Current Resume Data:**
Name: {resume_data.full_name}
Email: {resume_data.email}
Phone: {resume_data.phone}
Location: {resume_data.city}, {resume_data.state}

Professional Summary: {resume_data.professional_summary}

Work Experience:
{self._format_experience_for_prompt(resume_data.work_experience)}

Education:
{self._format_education_for_prompt(resume_data.education)}

Technical Skills: {', '.join(resume_data.technical_skills)}
Soft Skills: {', '.join(resume_data.soft_skills)}

**Current ATS Score:** {analysis['overall_score']}/100

**Major Issues to Address:**
{chr(10).join(['- ' + issue for issue in major_issues[:5]])}

**Optimization Requirements:**
1. Fix all identified ATS compatibility issues
2. Improve keyword density and relevance
3. Enhance section structure and organization
4. Optimize for better parsing and readability
5. Maintain professional tone while being background-friendly

Please create an ATS-optimized version that addresses these issues and maximizes compatibility with applicant tracking systems."""

        return base_content
    
    def _format_experience_for_prompt(self, experience: List[Dict]) -> str:
        """Format work experience for optimization prompt"""
        if not experience:
            return "No work experience provided"
        
        formatted = []
        for exp in experience:
            formatted.append(f"""
Position: {exp.get('position', 'N/A')}
Company: {exp.get('company', 'N/A')}
Dates: {exp.get('start_date', 'N/A')} - {exp.get('end_date', 'N/A')}
Description: {exp.get('description', 'N/A')}
""")
        return '\n'.join(formatted)
    
    def _format_education_for_prompt(self, education: List[Dict]) -> str:
        """Format education for optimization prompt"""
        if not education:
            return "No education provided"
        
        formatted = []
        for edu in education:
            formatted.append(f"""
Degree: {edu.get('degree', 'N/A')}
Field: {edu.get('field_of_study', 'N/A')}
Institution: {edu.get('institution', 'N/A')}
Year: {edu.get('graduation_year', 'N/A')}
""")
        return '\n'.join(formatted)
    
    def _extract_optimizations_applied(self, analysis: Dict[str, Any]) -> List[str]:
        """Extract list of optimizations that should be applied"""
        optimizations = []
        
        for category, result in analysis['category_scores'].items():
            if result['score'] < 80:
                category_name = category.replace('_', ' ').title()
                optimizations.append(f"Improved {category_name}")
        
        # Add standard optimizations
        optimizations.extend([
            "Enhanced ATS keyword integration",
            "Standardized formatting for better parsing",
            "Optimized section structure and organization"
        ])
        
        return optimizations[:6]  # Limit to 6 optimizations
    
    def _create_optimization_summary(self, original: Dict[str, Any], 
                                   optimized: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of optimizations performed"""
        improvement = optimized['overall_score'] - original['overall_score']
        
        category_improvements = {}
        for category in original['category_scores']:
            orig_score = original['category_scores'][category]['score']
            opt_score = optimized['category_scores'][category]['score']
            category_improvements[category] = {
                'original': orig_score,
                'optimized': opt_score,
                'improvement': opt_score - orig_score
            }
        
        return {
            'overall_improvement': improvement,
            'grade_change': f"{original['grade']} → {optimized['grade']}",
            'compatibility_improvement': f"{original['ats_compatibility_level']} → {optimized['ats_compatibility_level']}",
            'category_improvements': category_improvements,
            'top_improvements': self._get_top_improvements(category_improvements)
        }
    
    def _get_top_improvements(self, category_improvements: Dict) -> List[str]:
        """Get the top 3 category improvements"""
        sorted_improvements = sorted(
            category_improvements.items(),
            key=lambda x: x[1]['improvement'],
            reverse=True
        )
        
        top_improvements = []
        for category, improvement in sorted_improvements[:3]:
            if improvement['improvement'] > 5:  # Only include significant improvements
                category_name = category.replace('_', ' ').title()
                top_improvements.append(
                    f"{category_name}: +{improvement['improvement']:.1f} points"
                )
        
        return top_improvements

# Example usage and testing
if __name__ == "__main__":
    # Test the ATS analysis system
    try:
        # Create test resume data
        test_resume = ResumeData(
            full_name="Sarah Johnson",
            email="sarah.johnson@email.com",
            phone="(555) 123-4567",
            address="123 Main Street",
            city="Los Angeles",
            state="CA",
            zip_code="90210",
            professional_summary="Experienced customer service professional with strong communication skills and a track record of exceeding performance goals.",
            work_experience=[
                {
                    "company": "ABC Retail Store",
                    "position": "Sales Associate",
                    "start_date": "2022-01",
                    "end_date": "2024-01",
                    "description": "Provided excellent customer service, processed transactions, and maintained store appearance. Consistently exceeded monthly sales targets by 15%.",
                    "location": "Los Angeles, CA"
                }
            ],
            education=[
                {
                    "institution": "Los Angeles Community College",
                    "degree": "Associate Degree",
                    "field_of_study": "Business Administration",
                    "graduation_year": "2021"
                }
            ],
            technical_skills=["POS Systems", "Microsoft Office", "Inventory Management"],
            soft_skills=["Customer Service", "Communication", "Teamwork", "Problem Solving"]
        )
        
        # Test ATS analysis
        analyzer = ATSAnalyzer()
        analysis = analyzer.analyze_resume(test_resume)
        
        print("✅ ATS Analysis completed!")
        print(f"Overall Score: {analysis['overall_score']}/100 (Grade: {analysis['grade']})")
        print(f"Compatibility Level: {analysis['ats_compatibility_level']}")
        print(f"Estimated Pass Rate: {analysis['estimated_ats_pass_rate']}")
        
        print("\nTop Recommendations:")
        for i, rec in enumerate(analysis['recommendations'][:3], 1):
            print(f"{i}. {rec}")
        
        # Test ATS optimization
        optimizer = ATSOptimizer()
        optimization_result = optimizer.optimize_resume_for_ats(test_resume)
        
        if optimization_result['success']:
            print(f"\n✅ ATS Optimization completed!")
            print(f"Score Improvement: {optimization_result['original_score']:.1f} → {optimization_result['optimized_score']:.1f}")
            print(f"Improvement: +{optimization_result['improvement']:.1f} points")
            
            print("\nOptimizations Applied:")
            for opt in optimization_result['optimized_resume']['optimizations_applied'][:3]:
                print(f"- {opt}")
            
            print("\n" + "="*50)
            print("OPTIMIZED RESUME PREVIEW:")
            print("="*50)
            print(optimization_result['optimized_resume']['content'][:400] + "...")
        else:
            print(f"❌ ATS Optimization failed: {optimization_result['error']}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        # Fallback test
        print("Testing basic ATS analysis...")
        
        analyzer = ATSAnalyzer()
        basic_analysis = analyzer._analyze_format_compatibility("John Doe\nSoftware Engineer\nExperience with Python and JavaScript")
        print("✅ Basic ATS analysis working!")
        print(f"Format score: {basic_analysis['score']}/100")

