#!/usr/bin/env python3
"""
NEW UNIFIED CASE MANAGEMENT PLATFORM - 9-Database Architecture
Implements the precise database architecture with AI full CRUD permissions
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import uvicorn
import traceback

# Load environment
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import our new database access layer
from shared.database.new_access_layer import (
    db_access, 
    core_clients_service, 
    ai_service,
    DatabaseAccessLayer,
    CoreClientsService,
    AIAssistantService
)

# Import search system
try:
    from search.routes import router as search_router
    SEARCH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Search system not available: {e}")
    SEARCH_AVAILABLE = False

# Import sophisticated reminders system
try:
    from modules.reminders.routes import router as reminders_router
    REMINDERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sophisticated reminders system not available: {e}")
    REMINDERS_AVAILABLE = False

# Import sophisticated expungement system
try:
    from modules.legal.expungement_routes import router as expungement_router
    EXPUNGEMENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sophisticated expungement system not available: {e}")
    EXPUNGEMENT_AVAILABLE = False

# Pydantic models for API
class ClientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    risk_level: Optional[str] = "medium"
    case_status: Optional[str] = "active"
    case_manager_id: Optional[str] = None

class ClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    risk_level: Optional[str] = None
    case_status: Optional[str] = None
    case_manager_id: Optional[str] = None

class CaseNoteCreate(BaseModel):
    note_type: Optional[str] = "general"
    content: str
    created_by: Optional[str] = None

class AIConversation(BaseModel):
    client_id: Optional[str] = None
    user_id: str
    messages: List[Dict[str, Any]]
    context_data: Optional[Dict[str, Any]] = None

class NewUnifiedPlatform:
    """
    New Unified Platform using the 9-database architecture
    """
    
    def __init__(self):
        """Initialize with new database access layer"""
        self.db_access = db_access
        self.core_clients = core_clients_service
        self.ai_service = ai_service
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Case Management Suite - New Architecture",
            description="9-Database Architecture with AI Full CRUD",
            version="2.0.0"
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Set up routes
        self.setup_routes()
        
        # Include search router if available
        if SEARCH_AVAILABLE:
            self.app.include_router(search_router, prefix="/api")
            logger.info("✅ Search system integrated")
        else:
            logger.warning("⚠️ Search system not available")
            
        # Include sophisticated reminders router if available
        if REMINDERS_AVAILABLE:
            self.app.include_router(reminders_router, prefix="/api/reminders")
            logger.info("✅ Sophisticated reminders system integrated")
        else:
            logger.warning("⚠️ Sophisticated reminders system not available")
            
        # Include sophisticated expungement router if available
        if EXPUNGEMENT_AVAILABLE:
            self.app.include_router(expungement_router, prefix="/api/legal")
            logger.info("✅ Sophisticated expungement system integrated")
        else:
            logger.warning("⚠️ Sophisticated expungement system not available")
        
        logger.info("🚀 New Unified Platform initialized with 9-database architecture")
        
    def setup_routes(self):
        """Set up all API routes"""
        
        # ============= SYSTEM TEST ROUTES =============
        
        @self.app.get("/api/test/new-system")
        async def test_new_system():
            """Test endpoint to verify new system is working"""
            return {
                "status": "NEW_SYSTEM_ACTIVE",
                "architecture": "9-database",
                "ai_permissions": "FULL_CRUD",
                "timestamp": datetime.now().isoformat()
            }
        
        # ============= CORE CLIENTS ROUTES (MASTER DATABASE) =============
        
        @self.app.get("/api/clients")
        async def get_all_clients(module: str = Query("case_management")):
            """Get all clients - any module can read"""
            try:
                clients = self.core_clients.get_all_clients(module)
                return {"clients": clients, "count": len(clients)}
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except Exception as e:
                logger.error(f"Error getting clients: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/api/clients/{client_id}")
        async def get_client(client_id: str, module: str = Query("case_management")):
            """Get specific client"""
            try:
                client = self.core_clients.get_client(client_id, module)
                if not client:
                    raise HTTPException(status_code=404, detail="Client not found")
                return client
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except Exception as e:
                logger.error(f"Error getting client {client_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.post("/api/clients")
        async def create_client(client_data: ClientCreate, module: str = Query("case_management")):
            """Create new client - only Case Management or AI can create"""
            try:
                client_id = self.core_clients.create_client(client_data.dict(), module)
                return {"client_id": client_id, "message": "Client created successfully"}
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except Exception as e:
                logger.error(f"Error creating client: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.put("/api/clients/{client_id}")
        async def update_client(client_id: str, updates: ClientUpdate, module: str = Query("case_management")):
            """Update client - only Case Management or AI can update"""
            try:
                success = self.core_clients.update_client(client_id, updates.dict(exclude_unset=True), module)
                if not success:
                    raise HTTPException(status_code=404, detail="Client not found")
                return {"message": "Client updated successfully"}
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except Exception as e:
                logger.error(f"Error updating client {client_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.post("/api/clients/{client_id}/notes")
        async def add_case_note(client_id: str, note_data: CaseNoteCreate, module: str = Query("case_management")):
            """Add case note for client"""
            try:
                note_id = self.core_clients.add_case_note(client_id, note_data.dict(), module)
                return {"note_id": note_id, "message": "Case note added successfully"}
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except Exception as e:
                logger.error(f"Error adding case note: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # ============= AI ASSISTANT ROUTES (FULL CRUD ACCESS) =============
        
        @self.app.get("/api/ai/clients/{client_id}/complete-profile")
        async def get_complete_client_profile(client_id: str):
            """AI gets complete client profile across all databases"""
            try:
                profile = self.ai_service.get_client_complete_profile(client_id)
                return profile
            except Exception as e:
                logger.error(f"Error getting complete profile for {client_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.post("/api/ai/clients")
        async def ai_create_client(client_data: ClientCreate):
            """AI can create clients directly"""
            try:
                client_id = self.ai_service.create_client_anywhere(client_data.dict())
                return {"client_id": client_id, "message": "Client created by AI"}
            except Exception as e:
                logger.error(f"Error creating client via AI: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.post("/api/ai/conversations")
        async def save_ai_conversation(conversation: AIConversation):
            """Save AI conversation"""
            try:
                conversation_id = self.ai_service.save_conversation(conversation.dict())
                return {"conversation_id": conversation_id, "message": "Conversation saved"}
            except Exception as e:
                logger.error(f"Error saving AI conversation: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.put("/api/ai/clients/{client_id}/analytics")
        async def update_client_analytics(client_id: str, analytics_data: Dict[str, Any] = Body(...)):
            """Update client analytics"""
            try:
                analytics_id = self.ai_service.update_client_analytics(client_id, analytics_data)
                return {"analytics_id": analytics_id, "message": "Analytics updated"}
            except Exception as e:
                logger.error(f"Error updating analytics for {client_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.put("/api/ai/{database}/{table}/{record_id}")
        async def ai_update_any_record(database: str, table: str, record_id: str, updates: Dict[str, Any] = Body(...)):
            """AI can update any record in any database"""
            try:
                success = self.ai_service.update_any_database(database, table, record_id, updates)
                if not success:
                    raise HTTPException(status_code=404, detail="Record not found")
                return {"message": f"Record updated in {database}.{table}"}
            except Exception as e:
                logger.error(f"Error updating {database}.{table}.{record_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.post("/api/ai/chat")
        async def ai_chat(chat_request: Dict[str, Any] = Body(...)):
            """AI Chat endpoint using GPT-4o"""
            try:
                from openai import OpenAI
                
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    raise HTTPException(status_code=500, detail="OpenAI API key not configured")
                
                client = OpenAI(api_key=openai_api_key)
                
                # Get client context if client_id provided
                client_context = ""
                if chat_request.get("client_id"):
                    try:
                        profile = self.ai_service.get_client_complete_profile(chat_request["client_id"])
                        client_context = f"\n\nClient Context: {json.dumps(profile, indent=2)}"
                    except Exception as e:
                        logger.warning(f"Could not get client context: {e}")
                
                # Prepare system message
                system_message = f"""You are an AI assistant for a case management platform. You help case managers with:
                - Client assessment and planning
                - Resource recommendations
                - Case documentation
                - Service coordination
                - Risk assessment
                
                You have access to a 9-database architecture with client data across housing, benefits, legal, employment, services, reminders, and AI analytics.
                
                Be helpful, professional, and focused on case management best practices.{client_context}"""
                
                messages = [{"role": "system", "content": system_message}]
                messages.extend(chat_request.get("messages", []))
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content
                
                # Save conversation if client_id provided
                if chat_request.get("client_id"):
                    conversation_data = {
                        "client_id": chat_request["client_id"],
                        "user_id": chat_request.get("user_id", "system"),
                        "messages": messages + [{"role": "assistant", "content": ai_response}],
                        "context_data": {"model": "gpt-4o", "timestamp": datetime.now().isoformat()}
                    }
                    self.ai_service.save_conversation(conversation_data)
                
                return {
                    "response": ai_response,
                    "model": "gpt-4o",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error in AI chat: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # ============= MODULE-SPECIFIC ROUTES =============
        
        @self.app.get("/api/housing/clients/{client_id}")
        async def get_client_housing_data(client_id: str):
            """Get client housing data"""
            try:
                with self.db_access.get_connection('housing', 'housing') as conn:
                    cursor = conn.cursor()
                    
                    # Get housing profile
                    cursor.execute('SELECT * FROM client_housing_profiles WHERE client_id = ?', (client_id,))
                    profile = cursor.fetchone()
                    
                    # Get housing applications
                    cursor.execute('SELECT * FROM housing_applications WHERE client_id = ?', (client_id,))
                    applications = cursor.fetchall()
                    
                    return {
                        'profile': dict(profile) if profile else None,
                        'applications': [dict(app) for app in applications]
                    }
            except Exception as e:
                logger.error(f"Error getting housing data for {client_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/api/benefits/clients/{client_id}")
        async def get_client_benefits_data(client_id: str):
            """Get client benefits data"""
            try:
                with self.db_access.get_connection('benefits', 'benefits') as conn:
                    cursor = conn.cursor()
                    
                    # Get benefits profile
                    cursor.execute('SELECT * FROM client_benefits_profiles WHERE client_id = ?', (client_id,))
                    profile = cursor.fetchone()
                    
                    # Get benefits applications
                    cursor.execute('SELECT * FROM benefits_applications WHERE client_id = ?', (client_id,))
                    applications = cursor.fetchall()
                    
                    return {
                        'profile': dict(profile) if profile else None,
                        'applications': [dict(app) for app in applications]
                    }
            except Exception as e:
                logger.error(f"Error getting benefits data for {client_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/api/legal/clients/{client_id}")
        async def get_client_legal_data(client_id: str):
            """Get client legal data"""
            try:
                with self.db_access.get_connection('legal', 'legal') as conn:
                    cursor = conn.cursor()
                    
                    # Get legal cases
                    cursor.execute('SELECT * FROM legal_cases WHERE client_id = ?', (client_id,))
                    cases = cursor.fetchall()
                    
                    # Get expungement eligibility
                    cursor.execute('SELECT * FROM expungement_eligibility WHERE client_id = ?', (client_id,))
                    expungement = cursor.fetchone()
                    
                    return {
                        'cases': [dict(case) for case in cases],
                        'expungement': dict(expungement) if expungement else None
                    }
            except Exception as e:
                logger.error(f"Error getting legal data for {client_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/api/employment/clients/{client_id}")
        async def get_client_employment_data(client_id: str):
            """Get client employment data"""
            try:
                with self.db_access.get_connection('employment', 'employment') as conn:
                    cursor = conn.cursor()
                    
                    # Get employment profile
                    cursor.execute('SELECT * FROM client_employment_profiles WHERE client_id = ?', (client_id,))
                    profile = cursor.fetchone()
                    
                    # Get resumes
                    cursor.execute('SELECT * FROM resumes WHERE client_id = ?', (client_id,))
                    resumes = cursor.fetchall()
                    
                    # Get job applications
                    cursor.execute('SELECT * FROM job_applications WHERE client_id = ?', (client_id,))
                    applications = cursor.fetchall()
                    
                    return {
                        'profile': dict(profile) if profile else None,
                        'resumes': [dict(resume) for resume in resumes],
                        'applications': [dict(app) for app in applications]
                    }
            except Exception as e:
                logger.error(f"Error getting employment data for {client_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/api/services/clients/{client_id}")
        async def get_client_services_data(client_id: str):
            """Get client services data"""
            try:
                with self.db_access.get_connection('services', 'services') as conn:
                    cursor = conn.cursor()
                    
                    # Get client referrals
                    cursor.execute('SELECT * FROM client_referrals WHERE client_id = ?', (client_id,))
                    referrals = cursor.fetchall()
                    
                    return {
                        'referrals': [dict(ref) for ref in referrals]
                    }
            except Exception as e:
                logger.error(f"Error getting services data for {client_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # NOTE: Sophisticated reminders endpoints now handled by /api/reminders/* routes
        # Basic client reminders still available for backward compatibility
        @self.app.get("/api/basic-reminders/clients/{client_id}")
        async def get_basic_client_reminders(client_id: str):
            """Get basic client reminders (legacy endpoint)"""
            try:
                with self.db_access.get_connection('reminders', 'reminders') as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('SELECT * FROM reminders WHERE client_id = ? ORDER BY due_date', (client_id,))
                    reminders = cursor.fetchall()
                    
                    return {
                        'reminders': [dict(reminder) for reminder in reminders]
                    }
            except Exception as e:
                logger.error(f"Error getting basic reminders for {client_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # ============= SYSTEM ROUTES =============
        
        @self.app.get("/api/system/database-status")
        async def get_database_status():
            """Get status of all 9 databases"""
            try:
                status = {}
                for db_name, db_file in self.db_access.DATABASES.items():
                    db_path = Path(__file__).parent.parent / "databases" / db_file
                    status[db_name] = {
                        'file': db_file,
                        'exists': db_path.exists(),
                        'size': db_path.stat().st_size if db_path.exists() else 0
                    }
                return status
            except Exception as e:
                logger.error(f"Error getting database status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/api/system/access-matrix")
        async def get_access_matrix():
            """Get database access matrix"""
            return self.db_access.ACCESS_MATRIX
            
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "architecture": "9-database-system",
                "ai_permissions": "FULL_CRUD"
            }
            
        # ============= ERROR HANDLERS =============
        
        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            return JSONResponse(
                status_code=422,
                content={"detail": exc.errors(), "body": exc.body}
            )
            
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(f"Unhandled exception: {exc}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )

# Create the platform instance
platform = NewUnifiedPlatform()
app = platform.app

if __name__ == "__main__":
    print("🚀 Starting New Unified Case Management Platform")
    print("📊 9-Database Architecture")
    print("🤖 AI Assistant: FULL CRUD permissions")
    print("=" * 50)
    
    uvicorn.run(
        "main_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )