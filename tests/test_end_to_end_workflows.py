#!/usr/bin/env python3
"""
End-to-End Workflow Testing Suite
Tests complete business workflows across all modules and databases
"""

import pytest
import requests
import time
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EndToEndWorkflowTester:
    """Test complete end-to-end workflows"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Test data
        self.test_client_data = {
            'first_name': 'Maria',
            'last_name': 'Santos',
            'date_of_birth': '1985-03-15',
            'phone': '(555) 987-6543',
            'email': 'maria.santos.test@example.com',
            'address': '123 Main St, Los Angeles, CA 90210',
            'emergency_contact_name': 'Carlos Santos',
            'emergency_contact_phone': '(555) 987-6544',
            'risk_level': 'high',
            'case_status': 'active',
            'case_manager_id': 'cm_test_001',
            'goals': json.dumps(['housing', 'employment', 'legal', 'benefits']),
            'barriers': json.dumps(['criminal_record', 'housing_instability', 'unemployment'])
        }
        
        self.created_resources = {
            'clients': [],
            'legal_cases': [],
            'reminders': [],
            'applications': []
        }
    
    def cleanup_test_data(self):
        """Clean up test data created during tests"""
        # Clean up clients (this should cascade to related records)
        for client_id in self.created_resources['clients']:
            try:
                response = self.session.delete(f"{self.base_url}/api/case-management/clients/{client_id}")
                if response.status_code == 200:
                    logger.info(f"Cleaned up client: {client_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup client {client_id}: {e}")
        
        # Clean up other resources if needed
        logger.info("Test data cleanup completed")
    
    def wait_for_api_ready(self, timeout: int = 30) -> bool:
        """Wait for API to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}/api/health")
                if response.status_code == 200:
                    logger.info("API is ready")
                    return True
            except requests.exceptions.ConnectionError:
                time.sleep(1)
                continue
        
        logger.error("API not ready within timeout")
        return False
    
    def assert_api_response(self, response: requests.Response, expected_status: int = 200):
        """Assert API response is successful"""
        try:
            response_data = response.json() if response.content else {}
        except json.JSONDecodeError:
            response_data = {'raw_content': response.text}
        
        assert response.status_code == expected_status, \
            f"API call failed: {response.status_code} - {response_data}"
        
        return response_data

@pytest.fixture(scope="session")
def workflow_tester():
    """Session-scoped fixture for workflow testing"""
    tester = EndToEndWorkflowTester()
    
    # Wait for API to be ready
    if not tester.wait_for_api_ready():
        pytest.skip("API not available for testing")
    
    yield tester
    
    # Cleanup after all tests
    tester.cleanup_test_data()

