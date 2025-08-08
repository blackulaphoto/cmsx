#!/usr/bin/env python3
"""
Resume Routes - Corrected Architecture
FastAPI Router for Resume Builder aligned with 9-database architecture
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import json
import sys
import os
from datetime import datetime, date
import uuid

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from resume.models_corrected import (
    EmploymentDatabase, ClientEmploymentProfile, Resume, JobApplication, 
    ResumeTailoring, Client
)

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(tags=["resume"])

# Initialize database
employment_db = None

def get_employment_db():
    """Get thread-safe employment database instance"""
    global employment_db
    if employment_db is None:
        employment_db = EmploymentDatabase()
        employment_db.connect()
    return employment_db

# Pydantic models for API requests
class EmploymentProfileRequest(BaseModel):
    client_id: str
    work_history: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []
    skills: List[Dict[str, Any]] = []
    certifications: List[Dict[str, Any]] = []
    career_objective: str = ""
    preferred_industries: List[str] = []

class ResumeCreateRequest(BaseModel):
    client_id: str
    profile_id: Optional[str] = None
    template_type: str = "classic"
    resume_title: str = ""

class ResumeOptimizeRequest(BaseModel):
    resume_id: str
    optimization_type: str = "ats_optimization"
    job_description: Optional[str] = None

class JobApplicationRequest(BaseModel):
    client_id: str
    resume_id: str
    job_title: str
    company_name: str
    job_description: str = ""

# API Endpoints

@router.get("/")
async def resume_dashboard():
    """Resume builder dashboard"""
    return {
        "message": "Resume Builder API Ready - Corrected Architecture",
        "endpoints": [
            "/clients", "/profile", "/create", "/list", "/optimize", 
            "/generate-pdf", "/download", "/apply-job", "/applications"
        ]
    }

@router.get("/clients")
async def get_available_clients():
    """Get available clients from core_clients.db"""
    try:
        db = get_employment_db()
        clients = db.core_clients.get_available_clients()
        
        # Get resume counts for each client
        client_list = []
        for client in clients:
            resumes = db.resumes.get_resumes_by_client(client.client_id)
            client_list.append({
                "client_id": client.client_id,
                "first_name": client.first_name,
                "last_name": client.last_name,
                "phone": client.phone,
                "email": client.email,
                "has_resume": len(resumes) > 0,
                "active_resumes": len(resumes)
            })
        
        return {
            "success": True,
            "clients": client_list,
            "total_count": len(client_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting clients: {e}")
        raise HTTPException(status_code=500, detail=f"Client retrieval error: {str(e)}")

@router.post("/profile")
async def create_employment_profile(profile_request: EmploymentProfileRequest):
    """Create or update employment profile"""
    try:
        db = get_employment_db()
        
        # Check if client exists in core_clients.db
        client = db.core_clients.get_client_by_id(profile_request.client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Check if profile already exists
        existing_profile = db.profiles.get_profile_by_client(profile_request.client_id)
        
        if existing_profile:
            # Update existing profile
            existing_profile.work_history = profile_request.work_history
            existing_profile.education = profile_request.education
            existing_profile.skills = profile_request.skills
            existing_profile.certifications = profile_request.certifications
            existing_profile.career_objective = profile_request.career_objective
            existing_profile.preferred_industries = profile_request.preferred_industries
            
            success = db.profiles.update_profile(existing_profile)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update profile")
            
            return {
                "success": True,
                "profile_id": existing_profile.profile_id,
                "message": "Employment profile updated successfully"
            }
        else:
            # Create new profile
            profile = ClientEmploymentProfile(
                client_id=profile_request.client_id,
                work_history=profile_request.work_history,
                education=profile_request.education,
                skills=profile_request.skills,
                certifications=profile_request.certifications,
                career_objective=profile_request.career_objective,
                preferred_industries=profile_request.preferred_industries
            )
            
            profile_id = db.profiles.create_profile(profile)
            if not profile_id:
                raise HTTPException(status_code=500, detail="Failed to create profile")
            
            return {
                "success": True,
                "profile_id": profile_id,
                "message": "Employment profile created successfully"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/updating profile: {e}")
        raise HTTPException(status_code=500, detail=f"Profile operation error: {str(e)}")

@router.get("/profile/{client_id}")
async def get_employment_profile(client_id: str):
    """Get employment profile for client"""
    try:
        db = get_employment_db()
        
        # Check if client exists
        client = db.core_clients.get_client_by_id(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        profile = db.profiles.get_profile_by_client(client_id)
        if not profile:
            return {
                "success": True,
                "profile": None,
                "message": "No employment profile found for client"
            }
        
        return {
            "success": True,
            "profile": {
                "profile_id": profile.profile_id,
                "client_id": profile.client_id,
                "work_history": profile.work_history,
                "education": profile.education,
                "skills": profile.skills,
                "certifications": profile.certifications,
                "career_objective": profile.career_objective,
                "preferred_industries": profile.preferred_industries,
                "background_friendly_only": profile.background_friendly_only,
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail=f"Profile retrieval error: {str(e)}")

@router.post("/create")
async def create_resume(resume_request: ResumeCreateRequest):
    """Create resume from employment profile"""
    try:
        db = get_employment_db()
        
        # Verify client exists
        client = db.core_clients.get_client_by_id(resume_request.client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Get or create employment profile
        profile = None
        if resume_request.profile_id:
            # Use specific profile
            profile = db.profiles.get_profile_by_client(resume_request.client_id)
            if not profile or profile.profile_id != resume_request.profile_id:
                raise HTTPException(status_code=404, detail="Employment profile not found")
        else:
            # Get existing profile or create basic one
            profile = db.profiles.get_profile_by_client(resume_request.client_id)
            if not profile:
                # Create basic profile from client data
                profile = ClientEmploymentProfile(
                    client_id=resume_request.client_id,
                    career_objective=f"Seeking employment opportunities",
                    work_history=[],
                    skills=[{"category": "General", "skill_list": ["Reliable", "Team Player", "Detail-oriented"]}],
                    education=[]
                )
                profile_id = db.profiles.create_profile(profile)
                if not profile_id:
                    raise HTTPException(status_code=500, detail="Failed to create basic profile")
        
        # Generate resume content
        resume_content = {
            "personal_info": {
                "first_name": client.first_name,
                "last_name": client.last_name,
                "phone": client.phone,
                "email": client.email,
                "address": client.address
            },
            "career_objective": profile.career_objective,
            "work_experience": profile.work_history,
            "education": profile.education,
            "skills": profile.skills,
            "certifications": profile.certifications
        }
        
        # Calculate basic ATS score
        ats_score = calculate_basic_ats_score(resume_content)
        
        # Create resume record
        resume = Resume(
            client_id=resume_request.client_id,
            profile_id=profile.profile_id,
            template_type=resume_request.template_type,
            resume_title=resume_request.resume_title or f"Resume for {client.first_name} {client.last_name}",
            content=json.dumps(resume_content),
            ats_score=ats_score
        )
        
        resume_id = db.resumes.create_resume(resume)
        if not resume_id:
            raise HTTPException(status_code=500, detail="Failed to create resume")
        
        return {
            "success": True,
            "resume_id": resume_id,
            "ats_score": ats_score,
            "pdf_generated": False,  # PDF generation will be separate
            "pdf_url": f"/api/resume/download/{resume_id}",
            "message": "Resume created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating resume: {e}")
        raise HTTPException(status_code=500, detail=f"Resume creation error: {str(e)}")

@router.get("/list/{client_id}")
async def get_client_resumes(client_id: str):
    """Get all resumes for a client"""
    try:
        db = get_employment_db()
        
        # Verify client exists
        client = db.core_clients.get_client_by_id(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        resumes = db.resumes.get_resumes_by_client(client_id)
        
        # Get job application counts for each resume
        resume_list = []
        for resume in resumes:
            applications = db.applications.get_applications_by_client(client_id)
            app_count = len([app for app in applications if app.resume_id == resume.resume_id])
            
            resume_list.append({
                "resume_id": resume.resume_id,
                "resume_title": resume.resume_title,
                "template_type": resume.template_type,
                "ats_score": resume.ats_score,
                "created_at": resume.created_at.isoformat() if resume.created_at else None,
                "is_active": resume.is_active,
                "job_applications_count": app_count,
                "pdf_available": bool(resume.pdf_path and os.path.exists(resume.pdf_path))
            })
        
        return {
            "success": True,
            "resumes": resume_list,
            "total_count": len(resume_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client resumes: {e}")
        raise HTTPException(status_code=500, detail=f"Resume retrieval error: {str(e)}")

@router.post("/optimize")
async def optimize_resume(optimize_request: ResumeOptimizeRequest):
    """AI-powered resume optimization"""
    try:
        db = get_employment_db()
        
        # Get resume
        resume = db.resumes.get_resume_by_id(optimize_request.resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Parse current content
        current_content = json.loads(resume.content)
        
        # Simulate AI optimization (replace with actual OpenAI integration)
        optimized_content = simulate_ai_optimization(
            current_content, 
            optimize_request.optimization_type,
            optimize_request.job_description
        )
        
        # Calculate new ATS score
        new_ats_score = calculate_basic_ats_score(optimized_content)
        improvement = new_ats_score - (resume.ats_score or 0)
        
        # Update resume with optimized content
        resume.content = json.dumps(optimized_content)
        resume.ats_score = new_ats_score
        
        success = db.resumes.update_resume(resume)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update resume")
        
        return {
            "success": True,
            "optimized_content": {
                "career_objective": optimized_content.get("career_objective", ""),
                "highlighted_skills": [skill for skill_cat in optimized_content.get("skills", []) for skill in skill_cat.get("skill_list", [])],
                "work_experience_improvements": ["Enhanced job descriptions with action verbs", "Added quantifiable achievements"],
                "keyword_additions": ["Industry-specific keywords", "ATS-friendly terms"]
            },
            "ats_score_improvement": improvement,
            "new_ats_score": new_ats_score,
            "message": "Resume optimized successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing resume: {e}")
        raise HTTPException(status_code=500, detail=f"Resume optimization error: {str(e)}")

@router.post("/generate-pdf/{resume_id}")
async def generate_resume_pdf(resume_id: str):
    """Generate PDF for resume"""
    try:
        db = get_employment_db()
        
        # Get resume
        resume = db.resumes.get_resume_by_id(resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Get client info
        client = db.core_clients.get_client_by_id(resume.client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Generate PDF path
        client_dir = f"static/resumes/client_{resume.client_id}/"
        os.makedirs(client_dir, exist_ok=True)
        
        pdf_filename = f"resume_{resume_id}.pdf"
        pdf_path = f"{client_dir}{pdf_filename}"
        
        # Simulate PDF generation (replace with actual PDF generation)
        success = simulate_pdf_generation(resume, client, pdf_path)
        
        if success:
            # Update resume with PDF path
            resume.pdf_path = pdf_path
            db.resumes.update_resume(resume)
            
            return {
                "success": True,
                "pdf_path": pdf_path,
                "download_url": f"/api/resume/download/{resume_id}",
                "message": "PDF generated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="PDF generation failed")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation error: {str(e)}")

@router.get("/download/{resume_id}")
async def download_resume(resume_id: str):
    """Download resume PDF"""
    try:
        db = get_employment_db()
        
        resume = db.resumes.get_resume_by_id(resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        if not resume.pdf_path or not os.path.exists(resume.pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        # Get client for filename
        client = db.core_clients.get_client_by_id(resume.client_id)
        filename = f"resume_{client.first_name}_{client.last_name}.pdf" if client else f"resume_{resume_id}.pdf"
        
        return FileResponse(
            path=resume.pdf_path,
            filename=filename,
            media_type="application/pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading resume: {e}")
        raise HTTPException(status_code=500, detail=f"Resume download error: {str(e)}")

@router.post("/apply-job")
async def apply_to_job_with_resume(application_request: JobApplicationRequest):
    """Apply to job with resume"""
    try:
        db = get_employment_db()
        
        # Verify client and resume exist
        client = db.core_clients.get_client_by_id(application_request.client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        resume = db.resumes.get_resume_by_id(application_request.resume_id)
        if not resume or resume.client_id != application_request.client_id:
            raise HTTPException(status_code=404, detail="Resume not found for this client")
        
        # Create job application
        application = JobApplication(
            client_id=application_request.client_id,
            resume_id=application_request.resume_id,
            job_title=application_request.job_title,
            company_name=application_request.company_name,
            job_description=application_request.job_description,
            application_status="submitted",
            applied_date=date.today().isoformat()
        )
        
        application_id = db.applications.create_application(application)
        if not application_id:
            raise HTTPException(status_code=500, detail="Failed to create job application")
        
        # Calculate match score (simulate)
        match_score = calculate_job_match_score(resume.content, application_request.job_description)
        
        return {
            "success": True,
            "application_id": application_id,
            "tailored_resume_created": False,  # Could implement tailoring here
            "match_score": match_score,
            "message": "Job application created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job application: {e}")
        raise HTTPException(status_code=500, detail=f"Job application error: {str(e)}")

@router.get("/applications/{client_id}")
async def get_job_applications(client_id: str):
    """Get job applications for client"""
    try:
        db = get_employment_db()
        
        # Verify client exists
        client = db.core_clients.get_client_by_id(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        applications = db.applications.get_applications_by_client(client_id)
        
        application_list = []
        for app in applications:
            # Get resume info
            resume = db.resumes.get_resume_by_id(app.resume_id) if app.resume_id else None
            
            application_list.append({
                "application_id": app.application_id,
                "job_title": app.job_title,
                "company_name": app.company_name,
                "application_status": app.application_status,
                "applied_date": app.applied_date,
                "resume_used": app.resume_id,
                "resume_title": resume.resume_title if resume else "Unknown",
                "match_score": calculate_job_match_score(resume.content, app.job_description) if resume else 0.0,
                "follow_up_date": app.follow_up_date,
                "notes": app.notes
            })
        
        return {
            "success": True,
            "applications": application_list,
            "total_count": len(application_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job applications: {e}")
        raise HTTPException(status_code=500, detail=f"Job applications retrieval error: {str(e)}")

@router.get("/health")
async def resume_health_check():
    """Health check for resume service"""
    try:
        db = get_employment_db()
        
        # Test database connections
        clients = db.core_clients.get_available_clients()
        
        return {
            "status": "healthy",
            "employment_db_accessible": True,
            "core_clients_db_accessible": True,
            "active_clients_count": len(clients),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Resume health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Helper functions

def calculate_basic_ats_score(resume_content: Dict[str, Any]) -> int:
    """Calculate basic ATS score for resume content"""
    score = 0
    
    # Contact information (15 points)
    personal_info = resume_content.get("personal_info", {})
    if personal_info.get("phone"): score += 5
    if personal_info.get("email"): score += 5
    if personal_info.get("address"): score += 5
    
    # Career objective (15 points)
    if resume_content.get("career_objective"): score += 15
    
    # Work experience (25 points)
    work_exp = resume_content.get("work_experience", [])
    if work_exp:
        score += min(25, len(work_exp) * 8)
    
    # Skills section (20 points)
    skills = resume_content.get("skills", [])
    if skills:
        total_skills = sum(len(skill_cat.get("skill_list", [])) for skill_cat in skills)
        score += min(20, total_skills * 2)
    
    # Education (15 points)
    education = resume_content.get("education", [])
    if education: score += 15
    
    # Certifications (10 points)
    certifications = resume_content.get("certifications", [])
    if certifications: score += 10
    
    return min(100, score)

def simulate_ai_optimization(content: Dict[str, Any], optimization_type: str, job_description: Optional[str] = None) -> Dict[str, Any]:
    """Simulate AI optimization (replace with actual OpenAI integration)"""
    optimized = content.copy()
    
    # Enhance career objective
    if optimization_type == "job_specific" and job_description:
        optimized["career_objective"] = f"Motivated professional seeking to contribute to {job_description[:50]}... with proven experience and dedication."
    else:
        optimized["career_objective"] = f"Experienced professional with strong work ethic and commitment to excellence, seeking opportunities for growth and contribution."
    
    # Add industry keywords to skills if not present
    if "skills" not in optimized:
        optimized["skills"] = []
    
    # Add ATS-friendly skills
    ats_skills = {
        "category": "Core Competencies",
        "skill_list": ["Problem Solving", "Team Collaboration", "Time Management", "Attention to Detail"]
    }
    
    # Check if core competencies already exist
    has_core = any(skill.get("category") == "Core Competencies" for skill in optimized["skills"])
    if not has_core:
        optimized["skills"].append(ats_skills)
    
    return optimized

def calculate_job_match_score(resume_content: str, job_description: str) -> float:
    """Calculate job match score (simulate)"""
    try:
        content = json.loads(resume_content) if isinstance(resume_content, str) else resume_content
        
        # Simple keyword matching simulation
        resume_text = json.dumps(content).lower()
        job_text = job_description.lower()
        
        # Common job keywords
        keywords = ["experience", "skills", "team", "management", "customer", "service", "work", "professional"]
        
        matches = sum(1 for keyword in keywords if keyword in resume_text and keyword in job_text)
        score = (matches / len(keywords)) * 100
        
        return round(score, 1)
    except:
        return 50.0  # Default score

def simulate_pdf_generation(resume: Resume, client: Client, pdf_path: str) -> bool:
    """Simulate PDF generation (replace with actual PDF generation)"""
    try:
        # Create a simple HTML file as placeholder
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Resume - {client.first_name} {client.last_name}</title>
        </head>
        <body>
            <h1>{client.first_name} {client.last_name}</h1>
            <p>Phone: {client.phone}</p>
            <p>Email: {client.email}</p>
            <p>Address: {client.address}</p>
            <h2>Resume Content</h2>
            <p>Template: {resume.template_type}</p>
            <p>ATS Score: {resume.ats_score}</p>
            <p>Generated: {datetime.now().strftime('%B %d, %Y')}</p>
        </body>
        </html>
        """
        
        # Write HTML file (in production, this would be PDF generation)
        with open(pdf_path.replace('.pdf', '.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Create empty PDF file as placeholder
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4\n%Placeholder PDF file\n')
        
        return True
    except Exception as e:
        logger.error(f"PDF generation simulation failed: {e}")
        return False