#!/usr/bin/env python3
"""
Test Client Creation Workflow
Tests the full client creation flow from form submission to database persistence
"""

import requests
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000/api/case-management"
CASE_MANAGER_ID = "cm_001"

# Sample client data for testing
test_client_data = {
    "first_name": "John",
    "last_name": "TestClient",
    "date_of_birth": "1985-06-15",
    "phone": "(555) 123-4567",
    "email": "john.test@example.com",
    "address": "123 Test Street",
    "city": "Los Angeles",
    "state": "CA",
    "zip_code": "90210",
    "emergency_contact_name": "Jane TestContact",
    "emergency_contact_phone": "(555) 987-6543",
    "emergency_contact_relationship": "Spouse",
    "case_manager_id": CASE_MANAGER_ID,
    "risk_level": "Medium",
    "case_status": "Active",
    "housing_status": "Homeless",
    "employment_status": "Unemployed",
    "benefits_status": "Not Applied",
    "legal_status": "On Probation",
    "program_type": "Reentry",
    "referral_source": "Probation Officer",
    "prior_convictions": "Drug possession (2020)",
    "substance_abuse_history": "Past",
    "mental_health_status": "Stable",
    "transportation": "Public Transit",
    "medical_conditions": "None reported",
    "special_needs": "None",
    "goals": "Find stable housing and employment",
    "barriers": "Criminal record, lack of stable housing",
    "needs": ["housing", "employment", "benefits"],
    "notes": "Motivated client, completed drug treatment program in 2021"
}


def test_api_health():
    """Test API health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API Health Check: PASSED")
            return True
        else:
            print(f"❌ API Health Check: FAILED (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ API Health Check: ERROR - {e}")
        return False


def test_create_client():
    """Test client creation"""
    try:
        response = requests.post(
            f"{BASE_URL}/clients",
            headers={"Content-Type": "application/json"},
            data=json.dumps(test_client_data)
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Client Creation: PASSED")
                print(f"   Client ID: {data.get('client_id')}")
                return data.get('client_id')
            else:
                print(f"❌ Client Creation: FAILED - {data.get('message')}")
                return None
        else:
            print(f"❌ Client Creation: FAILED (Status: {response.status_code})")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Client Creation: ERROR - {e}")
        return None


def test_get_client(client_id):
    """Test retrieving a specific client"""
    try:
        response = requests.get(f"{BASE_URL}/clients/{client_id}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('client'):
                print("✅ Client Retrieval: PASSED")
                client = data['client']
                print(f"   Name: {client['full_name']}")
                print(f"   Risk Score: {client.get('risk_score', 'N/A')}")
                return True
            else:
                print(f"❌ Client Retrieval: FAILED - {data}")
                return False
        else:
            print(f"❌ Client Retrieval: FAILED (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Client Retrieval: ERROR - {e}")
        return False


def test_get_clients_list():
    """Test retrieving clients list for case manager"""
    try:
        response = requests.get(f"{BASE_URL}/clients?case_manager_id={CASE_MANAGER_ID}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Client List Retrieval: PASSED")
                print(f"   Total Clients: {data.get('total_count', 0)}")
                return True
            else:
                print(f"❌ Client List Retrieval: FAILED - {data}")
                return False
        else:
            print(f"❌ Client List Retrieval: FAILED (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Client List Retrieval: ERROR - {e}")
        return False


def test_dashboard_stats():
    """Test dashboard statistics"""
    try:
        response = requests.get(f"{BASE_URL}/dashboard/{CASE_MANAGER_ID}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Dashboard Statistics: PASSED")
                stats = data.get('statistics', {})
                print(f"   Total Clients: {stats.get('total_clients', 0)}")
                print(f"   High Risk: {stats.get('high_risk_clients', 0)}")
                return True
            else:
                print(f"❌ Dashboard Statistics: FAILED - {data}")
                return False
        else:
            print(f"❌ Dashboard Statistics: FAILED (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Dashboard Statistics: ERROR - {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Client Creation Workflow")
    print("=" * 50)
    
    # Test API health
    if not test_api_health():
        print("\n❌ API is not responding. Make sure the server is running.")
        return
    
    print()
    
    # Test client creation
    client_id = test_create_client()
    print()
    
    # Test client retrieval if creation succeeded
    if client_id:
        test_get_client(client_id)
        print()
    
    # Test client list retrieval
    test_get_clients_list()
    print()
    
    # Test dashboard statistics
    test_dashboard_stats()
    
    print("\n" + "=" * 50)
    print("🏁 Test Summary Complete")
    
    if client_id:
        print(f"\n✅ SUCCESS: Client created with ID: {client_id}")
        print("The full client creation workflow is working!")
    else:
        print("\n❌ FAILED: Client creation workflow has issues")


if __name__ == "__main__":
    main()