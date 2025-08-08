#!/usr/bin/env python3
"""
AI Resume Tailoring Engine for Job-Specific Customization
Analyzes job postings and tailors resume content to match requirements
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class JobAnalysis:
    """Job posting analysis results"""
    job_id: str
    title: str
    company: str
    keywords: List[str]
    required_skills: List[str]
    preferred_skills: List[str]
    experience_level: str
    industry: str
    responsibilities: List[str]
    qualifications: List[str]
    background_friendly_score: float
    analysis_confidence: str
    recommendations: List[str]

@dataclass
class TailoringRecommendation:
    """Individual tailoring recommendation"""
    section: str
    original_text: str
    suggested_text: str
    reason: str
    confidence: float
    keywords_added: List[str]

@dataclass
class TailoredResumeResult:
    """Complete tailored resume result"""
    resume_id: str
    job_analysis: JobAnalysis
    recommendations: List[TailoringRecommendation]
    tailored_content: Dict[str, Any]
    match_score: float
    keyword_coverage: float
    sections_improved: int
    processing_timestamp: str

class JobPostingAnalyzer:
    """Analyzes job postings to extract key requirements and characteristics"""
    
    def __init__(self):
        self.skill_keywords = self._load_skill_keywords()
        self.experience_patterns = self._load_experience_patterns()
        self.industry_keywords = self._load_industry_keywords()
    
    def _load_skill_keywords(self) -> Dict[str, List[str]]:
        """Load categorized skill keywords"""
        return {
            'technical': [
                'microsoft office', 'excel', 'powerpoint', 'word', 'outlook', 'access',
                'google workspace', 'gsuite', 'gmail', 'google docs', 'google sheets',
                'project management', 'data analysis', 'data entry', 'database',
                'crm', 'erp', 'salesforce', 'quickbooks', 'accounting software',
                'inventory management', 'pos systems', 'cash handling',
                'social media', 'marketing', 'email marketing', 'seo',
                'customer service software', 'help desk', 'ticketing systems',
                'warehouse management', 'logistics', 'supply chain',
                'quality control', 'safety protocols', 'osha', 'compliance',
                'forklift', 'machinery operation', 'equipment maintenance',
                'food service', 'restaurant pos', 'kitchen equipment',
                'medical terminology', 'hipaa', 'medical records',
                'construction', 'blueprint reading', 'hand tools', 'power tools'
            ],
            'soft': [
                'communication', 'verbal communication', 'written communication',
                'teamwork', 'collaboration', 'team player',
                'leadership', 'management', 'supervision', 'training',
                'problem solving', 'analytical thinking', 'critical thinking',
                'time management', 'organization', 'planning', 'scheduling',
                'attention to detail', 'accuracy', 'precision',
                'customer service', 'customer focus', 'client relations',
                'adaptability', 'flexibility', 'learning agility',
                'reliability', 'dependability', 'punctuality',
                'work ethic', 'initiative', 'self-motivated',
                'multitasking', 'prioritization', 'stress management',
                'sales', 'negotiation', 'persuasion',
                'creativity', 'innovation', 'problem resolution'
            ],
            'background_friendly': [
                'second chance', 'fresh start', 'new beginning',
                'entry level', 'no experience required', 'will train',
                'on the job training', 'paid training', 'apprenticeship',
                'equal opportunity', 'diverse workforce', 'inclusive',
                'rehabilitation', 'reentry', 'workforce development',
                'stable employment', 'long term opportunity',
                'supportive environment', 'mentorship', 'career growth'
            ]
        }
    
    def _load_experience_patterns(self) -> Dict[str, List[str]]:
        """Load experience level patterns"""
        return {
            'entry_level': [
                'entry level', 'no experience', 'will train', 'recent graduate',
                '0-1 years', '0-2 years', 'junior', 'trainee', 'apprentice'
            ],
            'mid_level': [
                '2-5 years', '3-5 years', 'experienced', 'proven track record',
                'demonstrated experience', 'several years'
            ],
            'senior_level': [
                '5+ years', '7+ years', '10+ years', 'senior', 'lead',
                'extensive experience', 'expert level', 'advanced'
            ]
        }
    
    def _load_industry_keywords(self) -> Dict[str, List[str]]:
        """Load industry-specific keywords"""
        return {
            'retail': ['retail', 'sales', 'customer service', 'cashier', 'merchandise', 'inventory'],
            'food_service': ['restaurant', 'food service', 'kitchen', 'server', 'cook', 'prep'],
            'warehouse': ['warehouse', 'logistics', 'shipping', 'receiving', 'forklift', 'packaging'],
            'construction': ['construction', 'building', 'contractor', 'trade', 'maintenance', 'repair'],
            'manufacturing': ['manufacturing', 'production', 'assembly', 'quality control', 'factory'],
            'healthcare': ['healthcare', 'medical', 'patient', 'clinical', 'nursing', 'therapy'],
            'office': ['administrative', 'office', 'clerical', 'data entry', 'reception', 'filing'],
            'security': ['security', 'guard', 'surveillance', 'patrol', 'safety', 'protection'],
            'cleaning': ['cleaning', 'janitorial', 'housekeeping', 'maintenance', 'sanitation'],
            'delivery': ['delivery', 'driver', 'transportation', 'logistics', 'courier', 'shipping']
        }
    
    def analyze_job_posting(self, job_data: Dict[str, Any]) -> JobAnalysis:
        """Analyze job posting and extract key information"""
        try:
            # Extract text content
            job_text = self._extract_job_text(job_data)
            
            # Analyze different aspects
            keywords = self._extract_keywords(job_text)
            skills = self._categorize_skills(keywords)
            experience_level = self._determine_experience_level(job_text)
            industry = self._identify_industry(job_text, keywords)
            responsibilities = self._extract_responsibilities(job_text)
            qualifications = self._extract_qualifications(job_text)
            
            # Calculate background-friendly score
            bg_score = self._calculate_background_friendly_score(job_data, job_text, keywords)
            
            # Generate recommendations
            recommendations = self._generate_job_recommendations(job_data, skills, experience_level)
            
            return JobAnalysis(
                job_id=job_data.get('id', str(uuid.uuid4())),
                title=job_data.get('title', ''),
                company=job_data.get('company', ''),
                keywords=keywords,
                required_skills=skills['required'],
                preferred_skills=skills['preferred'],
                experience_level=experience_level,
                industry=industry,
                responsibilities=responsibilities,
                qualifications=qualifications,
                background_friendly_score=bg_score,
                analysis_confidence='high' if len(keywords) > 10 else 'medium',
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error analyzing job posting: {e}")
            # Return basic analysis
            return JobAnalysis(
                job_id=job_data.get('id', str(uuid.uuid4())),
                title=job_data.get('title', ''),
                company=job_data.get('company', ''),
                keywords=[],
                required_skills=[],
                preferred_skills=[],
                experience_level='unknown',
                industry='general',
                responsibilities=[],
                qualifications=[],
                background_friendly_score=0.5,
                analysis_confidence='low',
                recommendations=[]
            )
    
    def _extract_job_text(self, job_data: Dict[str, Any]) -> str:
        """Extract all text content from job posting"""
        text_parts = []
        
        # Add basic job info
        if job_data.get('title'):
            text_parts.append(job_data['title'])
        if job_data.get('description'):
            text_parts.append(job_data['description'])
        if job_data.get('requirements'):
            if isinstance(job_data['requirements'], list):
                text_parts.extend(job_data['requirements'])
            else:
                text_parts.append(str(job_data['requirements']))
        
        # Add analysis data if available
        if job_data.get('analysis', {}).get('summary'):
            text_parts.append(job_data['analysis']['summary'])
        
        return ' '.join(text_parts).lower()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from job text"""
        keywords = []
        
        # Extract all skill keywords
        for category, skill_list in self.skill_keywords.items():
            for skill in skill_list:
                if skill.lower() in text:
                    keywords.append(skill)
        
        # Extract industry-specific terms
        for industry, terms in self.industry_keywords.items():
            for term in terms:
                if term.lower() in text:
                    keywords.append(term)
        
        # Remove duplicates while preserving order
        unique_keywords = []
        seen = set()
        for keyword in keywords:
            if keyword.lower() not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword.lower())
        
        return unique_keywords
    
    def _categorize_skills(self, keywords: List[str]) -> Dict[str, List[str]]:
        """Categorize keywords into required vs preferred skills"""
        technical_skills = []
        soft_skills = []
        
        for keyword in keywords:
            if keyword.lower() in [s.lower() for s in self.skill_keywords['technical']]:
                technical_skills.append(keyword)
            elif keyword.lower() in [s.lower() for s in self.skill_keywords['soft']]:
                soft_skills.append(keyword)
        
        # For simplicity, consider all as required (could be enhanced with NLP)
        return {
            'required': technical_skills + soft_skills[:5],  # Limit soft skills
            'preferred': []  # Could be enhanced to distinguish required vs preferred
        }
    
    def _determine_experience_level(self, text: str) -> str:
        """Determine experience level required"""
        for level, patterns in self.experience_patterns.items():
            for pattern in patterns:
                if pattern.lower() in text:
                    return level
        return 'entry_level'  # Default to entry level for background-friendly jobs
    
    def _identify_industry(self, text: str, keywords: List[str]) -> str:
        """Identify the primary industry"""
        industry_scores = {}
        
        for industry, terms in self.industry_keywords.items():
            score = 0
            for term in terms:
                if term.lower() in text:
                    score += 1
                if term in keywords:
                    score += 2  # Extra weight for extracted keywords
            industry_scores[industry] = score
        
        if industry_scores:
            return max(industry_scores, key=industry_scores.get)
        return 'general'
    
    def _extract_responsibilities(self, text: str) -> List[str]:
        """Extract key responsibilities from job text"""
        responsibilities = []
        
        # Look for bullet points or numbered lists
        bullet_patterns = [
            r'[•·*-]\s*([^•·*-\n]+)',
            r'\d+\.\s*([^\d\n]+)',
            r'(?:^|\n)\s*([A-Z][^.\n]+\.)',
        ]
        
        for pattern in bullet_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                cleaned = match.strip()
                if 10 < len(cleaned) < 200:  # Reasonable length
                    responsibilities.append(cleaned)
        
        return responsibilities[:10]  # Limit to 10 responsibilities
    
    def _extract_qualifications(self, text: str) -> List[str]:
        """Extract qualifications from job text"""
        qualifications = []
        
        # Look for education/certification requirements
        qual_patterns = [
            r'(?:bachelor|master|associate|degree|diploma|certificate|certification|license)[\w\s]+',
            r'(?:high school|ged|equivalent)[\w\s]*',
            r'(?:\d+\+?\s*years?)[\w\s]*experience',
            r'(?:required|must have|should have):\s*([^.\n]+)'
        ]
        
        for pattern in qual_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ''
                cleaned = match.strip()
                if 5 < len(cleaned) < 100:
                    qualifications.append(cleaned)
        
        return qualifications[:8]  # Limit to 8 qualifications
    
    def _calculate_background_friendly_score(self, job_data: Dict[str, Any], text: str, keywords: List[str]) -> float:
        """Calculate how background-friendly the job is"""
        score = 0.5  # Base score
        
        # Check for background-friendly keywords
        bg_keywords = self.skill_keywords['background_friendly']
        for keyword in bg_keywords:
            if keyword.lower() in text:
                score += 0.1
        
        # Use existing analysis score if available
        if job_data.get('analysis', {}).get('score'):
            existing_score = job_data['analysis']['score']
            score = (score + existing_score) / 2  # Average with our calculation
        
        # Boost for entry-level positions
        entry_patterns = self.experience_patterns['entry_level']
        for pattern in entry_patterns:
            if pattern.lower() in text:
                score += 0.1
                break
        
        # Industry adjustments
        industry = self._identify_industry(text, keywords)
        industry_boosts = {
            'warehouse': 0.15,
            'construction': 0.15,
            'food_service': 0.1,
            'cleaning': 0.1,
            'manufacturing': 0.1
        }
        score += industry_boosts.get(industry, 0)
        
        return min(1.0, score)  # Cap at 1.0
    
    def _generate_job_recommendations(self, job_data: Dict[str, Any], skills: Dict[str, List[str]], experience_level: str) -> List[str]:
        """Generate recommendations for applying to this job"""
        recommendations = []
        
        # Experience level recommendations
        if experience_level == 'entry_level':
            recommendations.append("This appears to be an entry-level position - emphasize your willingness to learn and any relevant training.")
        
        # Skill-based recommendations
        if skills['required']:
            recommendations.append(f"Highlight experience with: {', '.join(skills['required'][:3])}")
        
        # Background-friendly recommendations
        bg_score = job_data.get('analysis', {}).get('score', 0.5)
        if bg_score > 0.7:
            recommendations.append("This position shows strong background-friendly indicators - consider applying with confidence.")
        elif bg_score > 0.5:
            recommendations.append("This position may be open to candidates with backgrounds - focus on rehabilitation and skills.")
        
        # Industry-specific recommendations
        industry_tips = {
            'warehouse': "Emphasize physical capability, attention to detail, and safety awareness.",
            'construction': "Highlight any trade skills, safety training, and reliability.",
            'food_service': "Focus on customer service skills and ability to work in fast-paced environments.",
            'retail': "Emphasize customer service, cash handling, and sales experience.",
            'office': "Highlight computer skills, organization, and professional communication."
        }
        
        # Add industry tip if available
        text = self._extract_job_text(job_data)
        keywords = self._extract_keywords(text)
        industry = self._identify_industry(text, keywords)
        if industry in industry_tips:
            recommendations.append(industry_tips[industry])
        
        return recommendations[:5]  # Limit to 5 recommendations

