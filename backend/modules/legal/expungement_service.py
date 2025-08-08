#!/usr/bin/env python3
"""
Expungement Service for Case Management Suite
Comprehensive expungement eligibility engine and workflow management
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .expungement_models import (
    ExpungementCase, EligibilityRuleSet, ExpungementTask, ExpungementDatabase,
    ExpungementEligibilityStatus, ExpungementProcessStage, ExpungementServiceTier
)

logger = logging.getLogger(__name__)

@dataclass
class EligibilityAssessment:
    """Eligibility assessment result"""
    eligible: bool
    eligibility_date: Optional[str]
    wait_period_days: int
    requirements: List[str]
    disqualifying_factors: List[str]
    estimated_timeline: str
    estimated_cost: float
    next_steps: List[str]
    confidence_score: float

@dataclass
class ExpungementQuizResponse:
    """Response to eligibility quiz question"""
    question_id: str
    answer: Any
    follow_up_needed: bool = False

class ExpungementEligibilityEngine:
    """AI-powered eligibility assessment engine"""
    
    def __init__(self):
        self.db = ExpungementDatabase()
        self.jurisdiction_rules = self._load_jurisdiction_rules()
    
    def _load_jurisdiction_rules(self) -> Dict[str, EligibilityRuleSet]:
        """Load jurisdiction-specific rules"""
        # For now, return California rules as default
        ca_rules = EligibilityRuleSet(
            jurisdiction="CA",
            rule_name="California PC 1203.4 Expungement",
            statute_reference="PC 1203.4",
            eligible_offense_types=json.dumps([
                "misdemeanor", "felony_probation", "infraction"
            ]),
            ineligible_offense_types=json.dumps([
                "serious_felony", "violent_felony", "sex_offense_registration"
            ]),
            wait_period_months=0,  # No wait period if probation completed
            probation_completion_required=True,
            fines_payment_required=True,
            no_new_convictions_required=True,
            hearing_required=True,
            filing_fee=150.0,
            fee_waiver_available=True,
            required_documents=json.dumps([
                "petition_form", "case_information", "proof_of_completion",
                "character_references", "employment_verification"
            ]),
            typical_processing_days=90,
            hearing_scheduling_days=30
        )
        
        return {"CA": ca_rules}
    
    def run_eligibility_quiz(self, client_id: str, responses: List[ExpungementQuizResponse]) -> EligibilityAssessment:
        """Run guided eligibility assessment quiz"""
        try:
            # Process quiz responses
            quiz_data = self._process_quiz_responses(responses)
            
            # Determine jurisdiction (default to CA for demo)
            jurisdiction = quiz_data.get('jurisdiction', 'CA')
            rules = self.jurisdiction_rules.get(jurisdiction)
            
            if not rules:
                return self._create_unknown_assessment("Jurisdiction not supported")
            
            # Run eligibility checks
            eligibility_checks = self._run_eligibility_checks(quiz_data, rules)
            
            # Calculate assessment
            assessment = self._calculate_eligibility_assessment(quiz_data, rules, eligibility_checks)
            
            return assessment
            
        except Exception as e:
            logger.error(f"Eligibility quiz error: {e}")
            return self._create_unknown_assessment("Assessment error occurred")
    
    def _process_quiz_responses(self, responses: List[ExpungementQuizResponse]) -> Dict[str, Any]:
        """Process quiz responses into structured data"""
        quiz_data = {}
        
        for response in responses:
            if response.question_id == "conviction_date":
                quiz_data['conviction_date'] = response.answer
            elif response.question_id == "offense_type":
                quiz_data['offense_type'] = response.answer
            elif response.question_id == "probation_completed":
                quiz_data['probation_completed'] = response.answer
            elif response.question_id == "fines_paid":
                quiz_data['fines_paid'] = response.answer
            elif response.question_id == "new_convictions":
                quiz_data['new_convictions'] = response.answer
            elif response.question_id == "sentence_type":
                quiz_data['sentence_type'] = response.answer
            elif response.question_id == "jurisdiction":
                quiz_data['jurisdiction'] = response.answer
        
        return quiz_data
    
    def _run_eligibility_checks(self, quiz_data: Dict[str, Any], rules: EligibilityRuleSet) -> Dict[str, bool]:
        """Run individual eligibility checks"""
        checks = {}
        
        # Check offense type eligibility
        offense_type = quiz_data.get('offense_type', '').lower()
        eligible_types = json.loads(rules.eligible_offense_types)
        ineligible_types = json.loads(rules.ineligible_offense_types)
        
        checks['offense_eligible'] = offense_type in eligible_types
        checks['offense_not_disqualified'] = offense_type not in ineligible_types
        
        # Check probation completion
        checks['probation_completed'] = quiz_data.get('probation_completed', False)
        
        # Check fines payment
        checks['fines_paid'] = quiz_data.get('fines_paid', False)
        
        # Check new convictions
        checks['no_new_convictions'] = not quiz_data.get('new_convictions', True)
        
        # Check wait period (if applicable)
        conviction_date = quiz_data.get('conviction_date')
        if conviction_date and rules.wait_period_months > 0:
            try:
                conv_date = datetime.fromisoformat(conviction_date)
                wait_until = conv_date + timedelta(days=rules.wait_period_months * 30)
                checks['wait_period_satisfied'] = datetime.now() >= wait_until
            except:
                checks['wait_period_satisfied'] = False
        else:
            checks['wait_period_satisfied'] = True
        
        return checks
    
    def _calculate_eligibility_assessment(self, quiz_data: Dict[str, Any], rules: EligibilityRuleSet, checks: Dict[str, bool]) -> EligibilityAssessment:
        """Calculate final eligibility assessment"""
        
        # Determine eligibility
        required_checks = [
            'offense_eligible', 'offense_not_disqualified', 
            'probation_completed', 'fines_paid', 'no_new_convictions',
            'wait_period_satisfied'
        ]
        
        eligible = all(checks.get(check, False) for check in required_checks)
        
        # Calculate confidence score
        passed_checks = sum(1 for check in required_checks if checks.get(check, False))
        confidence_score = (passed_checks / len(required_checks)) * 100
        
        # Determine eligibility date
        eligibility_date = None
        wait_period_days = 0
        
        if eligible:
            eligibility_date = datetime.now().isoformat()
        elif not checks.get('wait_period_satisfied', True):
            # Calculate when wait period will be satisfied
            conviction_date = quiz_data.get('conviction_date')
            if conviction_date:
                try:
                    conv_date = datetime.fromisoformat(conviction_date)
                    wait_until = conv_date + timedelta(days=rules.wait_period_months * 30)
                    eligibility_date = wait_until.isoformat()
                    wait_period_days = (wait_until - datetime.now()).days
                except:
                    pass
        
        # Build requirements list
        requirements = []
        if rules.probation_completion_required:
            requirements.append("Complete all probation terms successfully")
        if rules.fines_payment_required:
            requirements.append("Pay all fines, fees, and restitution in full")
        if rules.no_new_convictions_required:
            requirements.append("No new criminal convictions since original case")
        if rules.wait_period_months > 0:
            requirements.append(f"Wait {rules.wait_period_months} months after conviction")
        
        # Build disqualifying factors
        disqualifying_factors = []
        if not checks.get('offense_eligible', True):
            disqualifying_factors.append("Offense type not eligible for expungement")
        if not checks.get('offense_not_disqualified', True):
            disqualifying_factors.append("Offense type specifically excluded from expungement")
        if not checks.get('probation_completed', True):
            disqualifying_factors.append("Probation not completed or violated")
        if not checks.get('fines_paid', True):
            disqualifying_factors.append("Outstanding fines, fees, or restitution")
        if not checks.get('no_new_convictions', True):
            disqualifying_factors.append("New convictions since original case")
        
        # Estimate timeline and cost
        if eligible:
            estimated_timeline = f"{rules.typical_processing_days} days"
            estimated_cost = rules.filing_fee
        else:
            estimated_timeline = "Not eligible at this time"
            estimated_cost = 0.0
        
        # Build next steps
        next_steps = []
        if eligible:
            next_steps = [
                "Gather required documentation",
                "Complete petition forms",
                "File petition with court",
                "Attend court hearing (if required)",
                "Receive court decision"
            ]
        else:
            for factor in disqualifying_factors:
                if "probation" in factor.lower():
                    next_steps.append("Complete probation requirements")
                elif "fines" in factor.lower():
                    next_steps.append("Pay outstanding financial obligations")
                elif "convictions" in factor.lower():
                    next_steps.append("Avoid new criminal convictions")
        
        return EligibilityAssessment(
            eligible=eligible,
            eligibility_date=eligibility_date,
            wait_period_days=wait_period_days,
            requirements=requirements,
            disqualifying_factors=disqualifying_factors,
            estimated_timeline=estimated_timeline,
            estimated_cost=estimated_cost,
            next_steps=next_steps,
            confidence_score=confidence_score
        )
    
    def _create_unknown_assessment(self, reason: str) -> EligibilityAssessment:
        """Create assessment for unknown eligibility"""
        return EligibilityAssessment(
            eligible=False,
            eligibility_date=None,
            wait_period_days=0,
            requirements=["Professional legal consultation required"],
            disqualifying_factors=[reason],
            estimated_timeline="Unknown",
            estimated_cost=0.0,
            next_steps=["Consult with qualified attorney"],
            confidence_score=0.0
        )

class ExpungementWorkflowManager:
    """Manages expungement workflow and task automation"""
    
    def __init__(self):
        self.db = ExpungementDatabase()
        self.eligibility_engine = ExpungementEligibilityEngine()
    
    def create_expungement_case(self, client_id: str, case_data: Dict[str, Any]) -> ExpungementCase:
        """Create new expungement case with automated workflow"""
        try:
            # Create expungement case
            expungement_case = ExpungementCase(
                client_id=client_id,
                **case_data
            )
            
            # Save to database
            self.db.save_expungement_case(expungement_case)
            
            # Generate initial workflow tasks
            self._generate_workflow_tasks(expungement_case)
            
            return expungement_case
            
        except Exception as e:
            logger.error(f"Create expungement case error: {e}")
            raise
    
    def _generate_workflow_tasks(self, case: ExpungementCase):
        """Generate automated workflow tasks based on case stage"""
        try:
            tasks = []
            
            if case.process_stage == ExpungementProcessStage.INTAKE.value:
                tasks.extend(self._generate_intake_tasks(case))
            elif case.process_stage == ExpungementProcessStage.ELIGIBILITY_REVIEW.value:
                tasks.extend(self._generate_eligibility_tasks(case))
            elif case.process_stage == ExpungementProcessStage.DOCUMENT_PREPARATION.value:
                tasks.extend(self._generate_document_tasks(case))
            elif case.process_stage == ExpungementProcessStage.FILING.value:
                tasks.extend(self._generate_filing_tasks(case))
            elif case.process_stage == ExpungementProcessStage.HEARING_SCHEDULED.value:
                tasks.extend(self._generate_hearing_prep_tasks(case))
            
            # Save all tasks
            for task in tasks:
                self.db.save_expungement_task(task)
                
        except Exception as e:
            logger.error(f"Generate workflow tasks error: {e}")
    
    def _generate_intake_tasks(self, case: ExpungementCase) -> List[ExpungementTask]:
        """Generate intake stage tasks"""
        tasks = []
        
        # Initial consultation task
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="consultation",
            task_title="Initial Expungement Consultation",
            task_description="Conduct initial consultation to gather case information and assess client needs",
            priority="high",
            due_date=(datetime.now() + timedelta(days=3)).isoformat(),
            assigned_to="case_manager",
            assigned_type="staff",
            estimated_hours=1.5
        ))
        
        # Case information gathering
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="information_gathering",
            task_title="Gather Case Information",
            task_description="Collect complete case information, court records, and conviction details",
            priority="high",
            due_date=(datetime.now() + timedelta(days=5)).isoformat(),
            assigned_to="case_manager",
            assigned_type="staff",
            estimated_hours=2.0
        ))
        
        return tasks
    
    def _generate_eligibility_tasks(self, case: ExpungementCase) -> List[ExpungementTask]:
        """Generate eligibility review tasks"""
        tasks = []
        
        # Eligibility assessment
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="eligibility_assessment",
            task_title="Complete Eligibility Assessment",
            task_description="Run comprehensive eligibility assessment using guided questionnaire",
            priority="high",
            due_date=(datetime.now() + timedelta(days=2)).isoformat(),
            assigned_to="case_manager",
            assigned_type="staff",
            estimated_hours=1.0
        ))
        
        # Legal research if needed
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="legal_research",
            task_title="Legal Research and Verification",
            task_description="Verify eligibility requirements and research any complex legal issues",
            priority="medium",
            due_date=(datetime.now() + timedelta(days=7)).isoformat(),
            assigned_to="attorney",
            assigned_type="attorney",
            estimated_hours=2.0
        ))
        
        return tasks
    
    def _generate_document_tasks(self, case: ExpungementCase) -> List[ExpungementTask]:
        """Generate document preparation tasks"""
        tasks = []
        
        # Document collection
        required_docs = json.loads(case.required_documents) if case.required_documents else []
        
        for doc_type in required_docs:
            tasks.append(ExpungementTask(
                expungement_id=case.expungement_id,
                client_id=case.client_id,
                task_type="document_collection",
                task_title=f"Collect {doc_type.replace('_', ' ').title()}",
                task_description=f"Obtain and prepare {doc_type.replace('_', ' ')} for petition filing",
                priority="high" if doc_type in ["petition_form", "case_information"] else "medium",
                due_date=(datetime.now() + timedelta(days=14)).isoformat(),
                assigned_to="client" if doc_type in ["employment_verification", "character_references"] else "case_manager",
                assigned_type="client" if doc_type in ["employment_verification", "character_references"] else "staff",
                estimated_hours=1.0
            ))
        
        # Petition preparation
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="petition_preparation",
            task_title="Prepare Expungement Petition",
            task_description="Complete and review expungement petition forms with all supporting documentation",
            priority="high",
            due_date=(datetime.now() + timedelta(days=21)).isoformat(),
            assigned_to="attorney",
            assigned_type="attorney",
            estimated_hours=3.0
        ))
        
        return tasks
    
    def _generate_filing_tasks(self, case: ExpungementCase) -> List[ExpungementTask]:
        """Generate filing stage tasks"""
        tasks = []
        
        # File petition
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="court_filing",
            task_title="File Expungement Petition",
            task_description="File completed petition with appropriate court and pay filing fees",
            priority="high",
            due_date=(datetime.now() + timedelta(days=2)).isoformat(),
            assigned_to="case_manager",
            assigned_type="staff",
            estimated_hours=2.0
        ))
        
        # Track filing status
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="status_tracking",
            task_title="Track Filing Status",
            task_description="Monitor petition status and court response",
            priority="medium",
            due_date=(datetime.now() + timedelta(days=14)).isoformat(),
            assigned_to="case_manager",
            assigned_type="staff",
            estimated_hours=0.5
        ))
        
        return tasks
    
    def _generate_hearing_prep_tasks(self, case: ExpungementCase) -> List[ExpungementTask]:
        """Generate hearing preparation tasks"""
        tasks = []
        
        # Client preparation
        tasks.append(ExpungementTask(
            expungement_id=case.expungement_id,
            client_id=case.client_id,
            task_type="hearing_preparation",
            task_title="Prepare Client for Hearing",
            task_description="Meet with client to prepare for court hearing, review process and expectations",
            priority="high",
            due_date=(datetime.now() + timedelta(days=7)).isoformat(),
            assigned_to="attorney",
            assigned_type="attorney",
            estimated_hours=1.5
        ))
        
        # Court appearance
        if case.hearing_date:
            tasks.append(ExpungementTask(
                expungement_id=case.expungement_id,
                client_id=case.client_id,
                task_type="court_appearance",
                task_title="Attend Court Hearing",
                task_description="Attend expungement hearing and represent client",
                priority="urgent",
                due_date=case.hearing_date,
                assigned_to="attorney",
                assigned_type="attorney",
                estimated_hours=3.0
            ))
        
        return tasks
    
    def update_case_stage(self, expungement_id: str, new_stage: str) -> bool:
        """Update case stage and generate new tasks"""
        try:
            # Get current case
            cases = self.db.get_expungement_cases()
            case = next((c for c in cases if c.expungement_id == expungement_id), None)
            
            if not case:
                return False
            
            # Update stage
            case.process_stage = new_stage
            case.last_updated = datetime.now().isoformat()
            
            # Generate new tasks for the stage
            self._generate_workflow_tasks(case)
            
            return True
            
        except Exception as e:
            logger.error(f"Update case stage error: {e}")
            return False
    
    def get_case_progress(self, expungement_id: str) -> Dict[str, Any]:
        """Get comprehensive case progress information"""
        try:
            # Get case
            cases = self.db.get_expungement_cases()
            case = next((c for c in cases if c.expungement_id == expungement_id), None)
            
            if not case:
                return {}
            
            # Get tasks
            tasks = self.db.get_expungement_tasks(expungement_id=expungement_id)
            
            # Calculate progress metrics
            total_tasks = len(tasks)
            completed_tasks = len([t for t in tasks if t.status == 'completed'])
            overdue_tasks = len([t for t in tasks if t.is_overdue])
            
            progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Get next actions
            pending_tasks = [t for t in tasks if t.status == 'pending']
            next_actions = sorted(pending_tasks, key=lambda x: (x.priority == 'urgent', x.priority == 'high', x.due_date or ''))[:3]
            
            return {
                'case': case.to_dict(),
                'progress_percentage': progress_percentage,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'overdue_tasks': overdue_tasks,
                'next_actions': [t.to_dict() for t in next_actions],
                'document_completion': case.document_completion_percentage,
                'estimated_completion': self._estimate_completion_date(case, tasks)
            }
            
        except Exception as e:
            logger.error(f"Get case progress error: {e}")
            return {}
    
    def _estimate_completion_date(self, case: ExpungementCase, tasks: List[ExpungementTask]) -> Optional[str]:
        """Estimate case completion date based on remaining tasks"""
        try:
            pending_tasks = [t for t in tasks if t.status != 'completed']
            if not pending_tasks:
                return datetime.now().isoformat()
            
            # Find latest due date
            due_dates = [t.due_date for t in pending_tasks if t.due_date]
            if due_dates:
                latest_due = max(due_dates)
                # Add buffer time based on case complexity
                completion_date = datetime.fromisoformat(latest_due) + timedelta(days=30)
                return completion_date.isoformat()
            
            return None
            
        except Exception as e:
            logger.error(f"Estimate completion date error: {e}")
            return None

class ExpungementDocumentGenerator:
    """Automated document generation for expungement petitions"""
    
    def __init__(self):
        self.templates = self._load_document_templates()
    
    def _load_document_templates(self) -> Dict[str, str]:
        """Load document templates"""
        # For demo purposes, return basic templates
        return {
            "ca_pc_1203_4": """
PETITION FOR DISMISSAL UNDER PENAL CODE SECTION 1203.4

TO THE HONORABLE JUDGE OF THE SUPERIOR COURT:

Petitioner {client_name} respectfully represents:

1. On {conviction_date}, petitioner was convicted of {offense_description} in case number {case_number}.

2. Petitioner was granted probation and has fulfilled all conditions of probation.

3. Petitioner has paid all fines, fees, and restitution ordered by the court.

4. Petitioner is not currently charged with, on probation for, or serving a sentence for any offense.

WHEREFORE, petitioner respectfully requests that this Honorable Court grant this petition and dismiss the charges pursuant to Penal Code Section 1203.4.

Respectfully submitted,

{attorney_name}
Attorney for Petitioner
            """,
            "character_reference_template": """
CHARACTER REFERENCE LETTER

To Whom It May Concern:

I am writing this letter to provide a character reference for {client_name} in support of their petition for expungement.

I have known {client_name} for {relationship_duration} in my capacity as {relationship_type}.

During this time, I have observed {client_name} to be {positive_qualities}.

{specific_examples}

I believe {client_name} has demonstrated genuine rehabilitation and deserves a second chance.

Sincerely,

{reference_name}
{reference_title}
{contact_information}
            """
        }
    
    def generate_petition(self, case: ExpungementCase, template_data: Dict[str, Any]) -> str:
        """Generate expungement petition document"""
        try:
            # Determine template based on jurisdiction and petition type
            template_key = f"{case.jurisdiction.lower()}_{case.petition_type.lower().replace(' ', '_')}"
            template = self.templates.get(template_key, self.templates.get("ca_pc_1203_4"))
            
            # Fill template with case data
            filled_template = template.format(**template_data)
            
            return filled_template
            
        except Exception as e:
            logger.error(f"Generate petition error: {e}")
            return ""
    
    def generate_character_reference_template(self, client_name: str) -> str:
        """Generate character reference template for client"""
        try:
            template = self.templates["character_reference_template"]
            
            # Provide template with placeholders
            template_data = {
                'client_name': client_name,
                'relationship_duration': '[DURATION]',
                'relationship_type': '[RELATIONSHIP TYPE]',
                'positive_qualities': '[POSITIVE QUALITIES]',
                'specific_examples': '[SPECIFIC EXAMPLES]',
                'reference_name': '[REFERENCE NAME]',
                'reference_title': '[REFERENCE TITLE]',
                'contact_information': '[CONTACT INFORMATION]'
            }
            
            return template.format(**template_data)
            
        except Exception as e:
            logger.error(f"Generate character reference template error: {e}")
            return ""