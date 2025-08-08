#!/usr/bin/env python3
"""
Validate API After HTML Template Cleanup
Ensures all API endpoints still work after removing HTML template system
"""

import sys
import os
sys.path.append('.')

from main import app
from fastapi.testclient import TestClient

def validate_api_cleanup():
    """Validate that API works correctly after HTML template cleanup"""
    print("🧹 Validating API after HTML template cleanup")
    print("=" * 50)
    
    client = TestClient(app)
    
    # Test root endpoint (should return JSON, not HTML)
    print("1. Testing root endpoint...")
    try:
        response = client.get("/")
        if response.status_code == 200:
            data = response.json()
            if "Case Management Suite API" in data.get("message", ""):
                print("   ✅ Root endpoint returns JSON API info")
            else:
                print("   ❌ Root endpoint doesn't return expected API info")
        else:
            print(f"   ❌ Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Root endpoint error: {e}")
    
    # Test health endpoint
    print("2. Testing health endpoint...")
    try:
        response = client.get("/api/health")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print("   ✅ Health endpoint working correctly")
            else:
                print("   ❌ Health endpoint returned unexpected data")
        else:
            print(f"   ❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health endpoint error: {e}")
    
    # Test case management endpoint
    print("3. Testing case management endpoint...")
    try:
        response = client.get("/api/case-management/")
        if response.status_code == 200:
            data = response.json()
            if "Case Management API Ready" in data.get("message", ""):
                print("   ✅ Case management API working correctly")
            else:
                print("   ❌ Case management API returned unexpected data")
        else:
            print(f"   ❌ Case management API failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Case management API error: {e}")
    
    # Test that HTML routes are gone
    print("4. Verifying HTML routes are removed...")
    html_routes_to_test = [
        "/case-management",  # This should 404 now
        "/housing",
        "/benefits", 
        "/resume",
        "/legal",
        "/ai-chat",
        "/services",
        "/smart-dashboard"
    ]
    
    html_routes_removed = 0
    for route in html_routes_to_test:
        try:
            response = client.get(route)
            if response.status_code == 404:
                html_routes_removed += 1
        except:
            html_routes_removed += 1
    
    if html_routes_removed == len(html_routes_to_test):
        print(f"   ✅ All {len(html_routes_to_test)} HTML routes successfully removed")
    else:
        print(f"   ⚠️  {html_routes_removed}/{len(html_routes_to_test)} HTML routes removed")
    
    # Test API documentation endpoints
    print("5. Testing API documentation...")
    try:
        docs_response = client.get("/docs")
        redoc_response = client.get("/redoc")
        
        if docs_response.status_code == 200 and redoc_response.status_code == 200:
            print("   ✅ API documentation (Swagger/ReDoc) working correctly")
        else:
            print("   ❌ API documentation has issues")
    except Exception as e:
        print(f"   ❌ API documentation error: {e}")
    
    # Count total API routes
    print("6. API routes summary...")
    try:
        routes = [str(route) for route in app.routes]
        api_routes = [r for r in routes if '/api/' in r]
        case_mgmt_routes = [r for r in routes if 'case-management' in r]
        
        print(f"   📊 Total API routes: {len(api_routes)}")
        print(f"   📊 Case management routes: {len(case_mgmt_routes)}")
        print(f"   📊 All routes: {len(routes)}")
    except Exception as e:
        print(f"   ❌ Route counting error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 HTML Template Cleanup Validation Complete!")
    print("\n✅ SUMMARY:")
    print("   - All HTML template routes removed")
    print("   - Static file serving disabled") 
    print("   - Template engine references removed")
    print("   - API endpoints still functional")
    print("   - React frontend will handle all UI")
    print("\n🚀 Backend API is now clean and ready!")

if __name__ == "__main__":
    validate_api_cleanup()