#!/usr/bin/env python3
"""
Predeploy smoke checks for Railway/Vercel readiness.
"""

from collections import Counter
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_module_loads():
    import main

    failures = {
        name: status
        for name, status in main.loaded_modules.items()
        if isinstance(status, str) and status.startswith("error:")
    }

    return failures, main


def check_duplicate_routes(app):
    pairs = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or []
        if not path:
            continue
        for method in methods:
            if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                pairs.append((method, path))

    counts = Counter(pairs)
    duplicates = sorted((m, p, c) for (m, p), c in counts.items() if c > 1)
    return duplicates


def check_required_paths(app):
    existing = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or []
        for method in methods:
            if path and method in {"GET", "POST"}:
                existing.add((method, path))

    required = [
        ("GET", "/api/health"),
        ("GET", "/api/housing/search"),
        ("GET", "/api/services/search"),
        ("POST", "/api/ai/chat"),
    ]

    missing = [item for item in required if item not in existing]
    return missing


def main_check():
    failures, main_module = check_module_loads()
    duplicates = check_duplicate_routes(main_module.app)
    missing_paths = check_required_paths(main_module.app)

    has_error = False

    if failures:
        has_error = True
        print("FAILED: module load errors detected")
        for name, status in failures.items():
            print(f" - {name}: {status}")

    if duplicates:
        has_error = True
        print("FAILED: duplicate method/path routes detected")
        for method, path, count in duplicates:
            print(f" - {method} {path} x{count}")

    if missing_paths:
        has_error = True
        print("FAILED: required API paths missing")
        for method, path in missing_paths:
            print(f" - {method} {path}")

    if has_error:
        return 1

    print("PASS: predeploy smoke checks succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main_check())
