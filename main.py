# ================================================================
# @generated
# @preserve
# @readonly
# DO NOT MODIFY THIS FILE
# Purpose: Production-approved unified system
# Any changes must be approved by lead developer.
# WARNING: Modifying this file may break the application.
# ================================================================

"""
Case Management Suite - Main Application Entry Point
Consolidated platform combining the best features from both codebases
"""

import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import uvicorn

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # Initialize search coordinator
        from backend.search.coordinator import get_coordinator
        coordinator = get_coordinator()
        logger.info("Search coordinator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize search coordinator: {e}")
    
    yield
    
    # Shutdown (if needed)
    logger.info("Application shutting down")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Case Management Suite",
    description="Comprehensive case management platform for reentry services",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware - configured for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server (default)
        "http://localhost:5175",  # Vite dev server (current)
        "http://localhost:3000",  # Create React App / alternative dev server
        "http://127.0.0.1:5173",  # Alternative localhost format
        "http://127.0.0.1:5175",  # Alternative localhost format (current)
        "http://127.0.0.1:3000",  # Alternative localhost format
        "https://cmsx-iggfqkus4-blackulaphotos-projects.vercel.app",  # Vercel frontend
        # Add production frontend URL here when deployed
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=[
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers",
        "Content-Type",
    ],
    max_age=3600,  # Preflight response cache duration
)

# Static files and templates removed - using React frontend served separately

# Module registry for health checks
loaded_modules = {}

# Import and include routers from modules
try:
    from backend.modules.housing.routes import router as housing_router
    app.include_router(housing_router, prefix="/api/housing", tags=["housing"])
    loaded_modules["housing"] = "loaded"
    logger.info("Housing module loaded successfully")
except Exception as e:
    loaded_modules["housing"] = f"error: {e}"
    logger.warning(f"Housing module not loaded: {e}")

try:
    from backend.modules.benefits.routes import router as benefits_router
    app.include_router(benefits_router, prefix="/api/benefits", tags=["benefits"])
    loaded_modules["benefits"] = "loaded"
    logger.info("Benefits module loaded successfully")
except Exception as e:
    loaded_modules["benefits"] = f"error: {e}"
    logger.warning(f"Benefits module not loaded: {e}")

try:
    from backend.modules.legal.routes import router as legal_router
    app.include_router(legal_router, prefix="/api/legal", tags=["legal"])
    loaded_modules["legal"] = "loaded"
    logger.info("Legal module loaded successfully")
except Exception as e:
    loaded_modules["legal"] = f"error: {e}"
    logger.warning(f"Legal module not loaded: {e}")

try:
    from backend.modules.resume.routes import router as resume_router
    app.include_router(resume_router, prefix="/api/resume", tags=["resume"])
    loaded_modules["resume"] = "loaded"
    logger.info("Resume module loaded successfully")
except Exception as e:
    loaded_modules["resume"] = f"error: {e}"
    logger.warning(f"Resume module not loaded: {e}")

# Unified AI module
try:
    from backend.modules.ai_unified.unified_routes import router as unified_ai_router
    app.include_router(unified_ai_router, prefix="/api/ai", tags=["ai"])
    loaded_modules["ai_unified"] = "loaded"
    logger.info("Unified AI loaded (Hybrid: GPT-4o + SQLite Memory)")
except Exception as e:
    loaded_modules["ai_unified"] = f"error: {e}"
    logger.warning(f"Unified AI module not loaded: {e}")
try:
    from backend.modules.services.routes import router as services_router
    app.include_router(services_router, prefix="/api/services", tags=["services"])
    loaded_modules["services"] = "loaded"
    logger.info("Services module loaded successfully")
except Exception as e:
    loaded_modules["services"] = f"error: {e}"
    logger.warning(f"Services module not loaded: {e}")

try:
    from backend.modules.jobs.routes import router as jobs_router
    app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
    loaded_modules["jobs"] = "loaded"
    logger.info("Jobs module loaded successfully")
except Exception as e:
    loaded_modules["jobs"] = f"error: {e}"
    logger.warning(f"Jobs module not loaded: {e}")

@app.on_event("startup")
async def initialize_reminders_db():
    """Ensure reminders DB is initialized"""
    try:
        from backend.modules.reminders.engine import initialize_db
        initialize_db()
        logger.info("Reminders DB initialized")
    except Exception as e:
        logger.error(f"Reminders DB init failed: {e}")

