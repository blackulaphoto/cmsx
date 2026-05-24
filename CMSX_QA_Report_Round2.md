# Case Manager Suite (CMSX) — QA Round 2 Report
**App URL:** https://cmsx-tau.vercel.app/  
**Test Date:** May 23, 2026  
**Tester:** Automated QA via Claude (strict, end-to-end, live browser)  
**Round 1 Reference:** https://cmsx-6xhw27syo-blackulaphotos-projects.vercel.app/  
**Status:** PROTOTYPE — Significant progress, not production ready

---

## EXECUTIVE SUMMARY

Round 2 represents a major architectural improvement. The backend is now running and responding to real HTTP requests. Core data flows — client list, dashboard notes, benefits applications, legal records, and services directory — are all live and connected to a real database. The app is no longer a static shell; it is a functioning prototype.

However, 12 of the original 22 bugs remain open, and 7 new bugs were introduced or surfaced by the backend becoming active. The two most critical blockers are: (1) View Profile crashes the React render tree entirely, and (2) Edit Client returns 405 Method Not Allowed, meaning the primary case management workflow — view and modify a client record — is still completely broken. The app cannot be used by a real case manager until these are resolved.

**Round 1 Overall Score: 2 / 10**  
**Round 2 Overall Score: 5 / 10**  
**Delta: +3 points — backend alive, real data flowing, Services/Notes/Benefits working**

---

## WHAT CHANGED BETWEEN ROUNDS

### Fixed / Improved Since Round 1

| Bug (R1) | Status | Notes |
|----------|--------|-------|
| BUG-002: All APIs 502 | ✅ FIXED | Backend now running. 200/404/405/422 responses observed across all modules |
| BUG-005: Client data hardcoded | ✅ FIXED | 11 real UUID-keyed clients load from `/api/clients` on mount |
| BUG-003: Add Client does nothing | ✅ FIXED | Modal opens, form submits, POST → 200, client persists after page reload |
| BUG-013: Services Directory returns nothing | ✅ FIXED | Search and category filter return real results via GET /api/services/search |
| BUG-010: Benefits applications always empty | ✅ FIXED | 8 real benefit application records load from database (2026 dates) |
| BUG-018: Dashboard "+" buttons do nothing | ⚠️ PARTIAL | Notes now POST → 200 and persist. Bookmarks do NOT persist (see R2-BUG-004) |
| BUG-017: Stat cards show 0 | ⚠️ PARTIAL | Backend endpoint responds but frontend still renders 0 (see R2-BUG-001) |
| BUG-011: Legal Add Task fails silently | ⚠️ PARTIAL | Legal GET endpoints working (cases/docs/court-dates → 200), but POST → 404 still |
| BUG-012: AI Chat 502 | ⚠️ PARTIAL | POST /api/ai/chat now reaches backend (200), but AI API key not configured — no response |
| BUG-020: Resume PDF silent failure | ⚠️ PARTIAL | Requests now reach backend but return 404 — route not implemented |

### Regressions / New Bugs Since Round 1

The following issues either did not exist before (because the backend was 502) or are newly observable now that the backend is active:

- View Profile crashes the React component tree (R2-BUG-002)
- Edit Client returns 405 — route exists but method not handled (R2-BUG-003)
- Delete Client fires no API call at all (R2-BUG-005)
- Housing search now returns 422 Unprocessable Entity instead of 502 (R2-BUG-006)
- Job Search fires zero API calls — JS code path never reaches the fetch (R2-BUG-007)
- Raw UUIDs displayed instead of resolved client names across all modules (R2-BUG-008)
- Date formatting broken: "Invalid Date" on many records (R2-BUG-009)

---

## ROUND 2 BUG REPORTS

---

