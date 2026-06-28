# Production Data Hygiene Audit v1

Branch: `audit/production-data-hygiene-v1`
Base master at audit start: `2f29686`
Date: 2026-06-27

## Scope

Audit only. No production data was deleted or modified.

Reviewed targets:

- Smart Daily tasks/reminders
- FMLA records
- UR records
- Medical provider display names
- Case Management / client records
- Benefits records
- Frontend and backend source code for hardcoded test/demo data
- Auth and seed startup paths

Constraints followed:

- No schema changes
- No auth/billing/Stripe/SaaS changes
- No Railway/Vercel changes
- No package/env changes
- No unrelated cleanup
- `USABILITY_AUDIT_2026-06-27.md` left untouched

## Evidence boundary

This report combines:

- Full code-path inspection in `frontend/` and `backend/`
- Grep sweeps across all `.py`, `.js`, `.jsx`, `.json` for: `test`, `QA`, `validation`, `mismatch`, `PostGet`, `dummy`, `sample`, `demo`, `seed`, `fake`, `debug`, and specific record names
- Local SQLite inspection under `databases/*.db`
- The live-production symptom list provided in the prompt

Direct production DB reads were **not** performed. Findings about DB records are based on local DB inspection and live-production symptoms. Production-side row counts should be verified before any deletions.

---

## Answers to audit questions

### 1. Which test-looking records are hardcoded in frontend/backend?

**None that are live production paths.** All confirmed hardcoded test strings are behind proper guards:

- `backend/modules/resume/routes.py` — `MockCoreClients` class with `test-client-1`, `Test Client`, etc.
  - Guard: `try/except ImportError` fallback only; activates only if `backend.modules.resume.models` fails to import. In production the models import cleanly, so this code never runs.
  - Risk: **none in normal production**.

- `backend/modules/resume/generator.py:590` — `full_name="Test User"`
  - Guard: inside `if __name__ == '__main__':` block (line 532). Never runs when imported.
  - Risk: **none**.

- `backend/api/enhanced_client_routes.py` — test client create/cleanup functions
  - Guard: router is **not registered** in `main.py`. Not accessible via any production API route.
  - Risk: **none**.

- `backend/modules/legal/seed_expungement_data.py` — seeds two expungement cases
  - Guard: only called via `if __name__ == '__main__':`. Not imported or called in `main.py`.
  - Risk: **none**.

- `backend/modules/reminders/database_integration.py:263` — `seed_initial_users()` with names Sarah Johnson, Michael Rodriguez
  - Guard: method is defined but **never called** anywhere in the codebase.
  - Risk: **none**.

- `frontend/src/pages/ResumeMinimal.jsx` — hardcoded `[{John Doe}, {Jane Smith}]` client list
  - Guard: this page is **not registered** in `frontend/src/App.jsx`. Dead code, unreachable.
  - Risk: **none currently**. Worth deleting or converting to a real API call if ever reactivated.

- `frontend/src/contexts/AuthContext.jsx` + `frontend/src/api/config.js` — test auth profile with `e2e.case.manager@example.com`
  - Guard: `isFrontendTestAuthEnabled` requires `VITE_ENABLE_TEST_AUTH === 'true'` AND not on a production-like domain. At `cmsx-tau.vercel.app`, `isProductionLikeFrontend` is `true`, so test auth is always disabled. Also requires `frontend/.env.e2e` to be loaded (not the production build).
  - Risk: **none in production**.

- `tests/test_ai_documentation_service.py` — `"client_name": "QA TestClient-Eval"`
  - Type: pytest fixture in a test file. Not deployed.
  - Risk: **none**. (`QA TestClient-Eval` in the live Smart Daily was a live DB record, not a source-code leak.)

### 2. Which are live database records?

Found in local DB inspection:

