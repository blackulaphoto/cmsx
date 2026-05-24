# CMSX — FMLA & Documentation Module Audit
**App URL:** https://cmsx-tau.vercel.app  
**Test Date:** May 24, 2026  
**Tester:** Automated QA via Claude (live browser, API-monitored)  
**Scope:** Two new modules — FMLA Tracker and Documentation Center

---

## OVERALL VERDICT

| Module | Status | Score | Summary |
|--------|--------|-------|---------|
| FMLA Tracker | INTEGRATED | **8 / 10** | Full CRUD works end-to-end. Sub-records (correspondence, docs, reminders) all persist. AI draft generates real clinical notes. Three bugs hold it back from production. |
| Documentation Center | SCAFFOLD | **4 / 10** | Template gallery, AI generation, and client linking all work. But neither Save Note nor Save Document fires any API call — nothing you write can be persisted. |

---

## FMLA TRACKER — DETAILED FINDINGS

### What Works (Verified with live API evidence)

**Full lifecycle is functional:**

- `GET /api/fmla?case_manager=cm_001 → 200` — Case list loads from real DB on mount
- `GET /api/fmla/summary?case_manager_id=cm_001 → 200` — Stat cards load real counts
- `POST /api/fmla → 200` — New case saves to DB, appears in list immediately
- `PUT /api/fmla/{uuid} → 200` — Edit/save updates existing case
- `POST /api/fmla/{uuid}/correspondence → 200` — Correspondence log persists
- `POST /api/fmla/{uuid}/documents → 200` — Paperwork checklist persists
- `POST /api/fmla/{uuid}/reminders → 200` — Reminders persist and show in list
- `POST /api/ai-documentation/note-draft → 200` — AI generates a real, structured clinical note (not a template — actual generated content with GOAL/INTERVENTION/RESPONSE/PLAN sections)

**Persistence confirmed:** Full page reload after creating a case, adding correspondence, adding a document entry, and creating a reminder — all four sub-records survived reload. This is the most complete, best-tested data persistence in the entire app.

**UI quality:** Excellent for a clinical tool. The right sidebar Case Summary updates dynamically, the MISSING ITEMS checklist accurately tracks what's incomplete, status dropdowns cover real workflow states, and the ROI tracking field is a detail most tools miss entirely.

**Search/filter:** Client name and employer search filters work client-side (URL updates, list filters correctly). No API calls needed for filtering.

---

### FMLA Bugs

---

**FMLA-BUG-001**  
**Title:** Edit form does not pre-populate saved text fields when loading existing case  
**Severity:** High  
**Steps:**
1. Create a new FMLA case with client name, employer name, HR contact
2. Reload the page
3. Click the case in the list to open it  

**Expected:** Form shows saved values in all fields  
**Actual:** Date fields (leave start date, expected return date) pre-populate correctly. All text inputs (client name, employer name, HR contact name, phone, email, provider name, etc.) are empty.  
**Evidence:** Direct inspection of input.value on all text inputs after loading a saved case — only date inputs had non-empty values.  
**Impact:** Case manager must re-enter all text data every session. Makes the edit form useless for reviewing saved records.  
**Fix:** On case load, read the fetched case JSON (`GET /api/fmla/{uuid}`) and set all form field values from the response. Match the React state initialization to the loaded data.

---

**FMLA-BUG-002**  
**Title:** "Apply Draft" button does not insert AI-generated text into Notes field  
**Severity:** Medium  
**Steps:**
1. Click "Draft Note" in AI Documentation Assist — AI generates a clinical note ✅
2. Click "Apply Draft"  

**Expected:** The generated note text is inserted into the Notes textarea in the main form  
**Actual:** Notes textarea remains empty (value length 0) after clicking Apply Draft  
**Evidence:** `document.querySelector('textarea').value` checked immediately after click — empty.  
**Note:** Apply Draft WORKS correctly in the Documentation module. The fix is to replicate that wiring in the FMLA component.  
**Fix:** Wire the Apply Draft handler in the FMLA component to write the generated draft string into the Notes textarea's React state, the same way it's implemented in the Documentation writer.

---

**FMLA-BUG-003**  
**Title:** "Create Task" button in AI suggested follow-up fires no API call  
**Severity:** Medium  
**Steps:**
1. Click "Draft Note" — AI generates note with a suggested follow-up task
2. Click "Create Task" on the suggested task  

