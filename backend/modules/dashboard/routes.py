"""
Dashboard API Routes - ClickUp-style components
Handles Notes, Docs, Bookmarks, and Resources
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import html
import os
import re
import uuid
import logging
import sqlite3
from urllib.parse import urlparse
from datetime import datetime, timedelta

from backend.shared.database.workspace_store import workspace_store
from backend.auth.service import ADMIN_ROLE, require_authenticated_user, require_role
from backend.shared.db_path import DB_DIR as _DB_DIR

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models
class Note(BaseModel):
    id: Optional[int] = None
    content: str
    pinned: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class Doc(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class Bookmark(BaseModel):
    id: Optional[int] = None
    title: str
    url: str
    description: Optional[str] = None
    favicon: Optional[str] = None
    created_at: Optional[str] = None

class Resource(BaseModel):
    id: Optional[str] = None
    name: str
    size: int
    type: str
    uploaded_at: Optional[str] = None
    file_path: Optional[str] = None

UPLOADS_DIR = "uploads/dashboard"

# Ensure directories exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
DEFAULT_CASE_MANAGER_ID = "cm_001"


def _safe_download_name(title: str, extension: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", (title or "document").strip()).strip("._")
    return f"{base or 'document'}.{extension}"


def _plain_document_text(doc: Dict[str, Any]) -> str:
    parts = [
        doc.get("title") or "Untitled Document",
        "",
        doc.get("content") or "",
    ]
    if doc.get("url"):
        parts.extend(["", f"Reference URL: {doc['url']}"])
    return "\n".join(parts).strip() + "\n"


def _html_document_text(doc: Dict[str, Any]) -> str:
    title = html.escape(doc.get("title") or "Untitled Document")
    content = html.escape(doc.get("content") or "").replace("\n", "<br>\n")
    url_block = ""
    if doc.get("url"):
        url = html.escape(doc["url"])
        url_block = f'<p class="reference">Reference URL: <a href="{url}">{url}</a></p>'
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.5; margin: 48px; color: #111827; }}
    h1 {{ font-size: 24px; margin-bottom: 24px; }}
    .content {{ white-space: normal; }}
    .reference {{ margin-top: 32px; color: #4b5563; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="content">{content}</div>
  {url_block}
</body>
</html>
"""


