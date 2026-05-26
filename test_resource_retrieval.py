"""
Test Script for Resource Retrieval Engine
Tests the curated provider search against Case Manager GPT benchmarks.
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.modules.resources.retrieval_engine import get_resource_engine


def print_separator():
    print("\n" + "=" * 80 + "\n")


async def test_benchmark_query(query: str, expected_providers: list):
    """Test a benchmark query and compare results"""
    print(f"QUERY: {query}")
    print(f"EXPECTED: {', '.join(expected_providers)}")
    print("-" * 80)

    # Get resource engine
    engine = get_resource_engine()

    # Search
    results = engine.search(query, limit=5)

    if not results:
        print("[FAIL] NO RESULTS FOUND")
        return False

    # Print results
    print(f"\nFOUND {len(results)} PROVIDERS:\n")
    for i, scored_provider in enumerate(results, 1):
        provider = scored_provider.provider
        print(f"{i}. {provider.name}")
        print(f"   Type: {provider.service_type} - {', '.join(provider.service_subtypes)}")
        if provider.phone:
            print(f"   Phone: {provider.phone}")
        if provider.neighborhood or provider.city:
            location = provider.neighborhood or provider.city
            print(f"   Location: {location}")
        if provider.insurance_accepted:
            print(f"   Insurance: {', '.join(provider.insurance_accepted)}")
        print(f"   Score: {scored_provider.total_score:.2f} (loc: {scored_provider.location_score:.2f}, "
              f"svc: {scored_provider.service_score:.2f}, qual: {scored_provider.quality_score:.2f})")
        if provider.notes:
            print(f"   Notes: {provider.notes}")
        print()

    # Check if expected providers are in top results
    found_names = [sp.provider.name.lower() for sp in results]
    expected_found = []
    for expected in expected_providers:
        if any(expected.lower() in name for name in found_names):
            expected_found.append(expected)

    if expected_found:
        print(f"[PASS] FOUND {len(expected_found)}/{len(expected_providers)} EXPECTED PROVIDERS:")
        for name in expected_found:
            print(f"   - {name}")
        return len(expected_found) >= len(expected_providers) / 2  # At least half
    else:
        print(f"[FAIL] NONE OF THE EXPECTED PROVIDERS FOUND")
        return False


async def main():
    """Run benchmark tests"""
    print_separator()
    print("RESOURCE RETRIEVAL ENGINE - BENCHMARK TESTS")
    print("Comparing against Case Manager GPT expected results")
    print_separator()

    # Test cases based on your Case Manager GPT comparison
    test_cases = [
        {
            "query": "I need detox in North Hollywood that takes Medi-Cal",
            "expected": ["Muse", "CRI-Help", "Tarzana", "Westwind"]
        },
        {
            "query": "Find me urgent care near Van Nuys",
            "expected": []  # We'll see what we get
        },
        {
            "query": "I need a food bank in Sherman Oaks",
            "expected": []  # We'll see what we get
        },
        {
            "query": "Emergency shelter tonight in North Hollywood",
            "expected": ["Hope of the Valley", "San Fernando Valley Rescue Mission"]
        },
        {
            "query": "MAT provider North Hollywood",
            "expected": ["CRI-Help"]
        },
    ]

    passed = 0
    total = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        print(f"TEST {i}/{total}")
        result = await test_benchmark_query(
            test_case["query"],
            test_case["expected"]
        )
        if result:
            passed += 1
        print_separator()

    # Summary
    print(f"RESULTS: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("[SUCCESS] ALL TESTS PASSED! Resource retrieval is working as expected.")
    elif passed >= total / 2:
        print("[PARTIAL] PARTIAL SUCCESS. Some improvements needed.")
    else:
        print("[FAILED] TESTS FAILED. Significant improvements needed.")


if __name__ == "__main__":
    asyncio.run(main())