class TestCompleteClientIntakeWorkflow:
    """Test complete client intake and case management workflow"""
    
    def test_client_intake_to_case_creation(self, workflow_tester):
        """Test complete client intake workflow"""
        # Step 1: Create new client
        logger.info("🔄 Step 1: Creating new client")
        
        response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/case-management/clients",
            json=workflow_tester.test_client_data
        )
        
        client_data = workflow_tester.assert_api_response(response, 201)
        client_id = client_data.get('client_id') or client_data.get('data', {}).get('client_id')
        
        assert client_id, f"Client ID not returned: {client_data}"
        workflow_tester.created_resources['clients'].append(client_id)
        
        logger.info(f"✅ Client created successfully: {client_id}")
        
        # Step 2: Verify client was created
        logger.info("🔄 Step 2: Verifying client creation")
        
        response = workflow_tester.session.get(
            f"{workflow_tester.base_url}/api/case-management/clients/{client_id}"
        )
        
        client_details = workflow_tester.assert_api_response(response)
        client_info = client_details.get('data', client_details)
        
        assert client_info.get('first_name') == workflow_tester.test_client_data['first_name']
        assert client_info.get('last_name') == workflow_tester.test_client_data['last_name']
        assert client_info.get('risk_level') == workflow_tester.test_client_data['risk_level']
        
        logger.info("✅ Client verification successful")
        
        # Step 3: Add case notes
        logger.info("🔄 Step 3: Adding case notes")
        
        case_note_data = {
            'note_type': 'intake',
            'content': 'Initial intake completed. Client needs housing, employment, and legal assistance.',
            'created_by': 'cm_test_001'
        }
        
        response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/case-management/clients/{client_id}/notes",
            json=case_note_data
        )
        
        note_response = workflow_tester.assert_api_response(response, 201)
        logger.info("✅ Case note added successfully")
        
        # Step 4: Update client status
        logger.info("🔄 Step 4: Updating client status")
        
        update_data = {
            'case_status': 'active',
            'updated_at': datetime.now().isoformat()
        }
        
        response = workflow_tester.session.put(
            f"{workflow_tester.base_url}/api/case-management/clients/{client_id}",
            json=update_data
        )
        
        workflow_tester.assert_api_response(response)
        logger.info("✅ Client status updated successfully")
        
        return client_id
    
    def test_unified_client_dashboard_workflow(self, workflow_tester):
        """Test unified client dashboard data aggregation"""
        # First create a client
        client_id = self.test_client_intake_to_case_creation(workflow_tester)
        
        # Step 5: Test unified client dashboard
        logger.info("🔄 Step 5: Testing unified client dashboard")
        
        response = workflow_tester.session.get(
            f"{workflow_tester.base_url}/api/clients/{client_id}/unified-view"
        )
        
        dashboard_data = workflow_tester.assert_api_response(response)
        unified_data = dashboard_data.get('data', dashboard_data)
        
        # Verify unified data structure
        assert 'client_info' in unified_data, "Client info missing from unified view"
        assert 'housing_status' in unified_data, "Housing status missing from unified view"
        assert 'employment_status' in unified_data, "Employment status missing from unified view"
        assert 'benefits_status' in unified_data, "Benefits status missing from unified view"
        assert 'legal_status' in unified_data, "Legal status missing from unified view"
        
        # Verify client info
        client_info = unified_data['client_info']
        assert client_info.get('client_id') == client_id
        assert client_info.get('first_name') == workflow_tester.test_client_data['first_name']
        
        logger.info("✅ Unified client dashboard working correctly")

class TestLegalServicesWorkflow:
    """Test complete legal services workflow"""
    
    def test_expungement_eligibility_to_case_creation(self, workflow_tester):
        """Test complete expungement workflow"""
        # First create a client
        client_response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/case-management/clients",
            json=workflow_tester.test_client_data
        )
        client_data = workflow_tester.assert_api_response(client_response, 201)
        client_id = client_data.get('client_id') or client_data.get('data', {}).get('client_id')
        workflow_tester.created_resources['clients'].append(client_id)
        
        # Step 1: Check expungement eligibility
        logger.info("🔄 Step 1: Checking expungement eligibility")
        
        eligibility_data = {
            'client_id': client_id,
            'conviction_types': ['misdemeanor'],
            'conviction_date': '2018-06-15',
            'completion_date': '2020-01-15',
            'has_new_charges': False,
            'probation_completed': True,
            'fines_paid': True
        }
        
        response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/legal/expungement-eligibility",
            json=eligibility_data
        )
        
        eligibility_result = workflow_tester.assert_api_response(response)
        eligibility_info = eligibility_result.get('data', eligibility_result)
        
        assert 'eligibility_score' in eligibility_info, "Eligibility score missing"
        assert 'eligible' in eligibility_info, "Eligibility status missing"
        
        eligibility_score = eligibility_info.get('eligibility_score', 0)
        is_eligible = eligibility_info.get('eligible', False)
        
        logger.info(f"✅ Eligibility check completed: Score={eligibility_score}, Eligible={is_eligible}")
        
        # Step 2: Create legal case if eligible
        if is_eligible:
            logger.info("🔄 Step 2: Creating legal case")
            
            case_data = {
                'client_id': client_id,
                'case_type': 'expungement',
                'case_status': 'open',
                'court_name': 'Los Angeles Superior Court',
                'case_number': f'TEST-{datetime.now().strftime("%Y%m%d")}-001',
                'attorney_name': 'Legal Aid Society',
                'description': 'Expungement petition for misdemeanor conviction'
            }
            
            response = workflow_tester.session.post(
                f"{workflow_tester.base_url}/api/legal/cases",
                json=case_data
            )
            
            case_result = workflow_tester.assert_api_response(response, 201)
            case_info = case_result.get('data', case_result)
            case_id = case_info.get('case_id')
            
            assert case_id, f"Case ID not returned: {case_result}"
            workflow_tester.created_resources['legal_cases'].append(case_id)
            
            logger.info(f"✅ Legal case created successfully: {case_id}")
            
            # Step 3: Add court date
            logger.info("🔄 Step 3: Scheduling court date")
            
            court_date_data = {
                'case_id': case_id,
                'client_id': client_id,
                'court_date': (datetime.now() + timedelta(days=30)).isoformat(),
                'court_type': 'hearing',
                'status': 'scheduled'
            }
            
            response = workflow_tester.session.post(
                f"{workflow_tester.base_url}/api/legal/court-dates",
                json=court_date_data
            )
            
            workflow_tester.assert_api_response(response, 201)
            logger.info("✅ Court date scheduled successfully")
            
            return case_id
        else:
            logger.info("ℹ️ Client not eligible for expungement, skipping case creation")
            return None

