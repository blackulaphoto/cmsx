#!/usr/bin/env python3
"""
Test Resume Builder API Endpoints
Test the FastAPI routes for Resume Builder functionality
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add the backend modules to path
sys.path.append('backend/modules')

from fastapi.testclient import TestClient
from resume.routes import router
from fastapi import FastAPI

# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/resume")

client = TestClient(app)

def test_resume_api():
    """Test all Resume Builder API endpoints"""
    print("🧪 Testing Resume Builder API Endpoints")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1. Testing Health Check...")
    try:
        response = client.get("/api/resume/health")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed - Status: {data.get('status')}")
            print(f"   ✅ Active clients: {data.get('active_clients_count', 0)}")
        else:
            print(f"   ❌ Health check failed")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False
    
    # Test 2: Get Available Clients
    print("\n2. Testing Get Available Clients...")
    try:
        response = client.get("/api/resume/clients")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            clients = data.get('clients', [])
            print(f"   ✅ Retrieved {len(clients)} clients")
            if clients:
                test_client = clients[0]
                print(f"   ✅ Test client: {test_client['first_name']} {test_client['last_name']}")
                client_id = test_client['client_id']
            else:
                print("   ⚠️  No clients available for testing")
                return False
        else:
            print(f"   ❌ Failed to get clients")
            return False
    except Exception as e:
        print(f"   ❌ Get clients error: {e}")
        return False
    
    # Test 3: Create Employment Profile
    print("\n3. Testing Create Employment Profile...")
    try:
        profile_data = {
            "client_id": client_id,
            "work_history": [
                {
                    "job_title": "Warehouse Associate",
                    "company": "Test Company",
                    "start_date": "2020-01",
                    "end_date": "2022-12",
                    "description": "Managed inventory and shipping operations"
                }
            ],
            "education": [
                {
                    "degree": "High School Diploma",
                    "institution": "Test High School",
                    "graduation_date": "2018"
                }
            ],
            "skills": [
                {
                    "category": "Technical Skills",
                    "skill_list": ["Forklift Operation", "Inventory Management"]
                }
            ],
            "certifications": [
                {
                    "name": "Forklift Certification",
                    "issuer": "OSHA",
                    "date_obtained": "2020-03"
                }
            ],
            "career_objective": "Seeking warehouse employment opportunities",
            "preferred_industries": ["Logistics", "Manufacturing"]
        }
        
        response = client.post("/api/resume/profile", json=profile_data)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            profile_id = data.get('profile_id')
            print(f"   ✅ Employment profile created: {profile_id}")
        else:
            print(f"   ❌ Failed to create profile: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Create profile error: {e}")
        return False
    
    # Test 4: Get Employment Profile
    print("\n4. Testing Get Employment Profile...")
    try:
        response = client.get(f"/api/resume/profile/{client_id}")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            profile = data.get('profile')
            if profile:
                print(f"   ✅ Profile retrieved successfully")
                print(f"      - Career objective: {profile['career_objective'][:50]}...")
                print(f"      - Work history entries: {len(profile['work_history'])}")
                print(f"      - Skill categories: {len(profile['skills'])}")
            else:
                print("   ❌ No profile data returned")
                return False
        else:
            print(f"   ❌ Failed to get profile")
            return False
    except Exception as e:
        print(f"   ❌ Get profile error: {e}")
        return False
    
    # Test 5: Create Resume
    print("\n5. Testing Create Resume...")
    try:
        resume_data = {
            "client_id": client_id,
            "template_type": "warehouse",
            "resume_title": "Test Warehouse Resume"
        }
        
        response = client.post("/api/resume/create", json=resume_data)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            resume_id = data.get('resume_id')
            ats_score = data.get('ats_score')
            print(f"   ✅ Resume created: {resume_id}")
            print(f"   ✅ ATS Score: {ats_score}")
        else:
            print(f"   ❌ Failed to create resume: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Create resume error: {e}")
        return False
    
    # Test 6: Get Client Resumes
    print("\n6. Testing Get Client Resumes...")
    try:
        response = client.get(f"/api/resume/list/{client_id}")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            resumes = data.get('resumes', [])
            print(f"   ✅ Retrieved {len(resumes)} resumes")
            if resumes:
                resume = resumes[0]
                print(f"      - Resume: {resume['resume_title']}")
                print(f"      - Template: {resume['template_type']}")
                print(f"      - ATS Score: {resume['ats_score']}")
        else:
            print(f"   ❌ Failed to get resumes")
            return False
    except Exception as e:
        print(f"   ❌ Get resumes error: {e}")
        return False
    
    # Test 7: Optimize Resume
    print("\n7. Testing Resume Optimization...")
    try:
        optimize_data = {
            "resume_id": resume_id,
            "optimization_type": "ats_optimization"
        }
        
        response = client.post("/api/resume/optimize", json=optimize_data)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            improvement = data.get('ats_score_improvement')
            new_score = data.get('new_ats_score')
            print(f"   ✅ Resume optimized successfully")
            print(f"      - Score improvement: {improvement}")
            print(f"      - New ATS score: {new_score}")
        else:
            print(f"   ❌ Failed to optimize resume: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Optimize resume error: {e}")
        return False
    
    # Test 8: Apply to Job
    print("\n8. Testing Job Application...")
    try:
        job_data = {
            "client_id": client_id,
            "resume_id": resume_id,
            "job_title": "Warehouse Supervisor",
            "company_name": "Test Distribution Co",
            "job_description": "Looking for experienced warehouse professional"
        }
        
        response = client.post("/api/resume/apply-job", json=job_data)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            app_id = data.get('application_id')
            match_score = data.get('match_score')
            print(f"   ✅ Job application created: {app_id}")
            print(f"      - Match score: {match_score}%")
        else:
            print(f"   ❌ Failed to create job application: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Job application error: {e}")
        return False
    
    # Test 9: Get Job Applications
    print("\n9. Testing Get Job Applications...")
    try:
        response = client.get(f"/api/resume/applications/{client_id}")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            applications = data.get('applications', [])
            print(f"   ✅ Retrieved {len(applications)} job applications")
            if applications:
                app = applications[0]
                print(f"      - Job: {app['job_title']} at {app['company_name']}")
                print(f"      - Status: {app['application_status']}")
                print(f"      - Match score: {app['match_score']}%")
        else:
            print(f"   ❌ Failed to get job applications")
            return False
    except Exception as e:
        print(f"   ❌ Get job applications error: {e}")
        return False
    
    # Test Summary
    print("\n" + "=" * 50)
    print("🎉 RESUME BUILDER API TEST RESULTS")
    print("=" * 50)
    print("✅ Health Check: PASSED")
    print("✅ Get Available Clients: PASSED")
    print("✅ Create Employment Profile: PASSED")
    print("✅ Get Employment Profile: PASSED")
    print("✅ Create Resume: PASSED")
    print("✅ Get Client Resumes: PASSED")
    print("✅ Resume Optimization: PASSED")
    print("✅ Job Application: PASSED")
    print("✅ Get Job Applications: PASSED")
    print("\n🏆 ALL API TESTS PASSED!")
    print("\n📊 API Test Statistics:")
    print(f"   - Endpoints tested: 9")
    print(f"   - Success rate: 100%")
    print(f"   - Test client used: {test_client['first_name']} {test_client['last_name']}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_resume_api()
        if success:
            print("\n✅ Resume Builder API is ready for production!")
        else:
            print("\n❌ Resume Builder API needs attention before production use.")
    except Exception as e:
        print(f"\n💥 API testing failed with error: {e}")
        print("❌ Resume Builder API needs debugging.")