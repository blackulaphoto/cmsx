#!/usr/bin/env python3
"""
Legal Case Management Routes for Second Chance Jobs Platform
Professional legal compliance tracking and court date management
"""

import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import logging
import json
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from backend.shared.db_path import DB_DIR as _DB_DIR
from .models import LegalCase, CourtDate, LegalDocument, LegalDatabase
from .expungement_routes import router as expungement_router
from .expungement_service import ExpungementEligibilityEngine
from backend.auth.authorization import assert_client_access, get_client_ids_for_org
from backend.auth.service import ADMIN_ROLE, require_authenticated_user, require_role
from backend.shared.tenancy import multi_tenant_enabled, resolve_org_id

# Create FastAPI router
router = APIRouter(tags=["legal"])
LEGAL_UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads" / "legal"
LEGAL_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Include expungement routes
router.include_router(expungement_router)

# Initialize database
legal_db = None
expungement_engine = ExpungementEligibilityEngine()

def get_legal_db():
    """Get thread-safe legal database instance"""
    # Create a new instance for each request to avoid threading issues
    return LegalDatabase(str(_DB_DIR / "legal_cases.db"))

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


def _get_client_name_map(org_id: Optional[str] = None) -> Dict[str, str]:
    """Load client_id -> full name mapping from core clients DB.

    Phase 3D1: when org_id is supplied (flag on), scope the map to that org so
    no other org's client names are loaded. None preserves prior behavior.
    """
    name_map: Dict[str, str] = {}
    try:
        conn = sqlite3.connect(str(_DB_DIR / "core_clients.db"))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if org_id is not None:
            cursor.execute(
                "SELECT client_id, first_name, last_name FROM clients WHERE org_id = ?",
                (org_id,),
            )
        else:
            cursor.execute("SELECT client_id, first_name, last_name FROM clients")
        for row in cursor.fetchall():
            first_name = (row["first_name"] or "").strip()
            last_name = (row["last_name"] or "").strip()
            full_name = f"{first_name} {last_name}".strip()
            name_map[row["client_id"]] = full_name or "Unknown Client"
    except Exception as e:
        logger.warning(f"Unable to load client names from core_clients.db: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return name_map


def _get_accessible_client_ids(current_user) -> Optional[List[str]]:
    # Phase 3D1: when multi-tenancy is on, an admin's "see all" becomes "all
    # clients in my org" (not None = all app data), and a non-admin's own-client
    # set is additionally org-filtered. Flag off -> prior behavior exactly
    # (admin None = all, non-admin = own case_manager's clients).
    org_scoped = multi_tenant_enabled()
    org_id = resolve_org_id(current_user) if org_scoped else None

    if current_user.is_admin:
        if org_scoped:
            return get_client_ids_for_org(org_id)
        return None

    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(str(_DB_DIR / "core_clients.db"))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if org_scoped:
            cursor.execute(
                "SELECT client_id FROM clients WHERE case_manager_id = ? AND org_id = ?",
                (current_user.case_manager_id, org_id),
            )
        else:
            cursor.execute(
                "SELECT client_id FROM clients WHERE case_manager_id = ?",
                (current_user.case_manager_id,),
            )
        return [row["client_id"] for row in cursor.fetchall() if row["client_id"]]
    except Exception as e:
        logger.warning(f"Unable to load accessible legal client scope: {e}")
        return []
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _ensure_legal_document_schema(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(legal_documents)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    columns_to_add = {
        "file_name": "TEXT",
        "file_size": "INTEGER DEFAULT 0",
        "content_type": "TEXT",
    }

    for column_name, definition in columns_to_add.items():
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE legal_documents ADD COLUMN {column_name} {definition}")

    connection.commit()

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
async def get_legal_cases(request: Request, client_id: Optional[str] = Query(None)):
    """Get legal cases"""
    legal_db = None
    try:
        current_user = require_authenticated_user(request)
        if client_id:
            assert_client_access(current_user, client_id)
        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()
        name_map = _get_client_name_map(resolve_org_id(current_user) if multi_tenant_enabled() else None)
        accessible_client_ids = _get_accessible_client_ids(current_user)

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
        where_clauses: List[str] = []
        if client_id:
            where_clauses.append("lc.client_id = ?")
            params.append(client_id)
        if accessible_client_ids is not None:
            if not accessible_client_ids:
                return {
                    'success': True,
                    'cases': [],
                    'total_count': 0
                }
            placeholders = ", ".join(["?"] * len(accessible_client_ids))
            where_clauses.append(f"lc.client_id IN ({placeholders})")
            params.extend(accessible_client_ids)
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
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
                "client_name": name_map.get(row["client_id"], "Unknown Client"),
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
async def create_legal_case(case_data: LegalCaseCreate, request: Request):
    """Create new legal case"""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, case_data.client_id)
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
async def get_court_dates(request: Request, client_id: Optional[str] = Query(None), days_ahead: int = Query(30)):
    """Get court dates"""
    legal_db = None
    try:
        current_user = require_authenticated_user(request)
        if client_id:
            assert_client_access(current_user, client_id)
        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()
        name_map = _get_client_name_map(resolve_org_id(current_user) if multi_tenant_enabled() else None)
        accessible_client_ids = _get_accessible_client_ids(current_user)
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
        if accessible_client_ids is not None:
            if not accessible_client_ids:
                return {
                    'success': True,
                    'court_dates': [],
                    'total_count': 0
                }
            placeholders = ", ".join(["?"] * len(accessible_client_ids))
            query += f" AND cd.client_id IN ({placeholders})"
            params.extend(accessible_client_ids)
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
                "client_name": name_map.get(row["client_id"], "Unknown Client"),
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
async def create_court_date(court_date_data: CourtDateCreate, request: Request):
    """Schedule new court date"""
    legal_db = None
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, court_date_data.client_id)
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
async def get_legal_documents(request: Request, client_id: Optional[str] = Query(None), document_type: Optional[str] = Query(None, alias="type")):
    """Get legal documents"""
    legal_db = None
    try:
        current_user = require_authenticated_user(request)
        if client_id:
            assert_client_access(current_user, client_id)
        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()
        _ensure_legal_document_schema(legal_db.connection)
        name_map = _get_client_name_map(resolve_org_id(current_user) if multi_tenant_enabled() else None)
        accessible_client_ids = _get_accessible_client_ids(current_user)

        query = """
            SELECT
                document_id, case_id, client_id, document_type, document_title,
                document_purpose, document_status, due_date, submitted_to, urgency_level, created_at,
                file_path, file_name, file_size, content_type, file_format
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
        if accessible_client_ids is not None:
            if not accessible_client_ids:
                return {
                    'success': True,
                    'documents': [],
                    'total_count': 0
                }
            placeholders = ", ".join(["?"] * len(accessible_client_ids))
            query += f" AND client_id IN ({placeholders})"
            params.extend(accessible_client_ids)
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        documents = [{
            "document_id": row["document_id"],
            "doc_id": row["document_id"],
            "case_id": row["case_id"],
            "client_id": row["client_id"],
            "client_name": name_map.get(row["client_id"], "Unknown Client"),
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
            "created_at": row["created_at"] or "",
            "file_path": row["file_path"] or "",
            "file_name": row["file_name"] or "",
            "file_size": row["file_size"] or 0,
            "content_type": row["content_type"] or "",
            "file_format": row["file_format"] or "",
            "has_file": bool(row["file_path"]),
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
async def create_legal_document(document_data: LegalDocumentCreate, request: Request):
    """Create new legal document"""
    legal_db = None
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, document_data.client_id)
        legal_db = get_legal_db()
        legal_db.connect()
        cursor = legal_db.connection.cursor()
        _ensure_legal_document_schema(legal_db.connection)

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


@router.post("/documents/{document_id}/upload")
async def upload_legal_document_file(document_id: str, request: Request, file: UploadFile = File(...)):
    """Attach an uploaded file to an existing legal document record"""
    legal_db = None
    try:
        current_user = require_authenticated_user(request)
        legal_db = get_legal_db()
        legal_db.connect()
        _ensure_legal_document_schema(legal_db.connection)
        cursor = legal_db.connection.cursor()

        cursor.execute(
            "SELECT document_id, client_id, case_id, document_title FROM legal_documents WHERE document_id = ?",
            (document_id,),
        )
        document_row = cursor.fetchone()
        if not document_row:
            raise HTTPException(status_code=404, detail="Legal document not found")
        assert_client_access(current_user, document_row["client_id"])
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="A file is required")

        safe_client_id = "".join(char for char in (document_row["client_id"] or "client") if char.isalnum() or char in {"-", "_"})
        client_upload_dir = LEGAL_UPLOADS_DIR / safe_client_id
        client_upload_dir.mkdir(parents=True, exist_ok=True)

        file_extension = Path(file.filename).suffix
        stored_name = f"{document_id}_{uuid4().hex}{file_extension}"
        stored_path = client_upload_dir / stored_name
        content = await file.read()
        with open(stored_path, "wb") as buffer:
            buffer.write(content)

        relative_path = str(Path(safe_client_id) / stored_name)
        file_format = file_extension.lstrip(".").upper() if file_extension else "FILE"
        submitted_date = datetime.now().date().isoformat()

        cursor.execute(
            """
            UPDATE legal_documents
            SET file_path = ?, file_name = ?, file_size = ?, content_type = ?, file_format = ?,
                document_status = CASE
                    WHEN document_status IN ('Draft', 'Missing', 'Pending') THEN 'Received'
                    ELSE document_status
                END,
                submitted_date = COALESCE(submitted_date, ?),
                last_updated = ?
            WHERE document_id = ?
            """,
            (
                relative_path,
                file.filename,
                len(content),
                file.content_type or "application/octet-stream",
                file_format,
                submitted_date,
                datetime.now().isoformat(),
                document_id,
            ),
        )
        legal_db.connection.commit()

        return {
            "success": True,
            "message": "Legal document file uploaded successfully",
            "document_id": document_id,
            "file_name": file.filename,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload legal document file error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            legal_db.close()
        except Exception:
            pass


@router.get("/documents/{document_id}/download")
async def download_legal_document_file(document_id: str, request: Request):
    """Download the uploaded file attached to a legal document"""
    legal_db = None
    try:
        current_user = require_authenticated_user(request)
        legal_db = get_legal_db()
        legal_db.connect()
        _ensure_legal_document_schema(legal_db.connection)
        cursor = legal_db.connection.cursor()
        cursor.execute(
            "SELECT file_path, file_name, content_type, client_id FROM legal_documents WHERE document_id = ?",
            (document_id,),
        )
        document_row = cursor.fetchone()
        if not document_row:
            raise HTTPException(status_code=404, detail="Legal document not found")
        assert_client_access(current_user, document_row["client_id"])
        if not document_row["file_path"]:
            raise HTTPException(status_code=404, detail="No uploaded file is attached to this document")

        file_path = (LEGAL_UPLOADS_DIR / document_row["file_path"]).resolve()
        uploads_root = LEGAL_UPLOADS_DIR.resolve()
        try:
            file_path.relative_to(uploads_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid file path") from exc

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        return FileResponse(
            path=file_path,
            filename=document_row["file_name"] or os.path.basename(file_path),
            media_type=document_row["content_type"] or "application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download legal document file error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            legal_db.close()
        except Exception:
            pass

@router.post("/compliance-check")
async def api_compliance_check(compliance_data: ComplianceCheck, request: Request):
    """Run compliance check for client"""
    legal_db = None
    try:
        current_user = require_authenticated_user(request)
        client_id = compliance_data.client_id
        assert_client_access(current_user, client_id)

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
async def api_expungement_eligibility(expungement_data: ExpungementCheck, request: Request):
    """Check expungement eligibility"""
    legal_db = None
    try:
        current_user = require_authenticated_user(request)
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
        assert_client_access(current_user, case_row["client_id"])

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
async def api_send_reminders(request: Request):
    """Send court date reminders"""
    try:
        current_user = require_authenticated_user(request)
        require_role(current_user, [ADMIN_ROLE])
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
async def api_warrant_check(warrant_data: WarrantCheck, request: Request):
    """Warrant checks are intentionally not part of this product."""
    require_authenticated_user(request)
    raise HTTPException(
        status_code=404,
        detail="Warrant checks are not supported in this application."
    )
