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

# ── Job Search Hub URL Generation ───────────────────────────────
print("\n[Job Search Hub — URL Generation]")

import urllib.parse as _uparse

# Primary boards: direct search deep-links. Must encode keyword + location.
# Uses quote() to match JS encodeURIComponent (space → %20, not +).
def _build_primary_urls(keywords, location, low_barrier=False):
    base = (keywords or "").strip() or "jobs"
    kw   = f"{base} entry level" if low_barrier else base
    loc  = (location or "Los Angeles, CA").strip()
    q    = _uparse.quote(kw,  safe="")
    l    = _uparse.quote(loc, safe="")
    return {
        "indeed":       f"https://www.indeed.com/jobs?q={q}&l={l}",
        "craigslist":   f"https://losangeles.craigslist.org/search/jjj?query={q}&sort=date",
        "google":       f"https://www.google.com/search?q={_uparse.quote(kw + ' jobs ' + loc, safe='')}",
        "linkedin":     f"https://www.linkedin.com/jobs/search/?keywords={q}&location={l}",
        "ziprecruiter": f"https://www.ziprecruiter.com/jobs-search?search={q}&location={l}",
    }

# Manual boards: homepage links only, no keyword/location encoded.
_MANUAL_BOARD_URLS = {
    "caljobs":     "https://www.caljobs.ca.gov",
    "glassdoor":   "https://www.glassdoor.com/Job/index.htm",
    "monster":     "https://www.monster.com",
    "snagajob":    "https://www.snagajob.com",
    "simplyhired": "https://www.simplyhired.com",
}

_PRIMARY_DOMAINS = {
    "indeed":       "indeed.com",
    "craigslist":   "craigslist.org",
    "google":       "google.com",
    "linkedin":     "linkedin.com",
    "ziprecruiter": "ziprecruiter.com",
}

# Boards where location appears in URL as a query param
_LOCATION_IN_URL_BOARDS = {"indeed", "linkedin", "ziprecruiter"}
# (Craigslist encodes location via regional subdomain; Google bakes it into q=)

def _check_url_generation():
    start  = time.time()
    errors = []

    test_cases = [
        ("photographer",  "Los Angeles"),
        ("office assistant", "Van Nuys"),
        ("warehouse",     "Burbank"),
    ]

    for kw, loc in test_cases:
        urls = _build_primary_urls(kw, loc)

        for board, url in urls.items():
            decoded = _uparse.unquote(url)

            # Domain check
            if _PRIMARY_DOMAINS[board] not in url:
                errors.append(f"[{kw}/{loc}] {board}: domain '{_PRIMARY_DOMAINS[board]}' missing")
                continue

            # Keyword must appear (decoded)
            if kw.lower() not in decoded.lower():
                errors.append(f"[{kw}/{loc}] {board}: keyword '{kw}' not in URL")

            # Location must appear for relevant boards
            if board in _LOCATION_IN_URL_BOARDS and loc.lower() not in decoded.lower():
                errors.append(f"[{kw}/{loc}] {board}: location '{loc}' not in URL")

            # Sanity: no literal 'undefined' / 'null' / empty params / double ??
            for bad in ("undefined", "null"):
                if bad in url:
                    errors.append(f"[{kw}/{loc}] {board}: '{bad}' in URL")
            if "??" in url or "&&" in url or url.endswith("&") or url.endswith("?"):
                errors.append(f"[{kw}/{loc}] {board}: malformed URL (double ?? or &&)")
            if "=&" in url or "=?" in url or "= " in url:
                errors.append(f"[{kw}/{loc}] {board}: empty or unencoded query param")

    # Manual boards: just validate they are well-formed HTTPS URLs with no junk
    for board, url in _MANUAL_BOARD_URLS.items():
        if not url.startswith("https://"):
            errors.append(f"manual {board}: must start with https://")
        for bad in ("undefined", "null", " "):
            if bad in url:
                errors.append(f"manual {board}: '{bad}' in URL")

    elapsed = time.time() - start
    combos  = len(test_cases)
    label   = f"URL generation: {combos} combos × 5 primary boards + 5 manual boards"
    if errors:
        print(f"  {FAIL}  [---] [{elapsed:.1f}s]  {label}")
        for e in errors:
            print(f"         -> {e}")
        return False
    print(f"  {PASS}  [---] [{elapsed:.1f}s]  {label}")
    return True

results.append(_check_url_generation())

# ── Job Search API (backend availability only, results count not required) ───
print("\n[Job Search API — endpoint reachability]")

# Results count no longer drives pass/fail — frontend uses external links as the
# primary flow.  These checks verify the endpoint is reachable and returns HTTP 200.
_job_spot_checks = [
    ("delivery+driver",   "transport"),
    ("office+assistant",  "admin / office"),
    ("food+service",      "food / bev / hosp"),
    ("retail+sales",      "retail / wholesale"),
    ("maintenance",       "skilled trade / craft"),
]
for kw, cat in _job_spot_checks:
    results.append(check(
        get(f"/api/jobs/search/quick?keywords={kw}&location=Los+Angeles&per_page=5",
            f"GET /api/jobs/search/quick?keywords={kw} [{cat}]"),
        expect_results=False   # 0 results is OK; endpoint must respond 200
    ))

# Relevance regression check — backend ranking only; WARN not FAIL so deploy isn't blocked
_photo_result = get(
    "/api/jobs/search/quick?keywords=photographer&location=Los+Angeles&per_page=5",
    "GET /api/jobs/search/quick?keywords=photographer [art / media / design]"
)
_PHOTO_TERMS = {"photographer", "photography", "photo", "camera", "studio", "imaging", "media", "creative"}

def _check_photographer_relevance(result):
    if not result["ok"]:
        icon = FAIL
        note = f"HTTP {result['status']} - {result.get('error', '')}"
        ok = False
    else:
        data = result["data"]
        query_used = (data.get("query_used") or "").lower()
        jobs = data.get("jobs") or []

        # Verify query_used echoes the right keyword
        if query_used and "photographer" not in query_used:
            icon = FAIL
            note = f"query_used='{query_used}' — backend did not search for 'photographer'"
            ok = False
        else:
            # Check whether top results contain at least one photography-related term
            relevant = 0
            top_titles = []
            for job in jobs[:5]:
                text = " ".join([
                    (job.get("title") or ""),
                    (job.get("description") or ""),
                    (job.get("provider") or ""),
                    (job.get("source") or ""),
                ]).lower()
                top_titles.append(job.get("title") or "(no title)")
                if any(t in text for t in _PHOTO_TERMS):
                    relevant += 1

            n = len(jobs)
            if relevant > 0:
                icon = PASS
                note = f"{n} results, {relevant}/{min(n,5)} relevant to 'photographer'"
                ok = True
            elif n == 0:
                icon = WARN
                note = "0 results — check SerpAPI key / quota"
                ok = True
            else:
                icon = WARN
                note = (
                    f"{n} results but none of top {min(n,5)} contain photography terms — "
                    "ranking regression likely. Top titles: " +
                    " | ".join(top_titles[:5])
                )
                ok = True  # WARN not FAIL so deploy isn't blocked

    t = f"{result['elapsed']:.1f}s"
    print(f"  {icon}  [{result['status']:3d}] [{t:>5}]  {result['label']}")
    if icon != PASS:
        print(f"         -> {note}")
    return ok

results.append(_check_photographer_relevance(_photo_result))

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