**Expected:** Task created in the main task system  
**Actual:** Zero API calls. No confirmation. Button click is a no-op.  
**Evidence:** API monitor shows no calls after click.  
**Fix:** Wire the Create Task handler to `POST /api/reminders/tasks` or whatever the task creation endpoint is. Pass the suggested task text, priority, and due date from the AI response as the payload.

---

### FMLA Honorable Mentions (Not bugs, but worth noting)

- The case manager ID is hardcoded as `cm_001` in the URL parameter. When real auth is added, this must read from the authenticated user's ID or the module will always load the wrong caseload.
- The AI draft note doesn't incorporate the specific client's context (it generates a generic template, not one personalized to the actual client data in the form). Once client profiles are fully linked, the AI brief should include client name, age, presenting issue, and goals for more accurate output.
- The "Due In 7 Days" stat card correctly shows the count of cases with deadlines in the next 7 days. Accurate when cases have no deadline set.

---

## DOCUMENTATION CENTER — DETAILED FINDINGS

### What Works (Verified with live API evidence)

- `GET /api/dashboard/docs → 200` — Module loads and connects to backend
- `POST /api/ai-documentation/note-draft → 200` — AI generates a real structured clinical note from the case manager brief
- `POST /api/ai-documentation/compliance-review → 200` — Compliance review runs against current draft
- **9 templates** across 5 categories: Clinical, Planning, Letters, FMLA, Client Notes — all render correctly
- **Category filters** work client-side (Clinical shows only clinical templates, Planning shows only planning docs, etc.)
- **Template switching** — clicking a template updates the "Current Draft Context" panel, changing save target, template name, and note type
- **Client linking** — clicking "Select a client for this note" opens a real dropdown of all clients from the database. Selecting a client updates the URL, sets context, and shows "CLIENT LINKED: Yes"
- **Apply Draft** — after AI generates a note, clicking Apply Draft correctly populates the final draft editor textarea
- **AI draft quality** — the generated notes are genuine clinical templates with proper GOAL / INTERVENTION / RESPONSE / MEDICAL / PLAN structure, signed with a case manager credential line and today's date

---

### Documentation Bugs

---

**DOC-BUG-001**  
**Title:** "Generate Draft" button does not call AI — it only copies the brief text verbatim  
**Severity:** Critical  
**Steps:**
1. Type rough notes into "Case manager brief" textarea
2. Click "Generate Draft"  

**Expected:** AI processes the rough notes and generates a formatted clinical note in the Final Draft editor  
**Actual:** The brief text is copied word-for-word into the Final Draft textarea. No API call is made. No transformation occurs.  
**Evidence:** API monitor: zero calls after clicking Generate Draft. The Final Draft textarea value is identical to the brief input.  
**Impact:** This is the primary workflow button — the entire UI is designed around it. It being a copy-paste instead of AI generation makes the core feature broken. The AI DOES work (Draft Note button calls it successfully) — the Generate Draft button just isn't wired to it.  
**Fix:** Wire Generate Draft to call `POST /api/ai-documentation/note-draft` with the brief text and selected template as payload. On response, populate the Final Draft textarea with the generated content. This is already implemented for the Draft Note button in the AI assist section — consolidate them.

---

**DOC-BUG-002**  
**Title:** "Save Note" button fires no API call and shows no error  
**Severity:** Critical  
**Steps:**
1. Generate or type content in the Final Draft editor
2. Link a client (confirmed: Maria Santos linked successfully)
3. Click "Save Note"  

**Expected:** Note saved to client's record, CLIENT NOTES counter increments  
**Actual:** Zero API calls. No success toast. No error message. CLIENT NOTES counter stays at 0.  
**Evidence:** API monitor: no calls after click, with and without client linked.  
**Fix:** Implement save handler: `POST /api/clients/{clientId}/notes` with `{ title, content, type, template }` as payload. On 200, refresh the notes list and increment the CLIENT NOTES counter.

---

**DOC-BUG-003**  
**Title:** "Save Document" button fires no API call and shows no error  
**Severity:** Critical  
**Steps:**
1. Switch to Documents tab
2. Select a template, apply a draft
3. Click "Save Document"  

