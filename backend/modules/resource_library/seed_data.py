"""
Seed data for the Resource Library - first batch of 21 verified resources.
All records set to verification_status = needs_review per product rule.
Run: python -m backend.modules.resource_library.seed_data
"""
import logging
from .database import initialize_db, insert_resource, resource_exists, get_resource_count

logger = logging.getLogger(__name__)

SEED_RESOURCES = [
    # 1 -----------------------------------------------------------------------
    {
        "provider_name": "Los Angeles Homeless Services Authority (LAHSA)",
        "service_name": "Coordinated Entry - Adults",
        "display_name": "Los Angeles Homeless Services Authority (LAHSA) - Coordinated Entry - Adults",
        "primary_category": "housing_navigation",
        "secondary_categories": ["case_management_resource"],
        "pathways": ["housing", "services", "case_management"],
        "tags": ["coordinated_entry", "housing_navigation", "adult", "homeless", "near_homeless", "la_county", "24_7"],
        "description": (
            "LAHSA provides housing support to adults who are homeless or unstably housed in "
            "Los Angeles County. Provides referrals to adult shelters and access to housing "
            "resources. Coordinates housing and services for homeless families and individuals "
            "countywide. Intake coordination connects clients with appropriate access points "
            "and housing resources based on need."
        ),
        "services_offered": ["Help Find Housing", "Navigating the System", "Help Hotlines"],
        "people_served": ["Adults 18+", "Individuals", "Homeless", "Near Homeless", "In Crisis", "Emergency"],
        "eligibility": [
            "Must be older than 17 years old.",
            "Must be homeless or unstably housed in Los Angeles County."
        ],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English", "Spanish"],
        "phone": "213-225-6581",
        "email": None,
        "website": "https://www.lahsa.org",
        "locations": [
            {"location_name": "ILCSC - Van Nuys Training House", "address": "14151 Haynes Street",
             "city": "Los Angeles", "state": "CA", "zip": "91401", "phone": "818-908-1199", "notes": "SPA-1"},
            {"location_name": "ILCSC - Van Nuys Service Office", "address": "14354 Haynes Street",
             "city": "Los Angeles", "state": "CA", "zip": "91401", "phone": "818-908-9525", "notes": "SPA-1"},
            {"location_name": "Hope of the Valley", "address": "11839 Sherman Way",
             "city": "Los Angeles", "state": "CA", "zip": "91605", "phone": "818-301-7988", "notes": "SPA-2"},
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "This is the adult Coordinated Entry access service. Store provider_name separately "
            "from service_name. Mark as needs_review until verified by staff before client referral."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://www.lahsa.org",
        "active": True,
    },
    # 2 -----------------------------------------------------------------------
    {
        "provider_name": "A New Way Of Life Reentry Project",
        "service_name": "Re-Entry Housing Services",
        "display_name": "A New Way Of Life Reentry Project - Re-Entry Housing Services",
        "primary_category": "reentry_housing",
        "secondary_categories": ["transitional_housing", "housing_navigation"],
        "pathways": ["housing", "services", "legal"],
        "tags": ["reentry", "women", "criminal_justice_history", "transitional_housing",
                 "public_assistance", "probation_parole_support", "family_reunification",
                 "employment_support", "housing_search", "sliding_scale"],
        "description": (
            "Provides supportive transitional housing to formerly incarcerated women. "
            "Helps women reunite with their children, work toward self-sufficiency, and "
            "receive support with life stabilization, public assistance, legal/court obligations, "
            "sobriety, employment, housing searches, and leadership skills."
        ),
        "services_offered": [
            "Short-Term Housing", "Help Find Housing", "Substance Abuse Counseling",
            "Financial Assistance", "Understand Government Programs", "Navigating the System",
            "Help Fill Out Forms", "Help Find Work"
        ],
        "people_served": ["All Ages", "Female", "Criminal Justice History"],
        "eligibility": ["Serves formerly incarcerated women."],
        "documents_required": [],
        "cost": "Sliding Scale",
        "languages": ["English", "Spanish"],
        "phone": "323-563-3575",
        "email": None,
        "website": "http://anewwayoflife.org/housing/",
        "locations": [
            {"location_name": "A New Way Of Life Mailing Address", "location_type": "Admin-Only",
             "city": "", "state": "CA", "zip": "", "phone": "323-563-3575"}
        ],
        "coverage_area": [
            "Los Angeles County, CA", "Orange County, CA",
            "Riverside County, CA", "San Bernardino County, CA", "Ventura County, CA"
        ],
        "cmsx_notes": (
            "Strong referral resource for formerly incarcerated women needing transitional housing "
            "and reentry support. Rent is 30% of income. Should appear under Reentry Housing, "
            "Transitional Housing, Criminal Justice History, Women, and Housing Navigation. "
            "Mark needs_review before direct referral because housing availability and intake "
            "requirements may change."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "http://anewwayoflife.org/housing/",
        "active": True,
    },
    # 3 -----------------------------------------------------------------------
    {
        "provider_name": "Libertana Home Health",
        "service_name": "California Community Transitions (CCT) Program",
        "display_name": "Libertana Home Health - California Community Transitions (CCT) Program",
        "primary_category": "disability_housing",
        "secondary_categories": ["healthcare_navigation", "benefits"],
        "pathways": ["housing", "medical", "benefits"],
        "tags": ["disability_housing", "community_transition", "medi_cal",
                 "nursing_facility_transition", "assisted_living_waiver",
                 "older_adults", "chronic_illness", "benefit_recipients",
                 "caregiver_support", "housing_navigation"],
        "description": (
            "CCT is a Medi-Cal program for nursing-home residents who have resided there at least "
            "90 days post-Medicare days. Libertana helps move residents to independent living or "
            "the Assisted Living Waiver program, including help finding housing (Section 8), "
            "security deposit and first month's rent, and one year of follow-up support."
        ),
        "services_offered": ["Help Find Housing"],
        "people_served": [
            "Adults 18+", "All Disabilities", "Chronic Illness",
            "Individuals", "Families", "Benefit Recipients", "Caregivers"
        ],
        "eligibility": [
            "Must be a Medi-Cal resident that has resided in a nursing home for at least 90 days post Medicare days.",
            "Helps older adults and adults with disabilities."
        ],
        "documents_required": [],
        "cost": "Accepts Childcare Subsidies",
        "languages": ["English"],
        "phone": "800-750-1444",
        "email": None,
        "website": "https://www.libertana.com/california-community-transitions",
        "locations": [
            {"location_name": "Libertana", "address": "5805 Sepulveda Boulevard, Suite 605",
             "city": "Los Angeles", "state": "CA", "zip": "91411", "phone": "800-750-1444"}
        ],
        "coverage_area": [
            "Fresno County, CA", "Los Angeles County, CA", "Orange County, CA",
            "Riverside County, CA", "San Bernardino County, CA", "San Diego County, CA"
        ],
        "cmsx_notes": (
            "Strong referral resource for Medi-Cal clients in nursing facilities who need "
            "transition planning into independent living, Section 8 housing, or Assisted Living "
            "Waiver placement. Mark needs_review before referral because CCT eligibility and "
            "county availability should be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://www.libertana.com/california-community-transitions",
        "active": True,
    },
    # 4 -----------------------------------------------------------------------
    {
        "provider_name": "Tarzana Treatment Centers, Inc. (TTC)",
        "service_name": "Community Counseling / Residential Treatment Services",
        "display_name": "Tarzana Treatment Centers, Inc. (TTC) - Community Counseling / Residential Treatment Services",
        "primary_category": "residential_treatment",
        "secondary_categories": ["sober_living", "sud_recovery", "mental_health"],
        "pathways": ["services", "housing", "medical"],
        "tags": ["sud_treatment", "residential_treatment", "sober_living", "detox",
                 "outpatient_treatment", "iop", "mat", "mental_health",
                 "community_counseling", "recovery_bridge_housing", "family_counseling",
                 "court_related", "domestic_violence_services", "hiv_aids_services", "sliding_scale"],
        "description": (
            "Comprehensive health care and treatment services for mental health and substance use. "
            "Services include medical detoxification, residential alcohol and drug treatment, "
            "outpatient treatment, sober living housing, family and individual counseling, "
            "HIV/AIDS services, family medical care, court programs, domestic violence services, "
            "and couples counseling."
        ),
        "services_offered": [
            "Sober Living", "Detox", "Residential Treatment", "Family Counseling",
            "Individual Counseling", "Outpatient Treatment", "HIV Treatment",
            "Mental Health Care", "After School Care"
        ],
        "people_served": ["Anyone In Need", "All Ages", "Individuals", "Families"],
        "eligibility": [
            "Anyone can access this program.",
            "Provide age and insurance (if applicable) along with the referral."
        ],
        "documents_required": [],
        "cost": "Sliding Scale",
        "languages": ["English"],
        "phone": "888-777-8565",
        "email": "treatment@tarzanatc.org",
        "website": "https://www.tarzanatc.org/services/community-counseling/",
        "locations": [
            {"location_name": "Tarzana Treatment Centers Reseda",
             "address": "7101 Baird Avenue", "city": "Los Angeles", "state": "CA",
             "zip": "91335", "phone": "818-342-5897"},
            {"location_name": "Tarzana Treatment Centers",
             "address": "18700 Oxnard Street", "city": "Los Angeles", "state": "CA",
             "zip": "91356", "phone": "818-654-3950"},
        ],
        "coverage_area": [
            "Los Angeles County, CA", "Orange County, CA",
            "Riverside County, CA", "San Bernardino County, CA", "Ventura County, CA"
        ],
        "cmsx_notes": (
            "Primarily a behavioral health and substance-use treatment provider with residential "
            "treatment, sober living, recovery bridge housing, outpatient treatment, counseling, "
            "MAT, youth services, and medical services. Useful for discharge planning, SUD "
            "referrals, sober living referrals, and mental health linkage. Mark needs_review "
            "before referral because level of care, insurance, availability, and admission "
            "criteria must be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://www.tarzanatc.org/services/community-counseling/",
        "active": True,
    },
    # 5 -----------------------------------------------------------------------
    {
        "provider_name": "El Nido Family Centers",
        "service_name": "Pacoima FamilySource Center",
        "display_name": "El Nido Family Centers - Pacoima FamilySource Center",
        "primary_category": "case_management_resource",
        "secondary_categories": ["benefits", "housing_navigation", "employment_support"],
        "pathways": ["services", "benefits", "housing"],
        "tags": ["family_source_center", "case_management", "housing_navigation",
                 "rental_assistance", "food_pantry", "calfresh", "diapers",
                 "benefits_support", "financial_assistance", "tax_prep",
                 "employment_services", "mental_health", "low_income",
                 "family_support", "english_spanish"],
        "description": (
            "Collaborative one-stop community center assisting low-income residents in the City "
            "of LA to become self-sufficient. Services include benefits support, housing assistance, "
            "food resources, financial coaching, tax preparation, tutoring, college preparation, "
            "career preparation, employment services, diapers, and CalFresh application assistance."
        ),
        "services_offered": [
            "Food Pantry", "Help Find Housing", "Help Pay For Housing", "Baby Supplies",
            "Clothing", "Help Pay For Transit", "Mental Health Care", "Financial Assistance",
            "Government Benefits", "Financial Education", "Tax Preparation",
            "Community Support Services", "More Education", "Case Management"
        ],
        "people_served": ["Anyone In Need", "All Ages"],
        "eligibility": ["Anyone can access this program."],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English", "Spanish"],
        "phone": "818-896-7776",
        "email": "info@elnidofamilycenters.org",
        "website": "https://www.elnidofamilycenters.org/",
        "locations": [
            {"location_name": "El Nido Family Centers Pacoima FamilySource Center",
             "address": "11243 Glenoaks Boulevard, Suite 417",
             "city": "Los Angeles", "state": "CA", "zip": "91331", "phone": "818-896-7776"}
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "Strong general case-management and family resource referral. Best used for "
            "low-income families, benefits linkage, food/diaper support, and broad stabilization "
            "needs. Mark needs_review before referral because specific service availability and "
            "intake requirements may change."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://www.elnidofamilycenters.org/",
        "active": True,
    },
    # 6 -----------------------------------------------------------------------
    {
        "provider_name": "LA Family Housing",
        "service_name": "Eligibility Screening",
        "display_name": "LA Family Housing - Eligibility Screening",
        "primary_category": "housing_navigation",
        "secondary_categories": ["case_management_resource", "rental_assistance"],
        "pathways": ["housing", "services"],
        "tags": ["housing_navigation", "eligibility_screening", "case_management",
                 "homeless_services", "temporary_shelter", "rental_assistance",
                 "rental_arrears", "spa_2", "san_fernando_valley",
                 "burbank", "glendale", "santa_clarita",
                 "families", "single_adults", "limited_english", "english_spanish"],
        "description": (
            "LA Family Housing is a nonprofit homeless services agency connecting families with "
            "minors and single adults experiencing homelessness or at risk of homelessness to "
            "temporary shelter, financial assistance for rent or rental arrears, housing-focused "
            "case management, housing advice, navigation services, and help paying for housing."
        ),
        "services_offered": [
            "Help Pay For Housing", "Temporary Shelter", "Help Find Housing",
            "Housing Advice", "Navigating The System", "Case Management"
        ],
        "people_served": [
            "Adults", "Children", "Seniors", "Homeless", "Near Homeless", "Limited English"
        ],
        "eligibility": [
            "Income at or below 50% of federal poverty guidelines.",
            "Must reside in SPA 2: San Fernando Valley, Burbank, Santa Clarita Valley, or Glendale."
        ],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English", "Spanish"],
        "phone": "818-255-2766",
        "email": None,
        "website": "https://lafh.org/",
        "locations": [
            {"location_name": "LA Family Housing", "location_type": "Admin-Only",
             "state": "CA", "phone": "818-255-2766", "website": "https://lafh.org/"}
        ],
        "coverage_area": ["SPA 2 - San Fernando Valley, Burbank, Santa Clarita Valley, Glendale"],
        "cmsx_notes": (
            "Strong referral resource for SPA-2 clients experiencing homelessness or at risk. "
            "Should appear under Housing Navigation, Eligibility Screening, Case Management, "
            "Temporary Shelter, Rental Assistance, and Homeless Services. Staff must verify "
            "eligibility, coverage ZIP, current application process, and availability before referral."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://lafh.org/",
        "active": True,
    },
    # 7 -----------------------------------------------------------------------
    {
        "provider_name": "NOHO Home Alliance",
        "service_name": "Homeless Services",
        "display_name": "NOHO Home Alliance - Homeless Services",
        "primary_category": "case_management_resource",
        "secondary_categories": ["housing_navigation", "food_support"],
        "pathways": ["services", "housing"],
        "tags": ["homeless_services", "drop_in_center", "access_center", "showers",
                 "meals", "clothing", "hygiene", "mail_services", "document_support",
                 "case_management", "medical_linkage", "housing_referrals",
                 "la_family_housing", "north_hollywood", "studio_city",
                 "free", "needs_hours_verification"],
        "description": (
            "Pop-up drop-in access centers for people experiencing homelessness in North "
            "Hollywood, Studio City, and nearby neighborhoods. Services include showers, "
            "clothing, toiletries, hot meals, electronics charging, medical care through "
            "Northeast Valley Medical Center, housing referrals through LA Family Housing, "
            "document support, mail services, and case management. Locations may change."
        ),
        "services_offered": [
            "Meals", "Help Find Housing", "Clothing", "Personal Care Items",
            "Personal Hygiene", "Help Find Healthcare", "Navigating The System",
            "Case Management", "Identification Recovery"
        ],
        "people_served": ["All Ages", "Individuals", "Families", "Homeless", "Near Homeless"],
        "eligibility": ["Contact provider to confirm current eligibility criteria."],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English"],
        "phone": "818-762-2909",
        "email": None,
        "website": "https://nohohome.org/access-service/",
        "locations": [
            {"location_name": "St. Matthew's Lutheran Church",
             "address": "11031 Camarillo Street", "city": "Los Angeles", "state": "CA",
             "zip": "91602", "phone": "818-762-2909",
             "notes": "Shower truck Wednesdays only. Mon/Wed 8:30 AM - 12:30 PM."},
            {"location_name": "MCC/UCC Church in the Valley",
             "address": "5730 Cahuenga Boulevard", "city": "Los Angeles", "state": "CA",
             "zip": "91601", "notes": "Fridays 8:00 AM - 12:00 PM."},
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "Useful immediate-stabilization referral for North Hollywood/Studio City area clients. "
            "Not a housing placement provider. Valuable for hygiene, meals, mail, document "
            "support, medical linkage, LA Family Housing referrals, and case management. "
            "Locations and hours routinely change; staff must verify current access site."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://nohohome.org/access-service/",
        "active": True,
    },
    # 8 -----------------------------------------------------------------------
    {
        "provider_name": "Walden Family Services",
        "service_name": "Transitional Housing Placement and Foster Care Program",
        "display_name": "Walden Family Services - Transitional Housing Placement and Foster Care Program",
        "primary_category": "transitional_housing",
        "secondary_categories": ["youth_housing"],
        "pathways": ["housing", "services"],
        "tags": ["transitional_housing", "foster_youth", "young_adults",
                 "ages_18_21", "independent_living", "homeless", "near_homeless",
                 "low_income", "rent_support", "utilities_support",
                 "therapy", "group_therapy", "employment_support",
                 "financial_education", "crisis_support",
                 "los_angeles_county", "riverside_county", "san_diego_county"],
        "description": (
            "Transitional Housing Plus Foster Care Program provides youth with a stable living "
            "environment to learn independent living skills. Helps youth choose housing, covers "
            "rent and utilities, provides home furnishings, and works with social workers to "
            "set realistic goals. Therapy, crisis intervention, and 24/7 emergency support."
        ),
        "services_offered": [
            "Residential Housing", "Short-Term Housing", "Meals", "Counseling",
            "Group Therapy", "Individual Counseling", "Financial Education",
            "Navigating The System", "Help Find Work"
        ],
        "people_served": ["Young Adults", "Teens", "Foster Youth", "Homeless", "Near Homeless", "Low-Income"],
        "eligibility": [
            "Ages 18 to 21.",
            "Must be finishing high school or equivalent, enrolled at least half-time in college/vocational, "
            "have a documented medical condition, or work at least 80 hours a month."
        ],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English"],
        "phone": "818-365-3665",
        "email": None,
        "website": "https://waldenfamily.org/programs/transitional-housing-placement-foster-care-program/",
        "locations": [
            {"location_name": "Walden Family Services - Los Angeles County",
             "address": "6345 Balboa Boulevard, Suite 130",
             "city": "Los Angeles", "state": "CA", "zip": "91316", "phone": "818-365-3665"},
            {"location_name": "Walden Family Services - Riverside County",
             "address": "3576 Arlington Avenue, Suite 105",
             "city": "Riverside", "state": "CA", "zip": "92506", "phone": "951-788-5905"},
        ],
        "coverage_area": ["Los Angeles County, CA", "Riverside County, CA", "San Diego County, CA"],
        "cmsx_notes": (
            "Strong referral resource for foster youth and young adults ages 18 to 21 needing "
            "transitional housing, independent living support, therapy, employment help, and "
            "crisis support. Mark needs_review before referral because county eligibility, "
            "opening availability, and THP+FC requirements should be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://waldenfamily.org/programs/transitional-housing-placement-foster-care-program/",
        "active": True,
    },
    # 9 -----------------------------------------------------------------------
    {
        "provider_name": "Hope the Mission",
        "service_name": "Shepherd's House",
        "display_name": "Hope the Mission - Shepherd's House",
        "primary_category": "family_shelter",
        "secondary_categories": ["transitional_housing"],
        "pathways": ["housing", "services"],
        "tags": ["family_shelter", "single_mothers", "mothers_with_children",
                 "homeless_families", "short_term_housing", "residential_housing",
                 "family_crisis_shelter", "los_angeles_county", "pacoima",
                 "free", "needs_availability_check"],
        "description": (
            "28-bed, 90-day family crisis shelter in Pacoima for single mothers and their "
            "children transitioning from homelessness. Can house 10 families nightly."
        ),
        "services_offered": ["Residential Housing", "Short-Term Housing"],
        "people_served": ["All Ages", "Families", "With Children", "Homeless", "Mothers"],
        "eligibility": ["Single mothers with children."],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English"],
        "phone": "818-392-0020",
        "email": "info@hopethemission.org",
        "website": "https://hopethemission.org/our-programs/shelters/family-shelters/",
        "locations": [
            {"location_name": "Hope the Mission", "location_type": "Admin-Only",
             "state": "CA", "phone": "818-392-0020"}
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "Not general adult shelter. Tagged specifically for families, single mothers, "
            "children, homelessness, short-term housing, and family crisis shelter. Mark "
            "needs_review: availability, admission requirements, and location must be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://hopethemission.org/our-programs/shelters/family-shelters/",
        "active": True,
    },
    # 10 ----------------------------------------------------------------------
    {
        "provider_name": "The Help Group",
        "service_name": "Project Six Adult Residential Program",
        "display_name": "The Help Group - Project Six Adult Residential Program",
        "primary_category": "disability_housing",
        "secondary_categories": ["mental_health", "healthcare_navigation"],
        "pathways": ["housing", "medical", "services"],
        "tags": ["disability_housing", "adult_residential_care",
                 "developmental_disability", "daily_living_skills",
                 "medication_management", "residential_care",
                 "independent_living_skills", "therapy", "psychiatric_evaluation",
                 "vocational_exploration", "regional_center_review",
                 "reduced_cost", "needs_eligibility_verification"],
        "description": (
            "Dedicated to improving the quality of life of adults with developmental disabilities. "
            "Provides residential housing, daily life skills support, medication management, "
            "therapy, psychiatric evaluation, community-based instruction, academic tutoring, "
            "vocational exploration, parent support, and on-site recreation."
        ),
        "services_offered": [
            "Residential Housing", "Daily Life Skills", "Medication Management", "Residential Care"
        ],
        "people_served": ["Adults", "Young Adults", "Teens", "Seniors", "Developmental Disability"],
        "eligibility": ["Contact provider to confirm eligibility criteria."],
        "documents_required": [],
        "cost": "Reduced Cost",
        "languages": ["English"],
        "phone": "818-267-2624",
        "email": None,
        "website": "https://www.thehelpgroup.org/program/project-six-2/",
        "locations": [
            {"location_name": "The Help Group",
             "address": "13130 Burbank Boulevard",
             "city": "Los Angeles", "state": "CA", "zip": "91401", "phone": "818-781-0360"}
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "For adults and transition-age clients with developmental disabilities needing "
            "structured residential care, daily living skills support, medication management, "
            "therapy, and independent living skill development. Not standard homeless housing or "
            "sober living. Mark needs_review: eligibility, payer requirements, Regional Center "
            "involvement, admission criteria, and availability must be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://www.thehelpgroup.org/program/project-six-2/",
        "active": True,
    },
    # 11 ----------------------------------------------------------------------
    {
        "provider_name": "Village Family Services",
        "service_name": "The Village Drop-In Center",
        "display_name": "Village Family Services - The Village Drop-In Center",
        "primary_category": "case_management_resource",
        "secondary_categories": ["youth_housing", "employment_support"],
        "pathways": ["services", "housing"],
        "tags": ["youth_services", "drop_in_center", "homeless_youth",
                 "ages_16_24", "foster_youth", "lgbtqia_youth",
                 "housing_navigation", "meals", "showers",
                 "behavioral_health", "mental_health",
                 "employment_support", "resume_development",
                 "job_placement", "education_support",
                 "case_management_resource", "free", "open_weekends"],
        "description": (
            "Safe, welcoming drop-in center for homeless youth ages 16-24. Staff create "
            "tailor-made plans supporting youth toward independence and wellness. Services "
            "include behavioral health, food, showers, housing navigation, education support, "
            "tutoring, employment coaching, resume workshops, and job placement."
        ),
        "services_offered": [
            "Meals", "Help Find Housing", "Clothes For Work", "Personal Hygiene",
            "Mental Health Care", "Community Support Services", "Navigating The System",
            "Resume Development", "Help Find Work", "Job Placement"
        ],
        "people_served": ["Young Adults", "Teens", "Foster Youth", "Homeless", "LGBTQIA+"],
        "eligibility": [
            "Ages 16 to 24.",
            "Designed for young people at risk of experiencing homelessness."
        ],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English"],
        "phone": None,
        "email": None,
        "website": "https://www.thevillagefs.org/dropin-center",
        "locations": [
            {"location_name": "Drop-in Center for Homeless Youth",
             "address": "6801 Coldwater Canyon Avenue",
             "city": "Los Angeles", "state": "CA", "zip": "91605",
             "hours": "Mon-Fri 9:30 AM - 3:30 PM, Sat-Sun 9:00 AM - 3:00 PM"}
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "Strong youth stabilization referral for clients ages 16-24 who are homeless or at "
            "risk, including foster youth and LGBTQIA+ youth. Not a housing placement program. "
            "Mark needs_review: walk-in procedures, phone contact, and current service "
            "availability should be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://www.thevillagefs.org/dropin-center",
        "active": True,
    },
    # 12 ----------------------------------------------------------------------
    {
        "provider_name": "Bonum Foundation",
        "service_name": "Care Coordination (Case Management)",
        "display_name": "Bonum Foundation - Care Coordination (Case Management)",
        "primary_category": "case_management_resource",
        "secondary_categories": ["healthcare_navigation", "benefits"],
        "pathways": ["services", "medical", "benefits"],
        "tags": ["case_management_resource", "care_coordination", "healthcare_navigation",
                 "benefits_navigation", "disability_support", "chronic_illness",
                 "limited_mobility", "dme", "hospital_discharge",
                 "food_insecurity", "public_benefits", "low_income",
                 "uninsured", "medi_cal", "medicare", "housing_navigation"],
        "description": (
            "Navigation, guidance, and coordination to help low-income individuals and families "
            "identify and access resources. Offers care coordination, one-on-one support, "
            "consultation and planning, help navigating complex healthcare systems, DME support, "
            "hospital discharge support, mobility assistance, food insecurity resources, "
            "and public benefits navigation."
        ),
        "services_offered": [
            "Case Management", "Navigating The System", "One-On-One Support",
            "Help Find Housing", "Help Find Healthcare", "Understand Government Programs"
        ],
        "people_served": [
            "Adults", "Seniors", "All Disabilities", "Limited Mobility",
            "Chronic Illness", "Individuals", "Families", "Low-Income", "Uninsured"
        ],
        "eligibility": [
            "Individuals with chronic disabilities.",
            "Targets low-income families without financial support, Medicare, or insurance coverage."
        ],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English"],
        "phone": "818-940-0330",
        "email": "intake@bonumfoundation.org",
        "website": "https://www.bonumfoundation.org/",
        "locations": [
            {"location_name": "Bonum Foundation", "state": "CA",
             "phone": "833-282-6686", "email": "intake@bonumfoundation.org",
             "hours": "Mon-Fri 9:00 AM - 5:30 PM"}
        ],
        "coverage_area": [
            "Los Angeles County, CA", "Orange County, CA",
            "Riverside County, CA", "San Bernardino County, CA", "Ventura County, CA"
        ],
        "cmsx_notes": (
            "Useful for clients with chronic illness, disability, limited mobility, hospital "
            "discharge needs, DME needs, public benefits needs, food insecurity, and care "
            "coordination needs. Not a direct housing provider. Mark needs_review because "
            "eligibility language is broad and may require confirmation."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://www.bonumfoundation.org/",
        "active": True,
    },
    # 13 ----------------------------------------------------------------------
    {
        "provider_name": "Neighborhood Legal Services of Los Angeles County (NLSLA)",
        "service_name": "Housing Program",
        "display_name": "Neighborhood Legal Services of Los Angeles County (NLSLA) - Housing Program",
        "primary_category": "legal_aid",
        "secondary_categories": ["tenant_rights", "eviction_prevention", "housing_navigation"],
        "pathways": ["legal", "housing", "services"],
        "tags": ["legal_aid", "tenant_rights", "housing_advice", "eviction_prevention",
                 "foreclosure_counseling", "mortgage_counseling", "public_housing",
                 "representation", "advocacy", "home_renters", "home_owners",
                 "los_angeles_county", "free", "needs_intake_verification"],
        "description": (
            "Housing Program provides services to promote safe and affordable housing for "
            "individuals and families. Assists homeowners and renters through legal advice, "
            "legal representation, eviction prevention, mortgage counseling, housing education, "
            "public housing navigation, foreclosure counseling, advocacy, and referrals to "
            "partner HUD-certified agencies."
        ),
        "services_offered": [
            "Housing Advice", "Foreclosure Counseling", "Public Housing",
            "Navigating The System", "Advocacy & Legal Aid", "Representation"
        ],
        "people_served": ["Adults 18+", "Individuals", "Families", "Home Owners", "Home Renters"],
        "eligibility": ["Contact provider to confirm eligibility criteria."],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English"],
        "phone": "800-433-6251",
        "email": None,
        "website": "https://www.nlsla.org/services/housing/",
        "locations": [
            {"location_name": "Pacoima", "address": "13327 Van Nuys Boulevard",
             "city": "Los Angeles", "state": "CA", "zip": "91331", "phone": "800-433-6251"},
            {"location_name": "Glendale", "address": "1102 East Chevy Chase Drive",
             "city": "Glendale", "state": "CA", "zip": "91205", "phone": "800-433-6251"},
            {"location_name": "El Monte", "address": "9354 Telstar Avenue",
             "city": "El Monte", "state": "CA", "zip": "91731", "phone": "800-433-6251"},
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "Strong legal referral for clients dealing with eviction risk, unsafe housing, "
            "landlord issues, foreclosure, mortgage problems, public housing issues, or "
            "housing-related legal difficulty. Not a housing placement resource. Mark "
            "needs_review: eligibility, intake availability, and office procedures should "
            "be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://www.nlsla.org/services/housing/",
        "active": True,
    },
    # 14 ----------------------------------------------------------------------
    {
        "provider_name": "Abused Women And Children Inc",
        "service_name": "Victim's Services",
        "display_name": "Abused Women And Children Inc - Victim's Services",
        "primary_category": "victim_services",
        "secondary_categories": ["transitional_housing", "legal_aid"],
        "pathways": ["services", "housing", "legal"],
        "tags": ["victim_services", "domestic_violence_support", "abuse_survivors",
                 "women", "children", "short_term_housing", "transitional_housing",
                 "housing_assistance", "counseling", "case_advocacy",
                 "legal_aid", "system_navigation",
                 "reduced_cost", "admin_only_location", "needs_phone_verification"],
        "description": (
            "Support to individuals, women, and children experiencing life crises. Services "
            "include counseling, training and education, transitional housing, referrals, "
            "public awareness, advocacy, networking, case advocacy, children's programs, "
            "and housing assistance."
        ),
        "services_offered": [
            "Short-Term Housing", "Counseling", "Navigating The System",
            "Skills & Training", "Advocacy & Legal Aid"
        ],
        "people_served": ["Children", "Individuals", "Abuse Or Neglect Survivors", "Female"],
        "eligibility": ["Contact provider by phone to confirm eligibility criteria."],
        "documents_required": [],
        "cost": "Reduced Cost",
        "languages": ["English"],
        "phone": "800-876-5690",
        "email": None,
        "website": "http://abusedwomenandchildren.org/",
        "locations": [
            {"location_name": "Mailing Address", "location_type": "Admin-Only",
             "state": "CA", "phone": "800-876-5690"}
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "Potentially useful for women, children, and abuse or neglect survivors needing "
            "short-term housing support, counseling, advocacy, legal aid connection, and "
            "crisis-related support. Program is unclaimed; eligibility criteria not listed; "
            "address is admin-only. Staff must verify by phone before referral."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "http://abusedwomenandchildren.org/",
        "active": True,
    },
    # 15 ----------------------------------------------------------------------
    {
        "provider_name": "Los Angeles County Department of Public Social Services (DPSS)",
        "service_name": "Temporary Homeless Assistance",
        "display_name": "Los Angeles County DPSS - Temporary Homeless Assistance",
        "primary_category": "rental_assistance",
        "secondary_categories": ["benefits", "housing_navigation"],
        "pathways": ["benefits", "housing", "services"],
        "tags": ["dpss", "calworks", "temporary_homeless_assistance",
                 "temporary_shelter_payments", "rental_assistance",
                 "emergency_housing_assistance", "homeless_families",
                 "domestic_violence_survivors", "housing_search",
                 "benefits_navigation", "documents_required",
                 "los_angeles_county", "free", "needs_eligibility_verification"],
        "description": (
            "Provides temporary shelter payments to homeless families while looking for permanent "
            "housing. Payments for up to 16 consecutive calendar days: $85/day for a family of "
            "up to 4, $15/day for each additional person (max $145/day). CalWORKs applicants "
            "fleeing domestic violence may receive a lump sum equal to 16 days and may be "
            "eligible for an additional 16 days."
        ),
        "services_offered": ["Help Pay For Housing"],
        "people_served": ["All Ages", "Families", "Homeless", "Domestic Violence Survivors"],
        "eligibility": [
            "Must be apparently eligible for CalWORKs or CalWORKs approved.",
            "Must meet the homeless definition.",
            "Must not have more than $100.00 in liquid resources.",
            "Must be actively searching for permanent housing."
        ],
        "documents_required": [
            "Verification for the housing search",
            "Verification of shelter expenditures"
        ],
        "cost": "Free",
        "languages": ["English"],
        "phone": None,
        "email": None,
        "website": "https://dpss.lacounty.gov/en/cash/calworks/homeless.html",
        "locations": [
            {"location_name": "East Valley - 11", "address": "7555 Van Nuys Boulevard",
             "city": "Los Angeles", "state": "CA", "zip": "91405"},
            {"location_name": "Rancho Park - 60", "address": "11110 West Pico Boulevard",
             "city": "Los Angeles", "state": "CA", "zip": "90064"},
            {"location_name": "Glendale - 02", "address": "4680 San Fernando Road",
             "city": "Glendale", "state": "CA", "zip": "91204", "phone": "818-701-8200"},
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "Important DPSS benefits resource for homeless families, CalWORKs applicants/"
            "participants, and domestic violence survivors needing temporary shelter payments. "
            "Not a housing provider. Categorize under Rental Assistance, Emergency Shelter "
            "Payments, CalWORKs, DPSS, Homeless Families, and Domestic Violence Survivors. "
            "Staff must verify CalWORKs eligibility, homeless status, liquid resource limit, "
            "housing search documentation, and nearest DPSS office before referral."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://dpss.lacounty.gov/en/cash/calworks/homeless.html",
        "active": True,
    },
    # 16 ----------------------------------------------------------------------
    {
        "provider_name": "Painted Brain",
        "service_name": "Enhanced Care Management (ECM)",
        "display_name": "Painted Brain - Enhanced Care Management (ECM)",
        "primary_category": "case_management_resource",
        "secondary_categories": ["mental_health", "healthcare_navigation", "housing_navigation"],
        "pathways": ["services", "medical", "housing", "benefits"],
        "tags": ["enhanced_care_management", "ecm", "case_management_resource",
                 "whole_person_care", "peer_support", "mental_health",
                 "dual_diagnosis", "substance_use_recovery", "housing_navigation",
                 "healthcare_navigation", "benefits_navigation",
                 "transportation_support", "food_resources", "community_support",
                 "chronic_illness", "homeless", "near_homeless", "low_income",
                 "uninsured", "underinsured", "lgbtqia", "veterans",
                 "immigrants", "reentry", "trauma_survivors",
                 "domestic_violence_survivors", "needs_eligibility_verification"],
        "description": (
            "Whole-person care coordination for people facing multiple challenges. Connects "
            "clients to medical, mental health, housing, food, transportation, community support, "
            "and benefit resources via a Peer Lead Care Manager who coordinates communication "
            "between healthcare providers, advocates for client needs, provides check-ins, "
            "offers emotional support, and helps build self-management skills."
        ),
        "services_offered": [
            "Psychiatric Emergency Services", "Nutrition Education", "Help Find Housing",
            "Housing Advice", "Addiction & Recovery", "Health Education", "In-Home Support",
            "Mental Health Care", "Peer Support", "Support Groups", "Virtual Support"
        ],
        "people_served": [
            "Anyone In Need", "All Ages", "Veterans", "Immigrants", "Undocumented",
            "Criminal Justice History", "All Disabilities", "Foster Youth",
            "LGBTQIA+", "Chronic Illness", "Homeless", "Near Homeless", "Low-Income"
        ],
        "eligibility": ["Anyone can access these services."],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English"],
        "phone": None,
        "email": None,
        "website": "https://paintedbrain.org/",
        "locations": [
            {"location_name": "Community Center", "location_type": "Admin-Only",
             "state": "CA", "website": "https://paintedbrain.org/",
             "hours": "Mon/Wed 11 AM - 4 PM, Thu 12 - 5 PM"}
        ],
        "coverage_area": ["CA"],
        "cmsx_notes": (
            "Strong referral for clients who need whole-person care coordination with mental "
            "health concerns, chronic illness, housing instability, substance use recovery, "
            "legal issues, transportation barriers, unemployment, benefits needs, and complex "
            "healthcare systems. Not a housing placement provider but supports housing navigation "
            "as part of ECM. Mark needs_review: ECM eligibility, payer requirements, service "
            "availability, and referral process should be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://paintedbrain.org/",
        "active": True,
    },
    # 17 ----------------------------------------------------------------------
    {
        "provider_name": "Harbor Recuperative Care (HRC)",
        "service_name": "Recuperative Care Shelter",
        "display_name": "Harbor Recuperative Care (HRC) - Recuperative Care Shelter",
        "primary_category": "medical_respite",
        "secondary_categories": ["housing_navigation", "case_management_resource"],
        "pathways": ["medical", "housing", "services"],
        "tags": ["medical_respite", "recuperative_care", "hospital_discharge",
                 "homeless_adults", "temporary_homeless", "post_treatment",
                 "chronic_illness", "limited_mobility", "wound_care",
                 "medication_assistance", "case_management",
                 "housing_navigation", "short_term_housing", "residential_care",
                 "hospital_referral_required", "documents_required",
                 "open_24_hours", "needs_referral_verification"],
        "description": (
            "30 beds of shelter for injured or ill homeless adults nearing release from hospitals. "
            "Assists recently discharged individuals in recovery by providing shelter, housing-"
            "focused case management, nourishing food, and support transitioning from recuperative "
            "care into more permanent housing."
        ),
        "services_offered": [
            "Help Find Housing", "Short-Term Housing", "Medical Care",
            "Case Management", "Residential Care"
        ],
        "people_served": [
            "Adults 18+", "Limited Mobility", "Post-Treatment",
            "Chronic Illness", "Individuals", "Homeless", "Near Homeless"
        ],
        "eligibility": [
            "Must be homeless or temporarily homeless.",
            "Must be referred by hospital case worker.",
            "Must be cleared of all active communicable diseases including COVID-19.",
            "If uninsured, must have at least one month supply of all prescribed medications.",
            "Must be able to self-represent, self-medicate with minimal help.",
            "Must be discharge ready per hospital policies."
        ],
        "documents_required": [
            {
                "type": "Written Referral",
                "details": "Discharge orders including diagnosis, dietary orders, follow-up appointments, "
                           "plan of care, and discharge prescriptions. Social worker evaluation required."
            }
        ],
        "cost": "Free",
        "languages": ["English"],
        "phone": "818-925-1451",
        "email": None,
        "website": "https://www.harborcares.org/residents",
        "locations": [
            {"location_name": "Harbor Care Center",
             "address": "11134 Sepulveda Boulevard",
             "city": "Los Angeles", "state": "CA", "zip": "91345",
             "phone": "818-925-1451", "hours": "Open 24 Hours / 7 Days"}
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "High-value referral for homeless or temporarily homeless adults being discharged "
            "from hospitals who need medical respite, recuperative care, wound care, medication "
            "support, case management, housing location services, and transition support into "
            "permanent housing. Hospital case worker referral, discharge readiness, communicable "
            "disease clearance, medication supply, and required documents must be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://www.harborcares.org/residents",
        "active": True,
    },
    # 18 ----------------------------------------------------------------------
    {
        "provider_name": "Foundation For Women Warriors",
        "service_name": "Warrior Assistance",
        "display_name": "Foundation For Women Warriors - Warrior Assistance",
        "primary_category": "financial_assistance",
        "secondary_categories": ["veteran_assistance", "benefits"],
        "pathways": ["benefits", "services"],
        "tags": ["veteran_assistance", "women_veterans", "financial_assistance",
                 "emergency_payments", "rent_assistance", "utility_assistance",
                 "healthcare_cost_assistance", "homelessness_prevention",
                 "near_homeless", "mothers", "southern_california",
                 "free", "needs_grant_availability_check"],
        "description": (
            "Provides women veterans with immediate grants to cover rent and emergency expenses "
            "such as medical bills, utility bills, and other necessities."
        ),
        "services_offered": [
            "Emergency Payments", "Help Pay For Healthcare",
            "Help Pay For Housing", "Help Pay For Utilities"
        ],
        "people_served": ["Adults 18+", "Veterans", "Female", "Near Homeless", "Mothers"],
        "eligibility": [
            "Must be a female veteran honorably discharged from US Armed Services.",
            "Must currently be a resident of Southern California.",
            "Must be in good health and financially sustainable.",
            "Must be employed, going to school, or working with a Foundation-approved employment organization."
        ],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English"],
        "phone": "310-733-2450",
        "email": None,
        "website": "https://foundationforwomenwarriors.org/programs/warrior-assistance/",
        "locations": [
            {"location_name": "North Hollywood Office",
             "address": "5062 Lankershim Boulevard #3013",
             "city": "Los Angeles", "state": "CA", "zip": "91601"}
        ],
        "coverage_area": [
            "Imperial County, CA", "Los Angeles County, CA", "Orange County, CA",
            "Riverside County, CA", "San Bernardino County, CA",
            "San Diego County, CA", "Santa Barbara County, CA", "Ventura County, CA"
        ],
        "cmsx_notes": (
            "Useful for women veterans in Southern California needing emergency financial "
            "assistance for rent, healthcare expenses, utilities, and urgent needs. Not a "
            "housing provider but can help prevent homelessness. Mark needs_review: eligibility, "
            "grant availability, documentation, and application requirements should be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://foundationforwomenwarriors.org/programs/warrior-assistance/",
        "active": True,
    },
    # 19 ----------------------------------------------------------------------
    {
        "provider_name": "Lutheran Social Services of Southern California (LSSSC)",
        "service_name": "Permanent Supportive / Rapid Re-Housing",
        "display_name": "Lutheran Social Services of Southern California (LSSSC) - Permanent Supportive/Rapid Re-Housing",
        "primary_category": "housing_navigation",
        "secondary_categories": ["rental_assistance", "transitional_housing"],
        "pathways": ["housing", "services", "benefits"],
        "tags": ["rapid_rehousing", "permanent_supportive_housing", "housing_navigation",
                 "help_pay_for_housing", "short_term_housing", "low_barrier_housing",
                 "supportive_services", "rental_assistance",
                 "homeless", "near_homeless", "low_income", "benefit_recipients",
                 "medical_care_linkage", "mental_health_care",
                 "employment_support", "financial_education",
                 "english_spanish", "needs_county_availability_check"],
        "description": (
            "Provides transitional housing and support services to help individuals and families "
            "lead more stable lives. Includes low-barrier affordable housing, healthcare support, "
            "rapid rehousing, permanent supportive housing support, help paying for housing, "
            "short-term housing, employment support, mental health care, and financial education."
        ),
        "services_offered": [
            "Help Pay For Housing", "Help Find Housing", "Short-Term Housing",
            "Help Find Work", "Help Pay For Healthcare", "Medical Care",
            "Mental Health Care", "Financial Education", "More Education"
        ],
        "people_served": [
            "Anyone In Need", "All Ages", "Homeless", "Near Homeless",
            "Benefit Recipients", "Low-Income"
        ],
        "eligibility": ["Contact provider to confirm eligibility criteria."],
        "documents_required": [],
        "cost": "Free",
        "languages": ["English", "Spanish"],
        "phone": "562-599-1321",
        "email": None,
        "website": "https://www.lsssc.org/transitional-services/",
        "locations": [
            {"location_name": "Lutheran Social Services - South Bay/Long Beach",
             "address": "1611 Pine Avenue", "city": "Long Beach", "state": "CA",
             "zip": "90813", "phone": "562-599-1321"},
            {"location_name": "Lutheran Social Services - Riverside County",
             "address": "6857 Indiana Avenue", "city": "Riverside", "state": "CA",
             "zip": "92506", "phone": "951-689-8447"},
        ],
        "coverage_area": [
            "Los Angeles County, CA", "Riverside County, CA",
            "San Bernardino County, CA", "Ventura County, CA"
        ],
        "cmsx_notes": (
            "Useful housing stabilization referral for homeless, near-homeless, low-income, and "
            "benefit-recipient clients. Mark needs_review: eligibility, county availability, "
            "office-specific service offerings, and referral requirements should be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://www.lsssc.org/transitional-services/",
        "active": True,
    },
    # 20 ----------------------------------------------------------------------
    {
        "provider_name": "AIDS Project Los Angeles (APLA) Health",
        "service_name": "Housing Support Services",
        "display_name": "APLA Health - Housing Support Services",
        "primary_category": "housing_navigation",
        "secondary_categories": ["healthcare_navigation", "tenant_rights"],
        "pathways": ["housing", "services", "medical"],
        "tags": ["hiv_aids", "housing_support", "housing_navigation",
                 "housing_retention", "affordable_housing", "tenant_rights",
                 "mediation", "case_management_coordination",
                 "lgbtqia", "homeless", "near_homeless",
                 "families", "individuals", "english_spanish",
                 "reduced_cost", "apla_health", "needs_eligibility_verification"],
        "description": (
            "Assists people living with HIV/AIDS who are experiencing homelessness, at risk of "
            "homelessness, or need assistance maintaining or retaining housing. Housing specialists "
            "help clients acquire, finance, and maintain affordable housing through housing plans, "
            "assistance applications, moving support, tenant rights education, affordable "
            "supportive housing referrals, and liaison support."
        ),
        "services_offered": [
            "Residential Housing", "Navigating The System", "One-On-One Support",
            "Help Find Housing", "Housing Advice", "Mediation"
        ],
        "people_served": [
            "All Ages", "LGBTQIA+", "HIV/AIDS", "Individuals", "Families",
            "Homeless", "Near Homeless"
        ],
        "eligibility": ["Contact provider to confirm eligibility criteria."],
        "documents_required": [],
        "cost": "Reduced Cost",
        "languages": ["English", "Spanish"],
        "phone": "213-201-1637",
        "email": "bbrown@apla.org",
        "website": "https://aplahealth.org/services/housing-support-services/",
        "locations": [
            {"location_name": "West Hollywood Office", "location_type": "Admin-Only",
             "phone": "213-201-1450", "hours": "Mon-Fri 8 AM - 5 PM"},
            {"location_name": "APLA Health and Wellness", "location_type": "Admin-Only",
             "phone": "213-201-1600"},
        ],
        "coverage_area": [
            "Los Angeles County, CA", "Orange County, CA",
            "Riverside County, CA", "San Bernardino County, CA", "Ventura County, CA"
        ],
        "cmsx_notes": (
            "Specialized housing support for clients living with HIV/AIDS who are homeless, near "
            "homeless, or at risk of losing housing. Not an emergency shelter or general housing "
            "placement resource. Mark needs_review: eligibility, documentation, appointment "
            "requirements, and housing availability should be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://aplahealth.org/services/housing-support-services/",
        "active": True,
    },
    # 21 ----------------------------------------------------------------------
    {
        "provider_name": "New Horizons",
        "service_name": "Residential & Community Living",
        "display_name": "New Horizons - Residential & Community Living",
        "primary_category": "disability_housing",
        "secondary_categories": ["housing_navigation"],
        "pathways": ["housing", "medical", "services"],
        "tags": ["disability_housing", "developmental_disability",
                 "supported_residential_living", "community_living",
                 "residential_homes", "independent_living_skills",
                 "daily_living_skills", "budgeting", "money_management",
                 "menu_planning", "support_network", "financial_education",
                 "san_fernando_valley", "north_hills",
                 "reduced_cost", "regional_center_review", "needs_availability_check"],
        "description": (
            "Helps adults with developmental disabilities get the most out of their living "
            "experience, whether in New Horizons' residential homes or independently. Supports "
            "clients with locating appropriate living arrangements, menu planning, budgeting, "
            "money management, daily living skills, and independent living support. Residential "
            "homes in San Fernando Valley have dedicated 24-hour staff."
        ),
        "services_offered": [
            "Residential Housing", "Support Network", "Financial Education"
        ],
        "people_served": ["Adults", "Young Adults", "Seniors", "Developmental Disability"],
        "eligibility": ["Contact provider to confirm eligibility criteria."],
        "documents_required": [],
        "cost": "Reduced Cost",
        "languages": ["English"],
        "phone": "818-894-9301",
        "email": "mveals@newhorizons-sfv.org",
        "website": "https://newhorizons-sfv.org/programs/residential/residential-community-living/",
        "locations": [
            {"location_name": "New Horizons, Inc",
             "address": "15725 Parthenia Street",
             "city": "North Hills", "state": "CA", "zip": "91343", "phone": "818-894-9301"}
        ],
        "coverage_area": ["Los Angeles County, CA"],
        "cmsx_notes": (
            "For adults, young adults, and seniors with developmental disabilities needing "
            "residential living, community living support, independent living skills, budgeting, "
            "money management, and 24-hour staff-supported residential homes. Not homeless "
            "shelter, sober living, or general affordable housing. Mark needs_review: eligibility, "
            "payer/funding source, Regional Center involvement, waitlist status, and residential "
            "availability must be confirmed."
        ),
        "verification_status": "needs_review",
        "source": "findhelp_detail_page",
        "source_url": "https://newhorizons-sfv.org/programs/residential/residential-community-living/",
        "active": True,
    },
]


def run_seed(force: bool = False) -> dict:
    """
    Seed the resource library with the first batch of resources.
    Skips records that already exist (matched by provider_name + service_name).
    Returns a summary dict.
    """
    initialize_db()
    inserted = 0
    skipped = 0
    errors = []

    for rec in SEED_RESOURCES:
        try:
            if not force and resource_exists(rec["provider_name"], rec["service_name"]):
                logger.info(f"Skipping existing resource: {rec['display_name']}")
                skipped += 1
                continue
            insert_resource(rec)
            logger.info(f"Seeded: {rec['display_name']}")
            inserted += 1
        except Exception as e:
            msg = f"Error seeding {rec.get('display_name')}: {e}"
            logger.error(msg)
            errors.append(msg)

    total = get_resource_count()
    return {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "total_in_db": total,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_seed()
    print(result)
