"""
Test Knowledge Enrichment
Verifies that knowledge files enrich Virgil DB results
"""

import sys
import io
from pathlib import Path

# Fix UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.modules.services.virgil_db_service import VirgilServiceDatabase


def test_enrichment_query(query: str, location: str = "Los Angeles, CA"):
    """Test a query and show enrichment"""
    print(f"\nQUERY: {query}")
    print(f"LOCATION: {location}")
    print("-" * 80)

    # Initialize service
    db_path = Path(__file__).parent / "databases" / "virgil_st_dev.db"
    service = VirgilServiceDatabase(db_path=str(db_path))

    # Search
    results = service.search_services_enhanced(query, location, limit=5)

    if not results:
        print("[NO RESULTS]\n")
        return

    print(f"Found {len(results)} results:\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. {result.get('name', 'Unknown')}")
        print(f"   Type: {result.get('type', 'N/A')}")
        print(f"   Source: {result.get('source', 'Unknown')}")

        # Show enrichment status
        if result.get('enriched'):
            print(f"   [ENRICHED from {result.get('enrichment_source', 'unknown')}]")

            if result.get('website'):
                print(f"   Website: {result['website']}")

            if result.get('payment_details'):
                print(f"   Payment: {result['payment_details']}")

            if result.get('services_details'):
                print(f"   Services: {result['services_details']}")

            if result.get('provider_notes'):
                notes = result['provider_notes']
                if len(notes) > 100:
                    notes = notes[:97] + "..."
                print(f"   Notes: {notes}")

        # Show description (truncated)
        desc = result.get('description', '')
        if desc:
            if len(desc) > 150:
                desc = desc[:147] + "..."
            print(f"   Description: {desc}")

        print()


def main():
    """Run enrichment tests"""
    print("\n" + "=" * 80)
    print("KNOWLEDGE ENRICHMENT TEST")
    print("Testing enrichment from knowledge files")
    print("=" * 80)

    # Test queries that should find enriched providers
    test_queries = [
        ("suboxone clinic Los Angeles", "Los Angeles, CA"),
        ("MAT provider JWCH", "Los Angeles, CA"),
        ("BAART Programs", "Los Angeles, CA"),
        ("Mariposa detox", "Los Angeles, CA"),
    ]

    for query, location in test_queries:
        test_enrichment_query(query, location)

    print("=" * 80)
    print("\nENRICHMENT TEST COMPLETE")
    print("\nProviders should show:")
    print("  - [ENRICHED from ...] marker")
    print("  - Detailed payment information")
    print("  - Detailed services information")
    print("  - Provider-specific notes")
    print("=" * 80)


if __name__ == "__main__":
    main()