class TestBenefitsCoordinationWorkflow:
    """Test complete benefits coordination workflow"""
    
    def test_disability_assessment_to_application(self, workflow_tester):
        """Test complete disability benefits workflow"""
        # First create a client
        client_response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/case-management/clients",
            json=workflow_tester.test_client_data
        )
        client_data = workflow_tester.assert_api_response(client_response, 201)
        client_id = client_data.get('client_id') or client_data.get('data', {}).get('client_id')
        workflow_tester.created_resources['clients'].append(client_id)
        
        # Step 1: Conduct disability assessment
        logger.info("🔄 Step 1: Conducting disability assessment")
        
        assessment_data = {
            'client_id': client_id,
            'medical_conditions': [
                'chronic_pain',
                'depression',
                'anxiety'
            ],
            'functional_limitations': [
                'difficulty_standing',
                'difficulty_concentrating',
                'difficulty_sleeping'
            ],
            'work_history': {
                'last_worked': '2019-12-15',
                'unable_to_work_since': '2020-01-01',
                'previous_occupation': 'restaurant_server'
            }
        }
        
        response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/benefits/assess-disability",
            json=assessment_data
        )
        
        assessment_result = workflow_tester.assert_api_response(response)
        assessment_info = assessment_result.get('data', assessment_result)
        
        assert 'approval_probability' in assessment_info, "Approval probability missing"
        assert 'recommended_benefits' in assessment_info, "Recommended benefits missing"
        
        approval_probability = assessment_info.get('approval_probability', 0)
        recommended_benefits = assessment_info.get('recommended_benefits', [])
        
        logger.info(f"✅ Disability assessment completed: Probability={approval_probability}%, Benefits={recommended_benefits}")
        
        # Step 2: Check eligibility for multiple programs
        logger.info("🔄 Step 2: Checking benefit eligibility")
        
        eligibility_data = {
            'client_id': client_id,
            'household_size': 1,
            'monthly_income': 0,
            'has_disability': True,
            'state': 'CA'
        }
        
        response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/benefits/eligibility-check",
            json=eligibility_data
        )
        
        eligibility_result = workflow_tester.assert_api_response(response)
        eligibility_info = eligibility_result.get('data', eligibility_result)
        
        assert 'eligible_programs' in eligibility_info, "Eligible programs missing"
        
        eligible_programs = eligibility_info.get('eligible_programs', [])
        logger.info(f"✅ Eligibility check completed: Eligible for {len(eligible_programs)} programs")
        
        # Step 3: Start benefit applications
        if eligible_programs:
            logger.info("🔄 Step 3: Starting benefit applications")
            
            for program in eligible_programs[:2]:  # Apply for first 2 programs
                application_data = {
                    'client_id': client_id,
                    'benefit_type': program.get('program_name', program),
                    'application_data': {
                        'household_size': 1,
                        'monthly_income': 0,
                        'has_disability': True,
                        'medical_conditions': assessment_data['medical_conditions']
                    }
                }
                
                response = workflow_tester.session.post(
                    f"{workflow_tester.base_url}/api/benefits/start-application",
                    json=application_data
                )
                
                app_result = workflow_tester.assert_api_response(response, 201)
                app_info = app_result.get('data', app_result)
                app_id = app_info.get('application_id')
                
                if app_id:
                    workflow_tester.created_resources['applications'].append(app_id)
                
                logger.info(f"✅ Application started for {program}")
        
        return client_id

