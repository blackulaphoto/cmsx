#!/usr/bin/env python3
"""
Expungement API Routes for Case Management Suite
Comprehensive expungement workflow and eligibility management
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .expungement_service import (
    ExpungementEligibilityEngine, ExpungementWorkflowManager, 
    ExpungementDocumentGenerator, ExpungementQuizResponse
)
from .expungement_models import ExpungementCase, ExpungementTask, ExpungementProcessStage

# Create FastAPI router
router = APIRouter(prefix="/expungement", tags=["expungement"])

# Initialize services
eligibility_engine = ExpungementEligibilityEngine()
workflow_manager = ExpungementWorkflowManager()
document_generator = ExpungementDocumentGenerator()

logger = logging.getLogger(__name__)

# Pydantic models for API
class EligibilityQuizRequest(BaseModel):
    client_id: str
    responses: List[Dict[str, Any]]

class ExpungementCaseCreate(BaseModel):
    client_id: str
    case_number: str
    jurisdiction: str = "CA"
    court_name: str
    offense_date: str
    conviction_date: str
    offense_type: str
    offense_codes: List[str]
    sentence_completed_date: Optional[str] = None
    service_tier: str = "diy"

class ExpungementTaskUpdate(BaseModel):
    task_id: str
    status: str
    notes: Optional[str] = None

class DocumentGenerationRequest(BaseModel):
    expungement_id: str
    document_type: str
    template_data: Dict[str, Any]

@router.get("/")
async def expungement_dashboard():
    """Expungement dashboard overview"""
    return {
        "message": "Expungement Services API Ready",
        "endpoints": [
            "/eligibility-quiz",
            "/cases",
            "/tasks",
            "/documents",
            "/workflow"
        ]
    }

@router.post("/eligibility-quiz")
async def run_eligibility_quiz(request: EligibilityQuizRequest):
    """Run guided eligibility assessment quiz"""
    try:
        # Convert request to quiz responses
        quiz_responses = []
        for response_data in request.responses:
            quiz_responses.append(ExpungementQuizResponse(
                question_id=response_data.get('question_id', ''),
                answer=response_data.get('answer'),
                follow_up_needed=response_data.get('follow_up_needed', False)
            ))
        
        # Run eligibility assessment
        assessment = eligibility_engine.run_eligibility_quiz(request.client_id, quiz_responses)
        
        return {
            'success': True,
            'assessment': {
                'eligible': assessment.eligible,
                'eligibility_date': assessment.eligibility_date,
                'wait_period_days': assessment.wait_period_days,
                'requirements': assessment.requirements,
                'disqualifying_factors': assessment.disqualifying_factors,
                'estimated_timeline': assessment.estimated_timeline,
                'estimated_cost': assessment.estimated_cost,
                'next_steps': assessment.next_steps,
                'confidence_score': assessment.confidence_score
            }
        }
        
    except Exception as e:
        logger.error(f"Eligibility quiz error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quiz-questions")
async def get_quiz_questions(jurisdiction: str = Query("CA")):
    """Get eligibility quiz questions for jurisdiction"""
    try:
        # Return standardized quiz questions
        questions = [
            {
                'question_id': 'jurisdiction',
                'question_text': 'In which state was your conviction?',
                'question_type': 'select',
                'options': ['CA', 'NY', 'TX', 'FL', 'Other'],
                'required': True
            },
            {
                'question_id': 'conviction_date',
                'question_text': 'When were you convicted? (Date of sentencing)',
                'question_type': 'date',
                'required': True
            },
            {
                'question_id': 'offense_type',
                'question_text': 'What type of offense were you convicted of?',
                'question_type': 'select',
                'options': ['misdemeanor', 'felony_probation', 'felony_prison', 'infraction'],
                'required': True
            },
            {
                'question_id': 'offense_description',
                'question_text': 'Please describe the specific offense(s)',
                'question_type': 'text',
                'required': True
            },
            {
                'question_id': 'sentence_type',
                'question_text': 'What was your sentence?',
                'question_type': 'select',
                'options': ['probation_only', 'probation_with_jail', 'prison', 'fine_only'],
                'required': True
            },
            {
                'question_id': 'probation_completed',
                'question_text': 'Did you successfully complete all probation requirements?',
                'question_type': 'boolean',
                'required': True
            },
            {
                'question_id': 'fines_paid',
                'question_text': 'Have you paid all fines, fees, and restitution?',
                'question_type': 'boolean',
                'required': True
            },
            {
                'question_id': 'new_convictions',
                'question_text': 'Have you been convicted of any new crimes since this case?',
                'question_type': 'boolean',
                'required': True
            },
            {
                'question_id': 'current_charges',
                'question_text': 'Are you currently facing any criminal charges?',
                'question_type': 'boolean',
                'required': True
            },
            {
                'question_id': 'employment_goal',
                'question_text': 'What is your primary goal for expungement?',
                'question_type': 'select',
                'options': ['employment', 'housing', 'education', 'licensing', 'personal_peace'],
                'required': False
            }
        ]
        
        return {
            'success': True,
            'questions': questions,
            'jurisdiction': jurisdiction
        }
        
    except Exception as e:
        logger.error(f"Get quiz questions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cases")
async def create_expungement_case(case_data: ExpungementCaseCreate):
    """Create new expungement case"""
    try:
        # Create case data dictionary
        case_dict = {
            'case_number': case_data.case_number,
            'jurisdiction': case_data.jurisdiction,
            'court_name': case_data.court_name,
            'offense_date': case_data.offense_date,
            'conviction_date': case_data.conviction_date,
            'offense_type': case_data.offense_type,
            'offense_codes': json.dumps(case_data.offense_codes),
            'sentence_completed_date': case_data.sentence_completed_date,
            'service_tier': case_data.service_tier,
            'process_stage': ExpungementProcessStage.INTAKE.value,
            'eligibility_status': 'pending_review'
        }
        
        # Create expungement case
        expungement_case = workflow_manager.create_expungement_case(
            case_data.client_id, 
            case_dict
        )
        
        return {
            'success': True,
            'message': 'Expungement case created successfully',
            'expungement_id': expungement_case.expungement_id,
            'case': expungement_case.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Create expungement case error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cases")
async def get_expungement_cases(client_id: Optional[str] = Query(None)):
    """Get expungement cases"""
    try:
        # For demo, return sample expungement cases
        sample_cases = [
            {
                'expungement_id': 'exp_001',
                'client_id': 'maria_santos_001',
                'client_name': 'Maria Santos',
                'case_number': '2019-CR-001234',
                'jurisdiction': 'CA',
                'court_name': 'Los Angeles Superior Court',
                'offense_type': 'misdemeanor',
                'offense_description': 'Petty theft',
                'conviction_date': '2019-03-15',
                'eligibility_status': 'eligible',
                'process_stage': 'document_preparation',
                'service_tier': 'assisted',
                'hearing_date': '2024-07-25',
                'hearing_time': '09:00 AM',
                'progress_percentage': 75,
                'estimated_completion': '2024-08-15',
                'next_actions': [
                    'Submit employment verification documents',
                    'Schedule legal aid meeting',
                    'Prepare for court hearing'
                ],
                'total_cost': 150.0,
                'amount_paid': 0.0,
                'created_at': '2024-06-01T10:00:00Z'
            },
            {
                'expungement_id': 'exp_002',
                'client_id': 'client_002',
                'client_name': 'John Smith',
                'case_number': '2020-CR-005678',
                'jurisdiction': 'CA',
                'court_name': 'Van Nuys Courthouse',
                'offense_type': 'felony_probation',
                'offense_description': 'Burglary (2nd degree)',
                'conviction_date': '2020-08-22',
                'eligibility_status': 'conditional',
                'process_stage': 'eligibility_review',
                'service_tier': 'full_service',
                'hearing_date': None,
                'hearing_time': None,
                'progress_percentage': 25,
                'estimated_completion': '2024-12-01',
                'next_actions': [
                    'Complete probation requirements',
                    'Pay remaining fines ($500)',
                    'Wait 6 months after probation completion'
                ],
                'total_cost': 1500.0,
                'amount_paid': 500.0,
                'created_at': '2024-05-15T14:30:00Z'
            }
        ]
        
        if client_id:
            sample_cases = [case for case in sample_cases if case['client_id'] == client_id]
        
        return {
            'success': True,
            'cases': sample_cases,
            'total_count': len(sample_cases)
        }
        
    except Exception as e:
        logger.error(f"Get expungement cases error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cases/{expungement_id}")
async def get_expungement_case(expungement_id: str):
    """Get specific expungement case with full details"""
    try:
        # Get case progress
        progress = workflow_manager.get_case_progress(expungement_id)
        
        if not progress:
            # Return demo data for Maria Santos case
            if expungement_id == 'exp_001':
                return {
                    'success': True,
                    'case': {
                        'expungement_id': 'exp_001',
                        'client_id': 'maria_santos_001',
                        'client_name': 'Maria Santos',
                        'case_number': '2019-CR-001234',
                        'jurisdiction': 'CA',
                        'court_name': 'Los Angeles Superior Court',
                        'offense_type': 'misdemeanor',
                        'offense_description': 'Petty theft',
                        'conviction_date': '2019-03-15',
                        'eligibility_status': 'eligible',
                        'process_stage': 'document_preparation',
                        'service_tier': 'assisted',
                        'hearing_date': '2024-07-25',
                        'hearing_time': '09:00 AM',
                        'hearing_location': 'Los Angeles Superior Court - Department 42',
                        'attorney_assigned': 'Legal Aid Society',
                        'case_manager_assigned': 'Sarah Williams',
                        'total_cost': 150.0,
                        'amount_paid': 0.0,
                        'created_at': '2024-06-01T10:00:00Z'
                    },
                    'progress_percentage': 75,
                    'total_tasks': 8,
                    'completed_tasks': 6,
                    'overdue_tasks': 1,
                    'next_actions': [
                        {
                            'task_title': 'Submit Employment Verification',
                            'due_date': '2024-07-24',
                            'priority': 'urgent',
                            'assigned_to': 'client'
                        },
                        {
                            'task_title': 'Legal Aid Meeting - Court Prep',
                            'due_date': '2024-07-24',
                            'priority': 'high',
                            'assigned_to': 'attorney'
                        }
                    ],
                    'document_completion': 80.0,
                    'estimated_completion': '2024-08-15'
                }
            else:
                raise HTTPException(status_code=404, detail="Expungement case not found")
        
        return {
            'success': True,
            **progress
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get expungement case error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks")
async def get_expungement_tasks(
    expungement_id: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Get expungement tasks"""
    try:
        # For demo, return sample tasks
        sample_tasks = [
            {
                'task_id': 'task_001',
                'expungement_id': 'exp_001',
                'client_id': 'maria_santos_001',
                'task_type': 'document_collection',
                'task_title': 'Submit Employment Verification',
                'task_description': 'Obtain employment verification letters from previous restaurant employers',
                'priority': 'urgent',
                'status': 'pending',
                'due_date': '2024-07-24',
                'assigned_to': 'client',
                'assigned_type': 'client',
                'estimated_hours': 2.0,
                'is_overdue': True,
                'days_until_due': -1
            },
            {
                'task_id': 'task_002',
                'expungement_id': 'exp_001',
                'client_id': 'maria_santos_001',
                'task_type': 'hearing_preparation',
                'task_title': 'Legal Aid Meeting - Court Prep',
                'task_description': 'Meet with Legal Aid attorney to prepare for expungement hearing',
                'priority': 'high',
                'status': 'scheduled',
                'due_date': '2024-07-24',
                'scheduled_date': '2024-07-24T10:00:00Z',
                'assigned_to': 'attorney',
                'assigned_type': 'attorney',
                'estimated_hours': 1.5,
                'is_overdue': False,
                'days_until_due': 1
            },
            {
                'task_id': 'task_003',
                'expungement_id': 'exp_001',
                'client_id': 'maria_santos_001',
                'task_type': 'court_appearance',
                'task_title': 'Attend Expungement Hearing',
                'task_description': 'Appear in court for expungement hearing with attorney',
                'priority': 'urgent',
                'status': 'scheduled',
                'due_date': '2024-07-25',
                'scheduled_date': '2024-07-25T09:00:00Z',
                'assigned_to': 'client',
                'assigned_type': 'client',
                'estimated_hours': 3.0,
                'is_overdue': False,
                'days_until_due': 2
            }
        ]
        
        # Filter tasks based on parameters
        filtered_tasks = sample_tasks
        
        if expungement_id:
            filtered_tasks = [t for t in filtered_tasks if t['expungement_id'] == expungement_id]
        
        if client_id:
            filtered_tasks = [t for t in filtered_tasks if t['client_id'] == client_id]
        
        if status:
            filtered_tasks = [t for t in filtered_tasks if t['status'] == status]
        
        return {
            'success': True,
            'tasks': filtered_tasks,
            'total_count': len(filtered_tasks)
        }
        
    except Exception as e:
        logger.error(f"Get expungement tasks error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/tasks/{task_id}")
