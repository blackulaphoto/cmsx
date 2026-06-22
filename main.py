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
import os
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

# Ensure writable runtime directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("databases", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
_vol = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
if _vol:
    import pathlib
    pathlib.Path(_vol, "databases").mkdir(parents=True, exist_ok=True)
    pathlib.Path(_vol, "admissions").mkdir(parents=True, exist_ok=True)

# CORS origins are configurable via CORS_ORIGINS (comma-separated).
default_cors_origins = [
    "http://localhost:5173",
    "http://localhost:5175",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:3000",
]
configured_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
is_production_runtime = os.getenv("RAILWAY_ENVIRONMENT", "").lower() == "production"
if configured_cors_origins:
    cors_origins = configured_cors_origins
elif is_production_runtime:
    cors_origins = []
else:
    cors_origins = default_cors_origins

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
if is_production_runtime and not cors_origins:
    logger.warning("CORS_ORIGINS is empty in production; browser clients will be blocked.")

from backend.auth.router import router as auth_router
from backend.auth.team_routes import router as team_router
from backend.auth.super_admin_routes import router as super_admin_router
from backend.billing.routes import router as billing_router
from backend.analytics.routes import event_router as analytics_event_router
from backend.analytics.routes import owner_router as owner_analytics_router
from backend.support.routes import ticket_router as support_ticket_router
from backend.support.routes import owner_router as owner_support_router
from backend.marketing.routes import owner_router as owner_marketing_router
from backend.auth.service import auth_service

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        from backend.search.coordinator import get_coordinator
        get_coordinator()
        logger.info("Search coordinator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize search coordinator: {e}")

    # Seed: base Resource Library (idempotent — only runs when DB is empty)
    try:
        from backend.modules.resource_library.seed_data import run_seed as _rl_seed
        from backend.modules.resource_library.database import get_resource_count
        if get_resource_count() == 0:
            result = _rl_seed()
            logger.info(f"Resource Library seeded: {result['inserted']} inserted, {result['skipped']} skipped")
        else:
            logger.info(f"Resource Library already has {get_resource_count()} records — seed skipped")
    except Exception as e:
        logger.error(f"Resource Library seed failed: {e}")

    # Seed: food resources batch 1 (idempotent — deduplicates by provider_name + service_name)
    try:
        from backend.modules.resource_library.food_seed import run_seed as _food_seed
        result = _food_seed()
        if result.get("error"):
            logger.error(f"Food seed error: {result['error']}")
        elif result["inserted"] > 0:
            logger.info(
                f"Food seed: {result['inserted']} imported "
                f"({result['verified']} verified, {result['needs_review']} needs_review), "
                f"{result['skipped']} skipped, {result['total_in_db']} total in DB"
            )
        else:
            logger.info(f"Food seed: all {result['skipped']} records already exist — skipped")
    except Exception as e:
        logger.error(f"Food resources seed failed: {e}")

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
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Test-Auth-Uid",
        "X-Test-Auth-User",
        "X-Test-Auth-Email",
        "X-Test-Auth-Name",
        "X-Test-Auth-Role",
        "X-Test-Auth-Case-Manager-Id",
        "X-Test-Auth-Case-Manager",
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

AUTH_EXEMPT_PATHS = {
    "/",
    "/api/health",
    "/api/sober-living-directory/seed-from-excel",
    "/docs",
    "/openapi.json",
    "/redoc",
}


@app.middleware("http")
async def firebase_auth_middleware(request, call_next):
    path = request.url.path
    if request.method == "OPTIONS" or path in AUTH_EXEMPT_PATHS:
        return await call_next(request)

    if path.startswith("/api"):
        try:
            if auth_service.is_test_auth_enabled():
                request.state.auth_user = auth_service.test_user_from_request(request)
            else:
                decoded = auth_service.verify_bearer_token(request.headers.get("Authorization"))
                request.state.auth_user = auth_service.upsert_profile_from_token(decoded)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return await call_next(request)

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
    from backend.modules.sober_living_directory.routes import router as sober_living_directory_router
    app.include_router(sober_living_directory_router, prefix="/api/sober-living-directory", tags=["sober-living-directory"])
    loaded_modules["sober_living_directory"] = "loaded"
    logger.info("Sober living directory module loaded successfully")
except Exception as e:
    loaded_modules["sober_living_directory"] = f"error: {e}"
    logger.warning(f"Sober living directory module not loaded: {e}")

try:
    from backend.modules.sober_living.routes import router as sober_living_router
    app.include_router(sober_living_router, tags=["sober-living"])
    loaded_modules["sober_living"] = "loaded"
    logger.info("Sober living management module loaded successfully")