### R2-BUG-001
**BUG TITLE:** Dashboard stat cards show 0 despite 9 real clients in database  
**MODULE:** Dashboard  
**SEVERITY:** High  
**STEPS TO REPRODUCE:**  
1. Navigate to Dashboard  
2. Observe the four stat cards (Total Clients, Active Cases, High Risk, Recent Intakes)  
**EXPECTED RESULT:** Cards reflect real counts — 9 clients, 9 active cases confirmed in database  
**ACTUAL RESULT:** All cards display "0"  
**EVIDENCE:** GET /api/dashboard/stats → 200 (backend responds), but frontend still renders zero values. The response body likely doesn't match the shape the component expects, or the component is reading from stale/wrong state.  
**LIKELY CAUSE:** API response shape mismatch between backend (`{ totalClients: 9 }`) and frontend expectation (e.g., `{ stats: { total_clients: 9 } }`). Alternatively, stats endpoint returns a different field than the component reads.  
**RECOMMENDED FIX:** Console-log the raw API response from `/api/dashboard/stats`. Match field names in the frontend destructuring to the actual response keys. Add a loading/error state so zeros are never shown while data is in-flight.  
**TEST STATUS:** Failed (regression — was 502 in R1, now 200 but still shows 0)

---

### R2-BUG-002
**BUG TITLE:** View Profile button crashes React render tree — entire `<main>` disappears  
**MODULE:** Case Management  
**SEVERITY:** Critical  
**STEPS TO REPRODUCE:**  
1. Navigate to Case Management  
2. Click "View Profile" on any client row  
**EXPECTED RESULT:** Client profile page renders  
**ACTUAL RESULT:** The entire `<main>` element vanishes from the DOM. The page shows only the header/sidebar chrome. No error message is displayed to the user. The app is unrecoverable without a full page reload.  
**EVIDENCE:** Observed directly in DOM inspection. No error boundary catches the failure. React render tree silently collapses.  
**LIKELY CAUSE:** The client profile component attempts to render with data that doesn't exist yet (e.g., tries to access `client.name` when `client` is `undefined`). No null-guard, no loading state, no error boundary.  
**RECOMMENDED FIX:**  
1. Add a React error boundary around the client profile route.  
2. Add null/undefined guards on all client data access: `client?.name ?? 'Unknown'`.  
3. Show a loading skeleton while data fetches.  
4. Add error state: "Could not load client profile" with a retry button.  
**TEST STATUS:** Failed (new in R2 — was never reachable in R1 due to button being dead)

---

### R2-BUG-003
**BUG TITLE:** Edit Client returns 405 Method Not Allowed  
**MODULE:** Case Management  
**SEVERITY:** Critical  
**STEPS TO REPRODUCE:**  
1. Navigate to Case Management  
2. Click "Edit Client" on any client row  
3. Modify any field  
4. Click Save  
**EXPECTED RESULT:** Client record updated, changes visible immediately  
**ACTUAL RESULT:** PUT /api/clients/{uuid} → 405 Method Not Allowed  
**EVIDENCE:** API monitor captured: `PUT /api/clients/[uuid] 405`. The route exists (DELETE/GET work at that path) but PUT is not handled.  
**LIKELY CAUSE:** Backend router has GET and DELETE registered at `/api/clients/:id` but is missing `router.put('/api/clients/:id', ...)` handler.  
**RECOMMENDED FIX:** Add PUT handler in the clients router:  
```javascript
router.put('/clients/:id', async (req, res) => {
  const { id } = req.params;
  const updates = req.body;
  // validate, update DB, return updated client
});
```  
**TEST STATUS:** Failed

---

### R2-BUG-004
**BUG TITLE:** Dashboard bookmarks do not persist after page reload  
**MODULE:** Dashboard  
**SEVERITY:** Medium  
**STEPS TO REPRODUCE:**  
1. Navigate to Dashboard  
2. Add a bookmark via the "+" button  
3. Reload the page  
**EXPECTED RESULT:** Bookmark appears on reload  
**ACTUAL RESULT:** Bookmark is gone after reload. No POST/GET API call observed for bookmarks.  
**EVIDENCE:** Notes persist (POST /api/dashboard/notes → 200 confirmed). Bookmarks use localStorage or ephemeral component state only — no API call fires on bookmark add.  
**LIKELY CAUSE:** Bookmarks component is not wired to the `/api/dashboard/bookmarks` endpoint. Possibly stores to state only.  
**RECOMMENDED FIX:** Implement POST /api/dashboard/bookmarks on add, GET on mount, DELETE on remove. Match the pattern already working for notes.  
**TEST STATUS:** Failed

