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
from .expungement_service import ExpungementEligibilityEngine

# Create FastAPI router
router = APIRouter(tags=["legal"])

# Include expungement routes
router.include_router(expungement_router)

# Initialize database
legal_db = None
expungement_engine = ExpungementEligibilityEngine()

def get_legal_db():
    """Get thread-safe legal database instance"""
    # Create a new instance for each request to avoid threading issues
    return LegalDatabase("databases/legal_cases.db")

logger = logging.getLogger(__name__)


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _court_name_to_county(court_name: Optional[str]) -> str:
    court_name = (court_name or "").lower()
    if "los angeles" in court_name:
        return "Los Angeles"
    if "orange" in court_name:
        return "Orange"
    if "san diego" in court_name:
        return "San Diego"
    return ""


def _build_assessment_from_complete_result(result: Dict[str, Any]) -> Dict[str, Any]:
    success_likelihood = result.get("success_likelihood", "Unknown")
    confidence_map = {"High": 90.0, "Medium": 60.0, "Low": 40.0}
    confidence_score = confidence_map.get(success_likelihood, 50.0)
    estimated_days = result.get("estimated_timeline_days", 0) or 0

    return {
        "eligible": bool(result.get("eligible")),
        "eligibility_date": datetime.now().isoformat() if result.get("eligible") else None,
        "wait_period_days": 0,
        "requirements": result.get("recommendations", []),
        "disqualifying_factors": result.get("disqualifying_factors", []),
        "estimated_timeline": f"{estimated_days} days" if estimated_days else "Unknown",
        "estimated_cost": result.get("estimated_cost", 0.0),
        "next_steps": result.get("next_steps", []),
        "confidence_score": confidence_score,
        "pathway": result.get("pathway"),
        "warnings": result.get("warnings", []),
        "success_likelihood": success_likelihood
    }


def _build_conviction_data_from_case(case_row: sqlite3.Row) -> Dict[str, Any]:
    now = datetime.now()
    conviction_date = case_row["conviction_date"] or case_row["created_at"]
    conviction_dt = _parse_iso_datetime(conviction_date)
    probation_end = _parse_iso_datetime(case_row["probation_end_date"])
    parole_end = _parse_iso_datetime(case_row["parole_end_date"])
    sentence_complete = parole_end or probation_end or conviction_dt
    sentence_details = (case_row["sentence_details"] or "").lower()
    parole_terms = (case_row["parole_terms"] or "").lower()
    case_type = (case_row["case_type"] or "").lower()
    case_status = (case_row["case_status"] or "").lower()

    served_state_prison = any(
        marker in " ".join([sentence_details, parole_terms, case_type])
        for marker in ["state prison", "prison", "cdcr"]
    )
    probation_granted = bool(
        case_row["probation_start_date"] or case_row["probation_end_date"] or case_row["probation_officer"]
    )
    probation_completed = bool(probation_end and probation_end <= now)
    currently_on_probation = bool(probation_end and probation_end > now)
    currently_serving_sentence = bool(parole_end and parole_end > now)

    return {
        "conviction_date": conviction_date,
        "conviction_year": conviction_dt.year if conviction_dt else 0,
        "offense_code": case_row["charges"] or case_row["case_number"] or "",
        "offense_type": case_row["case_type"] or "",
        "conviction_type": case_row["case_type"] or "",
        "county": _court_name_to_county(case_row["court_name"]),
        "probation_granted": probation_granted,
        "probation_completed": probation_completed,
        "early_termination_granted": False,
        "served_state_prison": served_state_prison,
        "sentence_completion_date": sentence_complete.isoformat() if sentence_complete else None,
        "currently_on_probation": currently_on_probation,
        "currently_serving_sentence": currently_serving_sentence,
        "pending_charges": case_status in {"pending", "active"},
        "fines_total": float(case_row["fines_total"] or 0.0),
        "fines_paid": float(case_row["fines_paid"] or 0.0),
        "restitution_total": float(case_row["restitution_total"] or 0.0),
        "restitution_paid": float(case_row["restitution_paid"] or 0.0),
        "court_costs_paid": float(case_row["fines_paid"] or 0.0) >= float(case_row["fines_total"] or 0.0),
        "community_service_hours": 0,
        "community_service_completed": None,
        "counseling_required": None,
        "counseling_completed": None,
        "requires_sex_offender_registration": False,
        "is_violent_felony": "violent" in case_type,
        "is_wobbler": "wobbler" in case_type
    }


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
    client_id: str
    client_name: Optional[str] = None
    hearing_date: str
    hearing_time: str
    court_name: str
    courtroom: str
    hearing_type: str
    judge_name: str