- **`databases/core_clients.db`** — obvious QA/test client identities
- **`databases/case_management.db`** and other module mirrors — mirrored test clients
- **`databases/reminders.db` → `active_reminders`** — test/smoke reminder tasks
- **`databases/reminders.db` → `client_contacts`** — contact history entries for test clients
- **`databases/unified_platform.db` → `benefits_applications`** — test/runtime benefits rows
- **`databases/virgil_st_dev.db` → `medi_cal_providers`** — source dataset with malformed display labels

### 3. Which records appear in production UI?

Confirmed or strongly implied by live code paths:

- Client selectors and client-driven pages read from `core_clients` → test clients appear in every ClientSelector dropdown
- Smart Daily reads `active_reminders` / prioritized tasks → test/smoke reminders surface in task buckets and Smart Summary
- Benefits page `GET /api/benefits/applications` when no client selected returns the global list → test applications can appear in counts and list
- Medical provider search reads `medi_cal_providers` → malformed provider labels surface in provider search results

### 4. Which records are attached to real clients?

High-confidence QA/test-only (safe to delete after Brandon confirmation):

- Clients: `Test`, `Test Client`, `Final Test`, `Test User`, `API TestUser`
- Emails: `audit.probe@example.test`, `audit2.probe@example.test`, `ai.fallback@example.test`, `daylife.468333@example.test`
- Benefits applications: `test-001`, `runtime benefits rt_*`, notes containing only `"test"`
- Reminders: `AI fallback reminder test`, `Initial Assessment due for Test Client`, `Runtime manual reminder rt_*`, `AI runtime reminder rt_*`

Ambiguous / may need checking:

- `Follow up on housing application for Unknown Client` — may be an orphan (client_id references a client not in `core_clients.db`)
- Several reminder rows reference client IDs with no matching `core_clients` record — likely orphan smoke artifacts

### 5. Which records can be safely hidden by client filter/UI logic?

Already fixed in PR #75: Smart Daily Smart Summary now scopes to selected client. No new UI-layer hiding is recommended. Data should be cleaned, not masked.

Low-risk display-layer improvements (NOT done in this audit, proposed for follow-up):

- Benefits global list: could skip applications where `client_id` has no matching row in `core_clients` (orphan filter)
- Medical provider labels: a display-sanitization guard could suppress generic labels (`PHYSICIAN`, `PRACTITIONER`, `None Reported`, `FARSI`) and metadata fragments in provider names

### 6. Which require manual DB cleanup?

Manual cleanup required (Brandon approval before any deletions):

1. Test clients in `core_clients.db` and all mirrored module tables (`case_management.db`, etc.)
2. Active reminder/task artifacts in `active_reminders` and `tasks`
3. Contact history rows in `client_contacts` for test clients
4. Benefits application artifacts in `unified_platform.db.benefits_applications`

### 7. Which should remain?

Leave alone (not production risk):

- All `*.test.jsx` and `*.test.js` files — test fixtures, not deployed
- `backend/modules/resource_library/seed_data.py` and `food_seed.py` — these run on startup but seed real production resources (21 verified resources + food pantries), not test data
- `backend/modules/sober_living_directory/seed_from_excel` — seeds real sober living listings from committed Excel
- `backend/modules/groups/seed_topics.py` — seeds real group topic data

---

## Findings table

| Record / source name | Page where it appears | Source type | Risk level | Recommended action | Brandon approval required |
| --- | --- | --- | --- | --- | --- |
| `MockCoreClients` / `test-client-1` in `resume/routes.py` | Resume (only on ImportError fallback, normally unreachable) | backend dead-code guard | none | Leave alone — ImportError guard | No |
| `ResumeMinimal.jsx` hardcoded John Doe / Jane Smith | Unrouted (not in App.jsx) | frontend dead code | none | Delete file or wire to real API if ever activated | No (low risk dead code) |
| `Test User` in `generator.py` | Script-only (`__main__` block) | backend `__main__` block | none | Leave alone | No |
| `enhanced_client_routes.py` test endpoint | Not registered in main.py | unregistered router | none | Leave alone unless router is re-registered | No |
| `seed_initial_users()` in `database_integration.py` | Never called | dead code | none | Leave alone | No |
| `seed_expungement_data.py` | `__main__` only | script entrypoint | none | Leave alone | No |
| Test auth profile (`e2e.case.manager@example.com`) | Production: disabled by domain guard | frontend env guard | none | Leave alone — correctly guarded | No |
| `QA TestClient-Eval` string | Test files only (`tests/test_ai_documentation_service.py`) | pytest fixture | none | Leave alone — not source code | No |
| `AI fallback reminder test` | Smart Daily | live DB record (`reminders.db.active_reminders`) | demo embarrassment | Delete manually | Yes |
| `Initial Assessment due for Test Client` | Smart Daily | live DB record (`reminders.db`) | demo embarrassment | Delete manually | Yes |
| `Runtime manual reminder rt_*` / `AI runtime reminder rt_*` | Smart Daily | live DB record (`reminders.db.active_reminders`) | user confusion | Delete manually as smoke artifacts | Yes |
| `Follow up on housing application for Unknown Client` | Smart Daily | live DB record (likely orphan) | user confusion | Verify client_id; delete if orphan | Yes |
| Contact history for `Test Client`, `Final Test` | Client overview / reminder-derived history | live DB record (`reminders.db.client_contacts`) | demo embarrassment | Delete after client cleanup | Yes |
| `Test`, `Test Client`, `Final Test`, `Test User`, `API TestUser` clients | ClientSelector / Case Management / all client-driven routes | live DB record (`core_clients.db` + module mirrors) | demo embarrassment / user confusion | Manual cleanup across all module DBs | Yes |
| `Audit Probe`, `Audit2 Probe`, `AIFallback Client`, `Daylife Client468333` (`example.test` mailboxes) | ClientSelector / Case Management | live DB record (`core_clients.db` + mirrors) | demo embarrassment | Manual cleanup unless explicitly kept as QA data | Yes |
| `test-001` benefits application | Benefits page / dashboard counts | live DB record (`unified_platform.db.benefits_applications`) | demo embarrassment | Delete manually | Yes |
| `runtime benefits rt_*` applications | Benefits page / dashboard counts | live DB record (`unified_platform.db.benefits_applications`) | user confusion | Delete manually | Yes |
| Generic Medi-Cal labels: `PHYSICIAN`, `PRACTITIONER`, `DISEASE PHYSICIAN`, `None Reported`, `FARSI` | Medical provider search | dataset formatting issue (`virgil_st_dev.db.medi_cal_providers`) | user confusion / unfinished look | Display-sanitization guard in a separate PR; longer-term: cleanse source dataset | Yes for data; code fix can be separate |
| Metadata fragments in provider group fields: `STE 300`, `SHERMAN OAKS, CA`, `MICHAEL LIN Distance: < 1 mi.` | Medical provider search | dataset formatting issue | unfinished look | Strengthen parser or display filter | Yes for data; code fix can be separate |
| `Audit Test FMLA Client`, `TEST FMLA Client`, `TEST UR Client`, `PostGet Mismatch...` | FMLA / UR if still live | **not found in local repo or local DB** | possible live-only records | Verify directly in current production DB before any action | Yes |

---

## Detailed notes by surface

### Smart Daily

Evidence:
- `SmartDaily.jsx` loads from `/api/reminders/…` → `active_reminders`
- Local DB contains active rows: `AI fallback reminder test`, `Initial Assessment due for Test Client`, `Runtime manual reminder rt_*`, `AI runtime reminder rt_*`, `Follow up on housing application for Unknown Client`
- PR #75 already scopes Smart Summary to selected client — these won't bleed into a specific client's summary, but they still exist globally and show when no client is selected

Assessment:
- Data artifacts, not code leaks. Clean from DB.

### FMLA

Evidence:
- `FMLA.jsx` reads `/api/fmla` and `/api/fmla/{caseId}`
- Local `databases/fmla.db` inspected — no `test`/`QA`/`PostGet`/`mismatch` names found

