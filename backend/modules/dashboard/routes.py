"""
Dashboard API Routes - ClickUp-style components
Handles Notes, Docs, Bookmarks, and Resources
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import logging
from urllib.parse import urlparse

from backend.shared.database.workspace_store import workspace_store

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

# Notes endpoints
@router.get("/dashboard/notes")
async def get_notes():
    """Get all notes"""
    try:
        notes = workspace_store.list_dashboard_items("dashboard_notes", DEFAULT_CASE_MANAGER_ID)
        for note in notes:
            note["pinned"] = bool(note.get("pinned"))
        return {"success": True, "notes": notes}
    except Exception as e:
        logger.error(f"Error getting notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/notes")
async def create_note(note: Note):
    """Create a new note"""
    try:
        new_note = workspace_store.create_dashboard_note(DEFAULT_CASE_MANAGER_ID, note.content, note.pinned)
        return {"success": True, "note": new_note}
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/dashboard/notes/{note_id}")
async def update_note(note_id: str, note: Note):
    """Update a note"""
    try:
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
async def delete_note(note_id: str):
    """Delete a note"""
    try:
        workspace_store.delete_dashboard_item("dashboard_notes", note_id)
        return {"success": True, "message": "Note deleted"}
    except Exception as e:
        logger.error(f"Error deleting note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Docs endpoints
@router.get("/dashboard/docs")
async def get_docs():
    """Get all documents"""
    try:
        docs = workspace_store.list_dashboard_items("dashboard_docs", DEFAULT_CASE_MANAGER_ID)
        return {"success": True, "docs": docs}
    except Exception as e:
        logger.error(f"Error getting docs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/docs")
async def create_doc(doc: Doc):
    """Create a new document"""
    try:
        new_doc = workspace_store.create_dashboard_doc(DEFAULT_CASE_MANAGER_ID, doc.title, doc.content, doc.url)
        return {"success": True, "doc": new_doc}
    except Exception as e:
        logger.error(f"Error creating doc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/dashboard/docs/{doc_id}")
async def update_doc(doc_id: str, doc: Doc):
    """Update a document"""
    try:
        updated = workspace_store.update_dashboard_doc(doc_id, doc.title, doc.content, doc.url)
        if not updated:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"success": True, "doc": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating doc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/dashboard/docs/{doc_id}")
async def delete_doc(doc_id: str):
    """Delete a document"""
    try:
        workspace_store.delete_dashboard_item("dashboard_docs", doc_id)
        return {"success": True, "message": "Document deleted"}
    except Exception as e:
        logger.error(f"Error deleting doc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bookmarks endpoints
@router.get("/dashboard/bookmarks")
async def get_bookmarks():
    """Get all bookmarks"""
    try:
        bookmarks = workspace_store.list_dashboard_items("dashboard_bookmarks", DEFAULT_CASE_MANAGER_ID)
        return {"success": True, "bookmarks": bookmarks}
    except Exception as e:
        logger.error(f"Error getting bookmarks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/bookmarks")
async def create_bookmark(bookmark: Bookmark):
    """Create a new bookmark"""
    try:
        try:
            domain = urlparse(bookmark.url).netloc
            favicon_url = f"https://www.google.com/s2/favicons?domain={domain}"
        except Exception:
            favicon_url = None
        new_bookmark = workspace_store.create_dashboard_bookmark(
            DEFAULT_CASE_MANAGER_ID,
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
async def delete_bookmark(bookmark_id: str):
    """Delete a bookmark"""
    try:
        workspace_store.delete_dashboard_item("dashboard_bookmarks", bookmark_id)
        return {"success": True, "message": "Bookmark deleted"}
    except Exception as e:
        logger.error(f"Error deleting bookmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Resources endpoints
@router.get("/dashboard/resources")
async def get_resources():
    """Get all resources"""
    try:
        resources = workspace_store.list_dashboard_items("dashboard_resources", DEFAULT_CASE_MANAGER_ID)
        return {"success": True, "resources": resources}
    except Exception as e:
        logger.error(f"Error getting resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/resources")
async def upload_resource(file: UploadFile = File(...)):
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
            DEFAULT_CASE_MANAGER_ID,
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
async def download_resource(resource_id: str):
    """Download a resource file"""
    try:
        resource = workspace_store.get_dashboard_resource(resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        
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
async def delete_resource(resource_id: str):
    """Delete a resource"""
    try:
        resource = workspace_store.get_dashboard_resource(resource_id)
        if resource:
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
async def get_dashboard_stats():
    """Get dashboard component statistics"""
    try:
        notes = workspace_store.list_dashboard_items("dashboard_notes", DEFAULT_CASE_MANAGER_ID)
        docs = workspace_store.list_dashboard_items("dashboard_docs", DEFAULT_CASE_MANAGER_ID)
        bookmarks = workspace_store.list_dashboard_items("dashboard_bookmarks", DEFAULT_CASE_MANAGER_ID)
        resources = workspace_store.list_dashboard_items("dashboard_resources", DEFAULT_CASE_MANAGER_ID)
        
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