**Expected:** Document saved to the suite document library, DOCUMENTS counter increments  
**Actual:** Zero API calls. No feedback. DOCUMENTS counter stays at 0.  
**Evidence:** API monitor: no calls after click.  
**Fix:** Implement `POST /api/dashboard/docs` with document data. On 200, refresh "Saved Documents" list and increment counter. The `GET /api/dashboard/docs` endpoint already exists and returns 200 — this is purely a missing POST handler and frontend wiring.

---

**DOC-BUG-004**  
**Title:** "Create Task" button in AI suggested follow-up fires no API call  
**Severity:** Medium  
**Same as FMLA-BUG-003.** Identical issue in the Documentation module.  
**Fix:** Same fix — wire to task creation endpoint with AI-suggested task details.

---

### Documentation Honorable Mentions (Design observations)

- The two-button AI pattern (Generate Draft + Draft Note) is confusing. Case managers will not understand the difference. Consolidate into one "Generate with AI" button that does the right thing.
- The Compliance Review returns "Documentation review found no obvious missing sections" even with an empty brief and no client context. That response is meaningless and could give false confidence. The review should flag what's missing (client ID, date of service, supervisor signature, etc.).
- The "Saved Notes" section at the bottom says "Select a client first" — the prompt to pick a client happens too late in the workflow. If you're writing a note you'll almost always know who it's for. Require client selection upfront before the brief/draft fields are enabled.
- The Documentation module does NOT call a notes-specific API on load — it hits `GET /api/dashboard/docs` which is the Dashboard's generic document endpoint. It should have its own endpoint (e.g., `/api/notes` or `/api/documentation`) that returns paginated note history with filters.

---

## SIDE-BY-SIDE COMPARISON

| Feature | FMLA | Documentation |
|---------|------|---------------|
| Loads from real API | ✅ | ✅ |
| Create new record | ✅ POST → 200 | ❌ No API call |
| Edit/update record | ✅ PUT → 200 | ❌ Not applicable |
| Sub-records (correspondence, docs, reminders) | ✅ All 3 persist | ❌ N/A |
| AI generation | ✅ Real clinical note | ✅ Real clinical note |
| Apply AI draft | ❌ Broken | ✅ Works |
| Client linking | ✅ Real client list | ✅ Real client list |
| Search/filter | ✅ Works | ✅ Category filter works |
| Persistence after reload | ✅ Confirmed | ❌ Nothing saves |
| Template system | N/A | ✅ 9 templates, filtering works |
| Stats/counters update | ✅ Accurate | ❌ Stay at 0 |

---

## PRIORITY FIX ORDER

**Fix today (blocks all real use):**

1. **DOC-BUG-001** — Wire Generate Draft to the AI endpoint. This is the headline feature of Documentation. It already works in the Draft Note button — just redirect it.
2. **DOC-BUG-002** — Wire Save Note to `POST /api/clients/{id}/notes`. Without this, Documentation is 100% decorative.
3. **DOC-BUG-003** — Wire Save Document to `POST /api/dashboard/docs`. Same issue, same fix pattern.

**Fix this sprint:**

4. **FMLA-BUG-001** — Pre-populate form fields on case load. The data is already being fetched (`GET /api/fmla/{uuid} → 200`) — just read it into form state on mount.
5. **FMLA-BUG-002** — Wire Apply Draft in the FMLA component to populate the Notes field. Copy the working implementation from Documentation.
6. **FMLA-BUG-003 / DOC-BUG-004** — Wire Create Task button. One fix, two modules.

**Estimated total effort:** 12–18 hours for all 6 fixes. The FMLA module is genuinely close to production-ready. Documentation needs 3 critical wiring fixes but the infrastructure (templates, AI, client linking) is solid.

---

## UPDATED APP SCORES

| Module | Previous Score | New Score | Delta |
|--------|---------------|-----------|-------|
| FMLA Tracker | (new) | **8 / 10** | — |
| Documentation Center | (new) | **4 / 10** | — |
| **App Overall** | **5 / 10** | **6 / 10** | +1 |

The FMLA module is the strongest piece of engineering in the entire app. If it gets the 3 bug fixes above, it's production-ready. Documentation has the right skeleton but needs its save path wired before it's useful to anyone.

---

*All API calls verified live via injected network monitor. All UI behaviors verified via direct DOM inspection and form interaction. Zero assumptions made without evidence.*
