"""
Test Enhanced Virgil DB Service
Tests the enhanced search across all resource types: food, treatment, medical, housing, etc.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.modules.services.virgil_db_service import VirgilServiceDatabase


def print_separator():
    print("\n" + "=" * 80 + "\n")


def test_query(service: VirgilServiceDatabase, query: str, location: str = "Los Angeles, CA"):
    """Test a single query and display results"""
    print(f"QUERY: {query}")
    print(f"LOCATION: {location}")
    print("-" * 80)

    try:
        results = service.search_services_enhanced(
            query=query,
            location=location,
            limit=10
        )

        if not results:
            print("[NO RESULTS FOUND]\n")
            return False

        print(f"\nFOUND {len(results)} PROVIDERS:\n")

        for i, result in enumerate(results[:5], 1):  # Show top 5
            print(f"{i}. {result.get('name', 'Unknown')}")

            # Show type and services
            result_type = result.get('type', 'N/A')
            print(f"   Type: {result_type}")

            # Show service subtypes if available
            subtypes = result.get('service_subtypes', [])
            if subtypes:
                print(f"   Services: {', '.join(subtypes)}")

            # Show location
            city = result.get('city', '')
            location_str = result.get('location', '')
            if city:
                print(f"   Location: {city}")
            elif location_str:
                print(f"   Location: {location_str}")

            # Show contact
            phone = result.get('phone', '')
            if phone:
                print(f"   Phone: {phone}")

            website = result.get('website', '')
            if website:
                print(f"   Website: {website}")

            # Show insurance
            insurance = result.get('insurance_accepted', [])
            if insurance:
                print(f"   Insurance: {', '.join(insurance)}")

            # Show scoring
            location_score = result.get('location_score', 0)
            print(f"   Location Score: {location_score:.2f}")

            print()

        return True

    except Exception as e:
        print(f"[ERROR] {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run comprehensive tests across all resource types"""
    print_separator()
    print("ENHANCED VIRGIL DB SERVICE - COMPREHENSIVE TESTS")
    print("Testing search across food, treatment, medical, housing, and other resources")
    print_separator()

    # Initialize service - use root databases folder, not backend/databases
    db_path = Path(__file__).parent / "databases" / "virgil_st_dev.db"
    service = VirgilServiceDatabase(db_path=str(db_path))

    # Test cases covering all major resource types
    test_cases = [
        # Food resources
        {
            "query": "food bank in Los Angeles",
            "location": "Los Angeles, CA",
            "category": "Food"
        },
        {
            "query": "emergency food assistance North Hollywood",
            "location": "North Hollywood, CA",
            "category": "Food"
        },

        # Treatment centers
        {
            "query": "detox center in Los Angeles with Medi-Cal",
            "location": "Los Angeles, CA",
            "category": "Treatment - Detox"
        },
        {
            "query": "residential treatment center North Hollywood",
            "location": "North Hollywood, CA",
            "category": "Treatment - Residential"
        },
        {
            "query": "MAT provider suboxone Los Angeles",
            "location": "Los Angeles, CA",
            "category": "Treatment - MAT"
        },

        # Medical providers
        {
            "query": "primary care doctor North Hollywood Medi-Cal",
            "location": "North Hollywood, CA",
            "category": "Medical - PCP"
        },
        {
            "query": "urgent care near Van Nuys",
            "location": "Van Nuys, CA",
            "category": "Medical - Urgent Care"
        },
        {
            "query": "STD testing clinic Los Angeles",
            "location": "Los Angeles, CA",
            "category": "Medical - STD Testing"
        },

        # Housing
        {
            "query": "emergency shelter tonight Los Angeles",
            "location": "Los Angeles, CA",
            "category": "Housing - Emergency"
        },
        {
            "query": "transitional housing North Hollywood",
            "location": "North Hollywood, CA",
            "category": "Housing - Transitional"
        },

        # Dental
        {
            "query": "free dental clinic Los Angeles Medi-Cal",
            "location": "Los Angeles, CA",
            "category": "Dental"
        },

        # Transportation
        {
            "query": "transportation assistance Los Angeles",
            "location": "Los Angeles, CA",
            "category": "Transportation"
        },
    ]

    passed = 0
    total = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        print(f"TEST {i}/{total} - {test_case['category']}")
        result = test_query(
            service,
            test_case["query"],
            test_case.get("location", "Los Angeles, CA")
        )
        if result:
            passed += 1
        print_separator()

    # Summary
    print(f"RESULTS: {passed}/{total} tests returned results ({passed/total*100:.0f}%)")

    if passed == total:
        print("[SUCCESS] ALL TESTS RETURNED RESULTS")
        print("\nPhase 1 Complete - Enhanced Virgil DB is working!")
        print("\nNext: Phase 2 - Build knowledge enrichment layer to add detailed notes")
    elif passed >= total / 2:
        print("[PARTIAL] Most tests passed - some improvements needed")
    else:
        print("[FAILED] Significant improvements needed")


if __name__ == "__main__":
    main()