class TestHousingSearchWorkflow:
    """Test complete housing search and application workflow"""
    
    def test_housing_search_to_application(self, workflow_tester):
        """Test complete housing search workflow"""
        # First create a client
        client_response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/case-management/clients",
            json=workflow_tester.test_client_data
        )
        client_data = workflow_tester.assert_api_response(client_response, 201)
        client_id = client_data.get('client_id') or client_data.get('data', {}).get('client_id')
        workflow_tester.created_resources['clients'].append(client_id)
        
        # Step 1: Search for housing
        logger.info("🔄 Step 1: Searching for housing")
        
        search_params = {
            'location': 'Los Angeles, CA',
            'max_price': 1500,
            'bedrooms': 1,
            'background_friendly': True
        }
        
        response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/housing/search",
            json=search_params
        )
        
        search_result = workflow_tester.assert_api_response(response)
        search_data = search_result.get('data', search_result)
        
        properties = search_data.get('properties', [])
        logger.info(f"✅ Housing search completed: Found {len(properties)} properties")
        
        # Step 2: Get background-friendly properties
        logger.info("🔄 Step 2: Getting background-friendly properties")
        
        response = workflow_tester.session.get(
            f"{workflow_tester.base_url}/api/housing/background-friendly"
        )
        
        bg_friendly_result = workflow_tester.assert_api_response(response)
        bg_friendly_data = bg_friendly_result.get('data', bg_friendly_result)
        
        bg_properties = bg_friendly_data.get('properties', [])
        logger.info(f"✅ Background-friendly search completed: Found {len(bg_properties)} properties")
        
        # Step 3: Submit housing application (if properties found)
        if properties or bg_properties:
            logger.info("🔄 Step 3: Submitting housing application")
            
            # Use first available property
            target_property = (properties + bg_properties)[0] if (properties + bg_properties) else None
            
            if target_property:
                application_data = {
                    'client_id': client_id,
                    'property_id': target_property.get('property_id', 'test_property_001'),
                    'property_name': target_property.get('property_name', 'Test Property'),
                    'property_address': target_property.get('address', '123 Test St, LA, CA'),
                    'application_data': {
                        'move_in_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                        'household_size': 1,
                        'monthly_income': 0,
                        'employment_status': 'unemployed',
                        'references': []
                    }
                }
                
                response = workflow_tester.session.post(
                    f"{workflow_tester.base_url}/api/housing/application",
                    json=application_data
                )
                
                app_result = workflow_tester.assert_api_response(response, 201)
                logger.info("✅ Housing application submitted successfully")
        
        return client_id