class ResumeContentTailorer:
    """Tailors resume content to match job requirements"""
    
    def __init__(self):
        self.action_verbs = self._load_action_verbs()
        self.skill_synonyms = self._load_skill_synonyms()
    
    def _load_action_verbs(self) -> Dict[str, List[str]]:
        """Load action verbs by category"""
        return {
            'leadership': ['led', 'managed', 'supervised', 'coordinated', 'directed', 'guided'],
            'achievement': ['achieved', 'accomplished', 'exceeded', 'improved', 'increased', 'enhanced'],
            'communication': ['communicated', 'presented', 'collaborated', 'negotiated', 'facilitated'],
            'technical': ['developed', 'implemented', 'operated', 'maintained', 'analyzed', 'processed'],
            'customer_service': ['served', 'assisted', 'supported', 'resolved', 'handled', 'addressed'],
            'organization': ['organized', 'planned', 'scheduled', 'coordinated', 'managed', 'prioritized']
        }
    
    def _load_skill_synonyms(self) -> Dict[str, List[str]]:
        """Load skill synonyms for better matching"""
        return {
            'customer service': ['customer support', 'client relations', 'customer care', 'customer assistance'],
            'microsoft office': ['ms office', 'office suite', 'word processing', 'spreadsheets'],
            'teamwork': ['collaboration', 'team player', 'cooperative', 'team-oriented'],
            'communication': ['interpersonal skills', 'verbal skills', 'written skills', 'correspondence'],
            'problem solving': ['troubleshooting', 'analytical thinking', 'issue resolution', 'critical thinking'],
            'time management': ['organization', 'prioritization', 'scheduling', 'planning'],
            'leadership': ['management', 'supervision', 'team leadership', 'project management'],
            'attention to detail': ['accuracy', 'precision', 'thoroughness', 'quality focus']
        }
    
    def tailor_resume_to_job(self, resume_data: Dict[str, Any], job_analysis: JobAnalysis) -> TailoredResumeResult:
        """Tailor complete resume to match job requirements"""
        try:
            recommendations = []
            tailored_content = resume_data.copy()
            
            # Tailor each section
            summary_rec = self._tailor_summary(resume_data.get('summary', ''), job_analysis)
            if summary_rec:
                recommendations.append(summary_rec)
                tailored_content['summary'] = summary_rec.suggested_text
            
            experience_recs = self._tailor_experience(resume_data.get('work_experience', []), job_analysis)
            recommendations.extend(experience_recs)
            if experience_recs:
                tailored_content['work_experience'] = self._apply_experience_recommendations(
                    resume_data.get('work_experience', []), experience_recs
                )
            
            skills_rec = self._tailor_skills(resume_data.get('technical_skills', []), resume_data.get('soft_skills', []), job_analysis)
            if skills_rec:
                recommendations.append(skills_rec)
                # Apply skills recommendations
                all_suggested_skills = skills_rec.keywords_added
                tailored_content['technical_skills'] = list(set(resume_data.get('technical_skills', []) + [s for s in all_suggested_skills if self._is_technical_skill(s)]))
                tailored_content['soft_skills'] = list(set(resume_data.get('soft_skills', []) + [s for s in all_suggested_skills if not self._is_technical_skill(s)]))
            
            # Calculate metrics
            match_score = self._calculate_match_score(tailored_content, job_analysis)
            keyword_coverage = self._calculate_keyword_coverage(tailored_content, job_analysis)
            
            return TailoredResumeResult(
                resume_id=str(uuid.uuid4()),
                job_analysis=job_analysis,
                recommendations=recommendations,
                tailored_content=tailored_content,
                match_score=match_score,
                keyword_coverage=keyword_coverage,
                sections_improved=len(recommendations),
                processing_timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error tailoring resume: {e}")
            return TailoredResumeResult(
                resume_id=str(uuid.uuid4()),
                job_analysis=job_analysis,
                recommendations=[],
                tailored_content=resume_data,
                match_score=0.5,
                keyword_coverage=0.3,
                sections_improved=0,
                processing_timestamp=datetime.utcnow().isoformat()
            )
    
    def _tailor_summary(self, summary: str, job_analysis: JobAnalysis) -> Optional[TailoringRecommendation]:
        """Tailor professional summary to job"""
        if not summary:
            # Create new summary if none exists
            suggested_summary = self._generate_summary_for_job(job_analysis)
            return TailoringRecommendation(
                section='summary',
                original_text='',
                suggested_text=suggested_summary,
                reason='Created job-specific professional summary',
                confidence=0.8,
                keywords_added=job_analysis.required_skills[:3]
            )
        
        # Enhance existing summary
        enhanced_summary = summary
        keywords_added = []
        
        # Add relevant keywords that aren't already present
        for skill in job_analysis.required_skills[:3]:
            if skill.lower() not in summary.lower():
                # Find good place to insert skill
                enhanced_summary = self._insert_skill_naturally(enhanced_summary, skill)
                keywords_added.append(skill)
        
        if keywords_added:
            return TailoringRecommendation(
                section='summary',
                original_text=summary,
                suggested_text=enhanced_summary,
                reason=f'Added relevant keywords: {", ".join(keywords_added)}',
                confidence=0.7,
                keywords_added=keywords_added
            )
        
        return None
    
    def _generate_summary_for_job(self, job_analysis: JobAnalysis) -> str:
        """Generate a job-specific professional summary"""
        experience_level = job_analysis.experience_level
        skills = job_analysis.required_skills[:3]
        industry = job_analysis.industry
        
        # Template based on experience level
        if experience_level == 'entry_level':
            template = f"Motivated professional seeking to begin career in {industry}. Eager to apply {', '.join(skills[:2])} skills in a dynamic work environment. Strong work ethic and commitment to learning and growth."
        else:
            template = f"Experienced professional with background in {industry}. Proven abilities in {', '.join(skills[:3])}. Seeking opportunity to contribute expertise and drive results in challenging role."
        
        return template
    
    def _insert_skill_naturally(self, text: str, skill: str) -> str:
        """Insert skill naturally into text"""
        # Simple insertion at end of first sentence
        sentences = text.split('.')
        if sentences:
            first_sentence = sentences[0].strip()
            if skill.lower() not in first_sentence.lower():
                enhanced_first = f"{first_sentence} with {skill} experience"
                return enhanced_first + '.' + '.'.join(sentences[1:])
        return text
    
    def _tailor_experience(self, experiences: List[Dict[str, Any]], job_analysis: JobAnalysis) -> List[TailoringRecommendation]:
        """Tailor work experience descriptions"""
        recommendations = []
        
        for i, exp in enumerate(experiences[:3]):  # Focus on top 3 experiences
            description = exp.get('description', '')
            if not description:
                continue
            
            enhanced_description = self._enhance_job_description(description, job_analysis)
            keywords_added = self._find_added_keywords(description, enhanced_description, job_analysis.required_skills)
            
            if enhanced_description != description:
                recommendations.append(TailoringRecommendation(
                    section=f'experience_{i}',
                    original_text=description,
                    suggested_text=enhanced_description,
                    reason='Enhanced with job-relevant keywords and action verbs',
                    confidence=0.8,
                    keywords_added=keywords_added
                ))
        
        return recommendations
    
    def _enhance_job_description(self, description: str, job_analysis: JobAnalysis) -> str:
        """Enhance job description with relevant keywords"""
        enhanced = description
        
        # Replace weak verbs with strong action verbs
        enhanced = self._strengthen_action_verbs(enhanced)
        
        # Add relevant skills where appropriate
        for skill in job_analysis.required_skills[:2]:
            if skill.lower() not in enhanced.lower():
                # Try to naturally incorporate the skill
                enhanced = self._incorporate_skill_in_description(enhanced, skill)
        
        return enhanced
    
    def _strengthen_action_verbs(self, text: str) -> str:
        """Replace weak verbs with stronger action verbs"""
        weak_to_strong = {
            'did': 'executed',
            'worked on': 'managed',
            'helped': 'assisted',
            'was responsible for': 'managed',
            'took care of': 'maintained',
            'dealt with': 'resolved'
        }
        
        enhanced = text
        for weak, strong in weak_to_strong.items():
            enhanced = re.sub(r'\b' + weak + r'\b', strong, enhanced, flags=re.IGNORECASE)
        
        return enhanced
    
    def _incorporate_skill_in_description(self, description: str, skill: str) -> str:
        """Naturally incorporate skill into job description"""
        # Simple approach: add to end of description
        if description.endswith('.'):
            return f"{description[:-1]} utilizing {skill}."
        else:
            return f"{description} utilizing {skill}."
    
    def _tailor_skills(self, technical_skills: List[str], soft_skills: List[str], job_analysis: JobAnalysis) -> Optional[TailoringRecommendation]:
        """Tailor skills section to job requirements"""
        all_current_skills = [s.lower() for s in technical_skills + soft_skills]
        missing_skills = []
        
        # Find missing required skills
        for skill in job_analysis.required_skills:
            if skill.lower() not in all_current_skills:
                # Check for synonyms
                if not self._has_skill_synonym(skill, all_current_skills):
                    missing_skills.append(skill)
        
        if missing_skills:
            return TailoringRecommendation(
                section='skills',
                original_text=f"Technical: {', '.join(technical_skills)}, Soft: {', '.join(soft_skills)}",
                suggested_text=f"Consider adding: {', '.join(missing_skills[:5])}",
                reason='Add missing job-relevant skills',
                confidence=0.9,
                keywords_added=missing_skills[:5]
            )
        
        return None
    
    def _has_skill_synonym(self, skill: str, current_skills: List[str]) -> bool:
        """Check if current skills include synonyms of target skill"""
        synonyms = self.skill_synonyms.get(skill.lower(), [])
        for synonym in synonyms:
            if any(synonym.lower() in current.lower() for current in current_skills):
                return True
        return False
    
    def _is_technical_skill(self, skill: str) -> bool:
        """Determine if skill is technical or soft"""
        technical_indicators = [
            'microsoft', 'office', 'excel', 'software', 'system', 'database',
            'computer', 'technology', 'program', 'application', 'tool'
        ]
        return any(indicator in skill.lower() for indicator in technical_indicators)
    
    def _apply_experience_recommendations(self, experiences: List[Dict[str, Any]], recommendations: List[TailoringRecommendation]) -> List[Dict[str, Any]]:
        """Apply experience recommendations to resume data"""
        enhanced_experiences = experiences.copy()
        
        for rec in recommendations:
            if rec.section.startswith('experience_'):
                try:
                    index = int(rec.section.split('_')[1])
                    if index < len(enhanced_experiences):
                        enhanced_experiences[index]['description'] = rec.suggested_text
                except (ValueError, IndexError):
                    continue
        
        return enhanced_experiences
    
    def _find_added_keywords(self, original: str, enhanced: str, keywords: List[str]) -> List[str]:
        """Find which keywords were added in enhancement"""
        added = []
        for keyword in keywords:
            if keyword.lower() not in original.lower() and keyword.lower() in enhanced.lower():
                added.append(keyword)
        return added
    
    def _calculate_match_score(self, resume_data: Dict[str, Any], job_analysis: JobAnalysis) -> float:
        """Calculate how well resume matches job requirements"""
        score = 0.0
        total_weight = 0
        
        # Check skill matches
        resume_skills = [s.lower() for s in resume_data.get('technical_skills', []) + resume_data.get('soft_skills', [])]
        job_skills = [s.lower() for s in job_analysis.required_skills]
        
        if job_skills:
            skill_matches = sum(1 for skill in job_skills if skill in resume_skills)
            score += (skill_matches / len(job_skills)) * 0.5
            total_weight += 0.5
        
        # Check keyword presence in summary and experience
        all_text = ' '.join([
            resume_data.get('summary', ''),
            ' '.join([exp.get('description', '') for exp in resume_data.get('work_experience', [])])
        ]).lower()
        
        keyword_matches = sum(1 for keyword in job_analysis.keywords if keyword.lower() in all_text)
        if job_analysis.keywords:
            score += (keyword_matches / len(job_analysis.keywords)) * 0.3
            total_weight += 0.3
        
        # Industry relevance
        if job_analysis.industry in all_text:
            score += 0.2
        total_weight += 0.2
        
        return score / total_weight if total_weight > 0 else 0.5
    
    def _calculate_keyword_coverage(self, resume_data: Dict[str, Any], job_analysis: JobAnalysis) -> float:
        """Calculate keyword coverage percentage"""
        if not job_analysis.keywords:
            return 0.5
        
        all_text = ' '.join([
            resume_data.get('summary', ''),
            ' '.join([s for s in resume_data.get('technical_skills', [])]),
            ' '.join([s for s in resume_data.get('soft_skills', [])]),
            ' '.join([exp.get('description', '') for exp in resume_data.get('work_experience', [])])
        ]).lower()
        
        coverage = sum(1 for keyword in job_analysis.keywords if keyword.lower() in all_text)
        return coverage / len(job_analysis.keywords)

class AIResumeTailoringEngine:
    """Main engine for AI-powered resume tailoring"""
    
    def __init__(self):
        self.job_analyzer = JobPostingAnalyzer()
        self.content_tailorer = ResumeContentTailorer()
        self.cache = {}  # Simple cache for job analyses
    
    def tailor_resume_for_job(self, resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> TailoredResumeResult:
        """Main method to tailor resume for specific job"""
        try:
            # Analyze job posting
            job_id = job_data.get('id', str(uuid.uuid4()))
            
            if job_id in self.cache:
                job_analysis = self.cache[job_id]
                logger.info(f"Using cached job analysis for {job_id}")
            else:
                job_analysis = self.job_analyzer.analyze_job_posting(job_data)
                self.cache[job_id] = job_analysis
                logger.info(f"Generated new job analysis for {job_analysis.title}")
            
            # Tailor resume content
            tailored_result = self.content_tailorer.tailor_resume_to_job(resume_data, job_analysis)
            
            logger.info(f"Resume tailoring completed - Match score: {tailored_result.match_score:.2f}")
            return tailored_result
            
        except Exception as e:
            logger.error(f"Error in resume tailoring: {e}")
            # Return basic result on error
            return TailoredResumeResult(
                resume_id=str(uuid.uuid4()),
                job_analysis=JobAnalysis(
                    job_id=job_data.get('id', str(uuid.uuid4())),
                    title=job_data.get('title', ''),
                    company=job_data.get('company', ''),
                    keywords=[],
                    required_skills=[],
                    preferred_skills=[],
                    experience_level='unknown',
                    industry='general',
                    responsibilities=[],
                    qualifications=[],
                    background_friendly_score=0.5,
                    analysis_confidence='low',
                    recommendations=[]
                ),
                recommendations=[],
                tailored_content=resume_data,
                match_score=0.5,
                keyword_coverage=0.3,
                sections_improved=0,
                processing_timestamp=datetime.utcnow().isoformat()
            )
    
    def get_job_analysis(self, job_data: Dict[str, Any]) -> JobAnalysis:
        """Get analysis for job posting only"""
        return self.job_analyzer.analyze_job_posting(job_data)
    
    def clear_cache(self):
        """Clear the analysis cache"""
        self.cache.clear()
        logger.info("Job analysis cache cleared")

# Example usage and testing
if __name__ == "__main__":
    engine = AIResumeTailoringEngine()
    
    # Test job data
    test_job = {
        'id': 'test_001',
        'title': 'Warehouse Associate',
        'company': 'ABC Logistics',
        'description': 'Entry-level warehouse position. Responsibilities include picking, packing, and shipping orders. Will train. Microsoft Office experience preferred. Forklift certification a plus.',
        'analysis': {
            'score': 0.8,
            'summary': 'Background-friendly warehouse position with training provided'
        }
    }
    
    # Test resume data
    test_resume = {
        'summary': 'Hardworking individual seeking stable employment',
        'work_experience': [
            {
                'title': 'General Laborer',
                'company': 'Construction Co',
                'description': 'Worked on construction sites, handled materials'
            }
        ],
        'technical_skills': ['Basic computer skills'],
        'soft_skills': ['Teamwork', 'Reliability']
    }
    
    # Test tailoring
    result = engine.tailor_resume_for_job(test_resume, test_job)
    
    print(f"✅ AI Resume Tailoring Engine Test Complete!")
    print(f"Match Score: {result.match_score:.2f}")
    print(f"Keyword Coverage: {result.keyword_coverage:.2f}")
    print(f"Recommendations: {len(result.recommendations)}")
    print(f"Job Analysis Confidence: {result.job_analysis.analysis_confidence}")