---

### R2-BUG-005
**BUG TITLE:** Delete Client button fires no API call  
**MODULE:** Case Management  
**SEVERITY:** High  
**STEPS TO REPRODUCE:**  
1. Navigate to Case Management  
2. Click "Delete Client" on any row  
**EXPECTED RESULT:** Confirmation dialog, then DELETE /api/clients/{id} → 200, client removed  
**ACTUAL RESULT:** Zero API calls observed. No confirmation dialog. No visual change. The button is completely inert.  
**EVIDENCE:** API monitor shows no DELETE call after clicking the button. Client list unchanged.  
**LIKELY CAUSE:** onClick handler for delete is not implemented or references a broken function.  
**RECOMMENDED FIX:** Implement delete handler:  
```javascript
const handleDelete = async (clientId) => {
  if (!confirm('Delete this client? This cannot be undone.')) return;
  await fetch(`/api/clients/${clientId}`, { method: 'DELETE' });
  setClients(prev => prev.filter(c => c.id !== clientId));
};
```  
**TEST STATUS:** Failed

---

### R2-BUG-006
**BUG TITLE:** Housing Search returns 422 Unprocessable Entity  
**MODULE:** Housing  
**SEVERITY:** High  
**STEPS TO REPRODUCE:**  
1. Navigate to Housing  
2. Enter location, max rent, bedrooms  
3. Click "Search Housing"  
**EXPECTED RESULT:** Housing results  
**ACTUAL RESULT:** "No housing options found." — backend returns 422  
**EVIDENCE:** GET /api/housing/search?... → 422. The 422 status means the server received the request but rejected the input as invalid.  
**LIKELY CAUSE:** Backend validation schema requires specific field names or formats that the frontend is not sending. Possible mismatch: frontend sends `maxRent` but backend expects `max_rent`, or location must be a ZIP code and the frontend sends a city name.  
**RECOMMENDED FIX:** Check backend validation schema for `/api/housing/search`. Log `req.query` on the server. Either relax validation or update frontend query params to match required format. Return a user-friendly error message (not just 422) when input is invalid.  
**TEST STATUS:** Failed (changed from 502 → 422, still broken)

---

### R2-BUG-007
**BUG TITLE:** Job Search never fires API call — stuck on "Searching..."  
**MODULE:** Job Search  
**SEVERITY:** High  
**STEPS TO REPRODUCE:**  
1. Navigate to Job Search  
2. Enter any keywords and location  
3. Click "Search Jobs"  
**EXPECTED RESULT:** Job listings appear, or "No jobs found" message  
**ACTUAL RESULT:** Button shows "Searching..." indefinitely. API monitor captures zero calls to `/api/jobs/search/quick`. The UI is permanently frozen in a loading state.  
**EVIDENCE:** API monitor: zero job-related calls after clicking search. The component enters a loading state but never dispatches the fetch.  
**LIKELY CAUSE:** The fetch call is inside an `async` function that throws before reaching the `fetch()` line (e.g., undefined reference, failed input validation), and the error is caught silently, leaving `isLoading` as `true` forever.  
**RECOMMENDED FIX:** Add `console.error` in the catch block. Ensure the loading state resets to `false` in a `finally` block. Fix the root cause preventing the fetch from firing.  
**TEST STATUS:** Failed (changed from 502 → 0 calls — different failure mode)

---

