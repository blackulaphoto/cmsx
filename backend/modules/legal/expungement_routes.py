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
import sqlite3
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

class EligibilityCheckRequest(BaseModel):
    conviction_data: Dict[str, Any]

def _build_assessment_from_complete_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize full eligibility result to UI assessment shape"""
    success_likelihood = result.get("success_likelihood", "Unknown")
    confidence_map = {"High": 90.0, "Medium": 60.0, "Low": 40.0}
    confidence_score = confidence_map.get(success_likelihood, 50.0)

    estimated_days = result.get("estimated_timeline_days", 0) or 0
    estimated_timeline = f"{estimated_days} days" if estimated_days else "Unknown"

    assessment = {
        "eligible": bool(result.get("eligible")),
        "eligibility_date": datetime.now().isoformat() if result.get("eligible") else None,
        "wait_period_days": 0,
        "requirements": result.get("recommendations", []),
        "disqualifying_factors": result.get("disqualifying_factors", []),
        "estimated_timeline": estimated_timeline,
        "estimated_cost": result.get("estimated_cost", 0.0),
        "next_steps": result.get("next_steps", []),
        "confidence_score": confidence_score
    }

    return assessment

def _map_quiz_to_conviction_data(quiz_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map quiz responses to conviction data expected by the eligibility engine"""
    conviction_date = quiz_data.get("conviction_date")
    conviction_year = None
    if conviction_date:
        try:
            conviction_year = datetime.fromisoformat(conviction_date).year
        except ValueError:
            conviction_year = None

    conviction_data = {
        "conviction_date": conviction_date,
        "conviction_year": conviction_year,
        "offense_code": quiz_data.get("offense_code", ""),
        "offense_type": quiz_data.get("offense_type", ""),
        "conviction_type": quiz_data.get("offense_type", ""),
        "county": quiz_data.get("county", ""),
        "probation_granted": quiz_data.get("probation_granted"),
        "probation_completed": quiz_data.get("probation_completed"),
        "early_termination_granted": quiz_data.get("early_termination_granted"),
        "served_state_prison": quiz_data.get("served_state_prison"),
        "sentence_completion_date": quiz_data.get("sentence_completion_date"),
        "currently_on_probation": quiz_data.get("currently_on_probation"),
        "currently_serving_sentence": quiz_data.get("currently_serving_sentence"),
        "pending_charges": quiz_data.get("pending_charges"),
        "fines_total": quiz_data.get("fines_total", 0.0),
        "fines_paid": quiz_data.get("fines_paid"),
        "restitution_total": quiz_data.get("restitution_total", 0.0),
        "restitution_paid": quiz_data.get("restitution_paid"),
        "court_costs_paid": quiz_data.get("court_costs_paid"),
        "community_service_hours": quiz_data.get("community_service_hours", 0),
        "community_service_completed": quiz_data.get("community_service_completed"),
        "counseling_required": quiz_data.get("counseling_required"),
        "counseling_completed": quiz_data.get("counseling_completed"),
        "requires_sex_offender_registration": quiz_data.get("requires_sex_offender_registration"),
        "is_violent_felony": quiz_data.get("is_violent_felony"),
        "is_wobbler": quiz_data.get("is_wobbler")
    }

    return conviction_data

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
        assessment_dict = {
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

        # If we captured additional fields, run full eligibility engine
        quiz_data = eligibility_engine._process_quiz_responses(quiz_responses)
        conviction_data = _map_quiz_to_conviction_data(quiz_data)
        if any(value is not None and value != "" for value in conviction_data.values()):
            complete_result = eligibility_engine.check_eligibility_complete(conviction_data)
            assessment_dict = _build_assessment_from_complete_result(complete_result)

        return {
            'success': True,
            'assessment': assessment_dict
        }
        
    except Exception as e:
        logger.error(f"Eligibility quiz error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check-eligibility")
async def check_expungement_eligibility(request: EligibilityCheckRequest):
    """Run full eligibility assessment using conviction data"""
    try:
        conviction_data = request.conviction_data or {}
        complete_result = eligibility_engine.check_eligibility_complete(conviction_data)
        assessment = _build_assessment_from_complete_result(complete_result)
        return {
            "success": True,
            "assessment": assessment
        }
    except Exception as e:
        logger.error(f"Check eligibility error: {e}", exc_info=True)
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
        db_cases = workflow_manager.db.get_expungement_cases(client_id=client_id)
        cases = []
        for case in db_cases:
            case_dict = case.to_dict()
            offense_description = case_dict.get('offense_description')
            if not offense_description:
                offense_description = case_dict.get('offense_type') or 'Unknown offense'
            cases.append({
                **case_dict,
                'client_name': case_dict.get('client_name', 'Unknown Client'),
                'offense_description': offense_description,
                'progress_percentage': round(case.document_completion_percentage, 2),
                'next_actions': []
            })

        return {
            'success': True,
            'cases': cases,
            'total_count': len(cases)
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
        db_tasks = workflow_manager.db.get_expungement_tasks(
            expungement_id=expungement_id,
            client_id=client_id
        )
        filtered_tasks = [task.to_dict() for task in db_tasks]

        if status:
            filtered_tasks = [t for t in filtered_tasks if t.get('status') == status]
        
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
        db_path = workflow_manager.db.db_path
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE expungement_tasks
                SET status = ?,
                    notes = COALESCE(?, notes),
                    last_updated = ?
                WHERE task_id = ?
                """,
                (update_data.status, update_data.notes, datetime.now().isoformat(), task_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

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
            raise HTTPException(status_code=404, detail=f"Expungement case {request.expungement_id} not found")
        
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
            raise HTTPException(status_code=404, detail=f"Expungement case {expungement_id} not found")
        
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
        db_path = workflow_manager.db.db_path
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM expungement_cases")
            total_cases = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM expungement_cases WHERE eligibility_status = 'eligible'")
            eligible_cases = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM expungement_cases WHERE process_stage = 'completed'")
            cases_completed = cursor.fetchone()["count"]
            cases_in_progress = max(total_cases - cases_completed, 0)
            success_rate = round((cases_completed / total_cases) * 100, 1) if total_cases else 0.0

            cursor.execute("""
                SELECT process_stage, COUNT(*) as count
                FROM expungement_cases
                GROUP BY process_stage
            """)
            cases_by_stage = {row["process_stage"] or "unknown": row["count"] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT jurisdiction, COUNT(*) as count
                FROM expungement_cases
                GROUP BY jurisdiction
            """)
            cases_by_jurisdiction = {row["jurisdiction"] or "unknown": row["count"] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT service_tier, COUNT(*) as count
                FROM expungement_cases
                GROUP BY service_tier
            """)
            service_tier_distribution = {row["service_tier"] or "unknown": row["count"] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT substr(created_at, 1, 7) as month, COUNT(*) as completions
                FROM expungement_cases
                WHERE process_stage = 'completed' AND created_at IS NOT NULL AND length(created_at) >= 7
                GROUP BY substr(created_at, 1, 7)
                ORDER BY month
            """)
            monthly_completions = [{"month": row["month"], "completions": row["completions"]} for row in cursor.fetchall()]

        analytics = {
            'total_cases': total_cases,
            'eligible_cases': eligible_cases,
            'cases_in_progress': cases_in_progress,
            'cases_completed': cases_completed,
            'success_rate': success_rate,
            'average_processing_days': None,
            'cases_by_stage': cases_by_stage,
            'cases_by_jurisdiction': cases_by_jurisdiction,
            'service_tier_distribution': service_tier_distribution,
            'monthly_completions': monthly_completions
        }
        
        return {
            'success': True,
            'analytics': analytics,
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get expungement analytics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