class TestIntelligentReminderWorkflow:
    """Test intelligent reminder and task management workflow"""
    
    def test_smart_task_prioritization_workflow(self, workflow_tester):
        """Test smart task prioritization and reminder workflow"""
        # First create a client
        client_response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/case-management/clients",
            json=workflow_tester.test_client_data
        )
        client_data = workflow_tester.assert_api_response(client_response, 201)
        client_id = client_data.get('client_id') or client_data.get('data', {}).get('client_id')
        workflow_tester.created_resources['clients'].append(client_id)
        
        # Step 1: Get smart dashboard for case manager
        logger.info("🔄 Step 1: Getting smart dashboard")
        
        case_manager_id = 'cm_test_001'
        response = workflow_tester.session.get(
            f"{workflow_tester.base_url}/api/reminders/smart-dashboard/{case_manager_id}"
        )
        
        dashboard_result = workflow_tester.assert_api_response(response)
        dashboard_data = dashboard_result.get('data', dashboard_result)
        
        assert 'priority_tasks' in dashboard_data, "Priority tasks missing from dashboard"
        assert 'client_urgency' in dashboard_data, "Client urgency missing from dashboard"
        
        priority_tasks = dashboard_data.get('priority_tasks', [])
        client_urgency = dashboard_data.get('client_urgency', [])
        
        logger.info(f"✅ Smart dashboard loaded: {len(priority_tasks)} priority tasks, {len(client_urgency)} urgent clients")
        
        # Step 2: Start automated process for client
        logger.info("🔄 Step 2: Starting automated process")
        
        process_data = {
            'client_id': client_id,
            'process_type': 'comprehensive_intake',
            'case_manager_id': case_manager_id
        }
        
        response = workflow_tester.session.post(
            f"{workflow_tester.base_url}/api/reminders/start-process",
            json=process_data
        )
        
        process_result = workflow_tester.assert_api_response(response, 201)
        process_info = process_result.get('data', process_result)
        
        assert 'process_id' in process_info, "Process ID missing"
        assert 'created_tasks' in process_info, "Created tasks missing"
        
        created_tasks = process_info.get('created_tasks', [])
        logger.info(f"✅ Automated process started: Created {len(created_tasks)} tasks")
        
        # Step 3: Check client urgency score
        logger.info("🔄 Step 3: Checking client urgency")
        
        response = workflow_tester.session.get(
            f"{workflow_tester.base_url}/api/reminders/client-urgency/{client_id}"
        )
        
        urgency_result = workflow_tester.assert_api_response(response)
        urgency_data = urgency_result.get('data', urgency_result)
        
        assert 'urgency_score' in urgency_data, "Urgency score missing"
        assert 'priority_factors' in urgency_data, "Priority factors missing"
        
        urgency_score = urgency_data.get('urgency_score', 0)
        priority_factors = urgency_data.get('priority_factors', [])
        
        logger.info(f"✅ Client urgency calculated: Score={urgency_score}, Factors={len(priority_factors)}")
        
        return client_id

class TestCrossModuleIntegrationWorkflow:
    """Test workflows that span multiple modules"""
    
    def test_complete_case_manager_day_workflow(self, workflow_tester):
        """Test complete case manager daily workflow across all modules"""
        logger.info("🚀 Starting complete case manager day workflow")
        
        # Step 1: Client Intake
        logger.info("🔄 Phase 1: Client Intake")
        client_id = TestCompleteClientIntakeWorkflow().test_client_intake_to_case_creation(workflow_tester)
        
        # Step 2: Legal Services
        logger.info("🔄 Phase 2: Legal Services")
        legal_case_id = TestLegalServicesWorkflow().test_expungement_eligibility_to_case_creation(workflow_tester)
        
        # Step 3: Benefits Coordination
        logger.info("🔄 Phase 3: Benefits Coordination")
        TestBenefitsCoordinationWorkflow().test_disability_assessment_to_application(workflow_tester)
        
        # Step 4: Housing Search
        logger.info("🔄 Phase 4: Housing Search")
        TestHousingSearchWorkflow().test_housing_search_to_application(workflow_tester)
        
        # Step 5: Task Management
        logger.info("🔄 Phase 5: Task Management")
        TestIntelligentReminderWorkflow().test_smart_task_prioritization_workflow(workflow_tester)
        
        # Step 6: Unified Dashboard Verification
        logger.info("🔄 Phase 6: Unified Dashboard Verification")
        response = workflow_tester.session.get(
            f"{workflow_tester.base_url}/api/clients/{client_id}/unified-view"
        )
        
        dashboard_data = workflow_tester.assert_api_response(response)
        unified_data = dashboard_data.get('data', dashboard_data)
        
        # Verify all modules have data
        assert unified_data.get('client_info'), "Client info missing"
        assert unified_data.get('legal_status'), "Legal status missing"
        assert unified_data.get('benefits_status'), "Benefits status missing"
        assert unified_data.get('housing_status'), "Housing status missing"
        
        logger.info("🎉 Complete case manager day workflow successful!")
        
        return {
            'client_id': client_id,
            'legal_case_id': legal_case_id,
            'workflow_completed': True
        }

if __name__ == "__main__":
    # Run end-to-end workflow tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])