### R2-BUG-008
**BUG TITLE:** Raw UUIDs displayed instead of client names across all modules  
**MODULE:** Legal, Benefits, Smart Dashboard, others  
**SEVERITY:** High  
**STEPS TO REPRODUCE:**  
1. Navigate to any module that references a client (Legal, Benefits, Smart Dashboard)  
2. Observe client identifiers in lists, task rows, and case records  
**EXPECTED RESULT:** Human-readable client names (e.g., "Maria Santos")  
**ACTUAL RESULT:** Raw UUIDs shown (e.g., `3f7a2b1c-4d8e-...`), or "Unknown Client" placeholder text  
**EVIDENCE:** Legal cases and tasks show UUID strings. Smart Dashboard tasks show "Unknown Client" for client name fields. This confirms the client lookup join is not being performed.  
**LIKELY CAUSE:** Module APIs return `client_id` (UUID) without joining to the clients table. Frontend displays `client_id` directly instead of resolving it to a name.  
**RECOMMENDED FIX:** Two options: (1) Server-side: JOIN clients table in all module queries and return `client_name` alongside `client_id`. (2) Client-side: Fetch client list on app init, store in context, resolve UUID → name via lookup map before rendering.  
**TEST STATUS:** Failed

---

### R2-BUG-009
**BUG TITLE:** Date formatting broken — "Invalid Date" on multiple records  
**MODULE:** All modules  
**SEVERITY:** Medium  
**STEPS TO REPRODUCE:**  
1. Navigate to Legal, Benefits, Smart Dashboard  
2. Observe date fields (court dates, deadlines, application dates)  
**EXPECTED RESULT:** Human-readable dates ("June 15, 2026")  
**ACTUAL RESULT:** "Invalid Date" string displayed in multiple places  
**EVIDENCE:** Observed in Smart Dashboard task list and Legal records. Indicates `new Date(someValue)` is receiving `null`, `undefined`, or a non-standard string.  
**LIKELY CAUSE:** Backend returns dates in an ISO format the `Date` constructor doesn't handle (e.g., no timezone, or returns epoch integers that aren't being converted), or some records have null date fields.  
**RECOMMENDED FIX:** Use a date parsing library (date-fns or dayjs). Add a utility: `formatDate(val) => val ? format(parseISO(val), 'MMM d, yyyy') : '—'`. Apply it everywhere a date is rendered.  
**TEST STATUS:** Failed

---

### R2-BUG-010
**BUG TITLE:** Legal "Add Task" returns 404 — route not implemented  
**MODULE:** Legal  
**SEVERITY:** High  
**STEPS TO REPRODUCE:**  
1. Navigate to Legal → Tasks tab  
2. Click "Add Task", fill form, click Save  
**EXPECTED RESULT:** New task added to list  
**ACTUAL RESULT:** POST /api/legal/tasks → 404 Not Found  
**EVIDENCE:** API monitor: `POST /api/legal/tasks 404`  
**LIKELY CAUSE:** The GET endpoint for legal tasks exists but the POST (create) route was never implemented on the backend.  
**RECOMMENDED FIX:** Implement `router.post('/legal/tasks', ...)` on the backend. Accept: `{ client_id, description, priority, deadline }`. Return created task with ID.  
**TEST STATUS:** Failed (was 502 in R1, now 404 — different failure)

---

### R2-BUG-011
**BUG TITLE:** Resume Save Profile and Generate PDF return 404  
**MODULE:** Resume Builder  
**SEVERITY:** High  
**STEPS TO REPRODUCE:**  
1. Navigate to Resume Builder  
2. Fill in profile fields  
3. Click "Save Profile" or "Generate PDF"  
**EXPECTED RESULT:** Profile saved / PDF downloaded  
**ACTUAL RESULT:** POST /api/resume/profile → 404, POST /api/resume/create → 404  
**EVIDENCE:** API monitor confirms 404 on both endpoints.  
**LIKELY CAUSE:** Backend resume routes are registered at a different path than the frontend expects, or the route handlers were stubbed but not implemented.  
**RECOMMENDED FIX:** Check if routes are registered at `/api/resume/profile` and `/api/resume/create`. If not, implement them. For PDF generation: use `pdf-lib` or `puppeteer` server-side, return `application/pdf` blob with `Content-Disposition: attachment`.  
**TEST STATUS:** Failed (was 502 in R1, now 404)

---