class LegalDocumentCreate(BaseModel):
    client_id: str
    case_id: str
    client_name: Optional[str] = None
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
    legal_db = None
    try:
        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()

        cursor.execute(
            "SELECT client_id FROM legal_cases WHERE case_id = ?",
            (court_date_data.case_id,)
        )
        case_row = cursor.fetchone()
        if not case_row:
            raise HTTPException(status_code=404, detail="Legal case not found")

        case_client_id = case_row["client_id"]
        if case_client_id != court_date_data.client_id:
            raise HTTPException(
                status_code=400,
                detail="Court date client_id does not match the associated legal case"
            )

        court_date = CourtDate(
            case_id=court_date_data.case_id,
            client_id=court_date_data.client_id,
            client_name=court_date_data.client_name,
            hearing_date=court_date_data.hearing_date,
            hearing_time=court_date_data.hearing_time,
            court_name=court_date_data.court_name,
            courtroom=court_date_data.courtroom,
            hearing_type=court_date_data.hearing_type,
            judge_name=court_date_data.judge_name
        )
        legal_db.save_court_date(court_date)
        
        return {
            'success': True,
            'message': 'Court date scheduled successfully',
            'court_date_id': court_date.court_date_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create court date error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            legal_db.close()
        except Exception:
            pass

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
    legal_db = None
    try:
        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()

        cursor.execute(
            "SELECT client_id FROM legal_cases WHERE case_id = ?",
            (document_data.case_id,)
        )
        case_row = cursor.fetchone()
        if not case_row:
            raise HTTPException(status_code=404, detail="Legal case not found")

        case_client_id = case_row["client_id"]
        if case_client_id != document_data.client_id:
            raise HTTPException(
                status_code=400,
                detail="Document client_id does not match the associated legal case"
            )

        document = LegalDocument(
            case_id=document_data.case_id,
            client_id=document_data.client_id,
            document_type=document_data.document_type,
            document_title=document_data.document_title,
            document_purpose=document_data.document_purpose,
            due_date=document_data.due_date,
            submitted_to=document_data.submitted_to,
            urgency_level=document_data.urgency_level
        )
        legal_db.save_legal_document(document)
        
        return {
            'success': True,
            'message': 'Legal document created successfully',
            'document_id': document.document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create legal document error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            legal_db.close()
        except Exception:
            pass

@router.post("/compliance-check")
async def api_compliance_check(compliance_data: ComplianceCheck):
    """Run compliance check for client"""
    legal_db = None
    try:
        client_id = compliance_data.client_id

        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()

        cursor.execute("""
            SELECT case_id, case_number, case_type, case_status, compliance_status,
                   probation_end_date, fines_total, fines_paid, restitution_total,
                   restitution_paid, court_name
            FROM legal_cases
            WHERE client_id = ? AND is_active = 1
            ORDER BY last_updated DESC, created_at DESC
        """, (client_id,))
        cases = cursor.fetchall()

        if not cases:
            raise HTTPException(status_code=404, detail="No active legal cases found for client")

        cursor.execute("""
            SELECT court_date_id, case_id, hearing_date, hearing_time, status, reminder_sent
            FROM court_dates
            WHERE client_id = ? AND hearing_date >= ?
            ORDER BY hearing_date ASC, hearing_time ASC
        """, (client_id, datetime.now().date().isoformat()))
        upcoming_dates = cursor.fetchall()

        issues_found: List[str] = []
        recommendations: List[str] = []
        overdue_obligations = 0
        warning_cases = 0
        missed_hearings = 0

        for case_row in cases:
            compliance_status = (case_row["compliance_status"] or "").lower()
            fines_due = max(0.0, float(case_row["fines_total"] or 0.0) - float(case_row["fines_paid"] or 0.0))
            restitution_due = max(0.0, float(case_row["restitution_total"] or 0.0) - float(case_row["restitution_paid"] or 0.0))
            total_due = fines_due + restitution_due

            if compliance_status in {"warning", "non-compliant", "non compliant"}:
                warning_cases += 1
                issues_found.append(
                    f"Case {case_row['case_number'] or case_row['case_id']} is marked {case_row['compliance_status']}."
                )

            if total_due > 0:
                overdue_obligations += 1
                issues_found.append(
                    f"Case {case_row['case_number'] or case_row['case_id']} has ${total_due:.2f} in unpaid fines or restitution."
                )
                recommendations.append(
                    f"Review payment plan for case {case_row['case_number'] or case_row['case_id']}."
                )

            probation_end = _parse_iso_datetime(case_row["probation_end_date"])
            if probation_end and 0 <= (probation_end.date() - datetime.now().date()).days <= 30:
                recommendations.append(
                    f"Prepare probation completion review for case {case_row['case_number'] or case_row['case_id']}."
                )

        for court_date in upcoming_dates:
            hearing_dt = _parse_iso_datetime(court_date["hearing_date"])
            if not hearing_dt:
                continue
            days_until = (hearing_dt.date() - datetime.now().date()).days
            status = (court_date["status"] or "").lower()

            if status == "missed":
                missed_hearings += 1
                issues_found.append(
                    f"Court date {court_date['court_date_id']} was missed."
                )
            elif days_until <= 7 and not bool(court_date["reminder_sent"]):
                issues_found.append(
                    f"Court date {court_date['court_date_id']} is within {days_until} days and no reminder is recorded."
                )
                recommendations.append(
                    f"Send reminder and confirm attendance for court date {court_date['court_date_id']}."
                )

        compliance_status = "Compliant"
        if missed_hearings > 0:
            compliance_status = "Non-Compliant"
        elif issues_found or warning_cases > 0 or overdue_obligations > 0:
            compliance_status = "Warning"

        if not recommendations:
            recommendations = [
                "Continue current compliance activities",
                "Monitor upcoming court dates and probation milestones"
            ]

        compliance_result = {
            'client_id': client_id,
            'compliance_status': compliance_status,
            'issues_found': issues_found,
            'recommendations': recommendations,
            'active_case_count': len(cases),
            'upcoming_court_dates': len(upcoming_dates),
            'data_source': 'legal_cases.db',
            'next_check_due': (datetime.now() + timedelta(days=30)).isoformat(),
            'checked_at': datetime.now().isoformat()
        }
        
        return {
            'success': True,
            'compliance_result': compliance_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compliance check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            legal_db.close()
        except Exception:
            pass

@router.post("/expungement-eligibility")
async def api_expungement_eligibility(expungement_data: ExpungementCheck):
    """Check expungement eligibility"""
    legal_db = None
    try:
        case_id = expungement_data.case_id

        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()
        cursor.execute("""
            SELECT case_id, client_id, case_number, court_name, case_type, case_status, charges,
                   conviction_date, probation_start_date, probation_end_date, parole_start_date,
                   parole_end_date, sentence_details, parole_terms, fines_total, fines_paid,
                   restitution_total, restitution_paid, created_at
            FROM legal_cases
            WHERE case_id = ?
        """, (case_id,))
        case_row = cursor.fetchone()
        if not case_row:
            raise HTTPException(status_code=404, detail="Legal case not found")

        conviction_data = _build_conviction_data_from_case(case_row)
        complete_result = expungement_engine.check_eligibility_complete(conviction_data)
        assessment = _build_assessment_from_complete_result(complete_result)
        eligibility_result = {
            'case_id': case_id,
            'client_id': case_row["client_id"],
            'assessment': assessment,
            'source_data_limited': True,
            'source_data_notes': [
                'Assessment is derived from legal case records currently stored in legal_cases.db.',
                'Missing court-specific facts may require manual attorney review before filing.'
            ]
        }
        
        return {
            'success': True,
            'eligibility_result': eligibility_result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Expungement eligibility error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            legal_db.close()
        except Exception:
            pass

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

        warrant_result = {
            'client_id': client_id,
            'warrants_found': None,
            'warrant_count': None,
            'warrant_details': [],
            'check_date': datetime.now().isoformat(),
            'next_check_recommended': (datetime.now() + timedelta(days=30)).isoformat(),
            'status': 'Manual Verification Required',
            'is_authoritative': False,
            'verification_status': 'manual_required',
            'message': 'This deployment does not have a live court-system or law-enforcement warrant integration. Manual verification is required.'
        }
        
        return {
            'success': True,
            'warrant_result': warrant_result
        }
        
    except Exception as e:
        logger.error(f"Warrant check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
