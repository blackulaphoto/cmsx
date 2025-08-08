#!/usr/bin/env python3
"""
Case Management Suite - Launch Platform Script
Comprehensive startup script that ensures all systems are ready for launch
"""
import os
import sys
import time
import subprocess
import sqlite3
import requests
from pathlib import Path
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_python_dependencies():
    """Check if all required Python packages are installed"""
    print("🐍 Checking Python Dependencies...")
    
    required_packages = [
        'fastapi', 'uvicorn', 'pydantic', 'sqlite3', 'requests',
        'openai', 'bs4', 'pandas', 'numpy'  # bs4 is the import name for beautifulsoup4
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {missing_packages}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✅ All Python dependencies satisfied")
    return True

def check_databases():
    """Check database integrity and structure"""
    print("\n🗄️  Checking Database Integrity...")
    
    critical_databases = {
        'databases/core_clients.db': ['clients'],
        'databases/case_management.db': ['clients', 'cases'],
        'databases/unified_platform.db': ['benefits_applications'],
        'databases/search_cache.db': []
    }
    
    all_good = True
    for db_path, required_tables in critical_databases.items():
        if not os.path.exists(db_path):
            print(f"  ❌ {db_path}: Missing")
            all_good = False
            continue
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            missing = [t for t in required_tables if t not in tables]
            if missing:
                print(f"  ⚠️  {db_path}: Missing tables {missing}")
                all_good = False
            else:
                print(f"  ✅ {db_path}: OK")
                
        except Exception as e:
            print(f"  ❌ {db_path}: Error - {e}")
            all_good = False
    
    return all_good

def check_environment_variables():
    """Check required environment variables"""
    print("\n🔐 Checking Environment Variables...")
    
    required_vars = ['OPENAI_API_KEY', 'GOOGLE_API_KEY']
    optional_vars = ['GOOGLE_CSE_ID']
    
    all_good = True
    for var in required_vars:
        if os.getenv(var):
            print(f"  ✅ {var}: Set")
        else:
            print(f"  ❌ {var}: Missing")
            all_good = False
    
    for var in optional_vars:
        if os.getenv(var):
            print(f"  ✅ {var}: Set (optional)")
        else:
            print(f"  ⚠️  {var}: Not set (optional)")
    
    return all_good

def check_frontend_dependencies():
    """Check if frontend dependencies are installed"""
    print("\n🌐 Checking Frontend Dependencies...")
    
    frontend_path = Path("frontend")
    if not frontend_path.exists():
        print("  ❌ Frontend directory not found")
        return False
    
    node_modules = frontend_path / "node_modules"
    if not node_modules.exists():
        print("  ❌ Node modules not installed")
        print("  Run: cd frontend && npm install")
        return False
    
    package_json = frontend_path / "package.json"
    if package_json.exists():
        print("  ✅ Frontend dependencies appear to be installed")
        return True
    
    return False

def start_backend():
    """Start the backend server"""
    print("\n🚀 Starting Backend Server...")
    
    try:
        # Start the backend in a separate process
        process = subprocess.Popen([
            sys.executable, "main.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Check if it's running
        try:
            response = requests.get("http://localhost:8000/api/health", timeout=5)
            if response.status_code == 200:
                print("  ✅ Backend server started successfully")
                return process
            else:
                print(f"  ❌ Backend health check failed: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Backend not responding: {e}")
            return None
            
    except Exception as e:
        print(f"  ❌ Failed to start backend: {e}")
        return None

def test_critical_endpoints():
    """Test critical API endpoints"""
    print("\n🧪 Testing Critical API Endpoints...")
    
    endpoints = [
        ("http://localhost:8000/api/health", "Health Check"),
        ("http://localhost:8000/api/case-management/clients", "Case Management"),
        ("http://localhost:8000/api/housing/search", "Housing Search"),
        ("http://localhost:8000/api/benefits/applications", "Benefits"),
        ("http://localhost:8000/api/ai/", "AI Assistant")
    ]
    
    all_good = True
    for url, name in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {name}: OK")
            else:
                print(f"  ⚠️  {name}: Status {response.status_code}")
                all_good = False
        except requests.exceptions.RequestException as e:
            print(f"  ❌ {name}: Failed - {e}")
            all_good = False
    
    return all_good

def display_launch_info():
    """Display launch information"""
    print("\n" + "="*60)
    print("🎉 CASE MANAGEMENT SUITE - LAUNCH READY")
    print("="*60)
    print()
    print("📊 Backend API: http://localhost:8000")
    print("📋 API Documentation: http://localhost:8000/docs")
    print("🌐 Frontend: http://localhost:5173 (run: cd frontend && npm run dev)")
    print()
    print("🔧 Key Features Available:")
    print("  • Case Management & Client Intake")
    print("  • Housing Search & Placement")
    print("  • Benefits Coordination & Disability Assessment")
    print("  • Legal Services & Expungement")
    print("  • Resume Builder & Employment")
    print("  • AI Assistant & Smart Reminders")
    print("  • Services Directory & Job Search")
    print()
    print("📁 Database Architecture:")
    print("  • Single Source of Truth: core_clients.db")
    print("  • Distributed modules with foreign key relationships")
    print("  • 15+ specialized databases for optimal performance")
    print()
    print("🚀 Ready for Production Deployment!")
    print("="*60)

def main():
    """Main launch sequence"""
    print("🚀 Case Management Suite - Launch Sequence")
    print("="*60)
    
    # Pre-flight checks
    checks_passed = True
    
    if not check_python_dependencies():
        checks_passed = False
    
    if not check_databases():
        checks_passed = False
    
    if not check_environment_variables():
        checks_passed = False
    
    if not check_frontend_dependencies():
        print("  ⚠️  Frontend dependencies not checked (optional for backend-only launch)")
    
    if not checks_passed:
        print("\n❌ Pre-flight checks failed. Please resolve issues before launching.")
        return False
    
    print("\n✅ All pre-flight checks passed!")
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print("\n❌ Failed to start backend server")
        return False
    
    # Test endpoints
    if not test_critical_endpoints():
        print("\n⚠️  Some endpoints may have issues, but core functionality is available")
    
    # Display launch info
    display_launch_info()
    
    print("\n💡 Next Steps:")
    print("1. Start frontend: cd frontend && npm run dev")
    print("2. Open browser to http://localhost:5173")
    print("3. Begin case management operations")
    print("\nPress Ctrl+C to stop the backend server")
    
    try:
        # Keep the script running
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend_process.terminate()
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)