def _pdf_escape(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _wrap_text(text: str, width: int = 92) -> List[str]:
    lines: List[str] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        while len(line) > width:
            split_at = line.rfind(" ", 0, width)
            if split_at <= 0:
                split_at = width
            lines.append(line[:split_at].strip())
            line = line[split_at:].strip()
        lines.append(line)
    return lines or [""]


def _render_pdf_bytes(doc: Dict[str, Any]) -> bytes:
    lines = _wrap_text(_plain_document_text(doc))
    pages = [lines[index:index + 46] for index in range(0, len(lines), 46)] or [[]]
    objects: List[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
    ]
    page_object_ids: List[int] = []

    for page_lines in pages:
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_object_ids.append(page_id)
        text_commands = ["BT", "/F1 10 Tf", "50 760 Td", "14 TL"]
        for line in page_lines:
            text_commands.append(f"({_pdf_escape(line)}) Tj")
            text_commands.append("T*")
        text_commands.append("ET")
        content = "\n".join(text_commands).encode("latin-1", errors="replace")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>".encode()
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(output)


def _current_scope(request: Request) -> str:
    return require_authenticated_user(request).case_manager_id


def _dict_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_count_query(conn: sqlite3.Connection, query: str, params: tuple = ()) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return 0


def _load_case_manager_names() -> Dict[str, str]:
    name_map: Dict[str, str] = {}
    try:
        with _dict_connection(str(_DB_DIR / "auth.db")) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT case_manager_id, full_name FROM user_profiles WHERE is_active = 1")
            for row in cursor.fetchall():
                if row["case_manager_id"]:
                    name_map[row["case_manager_id"]] = row["full_name"] or row["case_manager_id"]
    except Exception:
        pass
    return name_map


def _get_supervisor_overview() -> Dict[str, Any]:
    today = datetime.now().date().isoformat()
    cutoff = (datetime.now() - timedelta(days=7)).date().isoformat()
    name_map = _load_case_manager_names()

    with _dict_connection(str(_DB_DIR / "core_clients.db")) as core_conn:
        core_cursor = core_conn.cursor()
        core_cursor.execute("""
            SELECT
                COALESCE(NULLIF(TRIM(case_manager_id), ''), 'unassigned') AS case_manager_id,
                COUNT(*) AS total_clients,
                SUM(CASE WHEN LOWER(COALESCE(risk_level, '')) = 'high' THEN 1 ELSE 0 END) AS high_risk_clients,
                SUM(CASE WHEN DATE(COALESCE(created_at, CURRENT_TIMESTAMP)) >= DATE(?) THEN 1 ELSE 0 END) AS recent_intakes,
                SUM(CASE WHEN TRIM(COALESCE(barriers, '')) <> '' THEN 1 ELSE 0 END) AS clients_with_barriers
            FROM clients
            GROUP BY COALESCE(NULLIF(TRIM(case_manager_id), ''), 'unassigned')
            ORDER BY total_clients DESC, case_manager_id
        """, (cutoff,))
        manager_rows = core_cursor.fetchall()

    case_managers: List[Dict[str, Any]] = []
    all_client_ids: List[str] = []
    all_high_risk = 0
    total_clients = 0
    clients_with_barriers = 0

    for row in manager_rows:
        case_manager_id = row["case_manager_id"]
        with _dict_connection(str(_DB_DIR / "core_clients.db")) as core_conn:
            client_cursor = core_conn.cursor()
            client_cursor.execute(
                "SELECT client_id FROM clients WHERE COALESCE(NULLIF(TRIM(case_manager_id), ''), 'unassigned') = ?",
                (case_manager_id,),
            )
            client_ids = [client_row["client_id"] for client_row in client_cursor.fetchall()]

        all_client_ids.extend(client_ids)
        total_clients += int(row["total_clients"] or 0)
        all_high_risk += int(row["high_risk_clients"] or 0)
        clients_with_barriers += int(row["clients_with_barriers"] or 0)

        overdue_reminders = 0
        open_benefits = 0
        active_legal = 0
        active_fmla = 0

        try:
            with _dict_connection(str(_DB_DIR / "reminders.db")) as reminders_conn:
                overdue_reminders = _safe_count_query(
                    reminders_conn,
                    """
                    SELECT COUNT(*)
                    FROM active_reminders
                    WHERE case_manager_id = ?
                      AND status = 'Active'
                      AND DATE(due_date) < DATE(?)
                    """,
                    (case_manager_id, today),
                )
        except Exception:
            overdue_reminders = 0

        if client_ids:
            placeholders = ",".join("?" for _ in client_ids)
            try:
                with _dict_connection(str(_DB_DIR / "unified_platform.db")) as benefits_conn:
                    open_benefits = _safe_count_query(
                        benefits_conn,
                        f"""
                        SELECT COUNT(*)
                        FROM benefits_applications
                        WHERE client_id IN ({placeholders})
                          AND LOWER(COALESCE(status, '')) NOT IN ('approved', 'denied', 'closed', 'expired')
                        """,
                        tuple(client_ids),
                    )
            except Exception:
                open_benefits = 0

            try:
                with _dict_connection(str(_DB_DIR / "legal_cases.db")) as legal_conn:
                    active_legal = _safe_count_query(
                        legal_conn,
                        f"""
                        SELECT COUNT(*)
                        FROM legal_cases
                        WHERE client_id IN ({placeholders})
                          AND COALESCE(is_active, 1) = 1
                        """,
                        tuple(client_ids),
                    )
            except Exception:
                active_legal = 0

        try:
            with _dict_connection(str(_DB_DIR / "fmla.db")) as fmla_conn:
                active_fmla = _safe_count_query(
                    fmla_conn,
                    """
                    SELECT COUNT(*)
                    FROM fmla_cases
                    WHERE COALESCE(assigned_case_manager, '') = ?
                      AND LOWER(COALESCE(status, '')) <> 'closed'
                    """,
                    (case_manager_id,),
                )
        except Exception:
            active_fmla = 0

        completion_rate = 0
        total_work_items = overdue_reminders + open_benefits + active_legal
        if total_work_items > 0:
            completion_rate = max(0, round(100 - ((overdue_reminders / total_work_items) * 100)))

        case_managers.append({
            "case_manager_id": case_manager_id,
            "case_manager_name": name_map.get(case_manager_id, case_manager_id.replace("_", " ").title()),
            "total_clients": int(row["total_clients"] or 0),
            "high_risk_clients": int(row["high_risk_clients"] or 0),
            "recent_intakes": int(row["recent_intakes"] or 0),
            "clients_with_barriers": int(row["clients_with_barriers"] or 0),
            "overdue_reminders": overdue_reminders,
            "open_benefits_applications": open_benefits,
            "active_legal_cases": active_legal,
            "active_fmla_cases": active_fmla,
            "completion_rate": completion_rate,
        })

    highest_overdue = sorted(case_managers, key=lambda item: item["overdue_reminders"], reverse=True)[:5]
    highest_risk = sorted(case_managers, key=lambda item: item["high_risk_clients"], reverse=True)[:5]

    return {
        "generated_at": datetime.now().isoformat(),
        "team_summary": {
            "case_manager_count": len(case_managers),
            "total_clients": total_clients,
            "high_risk_clients": all_high_risk,
            "clients_with_barriers": clients_with_barriers,
            "overdue_reminders": sum(item["overdue_reminders"] for item in case_managers),
            "open_benefits_applications": sum(item["open_benefits_applications"] for item in case_managers),
            "active_legal_cases": sum(item["active_legal_cases"] for item in case_managers),
            "active_fmla_cases": sum(item["active_fmla_cases"] for item in case_managers),
        },
        "case_managers": case_managers,
        "alerts": {
            "highest_overdue_workloads": highest_overdue,
            "highest_risk_caseloads": highest_risk,
        }
    }

# Notes endpoints
@router.get("/dashboard/notes")
async def get_notes(request: Request):
    """Get all notes"""
    try:
        notes = workspace_store.list_dashboard_items("dashboard_notes", _current_scope(request))
        for note in notes:
            note["pinned"] = bool(note.get("pinned"))
        return {"success": True, "notes": notes}
    except Exception as e:
        logger.error(f"Error getting notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/notes")
async def create_note(note: Note, request: Request):
    """Create a new note"""
    try:
        new_note = workspace_store.create_dashboard_note(_current_scope(request), note.content, note.pinned)
        return {"success": True, "note": new_note}
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/dashboard/notes/{note_id}")
async def update_note(note_id: str, note: Note, request: Request):
    """Update a note"""
    try:
        current_user = require_authenticated_user(request)
        notes = workspace_store.list_dashboard_items("dashboard_notes", current_user.case_manager_id)
        if not any(item["id"] == note_id for item in notes) and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        updated = workspace_store.update_dashboard_note(note_id, note.content, note.pinned)
        if not updated:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"success": True, "note": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/dashboard/notes/{note_id}")
async def delete_note(note_id: str, request: Request):
    """Delete a note"""
    try:
        current_user = require_authenticated_user(request)
        notes = workspace_store.list_dashboard_items("dashboard_notes", current_user.case_manager_id)
        if not any(item["id"] == note_id for item in notes) and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        workspace_store.delete_dashboard_item("dashboard_notes", note_id)
        return {"success": True, "message": "Note deleted"}
    except Exception as e:
        logger.error(f"Error deleting note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Docs endpoints
@router.get("/dashboard/docs")
async def get_docs(request: Request):
    """Get all documents"""
    try:
        docs = workspace_store.list_dashboard_items("dashboard_docs", _current_scope(request))
        return {"success": True, "docs": docs}
    except Exception as e:
        logger.error(f"Error getting docs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/docs")
async def create_doc(doc: Doc, request: Request):
    """Create a new document"""
    try:
        new_doc = workspace_store.create_dashboard_doc(_current_scope(request), doc.title, doc.content, doc.url)
        return {"success": True, "doc": new_doc}
    except Exception as e:
        logger.error(f"Error creating doc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/dashboard/docs/{doc_id}")
async def update_doc(doc_id: str, doc: Doc, request: Request):
    """Update a document"""
    try:
        current_user = require_authenticated_user(request)
        docs = workspace_store.list_dashboard_items("dashboard_docs", current_user.case_manager_id)
        if not any(item["id"] == doc_id for item in docs) and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        updated = workspace_store.update_dashboard_doc(doc_id, doc.title, doc.content, doc.url)
        if not updated:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"success": True, "doc": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating doc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/docs/{doc_id}/download")
async def download_doc(doc_id: str, request: Request, format: str = Query("pdf")):
    """Download a saved document as PDF, text, markdown, or print-ready HTML."""
    try:
        current_user = require_authenticated_user(request)
        doc = workspace_store.get_dashboard_doc(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc.get("case_manager_id") != current_user.case_manager_id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        normalized_format = (format or "pdf").strip().lower()
        if normalized_format not in {"pdf", "txt", "md", "html"}:
            raise HTTPException(status_code=400, detail="Unsupported document format")

        if normalized_format == "html":
            filename = _safe_download_name(doc.get("title") or "document", "html")
            return Response(
                content=_html_document_text(doc),
                media_type="text/html; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        if normalized_format in {"txt", "md"}:
            filename = _safe_download_name(doc.get("title") or "document", normalized_format)
            return Response(
                content=_plain_document_text(doc),
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        filename = _safe_download_name(doc.get("title") or "document", "pdf")
        return Response(
            content=_render_pdf_bytes(doc),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/dashboard/docs/{doc_id}")
async def delete_doc(doc_id: str, request: Request):
    """Delete a document"""
    try:
        current_user = require_authenticated_user(request)
        docs = workspace_store.list_dashboard_items("dashboard_docs", current_user.case_manager_id)
        if not any(item["id"] == doc_id for item in docs) and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        workspace_store.delete_dashboard_item("dashboard_docs", doc_id)
        return {"success": True, "message": "Document deleted"}
    except Exception as e:
        logger.error(f"Error deleting doc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bookmarks endpoints
@router.get("/dashboard/bookmarks")
async def get_bookmarks(request: Request):
    """Get all bookmarks"""
    try:
        bookmarks = workspace_store.list_dashboard_items("dashboard_bookmarks", _current_scope(request))
        return {"success": True, "bookmarks": bookmarks}
    except Exception as e:
        logger.error(f"Error getting bookmarks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/bookmarks")
async def create_bookmark(bookmark: Bookmark, request: Request):
    """Create a new bookmark"""
    try:
        try:
            domain = urlparse(bookmark.url).netloc
            favicon_url = f"https://www.google.com/s2/favicons?domain={domain}"
        except Exception:
            favicon_url = None
        new_bookmark = workspace_store.create_dashboard_bookmark(
            _current_scope(request),
            bookmark.title,
            bookmark.url,
            bookmark.description,
            favicon_url,
        )
        return {"success": True, "bookmark": new_bookmark}
    except Exception as e:
        logger.error(f"Error creating bookmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/dashboard/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: str, request: Request):
    """Delete a bookmark"""
    try:
        current_user = require_authenticated_user(request)
        bookmarks = workspace_store.list_dashboard_items("dashboard_bookmarks", current_user.case_manager_id)
        if not any(item["id"] == bookmark_id for item in bookmarks) and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        workspace_store.delete_dashboard_item("dashboard_bookmarks", bookmark_id)
        return {"success": True, "message": "Bookmark deleted"}
    except Exception as e:
        logger.error(f"Error deleting bookmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Resources endpoints
@router.get("/dashboard/resources")
async def get_resources(request: Request):
    """Get all resources"""
    try:
        resources = workspace_store.list_dashboard_items("dashboard_resources", _current_scope(request))
        return {"success": True, "resources": resources}
    except Exception as e:
        logger.error(f"Error getting resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/resources")
async def upload_resource(request: Request, file: UploadFile = File(...)):
    """Upload a new resource file"""
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(UPLOADS_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        new_resource = workspace_store.create_dashboard_resource(
            _current_scope(request),
            resource_id=file_id,
            name=file.filename,
            size=len(content),
            content_type=file.content_type or "application/octet-stream",
            file_path=unique_filename,
        )
        return {"success": True, "resource": new_resource}
    except Exception as e:
        logger.error(f"Error uploading resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/resources/{resource_id}/download")
async def download_resource(resource_id: str, request: Request):
    """Download a resource file"""
    try:
        current_user = require_authenticated_user(request)
        resource = workspace_store.get_dashboard_resource(resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        if resource.get("case_manager_id") != current_user.case_manager_id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        file_path = os.path.join(UPLOADS_DIR, resource["file_path"])
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            filename=resource["name"],
            media_type=resource["type"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/dashboard/resources/{resource_id}")
async def delete_resource(resource_id: str, request: Request):
    """Delete a resource"""
    try:
        current_user = require_authenticated_user(request)
        resource = workspace_store.get_dashboard_resource(resource_id)
        if resource:
            if resource.get("case_manager_id") != current_user.case_manager_id and not current_user.is_admin:
                raise HTTPException(status_code=403, detail="Access denied")
            file_path = os.path.join(UPLOADS_DIR, resource["file_path"])
            if os.path.exists(file_path):
                os.remove(file_path)
            workspace_store.delete_dashboard_item("dashboard_resources", resource_id)
        
        return {"success": True, "message": "Resource deleted"}
    except Exception as e:
        logger.error(f"Error deleting resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard stats endpoint
@router.get("/dashboard/content-stats")
async def get_dashboard_stats(request: Request):
    """Get dashboard component statistics"""
    try:
        scope = _current_scope(request)
        notes = workspace_store.list_dashboard_items("dashboard_notes", scope)
        docs = workspace_store.list_dashboard_items("dashboard_docs", scope)
        bookmarks = workspace_store.list_dashboard_items("dashboard_bookmarks", scope)
        resources = workspace_store.list_dashboard_items("dashboard_resources", scope)
        
        stats = {
            "notes_count": len(notes),
            "pinned_notes": len([n for n in notes if n.get("pinned", False)]),
            "docs_count": len(docs),
            "bookmarks_count": len(bookmarks),
            "resources_count": len(resources),
            "total_file_size": sum(r.get("size", 0) for r in resources)
        }
        
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/supervisor/overview")
async def get_supervisor_overview(request: Request, supervisor_id: str = Query("supervisor")):
    """Get cross-module supervisor reporting overview"""
    try:
        current_user = require_authenticated_user(request)
        require_role(current_user, [ADMIN_ROLE])
        overview = _get_supervisor_overview()
        overview["supervisor_id"] = supervisor_id
        return {"success": True, "overview": overview}
    except Exception as e:
        logger.error(f"Error getting supervisor overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