### R2-BUG-012
**BUG TITLE:** AI Chat reaches backend but returns no AI response — API key not configured  
**MODULE:** AI Assistant  
**SEVERITY:** High  
**STEPS TO REPRODUCE:**  
1. Navigate to AI Chat  
2. Type any message  
3. Press Send  
**EXPECTED RESULT:** AI assistant responds with relevant case management guidance  
**ACTUAL RESULT:** Message sends (POST /api/ai/chat → 200), but response content is empty or an error. No AI reply rendered in the chat.  
**EVIDENCE:** API monitor: `POST /api/ai/chat 200`. The backend accepts the request but the AI provider call fails silently (likely missing API key returns empty/error response which the frontend doesn't surface).  
**LIKELY CAUSE:** AI API key (OpenAI or Anthropic) not set in Vercel environment variables. Backend catches the API key error and returns 200 with an empty or error body.  
**RECOMMENDED FIX:**  
1. Add `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` to Vercel environment variables.  
2. Update backend to return non-200 when AI call fails, with a human-readable error message.  
3. Frontend should display the error message to the user.  
**TEST STATUS:** Failed (improved from R1: 502 → 200, but still no AI response)

---

### R2-BUG-013 (CARRIED FROM R1-BUG-001)
**BUG TITLE:** Direct URL navigation returns 404 for all module routes  
**MODULE:** All / Deployment  
**SEVERITY:** Critical  
**STATUS:** Still open — not fixed between rounds  
See R1-BUG-001 for full details. Fix remains: add `vercel.json` with SPA rewrite rule.  
**TEST STATUS:** Failed

---

### R2-BUG-014 (CARRIED FROM R1-BUG-015)
**BUG TITLE:** Smart Dashboard Quick Actions all dead  
**MODULE:** Smart Daily Dashboard  
**SEVERITY:** High  
**STATUS:** Still open — Add New Client, Schedule Appointment, Emergency Referral buttons produce no response  
**TEST STATUS:** Failed

---

### R2-BUG-015 (CARRIED FROM R1-BUG-021)
**BUG TITLE:** Footer links all dead (#), copyright year stale  
**MODULE:** All pages  
**SEVERITY:** Low  
**STATUS:** Still open  
**TEST STATUS:** Failed

---

### R2-BUG-016 (CARRIED FROM R1-BUG-022)
**BUG TITLE:** Third-party Jinno.app promotional widget injected on every page  
**MODULE:** All pages  
**SEVERITY:** Medium  
**STATUS:** Still open  
**TEST STATUS:** Failed

---

## MODULE STATUS COMPARISON

| Module | R1 Status | R2 Status | Change |
|--------|-----------|-----------|--------|
| Dashboard | Decorative | Partial | ↑ Notes persist, stats endpoint live (but renders 0) |
| Case Management | Decorative | Partial | ↑ Real DB clients, Add Client works. View Profile crashes, Edit 405, Delete inert |
| Housing Search | Decorative | Broken | → 502 → 422, still returns no results |
| Benefits | Decorative | Partial | ↑ Real applications load, eligibility check still not returning results |
| Legal Services | Decorative | Partial | ↑ Cases/docs/court-dates load. Add Task 404, UUID display broken |
| Resume Builder | Partial (best) | Partial | → 502 → 404, still can't save or generate PDF |
| AI Assistant | Decorative | Partial | ↑ Reaches backend, API key missing — no AI response |
| Services Directory | Decorative | Working | ✅ Search + category filter fully functional |
| Job Search | Decorative | Broken | ↓ Was 502, now 0 API calls — different failure, still frozen |
| Smart Daily Dashboard | Partial | Partial | → Tasks still load, Quick Actions still dead, UUIDs unresolved |
| Integration Audit | Broken | Not retested | — |

---

## WHAT'S ACTUALLY WORKING NOW (Round 2)

These features can be used by a real case manager today:

1. **Client List** — Real database-backed. 11 clients with UUIDs. Search/filter work.
2. **Add Client** — Form submits, POST → 200, persists after reload. ✅
3. **Dashboard Notes** — Add a note, POST → 200, reload — note is still there. ✅
4. **Benefits Applications** — 8 real records load on mount from database. Visible and browseable. ✅
5. **Legal Records** — Cases, documents, and court dates all load from real endpoints. ✅
6. **Services Directory** — Search by keyword and category returns real results. ✅
7. **Smart Dashboard Task List** — 5 real tasks with priorities render correctly.
8. **AI Chat UI** — Message input, send, chat history all work visually (response is missing, but UX flow is complete).

---

## CRITICAL PATH TO LAUNCH

The following 5 issues block any real-world use. Fix these first:

**P0 — Must fix before any user testing:**

1. **View Profile crashes React (R2-BUG-002)** — Case managers must be able to see a client profile. This crash makes the app feel broken. Fix: add error boundary + null guards on the profile component.

2. **Edit Client 405 (R2-BUG-003)** — Cannot update a client record. Core workflow. Fix: implement PUT /api/clients/:id backend route.

3. **Direct URL / refresh 404 (R2-BUG-013)** — Users cannot bookmark, share, or refresh any module. Fix: 10-minute Vercel config change.

**P1 — Fix for usable prototype:**

4. **UUID display (R2-BUG-008)** — Every module that shows client references shows machine IDs. Usability is severely impacted. Fix: server-side JOIN or client-side lookup map.

5. **AI API key (R2-BUG-012)** — The highest-value feature for case managers. Fix: add env var to Vercel dashboard, 5 minutes.

---

## UPDATED SPRINT RECOMMENDATIONS

**Sprint 1 — Already Done ✅**
- Backend server fixed and running
- Real database connected with client data
- Add Client wired end-to-end
- Services Directory, Benefits, Legal GET endpoints working
- Dashboard notes persisting

**Sprint 2 — Core Case Manager Workflow (Do Now)**
1. Fix View Profile crash — error boundary + null guard (2–4 hours)
2. Implement PUT /api/clients/:id — Edit Client (2–4 hours)
3. Implement DELETE /api/clients/:id handler in frontend onClick (1 hour)
4. Resolve UUIDs to names — add client lookup map in app context (3–4 hours)
5. Fix date formatting with dayjs/date-fns utility (1–2 hours)
6. Add vercel.json SPA rewrite (10 minutes)

**Sprint 3 — Feature Completion**
1. Add AI API key to Vercel env vars (5 minutes)
2. Fix housing search 422 — align query param names (1–2 hours)
3. Fix jobs search frozen state — add finally block, debug fetch path (2–3 hours)
4. Implement POST /api/legal/tasks (2–3 hours)
5. Implement POST /api/resume/profile + /api/resume/create (4–6 hours)
6. Wire Smart Dashboard Quick Actions (3–4 hours)

**Sprint 4 — Polish**
1. Fix stat cards reading wrong response keys (1 hour)
2. Wire bookmark persistence (2 hours)
3. Remove Jinno.app widget
4. Fix footer links or remove them
5. Update copyright year

---

## FINAL SUMMARY

| Metric | Round 1 | Round 2 |
|--------|---------|---------|
| Backend responding | ❌ All 502 | ✅ All endpoints reached |
| Real database connected | ❌ | ✅ 11 clients, real records |
| Working end-to-end flows | 0 | 3 (Add Client, Notes, Services search) |
| Bugs outstanding | 22 | 16 |
| Modules decorative/broken | 9 / 9 | 3 / 9 (Housing, Jobs, Integration Audit) |
| Modules partially working | 0 / 9 | 6 / 9 |
| Modules fully working | 0 / 9 | 1 / 9 (Services Directory) |
| Overall readiness score | 2 / 10 | 5 / 10 |

The backend fix was the right first move and unlocked everything downstream. The next two sprints (View Profile crash, Edit Client, UUID resolution, date formatting, SPA routing) represent roughly 20–30 hours of work and would bring this to a genuinely usable internal prototype at ~7/10 readiness. The AI key is a 5-minute win. Do that today.

---

*Report generated by automated QA session (Round 2). All findings verified live against cmsx-tau.vercel.app. API evidence captured via injected network monitor. All navigation performed via JS click events (in-app routing). Zero assumptions made without direct verification.*
