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
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .models import LegalCase, CourtDate, LegalDocument, LegalDatabase
from .expungement_routes import router as expungement_router

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


def _get_client_name_map() -> Dict[str, str]:
    """Load client_id -> full name mapping from core clients DB."""
    name_map: Dict[str, str] = {}
    try:
        conn = sqlite3.connect("databases/core_clients.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT client_id, first_name, last_name FROM clients")
        for row in cursor.fetchall():
            first_name = (row["first_name"] or "").strip()
            last_name = (row["last_name"] or "").strip()
            full_name = f"{first_name} {last_name}".strip()
            name_map[row["client_id"]] = full_name or row["client_id"]
    except Exception as e:
        logger.warning(f"Unable to load client names from core_clients.db: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return name_map

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
    legal_db = None
    try:
        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()
        name_map = _get_client_name_map()

        query = """
            SELECT
                lc.case_id,
                lc.client_id,
                lc.case_type,
                lc.case_status,
                lc.court_name,
                lc.attorney_name,
                lc.notes,
                lc.compliance_status,
                MIN(cd.hearing_date) AS next_court_date,
                MIN(cd.hearing_time) AS next_court_time
            FROM legal_cases lc
            LEFT JOIN court_dates cd
                ON cd.case_id = lc.case_id
                AND (cd.status IS NULL OR cd.status = 'Scheduled')
        """
        params: List[Any] = []
        if client_id:
            query += " WHERE lc.client_id = ?"
            params.append(client_id)
        query += """
            GROUP BY
                lc.case_id, lc.client_id, lc.case_type, lc.case_status,
                lc.court_name, lc.attorney_name, lc.notes, lc.compliance_status
            ORDER BY lc.last_updated DESC, lc.created_at DESC
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()

        cases = []
        for row in rows:
            status = row["case_status"] or "Pending"
            compliance_status = (row["compliance_status"] or "").lower()
            priority = "High" if compliance_status == "warning" else "Medium"
            cases.append({
                "case_id": row["case_id"],
                "client_id": row["client_id"],
                "client_name": name_map.get(row["client_id"], row["client_id"]),
                "case_type": row["case_type"] or "Legal Case",
                "status": status.title(),
                "priority": priority,
                "court_date": row["next_court_date"] or "",
                "court_time": row["next_court_time"] or "",
                "court_location": row["court_name"] or "Not provided",
                "attorney": row["attorney_name"] or "Not assigned",
                "description": row["notes"] or "No description available",
                "progress": 50 if status.lower() == "active" else 25,
                "next_action": "Review case notes and upcoming deadlines"
            })

        return {
            'success': True,
            'cases': cases,
            'total_count': len(cases)
        }
        
    except Exception as e:
        logger.error(f"Get legal cases error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            legal_db.close()
        except Exception:
            pass

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
    legal_db = None
    try:
        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()
        name_map = _get_client_name_map()
        future_date = (datetime.now() + timedelta(days=days_ahead)).date().isoformat()
        today = datetime.now().date().isoformat()

        query = """
            SELECT
                cd.court_date_id,
                cd.case_id,
                cd.client_id,
                cd.hearing_date,
                cd.hearing_time,
                cd.court_name,
                cd.courtroom,
                cd.hearing_type,
                cd.judge_name,
                cd.required_attendance,
                cd.status,
                cd.transportation_arranged,
                cd.reminder_sent
            FROM court_dates cd
            WHERE cd.hearing_date >= ? AND cd.hearing_date <= ?
        """
        params: List[Any] = [today, future_date]
        if client_id:
            query += " AND cd.client_id = ?"
            params.append(client_id)
        query += " ORDER BY cd.hearing_date ASC, cd.hearing_time ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        court_dates = []
        for row in rows:
            days_until = None
            if row["hearing_date"]:
                try:
                    days_until = (datetime.fromisoformat(row["hearing_date"]).date() - datetime.now().date()).days
                except Exception:
                    days_until = None
            court_dates.append({
                "court_date_id": row["court_date_id"],
                "case_id": row["case_id"],
                "client_id": row["client_id"],
                "client_name": name_map.get(row["client_id"], row["client_id"]),
                "hearing_date": row["hearing_date"],
                "hearing_time": row["hearing_time"],
                "court_name": row["court_name"],
                "courtroom": row["courtroom"],
                "hearing_type": row["hearing_type"],
                "judge_name": row["judge_name"],
                "required_attendance": bool(row["required_attendance"]),
                "status": row["status"] or "Scheduled",
                "transportation_arranged": bool(row["transportation_arranged"]),
                "reminder_sent": bool(row["reminder_sent"]),
                "days_until": days_until
            })

        return {
            'success': True,
            'court_dates': court_dates,
            'total_count': len(court_dates)
        }
        
    except Exception as e:
        logger.error(f"Get court dates error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            legal_db.close()
        except Exception:
            pass

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
    legal_db = None
    try:
        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()
        name_map = _get_client_name_map()

        query = """
            SELECT
                document_id, case_id, client_id, document_type, document_title,
                document_purpose, document_status, due_date, submitted_to, urgency_level, created_at
            FROM legal_documents
            WHERE 1=1
        """
        params: List[Any] = []
        if client_id:
            query += " AND client_id = ?"
            params.append(client_id)
        if document_type:
            query += " AND document_type = ?"
            params.append(document_type)
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        documents = [{
            "document_id": row["document_id"],
            "doc_id": row["document_id"],
            "case_id": row["case_id"],
            "client_id": row["client_id"],
            "client_name": name_map.get(row["client_id"], row["client_id"]),
            "document_type": row["document_type"] or "Document",
            "document_title": row["document_title"] or "",
            "document_purpose": row["document_purpose"] or "",
            "document_status": row["document_status"] or "Draft",
            "status": row["document_status"] or "Draft",
            "due_date": row["due_date"] or "",
            "required_by": row["due_date"] or "",
            "submitted_to": row["submitted_to"] or "",
            "urgency_level": row["urgency_level"] or "Normal",
            "description": row["document_purpose"] or "",
            "created_at": row["created_at"] or ""
        } for row in rows]

        return {
            'success': True,
            'documents': documents,
            'total_count': len(documents)
        }
        
    except Exception as e:
        logger.error(f"Get legal documents error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            legal_db.close()
        except Exception:
            pass

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
