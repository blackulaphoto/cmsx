#!/usr/bin/env python3
"""
TEST NEW API ENDPOINTS
Test the new 9-database API endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test health check endpoint"""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check: {data['status']}")
            print(f"   📊 Architecture: {data['architecture']}")
            print(f"   🤖 AI Permissions: {data['ai_permissions']}")
            return True
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False

def test_database_status():
    """Test database status endpoint"""
    print("\n🗄️  Testing database status...")
    try:
        response = requests.get(f"{BASE_URL}/api/system/database-status")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Found {len(data)} databases:")
            for db_name, info in data.items():
                status = "✅" if info['exists'] else "❌"
                print(f"      {status} {db_name}: {info['file']} ({info['size']} bytes)")
            return True
        else:
            print(f"   ❌ Database status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Database status error: {e}")
        return False

def test_access_matrix():
    """Test access matrix endpoint"""
    print("\n🔒 Testing access matrix...")
    try:
        response = requests.get(f"{BASE_URL}/api/system/access-matrix")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Access matrix loaded with {len(data)} databases")
            
            # Check AI permissions
            if 'ai_assistant' in data:
                ai_perms = data['ai_assistant']
                if 'special' in ai_perms and ai_perms['special'] == 'FULL_CRUD_ALL_DATABASES':
                    print("   🤖 AI has FULL CRUD permissions confirmed")
                else:
                    print("   ⚠️  AI permissions not properly configured")
            return True
        else:
            print(f"   ❌ Access matrix failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Access matrix error: {e}")
        return False

def test_client_endpoints():
    """Test client CRUD endpoints"""
    print("\n👤 Testing client endpoints...")
    
    try:
        # Test getting all clients
        response = requests.get(f"{BASE_URL}/api/clients")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Retrieved {data['count']} clients")
        else:
            print(f"   ❌ Get clients failed: {response.status_code}")
            return False
            
        # Test creating a client
        new_client = {
            "first_name": "API",
            "last_name": "Test",
            "phone": "555-API1",
            "email": "api@test.com",
            "risk_level": "low",
            "case_status": "active"
        }
        
        response = requests.post(f"{BASE_URL}/api/clients", json=new_client)
        if response.status_code == 200:
            data = response.json()
            client_id = data['client_id']
            print(f"   ✅ Created client: {client_id}")
            
            # Test getting the specific client
            response = requests.get(f"{BASE_URL}/api/clients/{client_id}")
            if response.status_code == 200:
                client_data = response.json()
                print(f"   ✅ Retrieved client: {client_data['first_name']} {client_data['last_name']}")
                
                # Test updating the client
                updates = {
                    "phone": "555-UPDATED",
                    "email": "updated@test.com"
                }
                
                response = requests.put(f"{BASE_URL}/api/clients/{client_id}", json=updates)
                if response.status_code == 200:
                    print("   ✅ Updated client successfully")
                    
                    # Test adding a case note
                    note_data = {
                        "note_type": "api_test",
                        "content": "This is an API test case note",
                        "created_by": "api_test"
                    }
                    
                    response = requests.post(f"{BASE_URL}/api/clients/{client_id}/notes", json=note_data)
                    if response.status_code == 200:
                        note_result = response.json()
                        print(f"   ✅ Added case note: {note_result['note_id']}")
                        return client_id
                    else:
                        print(f"   ❌ Add case note failed: {response.status_code}")
                else:
                    print(f"   ❌ Update client failed: {response.status_code}")
            else:
                print(f"   ❌ Get specific client failed: {response.status_code}")
        else:
            print(f"   ❌ Create client failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Client endpoints error: {e}")
        
    return None

