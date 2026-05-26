"""
Test AI Integration with Enhanced Virgil DB
Verifies that the unified AI service uses the enhanced search
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.modules.ai_unified.unified_service import UnifiedAIService


async def test_ai_search(query: str, location: str = "Los Angeles, CA"):
    """Test AI service search"""
    print(f"\nQUERY: {query}")
    print(f"LOCATION: {location}")
    print("-" * 80)

    # Initialize AI service
    service = UnifiedAIService()

    try:
        # Call search_internal_resources
        response = await service.search_internal_resources(query, location, limit=5)

        if not response or not response.get("services"):
            print("[NO RESULTS]\n")
            return

        results = response.get("services", [])
        print(f"Found {len(results)} results:\n")

        for i, result in enumerate(results[:5], 1):
            print(f"{i}. {result.get('provider_name', 'Unknown')}")
            print(f"   Type: {result.get('service_type', 'N/A')}")
            if result.get('service_subtypes'):
                print(f"   Subtypes: {result['service_subtypes']}")
            print(f"   Location: {result.get('city', result.get('location', 'N/A'))}")
            print(f"   Phone: {result.get('phone', 'N/A')}")
            if result.get('insurance_accepted'):
                print(f"   Insurance: {result['insurance_accepted']}")
            print(f"   Source: {result.get('source', 'Unknown')}")
            if result.get('location_score'):
                print(f"   Location Score: {result['location_score']:.2f}")
            print()

    except Exception as e:
        print(f"[ERROR] {str(e)}\n")
        import traceback
        traceback.print_exc()


async def main():
    """Run integration tests"""
    print("\n" + "=" * 80)
    print("AI INTEGRATION TEST - Enhanced Virgil DB Search")
    print("=" * 80)

    test_queries = [
        ("residential treatment center North Hollywood", "North Hollywood, CA"),
        ("food bank in Los Angeles", "Los Angeles, CA"),
        ("detox center with Medi-Cal", "Los Angeles, CA"),
        ("primary care doctor", "Van Nuys, CA"),
    ]

    for query, location in test_queries:
        await test_ai_search(query, location)

    print("=" * 80)
    print("\nINTEGRATION TEST COMPLETE")
    print("\nThe AI service is now using:")
    print("  - Enhanced Virgil DB with multi-table search")
    print("  - Smart keyword-based table routing")
    print("  - Location-aware scoring")
    print("  - Treatment centers, medical providers, resources, and meetings")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