except Exception as e:
    loaded_modules["sober_living"] = f"error: {e}"
    logger.warning(f"Sober living management module not loaded: {e}")

try:
    from backend.modules.benefits.routes import router as benefits_router
    app.include_router(benefits_router, prefix="/api/benefits", tags=["benefits"])
    loaded_modules["benefits"] = "loaded"
    logger.info("Benefits module loaded successfully")
except Exception as e:
    loaded_modules["benefits"] = f"error: {e}"
    logger.warning(f"Benefits module not loaded: {e}")

try:
    from backend.modules.medical.routes import router as medical_router
    app.include_router(medical_router, prefix="/api/medical", tags=["medical"])
    loaded_modules["medical"] = "loaded"
    logger.info("Medical module loaded successfully")
except Exception as e:
    loaded_modules["medical"] = f"error: {e}"
    logger.warning(f"Medical module not loaded: {e}")

try:
    from backend.modules.rolodex.routes import router as rolodex_router
    app.include_router(rolodex_router, prefix="/api", tags=["rolodex"])
    loaded_modules["rolodex"] = "loaded"
    logger.info("Rolodex module loaded successfully")
except Exception as e:
    loaded_modules["rolodex"] = f"error: {e}"
    logger.warning(f"Rolodex module not loaded: {e}")

try:
    from backend.modules.legal.routes import router as legal_router
    app.include_router(legal_router, prefix="/api/legal", tags=["legal"])
    loaded_modules["legal"] = "loaded"
    logger.info("Legal module loaded successfully")
except Exception as e:
    loaded_modules["legal"] = f"error: {e}"
    logger.warning(f"Legal module not loaded: {e}")

try:
    from backend.modules.fmla.routes import router as fmla_router
    app.include_router(fmla_router, prefix="/api", tags=["fmla"])
    loaded_modules["fmla"] = "loaded"
    logger.info("FMLA module loaded successfully")
except Exception as e:
    loaded_modules["fmla"] = f"error: {e}"
    logger.warning(f"FMLA module not loaded: {e}")

try:
    from backend.modules.ur.routes import router as ur_router
    app.include_router(ur_router, prefix="/api", tags=["ur"])
    loaded_modules["ur"] = "loaded"
    logger.info("UR module loaded successfully")
except Exception as e:
    loaded_modules["ur"] = f"error: {e}"
    logger.warning(f"UR module not loaded: {e}")

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
    from backend.modules.ai_documentation.routes import router as ai_documentation_router
    app.include_router(ai_documentation_router, prefix="/api", tags=["ai-documentation"])
    loaded_modules["ai_documentation"] = "loaded"
    logger.info("AI Documentation module loaded successfully")
except Exception as e:
    loaded_modules["ai_documentation"] = f"error: {e}"
    logger.warning(f"AI Documentation module not loaded: {e}")
try:
    from backend.modules.transcription.routes import router as transcription_router
    app.include_router(transcription_router)
    loaded_modules["transcription"] = "loaded"
    logger.info("Transcription module loaded successfully")
except Exception as e:
    loaded_modules["transcription"] = f"error: {e}"
    logger.warning(f"Transcription module not loaded: {e}")
try:
    from backend.modules.services.routes import router as services_router
    app.include_router(services_router, prefix="/api/services", tags=["services"])
    loaded_modules["services"] = "loaded"
    logger.info("Services module loaded successfully")
except Exception as e:
    loaded_modules["services"] = f"error: {e}"
    logger.warning(f"Services module not loaded: {e}")

try:
    from backend.modules.resource_library.routes import router as resource_library_router
    app.include_router(resource_library_router, prefix="/api/resources", tags=["resource-library"])
    loaded_modules["resource_library"] = "loaded"
    logger.info("Resource Library module loaded successfully")
except Exception as e:
    loaded_modules["resource_library"] = f"error: {e}"
    logger.warning(f"Resource Library module not loaded: {e}")

try:
    from backend.modules.jobs.routes import router as jobs_router
    app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
    loaded_modules["jobs"] = "loaded"
    logger.info("Jobs module loaded successfully")
except Exception as e:
    loaded_modules["jobs"] = f"error: {e}"
    logger.warning(f"Jobs module not loaded: {e}")

try:
    from backend.modules.groups.routes import router as groups_router
    app.include_router(groups_router, prefix="/api", tags=["groups"])
    loaded_modules["groups"] = "loaded"
    logger.info("Groups facilitation module loaded successfully")