try:
    from backend.modules.reminders.routes import router as reminders_router
    app.include_router(reminders_router, prefix="/api/reminders", tags=["reminders"])
    loaded_modules["reminders"] = "loaded"
    logger.info("Reminders module loaded successfully")
except Exception as e:
    loaded_modules["reminders"] = f"error: {e}"
    logger.warning(f"Reminders module not loaded: {e}")

# Include the new simple search system
try:
    from backend.search.routes import router as search_router
    app.include_router(search_router, prefix="/api", tags=["search"])
    loaded_modules["search"] = "loaded"
    logger.info("Simple Search module loaded successfully")
except Exception as e:
    loaded_modules["search"] = f"error: {e}"
    logger.warning(f"Simple Search module not loaded: {e}")

# Include the case management module
try:
    from backend.modules.case_management.routes import router as case_management_router
    app.include_router(case_management_router, prefix="/api", tags=["case-management"])
    loaded_modules["case_management"] = "loaded"
    logger.info("Case Management module loaded successfully")
except Exception as e:
    loaded_modules["case_management"] = f"error: {e}"
    logger.warning(f"Case Management module not loaded: {e}")

# Include the unified client API
try:
    from backend.api.unified_client_api import router as unified_client_router
    app.include_router(unified_client_router, tags=["unified-client"])
    loaded_modules["unified_client"] = "loaded"
    logger.info("Unified Client API loaded successfully")
except Exception as e:
    loaded_modules["unified_client"] = f"error: {e}"
    logger.warning(f"Unified Client API not loaded: {e}")

# Include the system health endpoints
try:
    from backend.api.system_health import router as health_router
    app.include_router(health_router, tags=["system-health"])
    loaded_modules["system_health"] = "loaded"
    logger.info("System Health API loaded successfully")
except Exception as e:
    loaded_modules["system_health"] = f"error: {e}"
    logger.warning(f"System Health API not loaded: {e}")

# Include the client management endpoints
try:
    from backend.api.clients import router as clients_router
    app.include_router(clients_router, tags=["client-management"])
    loaded_modules["client_management"] = "loaded"
    logger.info("Client Management API loaded successfully")
except Exception as e:
    loaded_modules["client_management"] = f"error: {e}"
    logger.warning(f"Client Management API not loaded: {e}")

# Include the dashboard module for ClickUp-style components
try:
    from backend.modules.dashboard.sqlite_routes import router as dashboard_router
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
    loaded_modules["dashboard"] = "loaded"
    logger.info("Dashboard module loaded successfully")
except Exception as e:
    loaded_modules["dashboard"] = f"error: {e}"
    logger.warning(f"Dashboard module not loaded: {e}")

# Include ClickUp-style dashboard data endpoints (notes/docs/bookmarks/resources)
try:
    from backend.modules.dashboard.routes import router as dashboard_clickup_router
    app.include_router(dashboard_clickup_router, prefix="/api", tags=["dashboard"])
    loaded_modules["dashboard_clickup"] = "loaded"
    logger.info("Dashboard ClickUp routes loaded successfully")
except Exception as e:
    loaded_modules["dashboard_clickup"] = f"error: {e}"
    logger.warning(f"Dashboard ClickUp routes not loaded: {e}")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "modules": loaded_modules
    }

# Root API endpoint - returns API information
@app.get("/")
async def root():
    """Root API endpoint - returns information about available endpoints"""
    return {
        "message": "Case Management Suite API",
        "version": "2.0.0",
        "description": "Backend API for case management platform",
        "frontend": "React application served separately",
        "endpoints": {
            "health": "/api/health",
            "case_management": "/api/case-management",
            "housing": "/api/housing",
            "benefits": "/api/benefits",
            "legal": "/api/legal",
            "resume": "/api/resume",
            "ai": "/api/ai",
            "services": "/api/services",
            "jobs": "/api/jobs",
            "reminders": "/api/reminders",
            "search": "/api/search"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }

if __name__ == "__main__":
    # Configure uvicorn for production-ready deployment
    # Set reload=False to disable excessive watchfile logging
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled to prevent excessive watchfile logging
        log_level="info"
    ) 