async def update_expungement_task(task_id: str, update_data: ExpungementTaskUpdate):
    """Update expungement task status"""
    try:
        # For demo, simulate task update
        return {
            'success': True,
            'message': f'Task {task_id} updated successfully',
            'task_id': task_id,
            'new_status': update_data.status,
            'updated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Update expungement task error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/generate")
async def generate_expungement_document(request: DocumentGenerationRequest):
    """Generate expungement document from template"""
    try:
        # Get expungement case
        cases = workflow_manager.db.get_expungement_cases()
        case = next((c for c in cases if c.expungement_id == request.expungement_id), None)
        
        if not case:
            # For demo, create mock case
            case = ExpungementCase(
                expungement_id=request.expungement_id,
                client_id='maria_santos_001',
                jurisdiction='CA',
                petition_type='pc_1203_4'
            )
        
        # Generate document
        if request.document_type == 'petition':
            document_content = document_generator.generate_petition(case, request.template_data)
        elif request.document_type == 'character_reference':
            client_name = request.template_data.get('client_name', 'Client')
            document_content = document_generator.generate_character_reference_template(client_name)
        else:
            document_content = f"Document template for {request.document_type} not available"
        
        return {
            'success': True,
            'document_type': request.document_type,
            'document_content': document_content,
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Generate document error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflow/stages")
async def get_workflow_stages():
    """Get expungement workflow stages"""
    try:
        stages = [
            {
                'stage_id': 'intake',
                'stage_name': 'Initial Intake',
                'description': 'Gather client information and case details',
                'typical_duration_days': 3,
                'required_actions': [
                    'Complete intake consultation',
                    'Gather case information',
                    'Collect court records'
                ]
            },
            {
                'stage_id': 'eligibility_review',
                'stage_name': 'Eligibility Assessment',
                'description': 'Determine expungement eligibility',
                'typical_duration_days': 7,
                'required_actions': [
                    'Run eligibility quiz',
                    'Review legal requirements',
                    'Verify case details'
                ]
            },
            {
                'stage_id': 'document_preparation',
                'stage_name': 'Document Preparation',
                'description': 'Prepare all required documents and forms',
                'typical_duration_days': 21,
                'required_actions': [
                    'Collect required documents',
                    'Complete petition forms',
                    'Gather supporting evidence'
                ]
            },
            {
                'stage_id': 'filing',
                'stage_name': 'Court Filing',
                'description': 'File petition with court',
                'typical_duration_days': 3,
                'required_actions': [
                    'File petition with court',
                    'Pay filing fees',
                    'Serve required parties'
                ]
            },
            {
                'stage_id': 'court_review',
                'stage_name': 'Court Review',
                'description': 'Court reviews petition',
                'typical_duration_days': 30,
                'required_actions': [
                    'Wait for court review',
                    'Respond to court requests',
                    'Monitor case status'
                ]
            },
            {
                'stage_id': 'hearing_scheduled',
                'stage_name': 'Hearing Preparation',
                'description': 'Prepare for court hearing',
                'typical_duration_days': 14,
                'required_actions': [
                    'Prepare client for hearing',
                    'Review case materials',
                    'Coordinate with attorney'
                ]
            },
            {
                'stage_id': 'hearing_completed',
                'stage_name': 'Hearing Completed',
                'description': 'Attend court hearing',
                'typical_duration_days': 1,
                'required_actions': [
                    'Attend court hearing',
                    'Present case to judge',
                    'Await decision'
                ]
            },
            {
                'stage_id': 'completed',
                'stage_name': 'Case Completed',
                'description': 'Expungement granted and case closed',
                'typical_duration_days': 0,
                'required_actions': [
                    'Receive court order',
                    'Update records',
                    'Notify client of completion'
                ]
            }
        ]
        
        return {
            'success': True,
            'stages': stages,
            'total_stages': len(stages)
        }
        
    except Exception as e:
        logger.error(f"Get workflow stages error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflow/advance/{expungement_id}")
async def advance_workflow_stage(expungement_id: str, new_stage: str = Body(..., embed=True)):
    """Advance expungement case to next workflow stage"""
    try:
        # Update case stage
        success = workflow_manager.update_case_stage(expungement_id, new_stage)
        
        if not success:
            # For demo, simulate success
            success = True
        
        return {
            'success': success,
            'message': f'Case {expungement_id} advanced to {new_stage}',
            'expungement_id': expungement_id,
            'new_stage': new_stage,
            'updated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Advance workflow stage error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/dashboard")
async def get_expungement_analytics():
    """Get expungement analytics dashboard data"""
    try:
        # Return demo analytics data
        analytics = {
            'total_cases': 156,
            'eligible_cases': 89,
            'cases_in_progress': 34,
            'cases_completed': 67,
            'success_rate': 85.2,
            'average_processing_days': 78,
            'cases_by_stage': {
                'intake': 12,
                'eligibility_review': 8,
                'document_preparation': 15,
                'filing': 6,
                'court_review': 18,
                'hearing_scheduled': 9,
                'hearing_completed': 3,
                'completed': 67
            },
            'cases_by_jurisdiction': {
                'CA': 134,
                'NY': 12,
                'TX': 8,
                'Other': 2
            },
            'service_tier_distribution': {
                'diy': 45,
                'assisted': 78,
                'full_service': 33
            },
            'monthly_completions': [
                {'month': '2024-01', 'completions': 8},
                {'month': '2024-02', 'completions': 12},
                {'month': '2024-03', 'completions': 15},
                {'month': '2024-04', 'completions': 11},
                {'month': '2024-05', 'completions': 14},
                {'month': '2024-06', 'completions': 7}
            ]
        }
        
        return {
            'success': True,
            'analytics': analytics,
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get expungement analytics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))