except Exception as e:
    loaded_modules["groups"] = f"error: {e}"
    logger.warning(f"Groups facilitation module not loaded: {e}")

try:
    from backend.modules.messages.routes import router as messages_router
    app.include_router(messages_router, prefix="/api/messages", tags=["messages"])
    loaded_modules["messages"] = "loaded"
    logger.info("Messages module loaded successfully")
except Exception as e:
    loaded_modules["messages"] = f"error: {e}"
    logger.warning(f"Messages module not loaded: {e}")

try:
    from backend.modules.admissions.routes import router as admissions_router
    app.include_router(admissions_router, prefix="/api", tags=["admissions"])
    loaded_modules["admissions"] = "loaded"
    logger.info("Admissions module loaded successfully")
except Exception as e:
    loaded_modules["admissions"] = f"error: {e}"
    logger.warning(f"Admissions module not loaded: {e}")

@app.on_event("startup")
async def initialize_reminders_db():
    """Ensure reminders DB is initialized"""
    try:
        from backend.modules.reminders.engine import initialize_db
        initialize_db()
        logger.info("Reminders DB initialized")
    except Exception as e:
        logger.error(f"Reminders DB init failed: {e}")

@app.on_event("startup")
async def seed_sober_living_directory():
    """Auto-seed sober living directory from committed Excel if DB is empty."""
    try:
        from backend.modules.sober_living_directory.routes import get_directory_db, get_importer as get_sld_importer
        from pathlib import Path as _Path
        _db = get_directory_db()
        if not _db.list_listings({}):
            _excel = _Path(__file__).parent / "CA_Sober_Living_Directory.xlsx"
            if _excel.exists():
                _summary = get_sld_importer().import_file(
                    file_name=_excel.name,
                    content=_excel.read_bytes(),
                    source_name="CA Sober Living Directory",
                    source_type="spreadsheet_import",
                )
                logger.info(f"Sober living directory seeded: {_summary.get('listings_created', 0)} listings created")
            else:
                logger.warning(f"CA_Sober_Living_Directory.xlsx not found at {_excel}")
        else:
            logger.info("Sober living directory already has listings — seed skipped")
    except Exception as e:
        logger.error(f"Sober living directory seed failed: {e}")

@app.on_event("startup")
async def seed_resource_library():
    """Auto-seed Resource Library with first batch of resources if DB is empty."""
    try:
        from backend.modules.resource_library.seed_data import run_seed
        from backend.modules.resource_library.database import get_resource_count
        if get_resource_count() == 0:
            result = run_seed()
            logger.info(f"Resource Library seeded: {result['inserted']} inserted, {result['skipped']} skipped")
        else:
            logger.info(f"Resource Library already has {get_resource_count()} records — seed skipped")
    except Exception as e:
        logger.error(f"Resource Library seed failed: {e}")

@app.on_event("startup")
async def seed_food_resources():
    """Import food resources batch 1 — idempotent, deduplicates by provider_name + service_name."""
    try:
        from backend.modules.resource_library.food_seed import run_seed as food_run_seed
        result = food_run_seed()
        if result.get("error"):
            logger.error(f"Food seed error: {result['error']}")
        elif result["inserted"] > 0:
            logger.info(
                f"Food seed: {result['inserted']} imported "
                f"({result['verified']} verified, {result['needs_review']} needs_review), "
                f"{result['skipped']} skipped, {result['total_in_db']} total in DB"
            )
        else:
            logger.info(f"Food seed: all {result['skipped']} records already exist — skipped")
    except Exception as e:
        logger.error(f"Food resources seed failed: {e}")

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

try:
    app.include_router(auth_router)
    app.include_router(team_router)
    app.include_router(super_admin_router)
    app.include_router(billing_router)
    app.include_router(analytics_event_router)
    app.include_router(owner_analytics_router)
    app.include_router(support_ticket_router)
    app.include_router(owner_support_router)
    app.include_router(owner_marketing_router)
    loaded_modules["auth"] = "loaded"
    logger.info("Firebase auth routes loaded successfully")
except Exception as e:
    loaded_modules["auth"] = f"error: {e}"
    logger.warning(f"Firebase auth routes not loaded: {e}")

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
            "medical": "/api/medical",
            "rolodex": "/api/rolodex",
            "legal": "/api/legal",
            "fmla": "/api/fmla",
            "ur": "/api/ur",
            "resume": "/api/resume",
            "ai": "/api/ai",
            "ai_documentation": "/api/ai-documentation",
            "services": "/api/services",
            "jobs": "/api/jobs",
            "reminders": "/api/reminders",
            "search": "/api/search",
            "groups": "/api/groups"
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
