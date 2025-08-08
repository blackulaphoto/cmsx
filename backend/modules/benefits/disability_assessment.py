#!/usr/bin/env python3
"""
Disability Eligibility Assessment System for Second Chance Jobs Platform
Comprehensive SSI/SSDI assessment based on SSA guidelines
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DisabilityCondition:
    """Represents a medical condition that may qualify for disability benefits"""
    name: str
    category: str  # Physical, Mental, Sensory, etc.
    ssa_listing: str  # Social Security Administration disability listing number
    description: str
    severity_criteria: List[str]
    documentation_required: List[str]
    typical_approval_rate: float  # Percentage

# Enhanced disability criteria loader
def load_disability_criteria():
    """Load disability criteria from resource files"""
    criteria_dir = os.path.join(os.path.dirname(__file__), 'DISABILITY')
    disability_criteria = {}
    
    if os.path.exists(criteria_dir):
        for filename in os.listdir(criteria_dir):
            if filename.endswith('.txt'):
                try:
                    filepath = os.path.join(criteria_dir, filename)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Parse the content and extract key information
                        if 'MUSCLOSKELETAL' in filename.upper():
                            disability_criteria['musculoskeletal_detailed'] = content
                        elif 'MENTAL' in filename.upper():
                            disability_criteria['mental_disorders_detailed'] = content
                        elif 'CARDIOVASCULAR' in filename.upper():
                            disability_criteria['cardiovascular_detailed'] = content
                        elif 'VISION' in filename.upper():
                            disability_criteria['vision_impairment_detailed'] = content
                        elif 'RESPIRATORY' in filename.upper() or 'RESPITORY' in filename.upper():
                            disability_criteria['respiratory_detailed'] = content
                        elif 'DIGESTIVE' in filename.upper():
                            disability_criteria['digestive_detailed'] = content
                        elif 'NEUROLOGICAL' in filename.upper():
                            disability_criteria['neurological_detailed'] = content
                        elif 'ENDOCRINE' in filename.upper():
                            disability_criteria['endocrine_detailed'] = content
                        elif 'CANCER' in filename.upper():
                            disability_criteria['cancer_detailed'] = content
                        elif 'IMMUNE' in filename.upper():
                            disability_criteria['immune_detailed'] = content
                        elif 'SKIN' in filename.upper():
                            disability_criteria['skin_detailed'] = content
                        elif 'GENITOURINY' in filename.upper():
                            disability_criteria['genitourinary_detailed'] = content
                        elif 'HERMITOLOGICAL' in filename.upper():
                            disability_criteria['hematological_detailed'] = content
                        elif 'CONGENIAL' in filename.upper():
                            disability_criteria['congenital_detailed'] = content
                except Exception as e:
                    logger.warning(f"Could not load {filename}: {e}")
    
    return disability_criteria

# Load detailed criteria from resource files
DETAILED_CRITERIA = load_disability_criteria()

# SSA Blue Book Listings - Enhanced Qualifying Conditions with Detailed Criteria
QUALIFYING_CONDITIONS = {
    # Musculoskeletal System (1.00)
    "chronic_back_pain": DisabilityCondition(
        name="Chronic Back Pain / Spinal Disorders",
        category="Musculoskeletal",
        ssa_listing="1.15 - 1.16",
        description="Chronic pain and limited mobility due to spinal disorders",
        severity_criteria=[
            "Unable to walk effectively (requires assistive device)",
            "Unable to perform fine and gross motor movements effectively",
            "Chronic pain causing significant functional limitation",
            "Medical imaging showing significant structural abnormalities"
        ],
        documentation_required=[
            "MRI or CT scans of spine",
            "X-rays showing structural damage",
            "Physical therapy records",
            "Pain management treatment records",
            "Orthopedic or neurosurgeon evaluations",
            "Functional capacity evaluation"
        ],
        typical_approval_rate=0.32
    ),
    
    "vision_impairment": DisabilityCondition(
        name="Vision Impairment / Blindness",
        category="Sensory",
        ssa_listing="2.02 - 2.04",
        description="Significant vision loss affecting ability to work",
        severity_criteria=[
            "Visual acuity of 20/200 or worse in better eye with correction",
            "Visual field limitation to 20 degrees or less in better eye",
            "Unable to perform work-related visual tasks"
        ],
        documentation_required=[
            "Ophthalmologist examination reports",
            "Visual field testing results",
            "Visual acuity measurements",
            "Retinal photography or OCT scans",
            "Low vision rehabilitation records"
        ],
        typical_approval_rate=0.89  # Higher approval rate for severe vision loss
    ),
    
    # Mental Disorders (12.00)
    "depression_anxiety": DisabilityCondition(
        name="Depression and Anxiety Disorders",
        category="Mental Health",
        ssa_listing="12.04 - 12.06",
        description="Severe depression or anxiety significantly limiting function",
        severity_criteria=[
            "Marked limitation in understanding, remembering, or applying information",
            "Marked limitation in interacting with others",
            "Marked limitation in concentrating, persisting, or maintaining pace",
            "Marked limitation in adapting or managing oneself"
        ],
        documentation_required=[
            "Psychiatric evaluation reports",
            "Psychological testing results",
            "Therapy session notes",
            "Medication records and side effects",
            "Hospitalization records",
            "Function assessment questionnaires"
        ],
        typical_approval_rate=0.25
    ),
    
    "ptsd": DisabilityCondition(
        name="Post-Traumatic Stress Disorder (PTSD)",
        category="Mental Health",
        ssa_listing="12.15",
        description="PTSD significantly limiting daily functioning",
        severity_criteria=[
            "Intrusive recollections or re-experiencing trauma",
            "Avoidance of trauma-related stimuli",
            "Disturbance in mood and cognition",
            "Marked alterations in arousal and reactivity"
        ],
        documentation_required=[
            "PTSD diagnosis from qualified mental health professional",
            "Therapy records documenting symptoms",
            "PTSD assessment scale results",
            "Medication management records",
            "VA records (if veteran)",
            "Functional capacity evaluation for mental health"
        ],
        typical_approval_rate=0.35
    ),
    
    # Cardiovascular System (4.00)
    "heart_disease": DisabilityCondition(
        name="Cardiovascular Disease",
        category="Cardiovascular",
        ssa_listing="4.02 - 4.04",
        description="Heart conditions limiting physical capacity",
        severity_criteria=[
            "Chronic heart failure with symptoms at rest or minimal activity",
            "Ischemic heart disease with significant limitations",
            "Unable to perform sustained physical activity"
        ],
        documentation_required=[
            "Cardiology consultation reports",
            "Echocardiogram results",
            "Stress test results",
            "EKG recordings",
            "Cardiac catheterization results",
            "Exercise tolerance testing"
        ],
        typical_approval_rate=0.45
    ),
    
    # Additional common conditions
    "diabetes_complications": DisabilityCondition(
        name="Diabetes with Complications",
        category="Endocrine",
        ssa_listing="9.08",
        description="Diabetes with severe complications affecting multiple systems",
        severity_criteria=[
            "Diabetic neuropathy causing significant functional limitations",
            "Diabetic retinopathy with vision loss",
            "Diabetic nephropathy with kidney dysfunction",
            "Poor glucose control despite treatment compliance"
        ],
        documentation_required=[
            "Endocrinologist treatment records",
            "HbA1c test results over time",
            "Ophthalmology records",
            "Nephrology records",
            "Neurological testing for neuropathy"
        ],
        typical_approval_rate=0.38
    ),
    
    # Respiratory System (3.00)
    "chronic_respiratory_disorders": DisabilityCondition(
        name="Chronic Respiratory Disorders",
        category="Respiratory",
        ssa_listing="3.02 - 3.04",
        description="Chronic respiratory impairments including COPD, asthma, pulmonary fibrosis",
        severity_criteria=[
            "FEV1 equal to or less than specified values based on height",
            "Requires supplemental oxygen",
            "Frequent exacerbations requiring hospitalization",
            "Cor pulmonale (right heart failure) due to chronic pulmonary disease"
        ],
        documentation_required=[
            "Pulmonary function tests",
            "Arterial blood gas studies",
            "Chest x-rays and CT scans",
            "Hospitalization records for exacerbations",
            "Oxygen saturation monitoring"
        ],
        typical_approval_rate=0.55
    ),
    
    # Digestive System (5.00)
    "inflammatory_bowel_disease": DisabilityCondition(
        name="Inflammatory Bowel Disease",
        category="Digestive",
        ssa_listing="5.06",
        description="IBD including Crohn's disease and ulcerative colitis with severe limitations",
        severity_criteria=[
            "Two or more hospitalizations within a consecutive 6-month period",
            "Obstruction, bleeding, perforation, or abscess formation",
            "Need for supplemental daily enteral nutrition via gastrostomy",
            "Weight loss with BMI of less than 17.5"
        ],
        documentation_required=[
            "Gastroenterology consultation reports",
            "Endoscopy and colonoscopy reports",
            "Hospitalization records",
            "Nutritional assessments",
            "Imaging studies (CT, MRI)"
        ],
        typical_approval_rate=0.42
    ),
    
    # Genitourinary Disorders (6.00)
    "chronic_kidney_disease": DisabilityCondition(
        name="Chronic Kidney Disease",
        category="Genitourinary",
        ssa_listing="6.02",
        description="Chronic kidney disease requiring dialysis or with severe impairment",
        severity_criteria=[
            "Chronic hemodialysis or peritoneal dialysis",
            "Kidney transplantation",
            "Chronic kidney disease with specific lab values",
            "Complications of chronic kidney disease"
        ],
        documentation_required=[
            "Nephrology treatment records",
            "Dialysis records",
            "Laboratory results (creatinine, BUN, GFR)",
            "Transplant records if applicable",
            "Complications documentation"
        ],
        typical_approval_rate=0.73
    ),
    
    # Hematological Disorders (7.00)
    "chronic_anemia": DisabilityCondition(
        name="Chronic Anemia",
        category="Hematological",
        ssa_listing="7.02",
        description="Chronic anemia with severe fatigue and functional limitations",
        severity_criteria=[
            "Hemoglobin values consistently below specified levels",
            "Requires frequent blood transfusions",
            "Fatigue significantly limiting daily activities",
            "Complications from underlying cause"
        ],
        documentation_required=[
            "Hematology consultation reports",
            "Serial CBC results",
            "Transfusion records",
            "Bone marrow studies if performed",
            "Iron studies and B12/folate levels"
        ],
        typical_approval_rate=0.35
    ),
    
    # Skin Disorders (8.00)
    "chronic_skin_disorders": DisabilityCondition(
        name="Chronic Skin Disorders",
        category="Dermatological",
        ssa_listing="8.04 - 8.06",
        description="Chronic skin disorders with extensive lesions affecting function",
        severity_criteria=[
            "Extensive skin lesions that persist despite treatment",
            "Affects ability to use hands or walk effectively",
            "Requires intensive treatment regimen",
            "Associated with systemic complications"
        ],
        documentation_required=[
            "Dermatology consultation reports",
            "Photographs of skin lesions",
            "Treatment records and medication history",
            "Biopsy results if performed",
            "Functional capacity assessments"
        ],
        typical_approval_rate=0.28
    ),
    
    # Neurological Disorders (11.00)
    "epilepsy": DisabilityCondition(
        name="Epilepsy",
        category="Neurological",
        ssa_listing="11.02",
        description="Epilepsy with frequent seizures despite medication compliance",
        severity_criteria=[
            "Generalized tonic-clonic seizures occurring at least once a month",
            "Dyscognitive seizures occurring at least once a week",
            "Seizures not controlled by medication",
            "Significant cognitive or behavioral changes"
        ],
        documentation_required=[
            "Neurologist consultation reports",
            "EEG results",
            "Seizure diary or witness statements",
            "Medication compliance records",
            "Neuropsychological testing"
        ],
        typical_approval_rate=0.62
    ),
    
    "multiple_sclerosis": DisabilityCondition(
        name="Multiple Sclerosis",
        category="Neurological", 
        ssa_listing="11.09",
        description="Multiple sclerosis with significant functional limitations",
        severity_criteria=[
            "Disorganization of motor function in two extremities",
            "Significant and persistent disorganization of motor function",
            "Visual or mental impairments",
            "Limitation of activities of daily living"
        ],
        documentation_required=[
            "Neurologist treatment records",
            "MRI scan results",
            "Functional capacity evaluation",
            "Occupational therapy assessments",
            "Medical history documenting progression"
        ],
        typical_approval_rate=0.68
    ),
    
    # Cancer (13.00) 
    "malignant_neoplasms": DisabilityCondition(
        name="Malignant Neoplasms (Cancer)",
        category="Neoplastic",
        ssa_listing="13.00 - 13.29",
        description="Various forms of cancer with significant impact on functioning",
        severity_criteria=[
            "Inoperable or unresectable cancer",
            "Recurrent cancer despite treatment",
            "Cancer with distant metastases",
            "Undergoing or recovery from intensive treatment"
        ],
        documentation_required=[
            "Oncology treatment records",
            "Pathology reports",
            "Staging and imaging studies",
            "Treatment records (chemo, radiation)",
            "Surgical reports if applicable"
        ],
        typical_approval_rate=0.87
    ),
    
    # Immune System Disorders (14.00)
    "lupus": DisabilityCondition(
        name="Systemic Lupus Erythematosus",
        category="Immune System",
        ssa_listing="14.02",
        description="Systemic lupus with multi-organ involvement",
        severity_criteria=[
            "Involvement of two or more organ/body systems",
            "At least one of the involved organ/body systems must be involved to at least a moderate level of severity",
            "Symptoms or signs of severe fatigue, fever, malaise, or involuntary weight loss",
            "Limitation of activities of daily living"
        ],
        documentation_required=[
            "Rheumatology consultation reports",
            "Laboratory results (ANA, anti-DNA, complement levels)",
            "Organ-specific testing based on involvement",
            "Treatment records and medication history",
            "Functional capacity assessments"
        ],
        typical_approval_rate=0.71
    )
}

class DisabilityAssessment:
    """Comprehensive disability eligibility assessment"""
    
    def __init__(self):
        self.conditions = QUALIFYING_CONDITIONS
    
    def assess_eligibility(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess client eligibility for SSI/SSDI based on their profile
        
        Args:
            client_data: Dictionary containing client information
            
        Returns:
            Assessment results with recommendations
        """
        try:
            # Extract client information
            age = client_data.get('age', 0)
            medical_conditions = client_data.get('medical_conditions', [])
            work_history = client_data.get('work_history', [])
            current_income = client_data.get('current_income', 0)
            years_out_of_work = client_data.get('years_out_of_work', 0)
            
            # Calculate work credits for SSDI
            work_credits = self._calculate_work_credits(work_history, age)
            
            # Assess medical eligibility
            medical_assessment = self._assess_medical_conditions(medical_conditions)
            
            # Determine program eligibility
            ssi_eligible = self._assess_ssi_eligibility(age, current_income, medical_assessment)
            ssdi_eligible = self._assess_ssdi_eligibility(age, work_credits, medical_assessment)
            
            return {
                'client_assessment': {
                    'age': age,
                    'years_out_of_work': years_out_of_work,
                    'work_credits': work_credits,
                    'current_income': current_income
                },
                'medical_assessment': medical_assessment,
                'ssi_eligibility': ssi_eligible,
                'ssdi_eligibility': ssdi_eligible,
                'recommendations': self._generate_recommendations(ssi_eligible, ssdi_eligible, medical_assessment),
                'next_steps': self._generate_next_steps(ssi_eligible, ssdi_eligible),
                'estimated_timeline': self._estimate_timeline(medical_assessment),
                'required_documentation': self._get_required_documentation(medical_conditions)
            }
            
        except Exception as e:
            logger.error(f"Error in disability assessment: {e}")
            return {
                'error': str(e),
                'success': False
            }
    
    def _calculate_work_credits(self, work_history: List[Dict], age: int) -> Dict[str, Any]:
        """Calculate Social Security work credits"""
        total_years_worked = len([job for job in work_history if job.get('years_worked', 0) > 0])
        
        # Simplified calculation - in reality this would be more complex
        estimated_credits = min(total_years_worked * 4, 40)  # Max 40 credits
        
        # Credits needed for SSDI based on age
        if age < 24:
            credits_needed = 6
        elif age < 31:
            credits_needed = (age - 21) * 2
        else:
            credits_needed = min(40, (age - 22) * 2)
        
        return {
            'estimated_credits': estimated_credits,
            'credits_needed': credits_needed,
            'has_sufficient_credits': estimated_credits >= credits_needed,
            'years_worked': total_years_worked
        }
    
    def _assess_medical_conditions(self, medical_conditions: List[str]) -> Dict[str, Any]:
        """Assess medical conditions against SSA criteria with enhanced matching"""
        matching_conditions = []
        total_approval_probability = 0
        condition_categories = {}
        
        for condition_name in medical_conditions:
            condition_key = condition_name.lower().replace(' ', '_').replace('-', '_')
            
            # Direct match
            if condition_key in self.conditions:
                condition = self.conditions[condition_key]
                matching_conditions.append({
                    'name': condition.name,
                    'category': condition.category,
                    'ssa_listing': condition.ssa_listing,
                    'approval_rate': condition.typical_approval_rate,
                    'documentation_required': condition.documentation_required,
                    'severity_criteria': condition.severity_criteria,
                    'match_type': 'direct'
                })
                condition_categories[condition.category] = condition_categories.get(condition.category, 0) + 1
                
            else:
                # Fuzzy matching for partial matches
                partial_match = self._find_partial_condition_match(condition_name)
                if partial_match:
                    matching_conditions.append({
                        'name': partial_match.name,
                        'category': partial_match.category,
                        'ssa_listing': partial_match.ssa_listing,
                        'approval_rate': partial_match.typical_approval_rate * 0.8,  # Reduced for partial match
                        'documentation_required': partial_match.documentation_required,
                        'severity_criteria': partial_match.severity_criteria,
                        'match_type': 'partial',
                        'original_condition': condition_name
                    })
                    condition_categories[partial_match.category] = condition_categories.get(partial_match.category, 0) + 1
        
        # Calculate overall probability with category bonuses
        if matching_conditions:
            max_approval_rate = max([c['approval_rate'] for c in matching_conditions])
            
            # Bonus for multiple conditions in same category (comorbidity)
            category_bonus = 0
            for category, count in condition_categories.items():
                if count > 1:
                    category_bonus += 0.05 * (count - 1)  # 5% bonus per additional condition in category
            
            # Bonus for multiple body systems affected
            multi_system_bonus = 0.03 * max(0, len(condition_categories) - 1)
            
            final_approval_rate = min(max_approval_rate + category_bonus + multi_system_bonus, 0.95)
        else:
            final_approval_rate = 0.15  # Base rate for unlisted conditions
        
        return {
            'matching_conditions': matching_conditions,
            'has_qualifying_conditions': len(matching_conditions) > 0,
            'estimated_approval_probability': final_approval_rate,
            'condition_count': len(matching_conditions),
            'affected_body_systems': len(condition_categories),
            'category_breakdown': condition_categories,
            'detailed_criteria_available': len(DETAILED_CRITERIA) > 0
        }
    
    def _find_partial_condition_match(self, condition_name: str) -> Optional[DisabilityCondition]:
        """Find partial matches for conditions not directly in the database"""
        condition_lower = condition_name.lower()
        
        # Common condition mappings and keywords
        keyword_mappings = {
            'back': ['chronic_back_pain'],
            'spine': ['chronic_back_pain'],
            'depression': ['depression_anxiety'],
            'anxiety': ['depression_anxiety'],
            'diabetes': ['diabetes_complications'],
            'heart': ['heart_disease'],
            'cardiac': ['heart_disease'],
            'lung': ['chronic_respiratory_disorders'],
            'copd': ['chronic_respiratory_disorders'],
            'asthma': ['chronic_respiratory_disorders'],
            'kidney': ['chronic_kidney_disease'],
            'renal': ['chronic_kidney_disease'],
            'cancer': ['malignant_neoplasms'],
            'tumor': ['malignant_neoplasms'],
            'epilepsy': ['epilepsy'],
            'seizure': ['epilepsy'],
            'ms': ['multiple_sclerosis'],
            'multiple sclerosis': ['multiple_sclerosis'],
            'lupus': ['lupus'],
            'arthritis': ['chronic_back_pain'],  # Often affects spine/joints
            'fibromyalgia': ['chronic_back_pain'],  # Similar functional limitations
            'vision': ['vision_impairment'],
            'blind': ['vision_impairment'],
            'anemia': ['chronic_anemia'],
            'ibd': ['inflammatory_bowel_disease'],
            'crohn': ['inflammatory_bowel_disease'],
            'colitis': ['inflammatory_bowel_disease']
        }
        
        for keyword, condition_keys in keyword_mappings.items():
            if keyword in condition_lower:
                for key in condition_keys:
                    if key in self.conditions:
                        return self.conditions[key]
        
        return None
    
    def _assess_ssi_eligibility(self, age: int, income: float, medical_assessment: Dict) -> Dict[str, Any]:
        """Assess SSI eligibility"""
        # SSI income limits for 2024
        ssi_income_limit = 943  # Individual limit
        
        age_eligible = age >= 65
        disability_eligible = medical_assessment['has_qualifying_conditions']
        income_eligible = income <= ssi_income_limit
        
        overall_eligible = (age_eligible or disability_eligible) and income_eligible
        
        estimated_benefit = max(ssi_income_limit - income, 0) if overall_eligible else 0
        
        return {
            'eligible': overall_eligible,
            'age_qualified': age_eligible,
            'disability_qualified': disability_eligible,
            'income_qualified': income_eligible,
            'estimated_monthly_benefit': estimated_benefit,
            'income_limit': ssi_income_limit,
            'confidence_level': 'High' if overall_eligible else 'Low'
        }
    
    def _assess_ssdi_eligibility(self, age: int, work_credits: Dict, medical_assessment: Dict) -> Dict[str, Any]:
        """Assess SSDI eligibility"""
        has_work_credits = work_credits['has_sufficient_credits']
        has_disability = medical_assessment['has_qualifying_conditions']
        
        overall_eligible = has_work_credits and has_disability
        
        # Estimate SSDI benefit (simplified calculation)
        if overall_eligible:
            estimated_benefit = min(1500, max(800, work_credits['years_worked'] * 50))
        else:
            estimated_benefit = 0
        
        return {
            'eligible': overall_eligible,
            'work_credits_sufficient': has_work_credits,
            'disability_qualified': has_disability,
            'estimated_monthly_benefit': estimated_benefit,
            'work_credits': work_credits['estimated_credits'],
            'credits_needed': work_credits['credits_needed'],
            'confidence_level': 'High' if overall_eligible else 'Low'
        }
    
    def _generate_recommendations(self, ssi_eligible: Dict, ssdi_eligible: Dict, medical_assessment: Dict) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        if ssi_eligible['eligible']:
            recommendations.append(f"✅ **Apply for SSI** - You appear eligible with estimated benefit of ${ssi_eligible['estimated_monthly_benefit']}/month")
        
        if ssdi_eligible['eligible']:
            recommendations.append(f"✅ **Apply for SSDI** - You have sufficient work credits with estimated benefit of ${ssdi_eligible['estimated_monthly_benefit']}/month")
        
        if not ssi_eligible['eligible'] and not ssdi_eligible['eligible']:
            if not ssdi_eligible['work_credits_sufficient']:
                recommendations.append("⚠️ **Insufficient Work Credits** - Consider applying for SSI if you meet disability requirements")
            
            if not medical_assessment['has_qualifying_conditions']:
                recommendations.append("⚠️ **Medical Documentation Needed** - Gather comprehensive medical records to support your case")
        
        if medical_assessment['estimated_approval_probability'] < 0.3:
            recommendations.append("📋 **Consider Legal Assistance** - Your case may benefit from disability attorney representation")
        
        return recommendations
    
    def _generate_next_steps(self, ssi_eligible: Dict, ssdi_eligible: Dict) -> List[Dict[str, Any]]:
        """Generate actionable next steps"""
        steps = []
        
        if ssi_eligible['eligible'] or ssdi_eligible['eligible']:
            steps.extend([
                {
                    'step': 'Gather Medical Records',
                    'description': 'Collect all medical records, test results, and doctor reports',
                    'priority': 'High',
                    'estimated_time': '1-2 weeks'
                },
                {
                    'step': 'Contact Social Security Administration',
                    'description': 'Call 1-800-772-1213 to schedule application appointment',
                    'priority': 'High',
                    'estimated_time': '1 day'
                },
                {
                    'step': 'Complete Application',
                    'description': 'Fill out disability application forms (SSA-16 for SSDI, SSI-8000 for SSI)',
                    'priority': 'High',
                    'estimated_time': '2-3 hours'
                }
            ])
        
        steps.append({
            'step': 'Consider Legal Representation',
            'description': 'Consult with a disability attorney for complex cases',
            'priority': 'Medium',
            'estimated_time': '1 hour consultation'
        })
        
        return steps
    
    def _estimate_timeline(self, medical_assessment: Dict) -> Dict[str, str]:
        """Estimate application timeline"""
        if medical_assessment['estimated_approval_probability'] > 0.7:
            return {
                'initial_decision': '3-4 months',
                'total_process': '4-6 months',
                'likelihood': 'High approval probability'
            }
        elif medical_assessment['estimated_approval_probability'] > 0.4:
            return {
                'initial_decision': '3-5 months',
                'total_process': '6-12 months',
                'likelihood': 'Moderate approval probability, may require appeal'
            }
        else:
            return {
                'initial_decision': '3-6 months',
                'total_process': '12-24 months',
                'likelihood': 'Lower approval probability, likely requires appeal'
            }
    
    def _get_required_documentation(self, medical_conditions: List[str]) -> List[Dict[str, Any]]:
        """Get required documentation for specific conditions"""
        all_docs = set()
        
        for condition_name in medical_conditions:
            condition_key = condition_name.lower().replace(' ', '_').replace('-', '_')
            if condition_key in self.conditions:
                condition = self.conditions[condition_key]
                all_docs.update(condition.documentation_required)
        
        # Convert to list with priorities
        prioritized_docs = []
        for doc in all_docs:
            priority = 'High' if any(keyword in doc.lower() for keyword in ['medical', 'doctor', 'specialist']) else 'Medium'
            prioritized_docs.append({
                'document': doc,
                'priority': priority,
                'description': f'Required for supporting your disability claim'
            })
        
        return prioritized_docs

# Global assessment instance
disability_assessor = DisabilityAssessment()