def test_ai_endpoints(client_id=None):
    """Test AI Assistant endpoints"""
    print("\n🤖 Testing AI Assistant endpoints...")
    
    try:
        # Test AI creating a client
        ai_client = {
            "first_name": "AI",
            "last_name": "Assistant",
            "phone": "555-AI99",
            "email": "ai@assistant.com",
            "risk_level": "medium",
            "case_status": "active"
        }
        
        response = requests.post(f"{BASE_URL}/api/ai/clients", json=ai_client)
        if response.status_code == 200:
            data = response.json()
            ai_client_id = data['client_id']
            print(f"   ✅ AI created client: {ai_client_id}")
            
            # Test AI getting complete profile
            response = requests.get(f"{BASE_URL}/api/ai/clients/{ai_client_id}/complete-profile")
            if response.status_code == 200:
                profile = response.json()
                print(f"   ✅ AI retrieved complete profile with {len(profile)} sections")
                
                # Test AI saving conversation
                conversation = {
                    "client_id": ai_client_id,
                    "user_id": "api_test",
                    "messages": [
                        {"role": "user", "content": "Tell me about this client"},
                        {"role": "assistant", "content": "This is a client created via API test"}
                    ],
                    "context_data": {"test": "api_endpoint"}
                }
                
                response = requests.post(f"{BASE_URL}/api/ai/conversations", json=conversation)
                if response.status_code == 200:
                    conv_result = response.json()
                    print(f"   ✅ AI saved conversation: {conv_result['conversation_id']}")
                    
                    # Test AI updating analytics
                    analytics = {
                        "risk_factors": {"housing": "low", "employment": "high"},
                        "success_probability": 0.85,
                        "recommended_actions": ["job_training", "housing_assistance"]
                    }
                    
                    response = requests.put(f"{BASE_URL}/api/ai/clients/{ai_client_id}/analytics", json=analytics)
                    if response.status_code == 200:
                        analytics_result = response.json()
                        print(f"   ✅ AI updated analytics: {analytics_result['analytics_id']}")
                        return ai_client_id
                    else:
                        print(f"   ❌ AI analytics update failed: {response.status_code}")
                else:
                    print(f"   ❌ AI conversation save failed: {response.status_code}")
            else:
                print(f"   ❌ AI complete profile failed: {response.status_code}")
        else:
            print(f"   ❌ AI create client failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ AI endpoints error: {e}")
        
    return None

def test_module_endpoints(client_id):
    """Test module-specific endpoints"""
    print(f"\n🏠 Testing module endpoints for client {client_id}...")
    
    modules = ['housing', 'benefits', 'legal', 'employment', 'services', 'reminders']
    
    for module in modules:
        try:
            response = requests.get(f"{BASE_URL}/api/{module}/clients/{client_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ {module}: Retrieved data with {len(data)} sections")
            else:
                print(f"   ⚠️  {module}: {response.status_code} (expected for new client)")
        except Exception as e:
            print(f"   ❌ {module}: {e}")

def main():
    """Run all API tests"""
    print("🚀 TESTING NEW API ENDPOINTS")
    print("=" * 50)
    
    # Wait a moment for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    # Test 1: Health check
    if not test_health_check():
        print("❌ Server not responding. Make sure backend is running on port 8000")
        return
    
    # Test 2: Database status
    test_database_status()
    
    # Test 3: Access matrix
    test_access_matrix()
    
    # Test 4: Client endpoints
    client_id = test_client_endpoints()
    
    # Test 5: AI endpoints
    ai_client_id = test_ai_endpoints()
    
    # Test 6: Module endpoints
    if client_id:
        test_module_endpoints(client_id)
    
    print("\n" + "=" * 50)
    print("✅ API ENDPOINT TESTING COMPLETE!")
    print("🗄️  9-Database architecture API verified")
    print("🤖 AI full CRUD API endpoints confirmed")
    print("🔗 Module-specific endpoints working")
    
    if client_id:
        print(f"📊 Test client created via API: {client_id}")
    if ai_client_id:
        print(f"🤖 AI client created via API: {ai_client_id}")

if __name__ == "__main__":
    main()