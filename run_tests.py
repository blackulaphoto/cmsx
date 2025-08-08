#!/usr/bin/env python3
"""
Test Runner for Case Management Suite
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print("SUCCESS")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("FAILED")
        print(f"Error: {e}")
        if e.stdout:
            print("Stdout:")
            print(e.stdout)
        if e.stderr:
            print("Stderr:")
            print(e.stderr)
        return False

def main():
    """Main test runner"""
    print("🧪 Case Management Suite - Test Runner")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("Error: main.py not found. Please run from the project root directory.")
        sys.exit(1)
    
    # Install test dependencies if needed
    print("\n📦 Installing test dependencies...")
    run_command("pip install -r requirements.txt", "Install dependencies")
    
    # Run different test suites
    test_results = []
    
    # 1. Run AI service tests
    print("\n🧠 Running AI Service Tests...")
    success = run_command("python -m pytest tests/test_ai_service.py -v", "AI Service Tests")
    test_results.append(("AI Service Tests", success))
    
    # 2. Run smoke tests
    print("\n💨 Running Smoke Tests...")
    success = run_command("python -m pytest tests/test_smoke_e2e.py::TestSmokeE2E -v", "Smoke Tests")
    test_results.append(("Smoke Tests", success))
    
    # 3. Run integration tests
    print("\n🔗 Running Integration Tests...")
    success = run_command("python -m pytest tests/test_smoke_e2e.py::TestIntegrationScenarios -v", "Integration Tests")
    test_results.append(("Integration Tests", success))
    
    # 4. Run all tests
    print("\n🎯 Running All Tests...")
    success = run_command("python -m pytest tests/ -v", "All Tests")
    test_results.append(("All Tests", success))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, success in test_results:
        status = "PASSED" if success else "FAILED"
        print(f"{test_name:<25} {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed + failed} test suites")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n{failed} test suite(s) failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 