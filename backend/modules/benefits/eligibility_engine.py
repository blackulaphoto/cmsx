#!/usr/bin/env python3
"""
Universal Benefits Eligibility Assessment Engine
Comprehensive eligibility determination for all government benefit programs
"""

import csv
import json
import logging
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class EligibilityStatus(Enum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    PARTIALLY_ELIGIBLE = "partially_eligible"
    NEEDS_REVIEW = "needs_review"

@dataclass
class AssessmentQuestion:
    """Represents a single assessment question"""
    program: str
    category: str
    question: str
    question_type: str
    purpose: str
    qualifying_answers: List[str]
    disqualifying_answers: List[str]
    notes: str = ""

@dataclass
class AssessmentResult:
    """Results of an eligibility assessment"""
    program: str
    client_id: str
    status: EligibilityStatus
    confidence_score: float
    qualifying_factors: List[str]
    disqualifying_factors: List[str]
    missing_information: List[str]
    next_steps: List[str]
    required_documents: List[str]
    estimated_benefit_amount: Optional[float]
    processing_timeline: str
    assessment_data: Dict[str, Any]
    created_at: str

class UniversalEligibilityEngine:
    """Universal eligibility assessment engine for all benefit programs"""
    
    def __init__(self):
        self.criteria_data = {}
        self.questions_data = {}
        self.program_configs = {}
        self._active_program = None
        self._active_responses = {}
        self._load_assessment_data()
        self._initialize_program_configs()
    
    def _load_fallback_data(self):
        """Load fallback data when CSV files are missing or empty"""
        # Fallback questions data
        self.questions_data = {
            'SNAP/CalFresh': [
                {'category': 'Basic Info', 'question': 'How many people live in your household?', 'type': 'Number', 'purpose': 'Determine household size for eligibility'},
                {'category': 'Income', 'question': 'What is your household\'s total monthly gross income?', 'type': 'Currency', 'purpose': 'Verify income requirements'},
                {'category': 'Demographics', 'question': 'Are you a U.S. citizen or qualified immigrant?', 'type': 'Multiple Choice', 'purpose': 'Verify citizenship eligibility'},
                {'category': 'Special Circumstances', 'question': 'Does your household include anyone 60+ or disabled?', 'type': 'Yes/No', 'purpose': 'Apply special income limits'},
                {'category': 'Work Requirements', 'question': 'Are you 18-54 able-bodied without dependents?', 'type': 'Yes/No', 'purpose': 'Determine work requirements'},
                {'category': 'Student Status', 'question': 'Are you a student (18-49) enrolled at least half-time?', 'type': 'Yes/No', 'purpose': 'Check student eligibility rules'},
                {'category': 'Resources', 'question': 'Do you have less than $100 in cash/bank accounts?', 'type': 'Yes/No', 'purpose': 'Expedited service eligibility'},
                {'category': 'Basic Info', 'question': 'How many people live in your household?', 'type': 'Number', 'purpose': 'Determine household size for eligibility'}
            ],
            'Medicaid/Medi-Cal': [
                {'category': 'Income', 'question': 'What is your household income as percentage of Federal Poverty Level?', 'type': 'Percentage', 'purpose': 'Determine income eligibility'},
                {'category': 'Demographics', 'question': 'What is your age?', 'type': 'Number', 'purpose': 'Age-specific eligibility rules'},
                {'category': 'Special Status', 'question': 'Are you currently pregnant?', 'type': 'Yes/No', 'purpose': 'Pregnancy eligibility pathway'},
                {'category': 'Citizenship', 'question': 'Are you a U.S. citizen or qualified immigrant?', 'type': 'Multiple Choice', 'purpose': 'Citizenship requirements'},
                {'category': 'Residency', 'question': 'Are you a California resident?', 'type': 'Yes/No', 'purpose': 'Residency requirement'},
            ],
            'SSI': [
                {'category': 'Age/Disability', 'question': 'Are you 65+ blind or disabled?', 'type': 'Multiple Choice', 'purpose': 'Basic SSI eligibility'},
                {'category': 'Income', 'question': 'What is your monthly non-work income?', 'type': 'Currency', 'purpose': 'Non-work income limits'},
                {'category': 'Work Income', 'question': 'What is your monthly work income?', 'type': 'Currency', 'purpose': 'Work income limits with exclusions'},
                {'category': 'Resources', 'question': 'What is your total countable resources value?', 'type': 'Currency', 'purpose': 'Resource limits'},
                {'category': 'Citizenship', 'question': 'Are you a U.S. citizen or qualified immigrant?', 'type': 'Multiple Choice', 'purpose': 'Citizenship eligibility'},
            ],
            'SSDI': [
                {'category': 'Work Credits', 'question': 'How many Social Security work credits have you earned?', 'type': 'Number', 'purpose': 'Total work credits requirement'},
                {'category': 'Recent Work', 'question': 'How many work credits in the last 10 years?', 'type': 'Number', 'purpose': 'Recent work requirement'},
                {'category': 'Duration', 'question': 'Has your disability lasted 12+ months or expected to?', 'type': 'Yes/No', 'purpose': 'Duration requirement'},
                {'category': 'Current Work', 'question': 'Are you earning more than $1260 per month?', 'type': 'Yes/No', 'purpose': 'Substantial gainful activity test'},
            ],
            'Housing Vouchers/Section 8': [
                {'category': 'Income', 'question': 'Is your income at/below 50% of area median income?', 'type': 'Yes/No', 'purpose': 'Income eligibility'},
                {'category': 'Household', 'question': 'How many people are in your household?', 'type': 'Number', 'purpose': 'Household composition'},
                {'category': 'Citizenship', 'question': 'Are you a U.S. citizen or HUD-eligible immigrant?', 'type': 'Multiple Choice', 'purpose': 'Citizenship status'},
            ],
            'TANF': [
                {'category': 'Children', 'question': 'Do you have dependent children under 18?', 'type': 'Yes/No', 'purpose': 'Dependent children requirement'},
                {'category': 'Income', 'question': 'Is household income below state limit for family size?', 'type': 'Yes/No', 'purpose': 'Income eligibility'},
                {'category': 'Citizenship', 'question': 'Are you a U.S. citizen or qualified immigrant 5+ years?', 'type': 'Multiple Choice', 'purpose': 'Citizenship requirement'},
            ],
            'WIC': [
                {'category': 'Category', 'question': 'Are you pregnant breastfeeding postpartum or have children under 5?', 'type': 'Multiple Choice', 'purpose': 'Categorical eligibility'},
                {'category': 'Income', 'question': 'Is household income at/below 185% of Federal Poverty Level?', 'type': 'Yes/No', 'purpose': 'Income requirement'},
                {'category': 'Residency', 'question': 'Are you a California resident?', 'type': 'Yes/No', 'purpose': 'Residency requirement'},
            ],
            'LIHEAP': [
                {'category': 'Income', 'question': 'Is household income within LIHEAP guidelines?', 'type': 'Yes/No', 'purpose': 'Income eligibility'},
                {'category': 'Age', 'question': 'Is applicant at least 18 years old?', 'type': 'Yes/No', 'purpose': 'Age requirement'},
                {'category': 'Emergency', 'question': 'Do you have disconnection notice or energy emergency?', 'type': 'Yes/No', 'purpose': 'Emergency assistance'},
            ]
        }
        
        # Fallback criteria data
        self.criteria_data = {
            'SNAP/CalFresh': [
                {'question': 'How many people live in your household?', 'qualifying_answers': ['1', '2', '3', '4', '5', '6', '7', '8'], 'disqualifying_answers': [], 'notes': 'Household size determines benefit amount'},
                {'question': 'What is your household\'s total monthly gross income?', 'qualifying_answers': ['<=200% FPL'], 'disqualifying_answers': ['>200% FPL'], 'notes': 'Income limits based on Federal Poverty Level'},
                {'question': 'Are you a U.S. citizen or qualified immigrant?', 'qualifying_answers': ['yes', 'u.s. citizen', 'qualified immigrant'], 'disqualifying_answers': ['no', 'other'], 'notes': 'Must be citizen or qualified immigrant'},
            ],
            'Medicaid/Medi-Cal': [
                {'question': 'What is your household income as percentage of Federal Poverty Level?', 'qualifying_answers': ['<=138%'], 'disqualifying_answers': ['>138%'], 'notes': 'Income limit for adults'},
                {'question': 'Are you a California resident?', 'qualifying_answers': ['yes'], 'disqualifying_answers': ['no'], 'notes': 'Must be state resident'},
            ],
            'SSI': [
                {'question': 'Are you 65+ blind or disabled?', 'qualifying_answers': ['yes', '65+', 'blind', 'disabled'], 'disqualifying_answers': ['no'], 'notes': 'Basic eligibility - must meet one category'},
                {'question': 'What is your monthly non-work income?', 'qualifying_answers': ['<$987'], 'disqualifying_answers': ['>=$987'], 'notes': 'Income limit for individuals in 2024'},
            ],
            'SSDI': [
                {'question': 'How many Social Security work credits have you earned?', 'qualifying_answers': ['>=40'], 'disqualifying_answers': ['<40'], 'notes': 'Generally need 40 total credits'},
                {'question': 'Has your disability lasted 12+ months or expected to?', 'qualifying_answers': ['yes'], 'disqualifying_answers': ['no'], 'notes': 'Duration requirement for disability'},
            ],
            'Housing Vouchers/Section 8': [
                {'question': 'Is your income at/below 50% of area median income?', 'qualifying_answers': ['yes'], 'disqualifying_answers': ['no'], 'notes': 'Income eligibility requirement'},
            ],
            'TANF': [
                {'question': 'Do you have dependent children under 18?', 'qualifying_answers': ['yes'], 'disqualifying_answers': ['no'], 'notes': 'Must have dependent children'},
            ],
            'WIC': [
                {'question': 'Are you pregnant breastfeeding postpartum or have children under 5?', 'qualifying_answers': ['yes', 'pregnant', 'breastfeeding', 'postpartum'], 'disqualifying_answers': ['no'], 'notes': 'Categorical eligibility requirement'},
            ],
            'LIHEAP': [
                {'question': 'Is household income within LIHEAP guidelines?', 'qualifying_answers': ['yes'], 'disqualifying_answers': ['no'], 'notes': 'Income guidelines vary by area'},
            ]
        }

    def _load_assessment_data(self):
        """Load assessment criteria and questions from CSV files"""
        try:
            # Load eligibility criteria
            criteria_file = os.path.join(os.path.dirname(__file__), 'criteria', 'complete_benefits_eligibility_criteria.csv')
            if os.path.exists(criteria_file):
                with open(criteria_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if not rows:  # File is empty
                        logger.warning("Criteria CSV file is empty, using fallback data")
                        self._load_fallback_data()
                        return
                        
                    for row in rows:
                        program = row['Program']
                        if program not in self.criteria_data:
                            self.criteria_data[program] = []
                        
                        # Parse qualifying and disqualifying answers
                        qualifying = self._split_answers(row.get('Qualifying_Answers', ''))
                        disqualifying = self._split_answers(row.get('Disqualifying_Answers', ''))
                        
                        self.criteria_data[program].append({
                            'question': row['Question'],
                            'qualifying_answers': qualifying,
                            'disqualifying_answers': disqualifying,
                            'notes': row.get('Notes', '')
                        })
            else:
                logger.warning("Criteria CSV file not found, using fallback data")
                self._load_fallback_data()
                return
            
            # Load assessment questions structure
            questions_file = os.path.join(os.path.dirname(__file__), 'criteria', 'social_benefits_assessment_questions.csv')
            if os.path.exists(questions_file):
                with open(questions_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if not rows:  # File is empty
                        logger.warning("Questions CSV file is empty, using fallback data")
                        if not hasattr(self, 'questions_data') or not self.questions_data:
                            self._load_fallback_data()
                        return
                        
                    for row in rows:
                        program = row['Program']
                        if program not in self.questions_data:
                            self.questions_data[program] = []
                        
                        self.questions_data[program].append({
                            'category': row['Category'],
                            'question': row['Question'],
                            'type': row['Type'],
                            'purpose': row['Purpose']
                        })
            else:
                logger.warning("Questions CSV file not found, using fallback data")
                if not hasattr(self, 'questions_data') or not self.questions_data:
                    self._load_fallback_data()
                return
            
            # If we got here and still no data, use fallback
            if not self.criteria_data and not self.questions_data:
                logger.warning("No data loaded from CSV files, using fallback data")
                self._load_fallback_data()
            
            logger.info(f"Loaded assessment data for {len(self.criteria_data)} programs")
            
        except Exception as e:
            logger.error(f"Error loading assessment data: {e}")
            logger.info("Using fallback data due to loading error")
            self._load_fallback_data()
    
    def _initialize_program_configs(self):
        """Initialize program-specific configurations"""
        self.program_configs = {
            'SNAP/CalFresh': {
                'name': 'SNAP/CalFresh Food Assistance',
                'description': 'Monthly food assistance benefits',
                'processing_time': '30 days',
                'contact': '1-877-847-3663',
                'website': 'https://www.calfresh.ca.gov/',
                'required_documents': [
                    'Photo identification',
                    'Proof of income (pay stubs, unemployment benefits)',
                    'Proof of housing costs (rent receipt, utility bills)',
                    'Bank statements',
                    'Social Security cards for all household members'
                ],
                'estimated_benefits': {
                    1: 291, 2: 535, 3: 766, 4: 973, 5: 1155, 6: 1386, 7: 1532, 8: 1751
                }
            },
            'Medicaid/Medi-Cal': {
                'name': 'Medicaid/Medi-Cal Health Coverage',
                'description': 'Comprehensive healthcare coverage',
                'processing_time': '45 days',
                'contact': '1-800-300-1506',
                'website': 'https://www.coveredca.com/',
                'required_documents': [
                    'Photo identification',
                    'Proof of income',
                    'Proof of citizenship or immigration status',
                    'Proof of California residence',
                    'Social Security card'
                ],
                'estimated_benefits': None  # Coverage value varies
            },
            'SSI': {
                'name': 'Supplemental Security Income',
                'description': 'Monthly income for disabled individuals',
                'processing_time': '3-5 months',
                'contact': '1-800-772-1213',
                'website': 'https://www.ssa.gov/benefits/ssi/',
                'required_documents': [
                    'Birth certificate or proof of age',
                    'Social Security card',
                    'Medical records and treatment history',
                    'Work history and earnings records',
                    'Bank statements and financial records'
                ],
                'estimated_benefits': {
                    'individual': 987,
                    'couple': 1485
                }
            },
            'SSDI': {
                'name': 'Social Security Disability Insurance',
                'description': 'Disability benefits based on work history',
                'processing_time': '3-5 months',
                'contact': '1-800-772-1213',
                'website': 'https://www.ssa.gov/benefits/disability/',
                'required_documents': [
                    'Social Security card',
                    'Medical records and treatment history',
                    'Work history and earnings records',
                    'Tax returns',
                    'Birth certificate'
                ],
                'estimated_benefits': None  # Based on work history
            },
            'Housing Vouchers/Section 8': {
                'name': 'Housing Choice Voucher (Section 8)',
                'description': 'Rental assistance vouchers',
                'processing_time': '2+ years (waitlist)',
                'contact': 'Local Housing Authority',
                'website': 'https://www.hud.gov/topics/housing_choice_voucher',
                'required_documents': [
                    'Photo identification for all adults',
                    'Birth certificates for all children',
                    'Social Security cards for all members',
                    'Proof of income for all adults',
                    'Immigration documents (if applicable)'
                ],
                'estimated_benefits': None  # Varies by area
            },
            'TANF': {
                'name': 'Temporary Assistance for Needy Families',
                'description': 'Temporary cash assistance for families',
                'processing_time': '30 days',
                'contact': 'Local TANF Office',
                'website': 'https://www.cdss.ca.gov/inforesources/calworks',
                'required_documents': [
                    'Photo identification',
                    'Birth certificates for all children',
                    'Social Security cards',
                    'Proof of income',
                    'Proof of residence'
                ],
                'estimated_benefits': {
                    1: 692, 2: 1086, 3: 1348, 4: 1598, 5: 1848, 6: 2098, 7: 2348, 8: 2598
                }
            },
            'WIC': {
                'name': 'Women, Infants & Children Program',
                'description': 'Nutrition program for pregnant women and children',
                'processing_time': '1-2 weeks',
                'contact': '1-800-942-3678',
                'website': 'https://myfamily.wic.ca.gov/',
                'required_documents': [
                    'Photo identification',
                    'Proof of income',
                    'Proof of residence',
                    'Medical records (pregnancy verification)',
                    'Children\'s immunization records'
                ],
                'estimated_benefits': None  # Food packages
            },
            'LIHEAP': {
                'name': 'Low Income Home Energy Assistance',
                'description': 'Utility bill assistance',
                'processing_time': '2-4 weeks',
                'contact': 'Local Energy Assistance Office',
                'website': 'https://www.liheapca.com/',
                'required_documents': [
                    'Photo identification',
                    'Proof of income',
                    'Utility bills',
                    'Proof of residence',
                    'Social Security cards'
                ],
                'estimated_benefits': None  # Varies by need
            }
        }
    
    def get_program_questions(self, program: str) -> List[Dict[str, Any]]:
        """Get assessment questions for a specific program"""
        try:
            if program not in self.questions_data:
                logger.warning(f"No questions found for program: {program}")
                return []
            
            questions = []
            for i, q_data in enumerate(self.questions_data[program]):
                # Find corresponding criteria for this question
                criteria = None
                if program in self.criteria_data:
                    for c in self.criteria_data[program]:
                        if self._questions_match(q_data['question'], c['question']):
                            criteria = c
                            break
                
                question = {
                    'id': f"{program}_{i}",
                    'program': program,
                    'category': q_data['category'],
                    'question': q_data['question'],
                    'type': q_data['type'],
                    'purpose': q_data['purpose'],
                    'required': True,
                    'options': self._generate_question_options(q_data['type'], criteria),
                    'validation': self._get_validation_rules(q_data['type']),
                    'help_text': criteria['notes'] if criteria else ''
                }
                if question['type'] == 'Multiple Choice' and not question['options']:
                    question['options'] = self._fallback_options_for_question(question['question'])
                questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions for {program}: {e}")
            return []
    
    def _questions_match(self, q1: str, q2: str) -> bool:
        """Check if two questions are similar enough to be the same"""
        # Simple matching - could be enhanced with fuzzy matching
        q1_clean = self._normalize_question(q1)
        q2_clean = self._normalize_question(q2)
        
        # Check if questions contain similar key phrases
        q1_words = set(q1_clean.split())
        q2_words = set(q2_clean.split())
        
        # If 70% of words match, consider them the same question
        if len(q1_words) > 0 and len(q2_words) > 0:
            intersection = q1_words.intersection(q2_words)
            union = q1_words.union(q2_words)
            similarity = len(intersection) / len(union)
            return similarity > 0.7
        
        return False
    
    def _generate_question_options(self, question_type: str, criteria: Optional[Dict]) -> List[Dict[str, Any]]:
        """Generate answer options based on question type and criteria"""
        if question_type == 'Yes/No':
            return [
                {'value': 'yes', 'label': 'Yes'},
                {'value': 'no', 'label': 'No'}
            ]
        elif question_type == 'Multiple Choice':
            if criteria:
                options = []
                # Extract options from qualifying answers
                for answer in criteria['qualifying_answers']:
                    if answer and answer != 'None':
                        options.append({'value': answer.lower().replace(' ', '_'), 'label': answer})
                return options
            return []
        elif question_type in ['Number', 'Currency']:
            return []  # No predefined options for numeric inputs
        elif question_type == 'Percentage':
            return []  # No predefined options for percentage inputs
        else:
            return []

    def _fallback_options_for_question(self, question_text: str) -> List[Dict[str, Any]]:
        """Provide sensible defaults when criteria-driven options are missing"""
        text = (question_text or "").lower()

        if 'citizen' in text or 'immigration' in text:
            return [
                {'value': 'us_citizen', 'label': 'U.S. citizen'},
                {'value': 'qualified_non_citizen', 'label': 'Qualified non-citizen'},
                {'value': 'other', 'label': 'Other or unknown'}
            ]

        if '65' in text and 'blind' in text and 'disabled' in text:
            return [
                {'value': 'age_65_or_older', 'label': 'Age 65 or older'},
                {'value': 'blind', 'label': 'Blind'},
                {'value': 'disabled', 'label': 'Disabled'},
                {'value': 'none', 'label': 'None of the above'}
            ]

        if 'receive' in text or 'currently receive' in text:
            return [
                {'value': 'yes', 'label': 'Yes'},
                {'value': 'no', 'label': 'No'}
            ]

        return []
    
    def _get_validation_rules(self, question_type: str) -> Dict[str, Any]:
        """Get validation rules for different question types"""
        if question_type == 'Number':
            return {'type': 'number', 'min': 0}
        elif question_type == 'Currency':
            return {'type': 'number', 'min': 0, 'step': 0.01}
        elif question_type == 'Percentage':
            return {'type': 'number', 'min': 0, 'max': 100}
        else:
            return {}
    
    def assess_program_eligibility(self, program: str, client_id: str, responses: Dict[str, Any]) -> AssessmentResult:
        """Assess eligibility for a specific program"""
        try:
            logger.info(f"Assessing {program} eligibility for client {client_id}")

            if program not in self.criteria_data:
                return self._create_error_result(program, client_id, f"No criteria found for program: {program}")

            self._active_program = program
            self._active_responses = responses

            qualifying_factors = []
            disqualifying_factors = []
            missing_information = []
            confidence_score = 0.0
            total_questions = len(self.criteria_data[program])
            answered_questions = 0
            
            # Evaluate each criterion
            question_id_map = self._build_question_id_map(program)
            for criterion in self.criteria_data[program]:
                question = criterion['question']
                qualifying_answers = criterion['qualifying_answers']
                disqualifying_answers = criterion['disqualifying_answers']
                
                # Find matching response
                response_value = self._find_matching_response(question, responses, question_id_map)
                
                if response_value is None:
                    missing_information.append(question)
                    continue
                
                answered_questions += 1
                
                # Check if response is disqualifying
                if self._response_matches_criteria(response_value, disqualifying_answers):
                    disqualifying_factors.append(f"{question}: {response_value}")
                    continue
                
                # Check if response is qualifying
                if self._response_matches_criteria(response_value, qualifying_answers):
                    qualifying_factors.append(f"{question}: {response_value}")
                    confidence_score += 1.0
            
            # Calculate final confidence score
            if answered_questions > 0:
                confidence_score = (confidence_score / answered_questions) * 100
            
            # Determine eligibility status
            status = self._determine_eligibility_status(
                qualifying_factors,
                disqualifying_factors,
                missing_information,
                confidence_score,
                answered_questions
            )
            
            # Generate next steps and required documents
            next_steps = self._generate_next_steps(program, status, disqualifying_factors, missing_information)
            required_documents = self.program_configs.get(program, {}).get('required_documents', [])
            
            # Estimate benefit amount
            estimated_benefit = self._estimate_benefit_amount(program, responses)
            
            # Get processing timeline
            processing_timeline = self.program_configs.get(program, {}).get('processing_time', 'Unknown')
            
            return AssessmentResult(
                program=program,
                client_id=client_id,
                status=status,
                confidence_score=confidence_score,
                qualifying_factors=qualifying_factors,
                disqualifying_factors=disqualifying_factors,
                missing_information=missing_information,
                next_steps=next_steps,
                required_documents=required_documents,
                estimated_benefit_amount=estimated_benefit,
                processing_timeline=processing_timeline,
                assessment_data=responses,
                created_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error assessing {program} eligibility: {e}")
            return self._create_error_result(program, client_id, str(e))
    
    def _find_matching_response(
        self,
        question: str,
        responses: Dict[str, Any],
        question_id_map: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """Find the response that matches a given question"""
        # Try exact match first
        if question in responses:
            return str(responses[question])

        if question_id_map:
            normalized = self._normalize_question(question)
            question_id = question_id_map.get(normalized)
            if question_id and question_id in responses:
                return str(responses[question_id])
        
        # Try to find by question ID or similar key
        for key, value in responses.items():
            if self._questions_match(question, key):
                return str(value)
        
        return None
    
    def _response_matches_criteria(self, response: str, criteria_answers: List[str]) -> bool:
        """Check if a response matches any of the criteria answers"""
        if not criteria_answers or not response:
            return False
        
        response_lower = response.lower().strip()
        response_norm = self._normalize_answer(response_lower)
        
        for criteria in criteria_answers:
            if not criteria or criteria.lower().strip() == 'none':
                continue
            
            criteria_lower = criteria.lower().strip()
            criteria_norm = self._normalize_answer(criteria_lower)

            if criteria_lower in ['any', 'any number', 'any amount', 'any size', 'any value', 'n/a', 'na']:
                return True
            if any(token in criteria_lower for token in ['any number', 'any amount', 'any size', 'any value']):
                return True
            
            # Direct match
            if response_lower == criteria_lower:
                return True
            if response_norm and criteria_norm and response_norm == criteria_norm:
                return True
            if response_norm and criteria_norm and response_norm not in ['yes', 'no'] and response_norm in criteria_norm:
                return True
            
            # Check for partial matches or patterns
            if self._matches_yes_no(response_lower, criteria_lower):
                return True
            
            # Check for numeric ranges or comparisons
            if self._check_numeric_criteria(response, criteria):
                return True
        
        return False

    def _matches_yes_no(self, response_lower: str, criteria_lower: str) -> bool:
        """Match yes/no responses while avoiding complex condition traps"""
        if response_lower in ['true', '1']:
            response_lower = 'yes'
        if response_lower in ['false', '0']:
            response_lower = 'no'

        if response_lower not in ['yes', 'no']:
            return False

        criteria_norm = criteria_lower.strip()
        if criteria_norm in ['yes', 'no']:
            return criteria_norm == response_lower

        if criteria_norm.startswith((f"{response_lower} ", f"{response_lower}(", f"{response_lower}-", f"{response_lower} -")):
            if any(token in criteria_norm for token in [' and ', ' or ', ' without ', ' unless ', ' not working', ' no exemption', ' without qualifying', ' without exemption']):
                return False
            return True

        return False
    
    def _check_numeric_criteria(self, response: str, criteria: str) -> bool:
        """Check if numeric response meets criteria"""
        try:
            if not criteria:
                return False

            criteria_lower = criteria.lower().strip()
            if criteria_lower in ['any', 'any number', 'any amount', 'any size', 'any value', 'n/a', 'na']:
                return True
            if any(token in criteria_lower for token in ['any number', 'any amount', 'any size', 'any value']):
                return True

            response_match = re.findall(r'-?\d+(?:\.\d+)?', response)
            if not response_match:
                return False
            response_num = float(response_match[0])

            criteria_numbers = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?', criteria)]

            if ('%' in criteria_lower or 'fpl' in criteria_lower) and response_num > 300:
                household_size = self._get_household_size_response(self._active_program, self._active_responses)
                fpl_monthly = self._fpl_monthly_for_household(household_size or 1)
                if fpl_monthly:
                    response_num = (response_num / fpl_monthly) * 100

            if ('%' in criteria_lower or 'fpl' in criteria_lower) and response_num > 300:
                return False

            if 'between' in criteria_lower and len(criteria_numbers) >= 2:
                low, high = criteria_numbers[0], criteria_numbers[1]
                return low <= response_num <= high

            if '-' in criteria_lower and len(criteria_numbers) >= 2:
                low, high = criteria_numbers[0], criteria_numbers[1]
                return low <= response_num <= high

            if '<=' in criteria or 'at or below' in criteria_lower or 'no more than' in criteria_lower or 'up to' in criteria_lower or 'not more than' in criteria_lower:
                return bool(criteria_numbers) and response_num <= criteria_numbers[0]

            if '>=' in criteria or 'at least' in criteria_lower or 'no less than' in criteria_lower:
                return bool(criteria_numbers) and response_num >= criteria_numbers[0]

            if '+' in criteria_lower and criteria_numbers:
                return response_num >= criteria_numbers[0]

            if '<' in criteria or 'less than' in criteria_lower or 'under' in criteria_lower or 'below' in criteria_lower:
                return bool(criteria_numbers) and response_num < criteria_numbers[0]

            if '>' in criteria or 'more than' in criteria_lower or 'over' in criteria_lower or 'greater than' in criteria_lower:
                return bool(criteria_numbers) and response_num > criteria_numbers[0]

        except (ValueError, IndexError):
            return False

        return False

    def _normalize_question(self, question: str) -> str:
        """Normalize question text for matching against response keys"""
        if not question:
            return ""
        return re.sub(r'[^\w\s]', '', question.lower()).strip()

    def _normalize_answer(self, answer: str) -> str:
        """Normalize answer text for matching against criteria"""
        if not answer:
            return ""
        return re.sub(r'[^\w\s]', '', answer.lower().replace('_', ' ')).strip()

    def _split_answers(self, raw: str) -> List[str]:
        """Split qualifying/disqualifying answers without breaking comma clauses"""
        if not raw:
            return []
        cleaned = raw.replace(' OR ', ';').replace(' or ', ';')
        parts = []
        for chunk in cleaned.split(';'):
            part = chunk.strip()
            if part:
                parts.append(part)
        return parts

    def _build_question_id_map(self, program: str) -> Dict[str, str]:
        """Build mapping of normalized question text to question id"""
        question_id_map = {}
        for i, q_data in enumerate(self.questions_data.get(program, [])):
            normalized = self._normalize_question(q_data.get('question', ''))
            if normalized:
                question_id_map[normalized] = f"{program}_{i}"
        return question_id_map
    
    def _determine_eligibility_status(
        self,
        qualifying_factors: List[str],
        disqualifying_factors: List[str],
        missing_information: List[str],
        confidence_score: float,
        answered_questions: int
    ) -> EligibilityStatus:
        """Determine overall eligibility status"""
        if disqualifying_factors:
            return EligibilityStatus.NOT_ELIGIBLE

        if answered_questions == 0:
            return EligibilityStatus.NEEDS_REVIEW

        if confidence_score >= 80:
            return EligibilityStatus.ELIGIBLE
        elif confidence_score >= 60:
            return EligibilityStatus.PARTIALLY_ELIGIBLE
        else:
            if missing_information:
                return EligibilityStatus.NEEDS_REVIEW
            return EligibilityStatus.PARTIALLY_ELIGIBLE
    
    def _generate_next_steps(self, program: str, status: EligibilityStatus, 
                           disqualifying_factors: List[str], missing_information: List[str]) -> List[str]:
        """Generate next steps based on assessment results"""
        next_steps = []
        
        if status == EligibilityStatus.ELIGIBLE:
            next_steps.extend([
                "Gather required documentation",
                "Complete formal application",
                "Schedule interview if required",
                "Submit application to appropriate office"
            ])
        elif status == EligibilityStatus.PARTIALLY_ELIGIBLE:
            next_steps.extend([
                "Provide missing information",
                "Consult with case manager for guidance",
                "Consider alternative programs if available"
            ])
            if missing_information:
                next_steps.append(f"Complete assessment for: {', '.join(missing_information[:3])}")
        elif status == EligibilityStatus.NOT_ELIGIBLE:
            next_steps.extend([
                "Review disqualifying factors with case manager",
                "Explore alternative benefit programs",
                "Consider reapplying when circumstances change"
            ])
        else:  # NEEDS_REVIEW
            next_steps.extend([
                "Schedule consultation with case manager",
                "Provide additional documentation",
                "Complete full eligibility interview"
            ])
        
        return next_steps
    
    def _estimate_benefit_amount(self, program: str, responses: Dict[str, Any]) -> Optional[float]:
        """Estimate potential benefit amount based on responses"""
        try:
            config = self.program_configs.get(program, {})
            estimated_benefits = config.get('estimated_benefits')
            
            if not estimated_benefits:
                return None
            
            # For programs with household size-based benefits
            if isinstance(estimated_benefits, dict):
                household_size = responses.get('household_size')
                if household_size is None:
                    household_size = self._get_household_size_response(program, responses)
                if household_size is None:
                    return None
                household_size = int(household_size)
                return estimated_benefits.get(household_size, estimated_benefits.get(max(estimated_benefits.keys())))
            
            # For SSI individual/couple rates
            if program == 'SSI':
                marital_status = responses.get('marital_status', 'single')
                if 'married' in marital_status.lower():
                    return estimated_benefits.get('couple')
                else:
                    return estimated_benefits.get('individual')
            
            return None
            
        except Exception as e:
            logger.error(f"Error estimating benefit amount for {program}: {e}")
            return None

    def _get_household_size_response(self, program: str, responses: Dict[str, Any]) -> Optional[int]:
        """Extract household size from responses keyed by question id"""
        question_id_map = self._build_question_id_map(program)
        for question_text, question_id in question_id_map.items():
            if 'household' in question_text and ('how many' in question_text or 'people' in question_text):
                if question_id in responses:
                    try:
                        return int(float(responses[question_id]))
                    except (TypeError, ValueError):
                        return None
        return None

    def _fpl_monthly_for_household(self, household_size: int) -> Optional[float]:
        """Approximate monthly FPL for household size (2025 baseline)"""
        if household_size <= 0:
            return None
        base = 1580
        increment = 557
        if household_size <= 8:
            return base + increment * (household_size - 1)
        return base + increment * (household_size - 1)
    
    def _create_error_result(self, program: str, client_id: str, error_message: str) -> AssessmentResult:
        """Create an error result for failed assessments"""
        return AssessmentResult(
            program=program,
            client_id=client_id,
            status=EligibilityStatus.NEEDS_REVIEW,
            confidence_score=0.0,
            qualifying_factors=[],
            disqualifying_factors=[f"Assessment error: {error_message}"],
            missing_information=[],
            next_steps=["Contact case manager for assistance"],
            required_documents=[],
            estimated_benefit_amount=None,
            processing_timeline="Unknown",
            assessment_data={},
            created_at=datetime.now().isoformat()
        )
    
    def bulk_eligibility_assessment(self, client_id: str, responses: Dict[str, Any]) -> Dict[str, AssessmentResult]:
        """Assess eligibility for multiple programs simultaneously"""
        results = {}
        
        for program in self.program_configs.keys():
            try:
                result = self.assess_program_eligibility(program, client_id, responses)
                results[program] = result
            except Exception as e:
                logger.error(f"Error in bulk assessment for {program}: {e}")
                results[program] = self._create_error_result(program, client_id, str(e))
        
        return results
    
    def get_available_programs(self) -> List[Dict[str, Any]]:
        """Get list of all available programs with their configurations"""
        programs = []
        
        for program_key, config in self.program_configs.items():
            programs.append({
                'key': program_key,
                'name': config['name'],
                'description': config['description'],
                'processing_time': config['processing_time'],
                'contact': config['contact'],
                'website': config.get('website', ''),
                'has_assessment': program_key in self.questions_data
            })
        
        return programs
    
    def get_program_questions(self, program: str) -> List[Dict[str, Any]]:
        """Get assessment questions for a specific program"""
        if program in self.questions_data:
            questions = self.questions_data[program]
            
            # Format questions for frontend consumption
            formatted_questions = []
            for i, question_data in enumerate(questions):
                formatted_question = {
                    'id': f"{program}_{i}",
                    'program': program,
                    'category': question_data.get('category', 'General'),
                    'question': question_data.get('question', ''),
                    'type': question_data.get('type', 'Text'),
                    'purpose': question_data.get('purpose', ''),
                    'help_text': question_data.get('help_text', ''),
                    'options': question_data.get('options', [])
                }
                
                # Add options for specific question types
                if formatted_question['type'] == 'Yes/No':
                    formatted_question['options'] = [
                        {'value': 'yes', 'label': 'Yes'},
                        {'value': 'no', 'label': 'No'}
                    ]
                elif formatted_question['type'] == 'Multiple Choice' and not formatted_question['options']:
                    # Try to extract options from criteria data if available
                    if program in self.criteria_data:
                        for criterion in self.criteria_data[program]:
                            if criterion['question'].lower() in question_data.get('question', '').lower():
                                qualifying_answers = criterion.get('qualifying_answers', [])
                                if qualifying_answers and qualifying_answers != ['None']:
                                    formatted_question['options'] = [
                                        {'value': ans.lower().replace(' ', '_'), 'label': ans}
                                        for ans in qualifying_answers if ans and ans != 'None'
                                    ]
                                break
                    if not formatted_question['options']:
                        formatted_question['options'] = self._fallback_options_for_question(
                            formatted_question['question']
                        )

                if formatted_question['type'] == 'Multiple Choice' and '65' in formatted_question['question'].lower() and 'blind' in formatted_question['question'].lower() and 'disabled' in formatted_question['question'].lower():
                    formatted_question['options'] = self._fallback_options_for_question(
                        formatted_question['question']
                    )
                
                formatted_questions.append(formatted_question)
            
            return formatted_questions
        else:
            return []

# Global instance
_eligibility_engine = None

def get_eligibility_engine() -> UniversalEligibilityEngine:
    """Get singleton instance of eligibility engine"""
    global _eligibility_engine
    if _eligibility_engine is None:
        _eligibility_engine = UniversalEligibilityEngine()
    return _eligibility_engine