Assessment:
- `Audit Test FMLA Client`, `TEST FMLA Client`, `PostGet Mismatch...` from the live symptom report were **not found locally**. May be production-only or already cleaned. Requires direct production verification before any delete plan.

### UR

Evidence:
- `UR.jsx` reads `/api/ur` and `/api/ur/{caseId}`
- Local `databases/ur.db` inspected — no `TEST UR Client` found locally

Assessment:
- Same as FMLA: production-only verification needed before any action.

### Medical provider records

Evidence:
- `Medical.jsx` → `/api/medical/providers` → `medi_cal_providers`
- Backend already has guard logic to prefer org labels, but source rows still contain malformed values
- Examples: `PHYSICIAN`, `PRACTITIONER`, `DISEASE PHYSICIAN`, `None Reported`, `FARSI`, `STE 300`, `MICHAEL LIN Distance: < 1 mi. Networks:`

Assessment:
- Dataset/import normalization problem. Not a frontend code leak.
- A display-sanitization PR is appropriate as a follow-up. Data cleanup of the source dataset is the permanent fix.

### Case Management / Client names

Evidence:
- `core_clients.db` has QA/test identities and `example.test` emails
- Mirrored in module DBs

Assessment:
- Highest-confidence manual cleanup targets. These appear everywhere a ClientSelector or client-driven route is rendered.

### Benefits

Evidence:
- `Benefits.jsx` → `/api/benefits/applications` (global when no client selected)
- Local `unified_platform.db.benefits_applications` contains `test-001`, `runtime benefits rt_*`, row with `notes="test"`

Assessment:
- These inflate dashboard metrics and appear in the unfiltered Benefits list.

---

## Recommended cleanup plan

### Phase 1: Verify production state

Before deleting anything, Brandon should confirm the exact current production rows for:

- Smart Daily reminders containing `test`, `runtime`, `ai fallback`, `unknown client`
- Client records with names `Test`, `Audit`, `AIFallback`, `Daylife`, or emails ending `@example.test`
- Benefits applications for `test-001` and `runtime benefits rt_*`
- Any live FMLA/UR rows matching `Audit Test FMLA Client`, `TEST FMLA Client`, `TEST UR Client`, `PostGet Mismatch...`

### Phase 2: Manual data cleanup (after Phase 1 confirms)

Delete or archive, record-by-record, with Brandon approval:

1. Remove orphan reminder rows whose `client_id` has no match in `core_clients`
2. Remove clearly named test reminder/task/contact rows
3. Remove `test-001` and `runtime benefits rt_*` benefit applications
4. Remove test client rows from `core_clients` and all mirrored module tables
5. Re-verify Smart Daily, Benefits, and ClientSelector in production

### Phase 3: Optional follow-up code PRs (not part of this audit)

- Display-sanitization guard for Medical provider generic/malformed labels
- Orphan-application filter for the unfiltered Benefits global list

---

## Safe conclusions

1. **No hardcoded test data leaks into production code paths.** All found test strings are behind correct guards (ImportError fallbacks, `__main__` blocks, dead routes, env+domain guards, unregistered routers, or test files).
2. **`Medical filter validation test` is a pytest fixture**, not a production source-code leak. It was a live DB record that surfaced via the unscoped Smart Summary (fixed by PR #75).
3. **`QA TestClient-Eval`** appears only in `tests/test_ai_documentation_service.py` — not in any production source.
4. **The medical-provider display problem is a dataset/import formatting issue**, not demo seed code.
5. **FMLA and UR suspect names were not found in local DBs.** Production-side verification is required before any action.
6. **The core production hygiene problem is DB-level data**, not source code. Smart Daily, Benefits, and all client-driven surfaces will look clean once QA/test DB rows are deleted after Brandon's approval.

---

## Code changes in this PR

**None.** This is an audit-only PR. No source files were modified.

The only file staged for commit is this report.
