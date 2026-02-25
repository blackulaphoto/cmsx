"""
Dashboard API Routes - ClickUp-style components
Handles Notes, Docs, Bookmarks, and Resources
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import uuid
from datetime import datetime
import logging

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

# Data storage paths
DATA_DIR = "databases/dashboard"
UPLOADS_DIR = "uploads/dashboard"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

def load_data(filename: str) -> list:
    """Load data from JSON file"""
    file_path = os.path.join(DATA_DIR, filename)
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
        return []

def save_data(filename: str, data: list):
    """Save data to JSON file"""
    file_path = os.path.join(DATA_DIR, filename)
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save data: {e}")

# Notes endpoints
@router.get("/dashboard/notes")
async def get_notes():
    """Get all notes"""
    try:
        notes = load_data("notes.json")
        return {"success": True, "notes": notes}
    except Exception as e:
        logger.error(f"Error getting notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/notes")
async def create_note(note: Note):
    """Create a new note"""
    try:
        notes = load_data("notes.json")
        
        new_note = {
            "id": int(datetime.now().timestamp() * 1000),
            "content": note.content,
            "pinned": note.pinned,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Add to beginning of list, with pinned notes first
        if note.pinned:
            notes.insert(0, new_note)
        else:
            # Find first non-pinned note and insert there
            insert_index = 0
            for i, existing_note in enumerate(notes):
                if not existing_note.get("pinned", False):
                    insert_index = i
                    break
            else:
                insert_index = len(notes)
            notes.insert(insert_index, new_note)
        
        save_data("notes.json", notes)
        
        return {"success": True, "note": new_note}
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/dashboard/notes/{note_id}")
async def update_note(note_id: int, note: Note):
    """Update a note"""
    try:
        notes = load_data("notes.json")
        
        for i, existing_note in enumerate(notes):
            if existing_note["id"] == note_id:
                notes[i].update({
                    "content": note.content,
                    "pinned": note.pinned,
                    "updated_at": datetime.now().isoformat()
                })
                
                # Re-sort if pinned status changed
                notes.sort(key=lambda x: (not x.get("pinned", False), x.get("created_at", "")))
                
                save_data("notes.json", notes)
                return {"success": True, "note": notes[i]}
        
        raise HTTPException(status_code=404, detail="Note not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/dashboard/notes/{note_id}")
async def delete_note(note_id: int):
    """Delete a note"""
    try:
        notes = load_data("notes.json")
        
        notes = [note for note in notes if note["id"] != note_id]
        save_data("notes.json", notes)
        
        return {"success": True, "message": "Note deleted"}
    except Exception as e:
        logger.error(f"Error deleting note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Docs endpoints
@router.get("/dashboard/docs")
async def get_docs():
    """Get all documents"""
    try:
        docs = load_data("docs.json")
        return {"success": True, "docs": docs}
    except Exception as e:
        logger.error(f"Error getting docs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/docs")
async def create_doc(doc: Doc):
    """Create a new document"""
    try:
        docs = load_data("docs.json")
        
        new_doc = {
            "id": int(datetime.now().timestamp() * 1000),
            "title": doc.title,
            "content": doc.content,
            "url": doc.url,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        docs.insert(0, new_doc)
        save_data("docs.json", docs)
        
        return {"success": True, "doc": new_doc}
    except Exception as e:
        logger.error(f"Error creating doc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/dashboard/docs/{doc_id}")
async def update_doc(doc_id: int, doc: Doc):
    """Update a document"""
    try:
        docs = load_data("docs.json")
        
        for i, existing_doc in enumerate(docs):
            if existing_doc["id"] == doc_id:
                docs[i].update({
                    "title": doc.title,
                    "content": doc.content,
                    "url": doc.url,
                    "updated_at": datetime.now().isoformat()
                })
                
                save_data("docs.json", docs)
                return {"success": True, "doc": docs[i]}
        
        raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating doc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/dashboard/docs/{doc_id}")
async def delete_doc(doc_id: int):
    """Delete a document"""
    try:
        docs = load_data("docs.json")
        
        docs = [doc for doc in docs if doc["id"] != doc_id]
        save_data("docs.json", docs)
        
        return {"success": True, "message": "Document deleted"}
    except Exception as e:
        logger.error(f"Error deleting doc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bookmarks endpoints
@router.get("/dashboard/bookmarks")
async def get_bookmarks():
    """Get all bookmarks"""
    try:
        bookmarks = load_data("bookmarks.json")
        return {"success": True, "bookmarks": bookmarks}
    except Exception as e:
        logger.error(f"Error getting bookmarks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/bookmarks")
async def create_bookmark(bookmark: Bookmark):
    """Create a new bookmark"""
    try:
        bookmarks = load_data("bookmarks.json")
        
        # Generate favicon URL
        try:
            from urllib.parse import urlparse
            domain = urlparse(bookmark.url).netloc
            favicon_url = f"https://www.google.com/s2/favicons?domain={domain}"
        except:
            favicon_url = None
        
        new_bookmark = {
            "id": int(datetime.now().timestamp() * 1000),
            "title": bookmark.title,
            "url": bookmark.url,
            "description": bookmark.description,
            "favicon": favicon_url,
            "created_at": datetime.now().isoformat()
        }
        
        bookmarks.insert(0, new_bookmark)
        save_data("bookmarks.json", bookmarks)
        
        return {"success": True, "bookmark": new_bookmark}
    except Exception as e:
        logger.error(f"Error creating bookmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/dashboard/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: int):
    """Delete a bookmark"""
    try:
        bookmarks = load_data("bookmarks.json")
        
        bookmarks = [bookmark for bookmark in bookmarks if bookmark["id"] != bookmark_id]
        save_data("bookmarks.json", bookmarks)
        
        return {"success": True, "message": "Bookmark deleted"}
    except Exception as e:
        logger.error(f"Error deleting bookmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Resources endpoints
@router.get("/dashboard/resources")
async def get_resources():
    """Get all resources"""
    try:
        resources = load_data("resources.json")
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
        
        # Create resource record
        resources = load_data("resources.json")
        
        new_resource = {
            "id": file_id,
            "name": file.filename,
            "size": len(content),
            "type": file.content_type or "application/octet-stream",
            "uploaded_at": datetime.now().isoformat(),
            "file_path": unique_filename
        }
        
        resources.insert(0, new_resource)
        save_data("resources.json", resources)
        
        return {"success": True, "resource": new_resource}
    except Exception as e:
        logger.error(f"Error uploading resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/resources/{resource_id}/download")
async def download_resource(resource_id: str):
    """Download a resource file"""
    try:
        resources = load_data("resources.json")
        
        resource = next((r for r in resources if r["id"] == resource_id), None)
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
        resources = load_data("resources.json")
        
        # Find and remove resource
        resource = next((r for r in resources if r["id"] == resource_id), None)
        if resource:
            # Delete file
            file_path = os.path.join(UPLOADS_DIR, resource["file_path"])
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Remove from list
            resources = [r for r in resources if r["id"] != resource_id]
            save_data("resources.json", resources)
        
        return {"success": True, "message": "Resource deleted"}
    except Exception as e:
        logger.error(f"Error deleting resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard stats endpoint
@router.get("/dashboard/content-stats")
async def get_dashboard_stats():
    """Get dashboard component statistics"""
    try:
        notes = load_data("notes.json")
        docs = load_data("docs.json")
        bookmarks = load_data("bookmarks.json")
        resources = load_data("resources.json")
        
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
