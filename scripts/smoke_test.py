#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMSX Post-Deploy Smoke Test
Usage:
  python scripts/smoke_test.py [BASE_URL]

BASE_URL defaults to http://localhost:8000 or $SMOKE_TEST_URL env var.

Auth options (pick one):
  SMOKE_TEST_TOKEN=<firebase_bearer>   Send as Authorization: Bearer <token>
  SMOKE_TEST_AUTH=test                 Send X-Test-Auth-Role: admin
                                       (server must have ENABLE_TEST_AUTH=1 + APP_ENV=test)
"""
import sys
import os
import io
import json
import time
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Force UTF-8 output so Unicode chars print safely on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("SMOKE_TEST_URL", "http://localhost:8000")).rstrip("/")

TIMEOUT = 20

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"

# Build auth headers for all requests
_AUTH_HEADERS: dict = {}
_bearer = os.getenv("SMOKE_TEST_TOKEN", "").strip()
_test_auth = os.getenv("SMOKE_TEST_AUTH", "").strip().lower()

if _bearer:
    _AUTH_HEADERS["Authorization"] = f"Bearer {_bearer}"
    print(f"[auth] Using Bearer token (SMOKE_TEST_TOKEN)")
elif _test_auth == "test":
    _AUTH_HEADERS["X-Test-Auth-Role"] = "admin"
    print(f"[auth] Using test-auth header (requires ENABLE_TEST_AUTH=1 + APP_ENV=test on server)")
else:
    print("[auth] No auth configured — protected routes will return 401 (set SMOKE_TEST_TOKEN or SMOKE_TEST_AUTH=test)")


def get(path, label=None):
    url = BASE_URL + path
    label = label or path
    start = time.time()
    try:
        headers = {"Accept": "application/json", **_AUTH_HEADERS}
        req = Request(url, headers=headers)
        with urlopen(req, timeout=TIMEOUT) as resp:
            elapsed = time.time() - start
            data = json.loads(resp.read())
            return {"ok": True, "status": resp.status, "data": data, "elapsed": elapsed, "label": label}
    except HTTPError as e:
        elapsed = time.time() - start
        try:
            detail = json.loads(e.read()).get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"ok": False, "status": e.code, "error": detail, "elapsed": elapsed, "label": label}
    except Exception as e:
        elapsed = time.time() - start
        return {"ok": False, "status": 0, "error": str(e), "elapsed": elapsed, "label": label}


def _count(data):
    for key in ("total_count", "total_results", "count", "resource_count"):
        val = data.get(key)
        if isinstance(val, int):
            return val
    for key in ("results", "jobs", "service_providers", "providers", "listings", "templates"):
        val = data.get(key)
        if isinstance(val, list):
            return len(val)
    return None


def check(result, expect_results=False):
    if not result["ok"]:
        icon = FAIL
        note = f"HTTP {result['status']} - {result.get('error', '')}"
        ok = False
    else:
        data = result["data"]
        success = data.get("success", True)
        n = _count(data)
        if not success:
            icon = FAIL
            note = f"success=false - {data.get('error') or data.get('message') or data.get('warning') or ''}"
            ok = False
        elif expect_results and n == 0:
            icon = WARN
            note = "0 results - check API keys and DB seeding"
            ok = True
        else:
            icon = PASS
            note = f"{n} results" if n is not None else data.get("status", "ok")
            ok = True

    t = f"{result['elapsed']:.1f}s"
    print(f"  {icon}  [{result['status']:3d}] [{t:>5}]  {result['label']}")
    if not ok or icon == WARN:
        print(f"         -> {note}")
    return ok


print(f"\nCMSX Smoke Test -> {BASE_URL}\n{'-'*60}")
results = []

# ── Health ───────────────────────────────────────────────────────
print("\n[Health]")
results.append(check(get("/api/health", "GET /api/health")))
results.append(check(get("/api/resources/health", "GET /api/resources/health")))

# ── Resource Library ─────────────────────────────────────────────
print("\n[Resource Library]")
results.append(check(
    get("/api/resources/search?category=food_support&per_page=5",
        "GET /api/resources/search?category=food_support"),
    expect_results=True
))
results.append(check(
    get("/api/resources/search?category=housing_navigation&per_page=5",
        "GET /api/resources/search?category=housing_navigation"),
    expect_results=True
))

# ── Services ─────────────────────────────────────────────────────
print("\n[Services]")
results.append(check(
    get("/api/services/search?category=food&page=1&per_page=5",
        "GET /api/services/search?category=food"),
    expect_results=True
))
results.append(check(
    get("/api/services/search?search=mental+health&page=1&per_page=5",
        "GET /api/services/search?search=mental+health"),
    expect_results=True
))

# ── Medical ──────────────────────────────────────────────────────
print("\n[Medical]")
results.append(check(
    get("/api/medical/providers?category=medi-cal&city=Los+Angeles&per_page=5",
        "GET /api/medical/providers?category=medi-cal"),
    expect_results=True
))

# ── Sober Living ─────────────────────────────────────────────────
print("\n[Sober Living]")
results.append(check(
    get("/api/sober-living-directory/listings?page=1&per_page=5",
        "GET /api/sober-living-directory/listings"),
    expect_results=True
))

# ── Job Search ───────────────────────────────────────────────────
print("\n[Job Search]")
results.append(check(
    get("/api/jobs/search/quick?keywords=delivery+driver&location=Los+Angeles&per_page=5",
        "GET /api/jobs/search/quick?keywords=delivery+driver"),
    expect_results=True
))

# ── Admissions ───────────────────────────────────────────────────
print("\n[Admissions]")
results.append(check(get("/api/admissions/templates", "GET /api/admissions/templates")))

# ── Summary ──────────────────────────────────────────────────────
passed = sum(1 for r in results if r)
total = len(results)
print(f"\n{'-'*60}")
if passed == total:
    print(f"  {passed}/{total} checks passed  {PASS}")
else:
    print(f"  {passed}/{total} checks passed  ({total - passed} failed)  {FAIL}")
print()
sys.exit(0 if passed == total else 1)
