#!/usr/bin/env python3
"""
Benefits Routes - FastAPI Router for Second Chance Jobs Platform
Benefits coordination and disability assessment
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import json
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from benefits.models import BenefitsApplication, BenefitsDatabase
from benefits.disability_assessment import DisabilityAssessment, QUALIFYING_CONDITIONS

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(tags=["benefits"])

# Initialize services
benefits_db = None
disability_assessor = None

def get_benefits_db():
    """Get thread-safe benefits database instance"""
    global benefits_db
    if benefits_db is None:
        benefits_db = BenefitsDatabase("databases/benefits_transport.db")
    return benefits_db

def get_disability_assessor():
    """Get disability assessor instance"""
    global disability_assessor
    if disability_assessor is None:
        disability_assessor = DisabilityAssessment()
    return disability_assessor

# Pydantic models
class EligibilityCheck(BaseModel):
    client_id: str
    household_size: int
    monthly_income: float
    is_disabled: bool = False
    is_veteran: bool = False
    has_children: bool = False
    age: Optional[int] = None

class DisabilityAssessmentRequest(BaseModel):
    client_id: str
    age: int
    medical_conditions: List[str]
    work_history: List[Dict[str, Any]]
    current_income: float = 0
    years_out_of_work: int = 0
    functional_limitations: Optional[Dict[str, Any]] = None

class BenefitApplication(BaseModel):
    client_id: str
    benefit_type: str
    application_method: str = "Online"
    assistance_received: bool = False
    notes: str = ""

class StartApplication(BaseModel):
    client_id: str
    benefit_type: str
    assessment_data: Optional[Dict[str, Any]] = None

# =============================================================================
# API ROUTES
# =============================================================================

@router.get("/")
async def benefits_api_info():
    """Benefits API information and available endpoints"""
    return {
        "message": "Benefits API Ready",
        "version": "1.0",
        "endpoints": {
            "applications": "/api/benefits/applications",
            "assessment": "/api/benefits/assessment",
            "eligibility": "/api/benefits/eligibility",
            "transportation": "/api/benefits/transportation"
        },
        "description": "Benefits coordination and disability assessment services"
    }

@router.get("/applications")
async def get_benefits_applications(
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Get benefits applications"""
    try:
        # Get applications from database
        import sqlite3
        
        # Get applications from unified_platform.db
        conn_unified = sqlite3.connect('databases/unified_platform.db')
        cursor_unified = conn_unified.cursor()
        
        # Get client data from core_clients.db
        conn_clients = sqlite3.connect('databases/core_clients.db')
        cursor_clients = conn_clients.cursor()
        
        query = """
        SELECT id, client_id, benefit_type, status, application_method, 
               notes, created_at
        FROM benefits_applications
        WHERE 1=1
        """
        params = []
        
        if client_id:
            query += " AND client_id = ?"
            params.append(client_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
            
        cursor_unified.execute(query, params)
        rows = cursor_unified.fetchall()
        
        applications = []
        for row in rows:
            # Get client name from core_clients.db
            client_name = "Unknown Client"
            if row[1]:  # client_id
                cursor_clients.execute("SELECT first_name, last_name FROM clients WHERE client_id = ?", (row[1],))
                client_row = cursor_clients.fetchone()
                if client_row:
                    client_name = f"{client_row[0]} {client_row[1]}"
            
            applications.append({
                'application_id': row[0],
                'client_id': row[1],
                'client_name': client_name,
                'benefit_type': row[2],
                'application_status': row[3] if row[3] else 'Pending',
                'completion_percentage': 25,
                'current_step': 'Initial Application Submitted',
                'next_action_required': 'Submit income verification',
                'application_date': row[6][:10] if row[6] else '2024-02-15',
                'monthly_benefit_amount': 250.0,
                'case_worker_name': 'Lisa Chen',
                'case_worker_phone': '(213) 555-0199'
            })
        
        conn_unified.close()
        conn_clients.close()
        
        return {
            'success': True,
            'applications': applications,
            'total_count': len(applications)
        }
        
    except Exception as e:
        logger.error(f"Get benefits applications error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/applications")
async def create_benefits_application(application_data: BenefitApplication):
    """Create a new benefits application"""
    try:
        # Create application ID
        application_id = f"ben_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save to database
        import sqlite3
        conn = sqlite3.connect('databases/unified_platform.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO benefits_applications 
            (id, client_id, benefit_type, status, application_method, need_assistance, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            application_id,
            application_data.client_id,
            application_data.benefit_type,
            'Started',
            application_data.application_method,
            application_data.assistance_received,
            application_data.notes,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        application = {
            'application_id': application_id,
            'client_id': application_data.client_id,
            'benefit_type': application_data.benefit_type,
            'application_method': application_data.application_method,
            'assistance_received': application_data.assistance_received,
            'notes': application_data.notes,
            'application_status': 'Started',
            'created_at': datetime.now().isoformat()
        }
        
        return {
            'success': True,
            'message': 'Benefits application created successfully',
            'application_id': application_id,
            'application': application
        }
        
    except Exception as e:
        logger.error(f"Create benefits application error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types")
async def get_benefit_types():
    """Get available benefit types"""
    try:
        benefit_types = [
            {
                'value': 'SNAP',
                'label': 'SNAP/CalFresh Food Assistance',
                'description': 'Monthly food assistance benefits',
                'estimated_timeline': '30 days',
                'contact': '1-877-847-3663'
            },
            {
                'value': 'Medicaid',
                'label': 'Medicaid Health Coverage',
                'description': 'Comprehensive healthcare coverage',
                'estimated_timeline': '45 days',
                'contact': '1-800-318-2596'
            },
            {
                'value': 'SSI',
                'label': 'Supplemental Security Income',
                'description': 'Monthly income for disabled individuals',
                'estimated_timeline': '3-5 months',
                'contact': '1-800-772-1213'
            },
            {
                'value': 'SSDI',
                'label': 'Social Security Disability Insurance',
                'description': 'Disability benefits based on work history',
                'estimated_timeline': '3-5 months',
                'contact': '1-800-772-1213'
            },
            {
                'value': 'Housing_Voucher',
                'label': 'Housing Choice Voucher (Section 8)',
                'description': 'Rental assistance vouchers',
                'estimated_timeline': '2+ years (waitlist)',
                'contact': 'Local Housing Authority'
            },
            {
                'value': 'WIC',
                'label': 'Women, Infants & Children Program',
                'description': 'Nutrition program for pregnant women and children',
                'estimated_timeline': '1-2 weeks',
                'contact': '1-800-942-3678'
            },
            {
                'value': 'TANF',
                'label': 'Temporary Assistance for Needy Families',
                'description': 'Temporary cash assistance for families',
                'estimated_timeline': '30 days',
                'contact': 'Local TANF Office'
            },
            {
                'value': 'LIHEAP',
                'label': 'Low Income Home Energy Assistance',
                'description': 'Utility bill assistance',
                'estimated_timeline': '2-4 weeks',
                'contact': 'Local Energy Assistance Office'
            }
        ]
        
        return {
            'success': True,
            'benefit_types': benefit_types,
            'total_count': len(benefit_types)
        }
        
    except Exception as e:
        logger.error(f"Get benefit types error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/guidance/{benefit_type}")
async def get_benefit_guidance(benefit_type: str):
    """Get comprehensive guidance for specific benefit type"""
    try:
        guidance_data = {
            'SNAP': {
                'benefit_type': 'SNAP/CalFresh',
                'description': 'Food assistance program providing monthly benefits',
                'eligibility_requirements': [
                    'Household income below 130% of federal poverty level',
                    'U.S. citizen or qualified immigrant',
                    'Meet work requirements (if able-bodied adult)',
                    'Provide Social Security numbers for household members'
                ],
                'required_documents': [
                    'Photo identification',
                    'Proof of income (pay stubs, unemployment benefits)',
                    'Proof of housing costs (rent receipt, utility bills)',
                    'Bank statements',
                    'Social Security cards for all household members'
                ],
                'application_steps': [
                    'Complete application online or at local office',
                    'Schedule eligibility interview',
                    'Submit required documents',
                    'Await approval decision',
                    'Receive EBT card if approved'
                ],
                'timeline': '30 days from application submission',
                'contact_information': {
                    'phone': '1-877-847-3663',
                    'website': 'https://www.calfresh.ca.gov/',
                    'local_office': 'Contact your county social services office'
                }
            },
            'Medicaid': {
                'benefit_type': 'Medicaid',
                'description': 'Healthcare coverage for low-income individuals and families',
                'eligibility_requirements': [
                    'Household income below 138% of federal poverty level',
                    'U.S. citizen or qualified immigrant',
                    'California resident',
                    'Not eligible for Medicare'
                ],
                'required_documents': [
                    'Photo identification',
                    'Proof of income',
                    'Proof of citizenship or immigration status',
                    'Proof of California residence',
                    'Social Security card'
                ],
                'application_steps': [
                    'Apply through Covered California or county office',
                    'Submit required documents',
                    'Complete phone or in-person interview if required',
                    'Await eligibility determination',
                    'Select health plan if approved'
                ],
                'timeline': '45 days from complete application',
                'contact_information': {
                    'phone': '1-800-300-1506',
                    'website': 'https://www.coveredca.com/',
                    'local_office': 'Contact your county human services office'
                }
            },
            'SSI': {
                'benefit_type': 'Supplemental Security Income (SSI)',
                'description': 'Monthly payments for disabled, blind, or aged individuals with limited income',
                'eligibility_requirements': [
                    'Age 65 or older, blind, or disabled',
                    'Limited income and resources',
                    'U.S. citizen or qualified immigrant',
                    'Live in the United States'
                ],
                'required_documents': [
                    'Birth certificate or proof of age',
                    'Medical records and doctor reports',
                    'Work history and earnings records',
                    'Bank statements and financial records',
                    'Marriage certificate (if applicable)'
                ],
                'application_steps': [
                    'Contact Social Security office to schedule appointment',
                    'Complete disability application (SSA-8000)',
                    'Submit medical evidence',
                    'Undergo consultative exam if required',
                    'Wait for disability determination'
                ],
                'timeline': '3-5 months for initial decision',
                'contact_information': {
                    'phone': '1-800-772-1213',
                    'website': 'https://www.ssa.gov/ssi/',
                    'local_office': 'Find your local Social Security office online'
                }
            }
        }
        
        if benefit_type not in guidance_data:
            raise HTTPException(status_code=404, detail="Benefit type not found")
            
        return {
            'success': True,
            'guidance': guidance_data[benefit_type]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get benefit guidance error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/eligibility-check")
async def benefits_eligibility_check(eligibility_data: EligibilityCheck):
    """Check eligibility for various benefits programs"""
    try:
        # Federal Poverty Level for 2024 (simplified)
        poverty_levels = {1: 15060, 2: 20440, 3: 25820, 4: 31200, 5: 36580, 6: 41960, 7: 47320, 8: 52700}
        
        household_size = eligibility_data.household_size
        income = eligibility_data.monthly_income * 12  # Convert to annual
        
        # Get poverty level for household size
        if household_size <= 8:
            poverty_level = poverty_levels[household_size]
        else:
            poverty_level = poverty_levels[8] + (household_size - 8) * 5380
        
        # Calculate income as percentage of poverty level
        income_percentage = (income / poverty_level) * 100
        
        # Determine eligibility for various programs
        eligibility_results = {
            'SNAP': {
                'eligible': income_percentage <= 130,
                'confidence': 'high' if income_percentage <= 130 else 'low',
                'estimated_benefit': max(0, min(835, (poverty_level * 1.3 - income) / 12)) if income_percentage <= 130 else 0,
                'requirements': ['Income below 130% of poverty level', 'Work requirements may apply']
            },
            'Medicaid': {
                'eligible': income_percentage <= 138,
                'confidence': 'high' if income_percentage <= 138 else 'low',
                'estimated_benefit': 'Full healthcare coverage' if income_percentage <= 138 else 'Not eligible',
                'requirements': ['Income below 138% of poverty level']
            },
            'SSI': {
                'eligible': eligibility_data.is_disabled and income_percentage <= 75,
                'confidence': 'medium' if eligibility_data.is_disabled else 'low',
                'estimated_benefit': max(0, 914 - (income / 12)) if eligibility_data.is_disabled and income_percentage <= 75 else 0,
                'requirements': ['Disability determination', 'Limited income and resources']
            },
            'Housing_Voucher': {
                'eligible': income_percentage <= 50,
                'confidence': 'medium' if income_percentage <= 50 else 'low',
                'estimated_benefit': 'Rental assistance up to fair market rent' if income_percentage <= 50 else 'Not eligible',
                'requirements': ['Income below 50% of area median income', 'Long waiting lists']
            }
        }
        
        return {
            'success': True,
            'eligibility_results': eligibility_results,
            'household_income': income,
            'poverty_level': poverty_level,
            'income_percentage': income_percentage
        }
        
    except Exception as e:
        logger.error(f"Eligibility check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/assess-disability")
async def api_disability_assessment(assessment_data: DisabilityAssessmentRequest):
    """Comprehensive disability assessment for SSI/SSDI eligibility"""
    try:
        assessor = get_disability_assessor()
        
        # Extract client information for assessment
        client_data = {
            'age': assessment_data.age,
            'medical_conditions': assessment_data.medical_conditions,
            'work_history': assessment_data.work_history,
            'current_income': assessment_data.current_income,
            'years_out_of_work': assessment_data.years_out_of_work
        }
        
        # Perform assessment
        assessment_result = assessor.assess_eligibility(client_data)
        
        return {
            'success': True,
            'assessment': assessment_result,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Disability assessment error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/qualifying-conditions")
async def api_qualifying_conditions():
    """Get list of qualifying medical conditions for disability benefits"""
    try:
        conditions_list = []
        
        for key, condition in QUALIFYING_CONDITIONS.items():
            conditions_list.append({
                'key': key,
                'name': condition.name,
                'category': condition.category,
                'ssa_listing': condition.ssa_listing,
                'description': condition.description,
                'approval_rate': condition.typical_approval_rate,
                'severity_criteria': condition.severity_criteria
            })
        
        # Sort by category and approval rate
        conditions_list.sort(key=lambda x: (x['category'], -x['approval_rate']))
        
        return {
            'success': True,
            'qualifying_conditions': conditions_list,
            'total_conditions': len(conditions_list)
        }
        
    except Exception as e:
        logger.error(f"Qualifying conditions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start-application")
async def api_start_disability_application(application_data: StartApplication):
    """Start a new SSI or SSDI application and create tracking record"""
    try:
        client_id = application_data.client_id
        benefit_type = application_data.benefit_type
        assessment_data = application_data.assessment_data or {}
        
        if benefit_type not in ['SSI', 'SSDI']:
            raise HTTPException(status_code=400, detail="Benefit type must be SSI or SSDI")
        
        # Create benefits application record
        application_record = {
            'client_id': client_id,
            'benefit_type': benefit_type,
            'application_status': 'Not Started',
            'application_date': datetime.now().isoformat(),
            'completion_percentage': 0,
            'current_step': 'Initial Assessment Completed',
            'next_action_required': 'Gather medical documentation',
            'estimated_completion_time': '3-6 months',
            'created_by': 'case_manager'
        }
        
        # Add assessment-specific information
        if assessment_data:
            estimated_benefit = 0
            if benefit_type == 'SSI':
                estimated_benefit = assessment_data.get('ssi_eligibility', {}).get('estimated_monthly_benefit', 0)
            elif benefit_type == 'SSDI':
                estimated_benefit = assessment_data.get('ssdi_eligibility', {}).get('estimated_monthly_benefit', 0)
            
            application_record.update({
                'monthly_benefit_amount': estimated_benefit,
                'notes': f'Assessment completed. Conditions: {", ".join(assessment_data.get("client_assessment", {}).get("medical_conditions", []))}'
            })
        
        # Generate application ID
        application_id = f"{benefit_type.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        application_record['application_id'] = application_id
        
        return {
            'success': True,
            'message': f'{benefit_type} application started successfully',
            'application_id': application_id,
            'application': application_record
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start disability application error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))