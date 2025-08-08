#!/usr/bin/env python3
"""
Legal Case Management Routes for Second Chance Jobs Platform
Professional legal compliance tracking and court date management
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import logging
import json
from typing import Dict, List, Any, Optional
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from legal.models import LegalCase, CourtDate, LegalDocument, LegalDatabase
from legal.expungement_routes import router as expungement_router

# Create FastAPI router
router = APIRouter(tags=["legal"])

# Include expungement routes
router.include_router(expungement_router)

# Initialize database
legal_db = None

def get_legal_db():
    """Get thread-safe legal database instance"""
    # Create a new instance for each request to avoid threading issues
    return LegalDatabase("databases/legal_cases.db")

logger = logging.getLogger(__name__)

# Pydantic models
class LegalCaseCreate(BaseModel):
    client_id: str
    case_number: str
    court_name: str
    case_type: str
    charges: List[str]
    probation_officer: Optional[str] = None
    probation_phone: Optional[str] = None
    probation_start_date: Optional[str] = None
    probation_end_date: Optional[str] = None

class CourtDateCreate(BaseModel):
    case_id: str
    client_name: str
    hearing_date: str
    hearing_time: str
    court_name: str
    courtroom: str
    hearing_type: str
    judge_name: str

class LegalDocumentCreate(BaseModel):
    client_name: str
    document_type: str
    document_title: str
    document_purpose: str
    due_date: str
    submitted_to: str
    urgency_level: str = "Medium"

class ComplianceCheck(BaseModel):
    client_id: str

class ExpungementCheck(BaseModel):
    case_id: str

class WarrantCheck(BaseModel):
    client_id: str

@router.get("/")
async def legal_dashboard():
    """Legal case management dashboard"""
    return {"message": "Legal Dashboard API Ready", "endpoints": ["/cases", "/court-dates", "/documents", "/compliance-check"]}

@router.get("/cases")
async def get_legal_cases(client_id: Optional[str] = Query(None)):
    """Get legal cases"""
    try:
        # For demo, return sample legal cases
        sample_cases = [
            {
                'case_id': 'case_001',
                'client_id': 'client_001',
                'case_number': '2023-CR-001234',
                'court_name': 'Los Angeles Superior Court',
                'case_type': 'Felony',
                'case_status': 'Active',
                'charges': ["Burglary", "Possession of Controlled Substance"],
                'probation_officer': 'Sarah Johnson',
                'probation_phone': '(213) 555-0123',
                'probation_start_date': '2023-06-01',
                'probation_end_date': '2026-06-01',
                'compliance_status': 'Compliant',
                'expungement_eligible': True,
                'fines_total': 2500.0,
                'fines_paid': 1000.0,
                'next_court_date': '2024-03-15'
            },
            {
                'case_id': 'case_002',
                'client_id': 'client_002',
                'case_number': '2024-CR-000567',
                'court_name': 'Van Nuys Courthouse',
                'case_type': 'Misdemeanor',
                'case_status': 'Active',
                'charges': ["Petty Theft"],
                'probation_officer': 'Michael Chen',
                'probation_phone': '(818) 555-0456',
                'probation_start_date': '2024-01-15',
                'probation_end_date': '2025-01-15',
                'compliance_status': 'Warning',
                'expungement_eligible': False,
                'fines_total': 800.0,
                'fines_paid': 800.0,
                'next_court_date': '2024-02-28'
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
        logger.error(f"Get legal cases error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cases")
async def create_legal_case(case_data: LegalCaseCreate):
    """Create new legal case"""
    try:
        # Create legal case
        legal_case = LegalCase(
            client_id=case_data.client_id,
            case_number=case_data.case_number,
            court_name=case_data.court_name,
            case_type=case_data.case_type,
            charges=json.dumps(case_data.charges),
            probation_officer=case_data.probation_officer,
            probation_phone=case_data.probation_phone,
            probation_start_date=case_data.probation_start_date,
            probation_end_date=case_data.probation_end_date
        )
        legal_db = get_legal_db()
        case_id = legal_db.save_legal_case(legal_case)
        
        return {
            'success': True,
            'message': 'Legal case created successfully',
            'case_id': legal_case.case_id
        }
        
    except Exception as e:
        logger.error(f"Create legal case error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/court-dates")
async def get_court_dates(client_id: Optional[str] = Query(None), days_ahead: int = Query(30)):
    """Get court dates"""
    try:
        # For demo, return sample court dates
        sample_court_dates = [
            {
                'court_date_id': 'court_001',
                'case_id': 'case_001',
                'client_name': 'John Smith',
                'hearing_date': '2024-02-28',
                'hearing_time': '09:00 AM',
                'court_name': 'Los Angeles Superior Court',
                'courtroom': 'Department 42',
                'hearing_type': 'Probation Review',
                'judge_name': 'Hon. Maria Rodriguez',
                'required_attendance': True,
                'status': 'Scheduled',
                'transportation_arranged': False,
                'reminder_sent': False,
                'days_until': 8
            },
            {
                'court_date_id': 'court_002',
                'case_id': 'case_002',
                'client_name': 'Maria Garcia',
                'hearing_date': '2024-03-15',
                'hearing_time': '02:00 PM',
                'court_name': 'Van Nuys Courthouse',
                'courtroom': 'Department 12',
                'hearing_type': 'Sentencing',
                'judge_name': 'Hon. David Park',
                'required_attendance': True,
                'status': 'Scheduled',
                'transportation_arranged': True,
                'reminder_sent': True,
                'days_until': 23
            }
        ]
        
        return {
            'success': True,
            'court_dates': sample_court_dates,
            'total_count': len(sample_court_dates)
        }
        
    except Exception as e:
        logger.error(f"Get court dates error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/court-dates")
async def create_court_date(court_date_data: CourtDateCreate):
    """Schedule new court date"""
    try:
        # Create court date
        court_date = CourtDate(
            case_id=court_date_data.case_id,
            client_name=court_date_data.client_name,
            hearing_date=court_date_data.hearing_date,
            hearing_time=court_date_data.hearing_time,
            court_name=court_date_data.court_name,
            courtroom=court_date_data.courtroom,
            hearing_type=court_date_data.hearing_type,
            judge_name=court_date_data.judge_name
        )
        legal_db = get_legal_db()
        court_date_id = legal_db.save_court_date(court_date)
        
        return {
            'success': True,
            'message': 'Court date scheduled successfully',
            'court_date_id': court_date.court_date_id
        }
        
    except Exception as e:
        logger.error(f"Create court date error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def get_legal_documents(client_id: Optional[str] = Query(None), document_type: Optional[str] = Query(None, alias="type")):
    """Get legal documents"""
    try:
        # For demo, return sample legal documents
        sample_documents = [
            {
                'document_id': 'doc_001',
                'client_name': 'John Smith',
                'document_type': 'Court Letter',
                'document_title': 'Employment Verification Letter',
                'document_purpose': 'Proof of employment for probation officer',
                'document_status': 'Generated',
                'due_date': '2024-02-25',
                'submitted_to': 'Probation Department',
                'urgency_level': 'High',
                'created_at': '2024-02-20T10:00:00'
            },
            {
                'document_id': 'doc_002',
                'client_name': 'Maria Garcia',
                'document_type': 'Expungement Application',
                'document_title': 'Petition for Dismissal - PC 1203.4',
                'document_purpose': 'Request for record expungement',
                'document_status': 'Draft',
                'due_date': '2024-03-01',
                'submitted_to': 'Superior Court',
                'urgency_level': 'Medium',
                'created_at': '2024-02-18T14:30:00'
            }
        ]
        
        if document_type:
            sample_documents = [doc for doc in sample_documents if doc['document_type'] == document_type]
        
        return {
            'success': True,
            'documents': sample_documents,
            'total_count': len(sample_documents)
        }
        
    except Exception as e:
        logger.error(f"Get legal documents error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents")
async def create_legal_document(document_data: LegalDocumentCreate):
    """Create new legal document"""
    try:
        # Create legal document
        document = LegalDocument(**document_data.dict())
        
        return {
            'success': True,
            'message': 'Legal document created successfully',
            'document_id': document.document_id
        }
        
    except Exception as e:
        logger.error(f"Create legal document error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compliance-check")
async def api_compliance_check(compliance_data: ComplianceCheck):
    """Run compliance check for client"""
    try:
        client_id = compliance_data.client_id
        
        # Simulate compliance check
        compliance_result = {
            'client_id': client_id,
            'compliance_status': 'Compliant',
            'issues_found': [],
            'recommendations': [
                'Continue current compliance activities',
                'Schedule next probation meeting',
                'Update employment verification'
            ],
            'next_check_due': (datetime.now() + timedelta(days=30)).isoformat(),
            'checked_at': datetime.now().isoformat()
        }
        
        return {
            'success': True,
            'compliance_result': compliance_result
        }
        
    except Exception as e:
        logger.error(f"Compliance check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/expungement-eligibility")
async def api_expungement_eligibility(expungement_data: ExpungementCheck):
    """Check expungement eligibility"""
    try:
        case_id = expungement_data.case_id
        
        # Simulate expungement eligibility check
        eligibility_result = {
            'case_id': case_id,
            'eligible': True,
            'eligibility_date': '2024-06-01',
            'requirements': [
                'Complete all probation terms',
                'Pay all fines and restitution',
                'No new convictions',
                'Complete community service hours'
            ],
            'estimated_timeline': '3-6 months',
            'estimated_cost': 150.0,
            'next_steps': [
                'File PC 1203.4 petition',
                'Schedule court hearing',
                'Prepare supporting documentation'
            ]
        }
        
        return {
            'success': True,
            'eligibility_result': eligibility_result
        }
        
    except Exception as e:
        logger.error(f"Expungement eligibility error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reminders")
async def api_send_reminders():
    """Send court date reminders"""
    try:
        # Get upcoming court dates
        legal_db = get_legal_db()
        upcoming_dates = legal_db.get_upcoming_court_dates(days_ahead=7)
        
        reminders_sent = []
        for court_date in upcoming_dates:
            if not court_date.reminder_sent:
                # Simulate sending reminder
                reminders_sent.append({
                    'court_date_id': court_date.court_date_id,
                    'client_id': court_date.client_id,
                    'hearing_date': court_date.hearing_date,
                    'reminder_type': 'SMS and Email',
                    'sent_at': datetime.now().isoformat()
                })
        
        return {
            'success': True,
            'message': f'Sent {len(reminders_sent)} court date reminders',
            'reminders_sent': reminders_sent
        }
        
    except Exception as e:
        logger.error(f"Send reminders error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={'error': str(e), 'reminders_sent': []})

@router.post("/warrant-check")
async def api_warrant_check(warrant_data: WarrantCheck):
    """Check for outstanding warrants"""
    try:
        client_id = warrant_data.client_id
        
        # Simulate warrant check (in real implementation, this would connect to court systems)
        warrant_result = {
            'client_id': client_id,
            'warrants_found': False,
            'warrant_count': 0,
            'warrant_details': [],
            'check_date': datetime.now().isoformat(),
            'next_check_recommended': (datetime.now() + timedelta(days=30)).isoformat(),
            'status': 'Clear'
        }
        
        return {
            'success': True,
            'warrant_result': warrant_result
        }
        
    except Exception as e:
        logger.error(f"Warrant check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

