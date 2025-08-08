#!/usr/bin/env python3
"""
Sample Social Services Data Generator
Creates sample service provider data for testing the professional dashboard
"""

import sys
import os
import random
from datetime import datetime, timedelta

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.models import ServiceProvider, SocialService, SocialServicesDatabase

def create_sample_services_data():
    """Create sample service provider data for testing"""
    
    # Initialize database
    db = SocialServicesDatabase("databases/social_services.db")
    
    # Sample service categories and providers
    sample_providers = [
        # Housing Services
        {
            'name': 'Los Angeles Housing Authority',
            'organization_type': 'Government',
            'city': 'Los Angeles',
            'county': 'Los Angeles',
            'phone_main': '(213) 252-2000',
            'email': 'info@hacla.org',
            'website': 'https://www.hacla.org',
            'background_check_policy': 'Case-by-case review for criminal background',
            'case_by_case_review': True,
            'accepts_medicaid': True,
            'services': [
                {
                    'service_category': 'Housing Services',
                    'service_type': 'Section 8 Housing Vouchers',
                    'service_level': 'Ongoing',
                    'description': 'Housing choice vouchers for low-income families',
                    'current_availability': 'Waitlist'
                },
                {
                    'service_category': 'Housing Services',
                    'service_type': 'Public Housing',
                    'service_level': 'Ongoing',
                    'description': 'Affordable rental housing for families',
                    'current_availability': 'Waitlist'
                }
            ]
        },
        {
            'name': 'Hope of the Valley Rescue Mission',
            'organization_type': 'Nonprofit',
            'city': 'North Hollywood',
            'county': 'Los Angeles',
            'phone_main': '(818) 392-0020',
            'email': 'info@hopeofthevalley.org',
            'website': 'https://www.hopeofthevalley.org',
            'background_check_policy': 'Background-friendly with case-by-case review',
            'case_by_case_review': True,
            'accepts_medicaid': True,
            'sliding_scale_available': True,
            'services': [
                {
                    'service_category': 'Housing Services',
                    'service_type': 'Emergency Shelter',
                    'service_level': 'Emergency',
                    'description': 'Emergency housing for homeless individuals',
                    'current_availability': 'Accepting'
                },
                {
                    'service_category': 'Housing Services',
                    'service_type': 'Transitional Housing',
                    'service_level': 'Ongoing',
                    'description': 'Temporary housing with support services',
                    'current_availability': 'Accepting'
                }
            ]
        },
        
        # Mental Health Services
        {
            'name': 'LAC+USC Medical Center Mental Health',
            'organization_type': 'Government',
            'city': 'Los Angeles',
            'county': 'Los Angeles',
            'phone_main': '(323) 409-1000',
            'email': 'mentalhealth@dhs.lacounty.gov',
            'background_check_policy': 'Background-friendly services available',
            'case_by_case_review': True,
            'accepts_medicaid': True,
            'telehealth_available': True,
            'services': [
                {
                    'service_category': 'Mental Health Services',
                    'service_type': 'Individual Therapy',
                    'service_level': 'Ongoing',
                    'description': 'Individual counseling and therapy services',
                    'current_availability': 'Accepting'
                },
                {
                    'service_category': 'Mental Health Services',
                    'service_type': 'Crisis Intervention',
                    'service_level': 'Emergency',
                    'description': '24/7 crisis mental health services',
                    'current_availability': 'Accepting'
                }
            ]
        },
        
        # Substance Abuse Services
        {
            'name': 'Tarzana Treatment Centers',
            'organization_type': 'Nonprofit',
            'city': 'Tarzana',
            'county': 'Los Angeles',
            'phone_main': '(818) 996-1051',
            'email': 'info@tarzanatc.org',
            'website': 'https://www.tarzanatc.org',
            'background_check_policy': 'Accepts individuals with criminal background',
            'case_by_case_review': True,
            'accepts_medicaid': True,
            'sliding_scale_available': True,
            'services': [
                {
                    'service_category': 'Substance Abuse',
                    'service_type': 'Outpatient Treatment',
                    'service_level': 'Ongoing',
                    'description': 'Outpatient substance abuse treatment programs',
                    'current_availability': 'Accepting'
                },
                {
                    'service_category': 'Substance Abuse',
                    'service_type': 'Medication-Assisted Treatment',
                    'service_level': 'Intensive',
                    'description': 'MAT for opioid addiction treatment',
                    'current_availability': 'Accepting'
                }
            ]
        },
        
        # Legal Services
        {
            'name': 'Public Counsel Law Center',
            'organization_type': 'Nonprofit',
            'city': 'Los Angeles',
            'county': 'Los Angeles',
            'phone_main': '(213) 385-2977',
            'email': 'info@publiccounsel.org',
            'website': 'https://www.publiccounsel.org',
            'background_check_policy': 'Specifically serves justice-involved individuals',
            'case_by_case_review': True,
            'sliding_scale_available': True,
            'free_services': True,
            'services': [
                {
                    'service_category': 'Legal Services',
                    'service_type': 'Expungement Assistance',
                    'service_level': 'Ongoing',
                    'description': 'Legal assistance for record expungement',
                    'current_availability': 'Accepting'
                },
                {
                    'service_category': 'Legal Services',
                    'service_type': 'Legal Aid',
                    'service_level': 'Ongoing',
                    'description': 'General legal assistance for low-income individuals',
                    'current_availability': 'Waitlist'
                }
            ]
        },
        
        # Medical Services
        {
            'name': 'Venice Family Clinic',
            'organization_type': 'Nonprofit',
            'city': 'Venice',
            'county': 'Los Angeles',
            'phone_main': '(310) 392-8636',
            'email': 'info@venicefamilyclinic.org',
            'website': 'https://www.venicefamilyclinic.org',
            'background_check_policy': 'Background-friendly healthcare services',
            'case_by_case_review': True,
            'accepts_medicaid': True,
            'sliding_scale_available': True,
            'services': [
                {
                    'service_category': 'Medical Services',
                    'service_type': 'Primary Care',
                    'service_level': 'Ongoing',
                    'description': 'Comprehensive primary healthcare services',
                    'current_availability': 'Accepting'
                },
                {
                    'service_category': 'Medical Services',
                    'service_type': 'Dental Services',
                    'service_level': 'Ongoing',
                    'description': 'Dental care and oral health services',
                    'current_availability': 'Waitlist'
                }
            ]
        },
        
        # Employment Support
        {
            'name': 'Goodwill of Southern California',
            'organization_type': 'Nonprofit',
            'city': 'Los Angeles',
            'county': 'Los Angeles',
            'phone_main': '(323) 223-1211',
            'email': 'info@goodwillsocal.org',
            'website': 'https://www.goodwillsocal.org',
            'background_check_policy': 'Specifically serves individuals with criminal background',
            'case_by_case_review': True,
            'accepts_medicaid': False,
            'sliding_scale_available': True,
            'services': [
                {
                    'service_category': 'Employment Support',
                    'service_type': 'Job Training',
                    'service_level': 'Ongoing',
                    'description': 'Job training and skill development programs',
                    'current_availability': 'Accepting'
                },
                {
                    'service_category': 'Employment Support',
                    'service_type': 'Placement Services',
                    'service_level': 'Ongoing',
                    'description': 'Job placement and career support services',
                    'current_availability': 'Accepting'
                }
            ]
        },
        
        # Benefits Coordination
        {
            'name': 'Department of Public Social Services',
            'organization_type': 'Government',
            'city': 'Los Angeles',
            'county': 'Los Angeles',
            'phone_main': '(866) 613-3777',
            'email': 'info@dpss.lacounty.gov',
            'background_check_policy': 'Case-by-case review for benefits eligibility',
            'case_by_case_review': True,
            'accepts_medicaid': True,
            'services': [
                {
                    'service_category': 'Benefits Coordination',
                    'service_type': 'SNAP/CalFresh',
                    'service_level': 'Ongoing',
                    'description': 'Food assistance benefits application and support',
                    'current_availability': 'Accepting'
                },
                {
                    'service_category': 'Benefits Coordination',
                    'service_type': 'Medicaid Enrollment',
                    'service_level': 'Ongoing',
                    'description': 'Healthcare coverage enrollment assistance',
                    'current_availability': 'Accepting'
                }
            ]
        },
        
        # Transportation Services
        {
            'name': 'Access Services',
            'organization_type': 'Nonprofit',
            'city': 'El Monte',
            'county': 'Los Angeles',
            'phone_main': '(800) 827-0829',
            'email': 'info@accessla.org',
            'website': 'https://www.accessla.org',
            'background_check_policy': 'Background check not required for transportation',
            'case_by_case_review': False,
            'accepts_medicaid': True,
            'services': [
                {
                    'service_category': 'Transportation',
                    'service_type': 'Medical Transport',
                    'service_level': 'Ongoing',
                    'description': 'Transportation to medical appointments',
                    'current_availability': 'Accepting'
                },
                {
                    'service_category': 'Transportation',
                    'service_type': 'Bus Passes',
                    'service_level': 'Ongoing',
                    'description': 'Reduced-fare transit passes',
                    'current_availability': 'Accepting'
                }
            ]
        }
    ]
    
    # Create providers and services
    for provider_data in sample_providers:
        # Extract services data
        services_data = provider_data.pop('services', [])
        
        # Add default values
        provider_data.setdefault('state', 'CA')
        provider_data.setdefault('zip_code', '90210')
        provider_data.setdefault('address', '123 Main St')
        provider_data.setdefault('primary_contact', 'Main Office')
        provider_data.setdefault('hours_operation', 'Monday-Friday 8:00 AM - 5:00 PM')
        provider_data.setdefault('appointment_types', 'Scheduled, Walk-in')
        provider_data.setdefault('languages_offered', 'English, Spanish')
        provider_data.setdefault('total_capacity', random.randint(50, 500))
        provider_data.setdefault('current_capacity', random.randint(10, 50))
        provider_data.setdefault('success_rate', random.uniform(0.6, 0.95))
        provider_data.setdefault('completion_rate', random.uniform(0.5, 0.9))
        provider_data.setdefault('client_satisfaction', random.uniform(3.5, 5.0))
        provider_data.setdefault('referral_volume_monthly', random.randint(20, 200))
        
        # Create service provider
        provider = ServiceProvider(**provider_data)
        
        try:
            provider_id = db.save_service_provider(provider)
            print(f"Created provider: {provider.name}")
            
            # Create associated services
            for service_data in services_data:
                service_data['provider_id'] = provider.provider_id
                service_data.setdefault('description', 'Professional service description')
                service_data.setdefault('eligibility_criteria', 'Contact provider for eligibility details')
                service_data.setdefault('referral_process', 'Call or email to initiate referral')
                service_data.setdefault('success_rate', random.uniform(0.6, 0.9))
                service_data.setdefault('completion_rate', random.uniform(0.5, 0.85))
                
                service = SocialService(**service_data)
                service_id = db.save_social_service(service)
                print(f"  Created service: {service.service_category} - {service.service_type}")
                
        except Exception as e:
            print(f"Error creating provider {provider.name}: {e}")
    
    # Get final statistics
    stats = db.get_provider_statistics()
    print(f"\nFinal Database Statistics:")
    print(f"  - Total Providers: {stats['total_providers']}")
    print(f"  - Total Services: {stats['total_services']}")
    print(f"  - Background-Friendly: {stats['background_friendly_providers']} ({stats['background_friendly_percentage']:.1f}%)")
    print(f"  - Service Categories: {len(stats['by_service_category'])}")
    print(f"  - Counties: {len(stats['by_county'])}")
    
    db.close()
    return stats

if __name__ == "__main__":
    print("Creating sample social services data...")
    stats = create_sample_services_data()
    print("Sample data creation completed!")