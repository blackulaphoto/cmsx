# TASK / REMINDER / AI Pipeline Evaluation

## 1. Executive Summary

Current diagnosis:

- Smart Daily already has a backend truth source: the reminders repository `get_prioritized_tasks(...)` path merges `intelligent_tasks`, `active_reminders`, and workspace `client_tasks`.
- Client Dashboard was historically split away from that source and read only workspace `client_tasks` through `/api/case-management/tasks/*`.
- The current `master` branch includes a frontend-side merge in `frontend/src/pages/ClientDashboard.jsx` so the dashboard now shows reminders and intelligent tasks alongside workspace tasks, but that is still not a canonical backend service.
- AI context is still incomplete:
  - Full-page `AIChat` sends `client_id` and `client_name` when the user selects a client.
  - Popup assistant `frontend/src/components/AIAssistant/AIAssistantPopup.jsx` sends no client context at all.
  - Backend selected-client task injection in `backend/modules/ai_unified/unified_routes.py` only runs when `client_id` is already provided.
  - There is no pre-response backend resolution of a uniquely named client from a message like "What overdue reminders/tasks do I have for John Collins?"
- Local data cannot prove the reported "John Collins" reminder set:
  - Local `core_clients.db` contains `John Smith`, not `John Collins`.
  - Local `active_reminders` includes multiple runtime/test-looking rows and several orphaned `client_id` values with no matching core client.
  - Local `intelligent_tasks` rows are real persisted rows for `Maria Santos`.

Bottom line:

- The split-store problem is real.
- Smart Daily is closest to the actual truth.
- Client Dashboard was patched at the UI layer, not yet unified at the backend layer.
- AI still does not have a truthful canonical client work-items source unless a selected `client_id` is already supplied.

## 2. Current Architecture

```text
Smart Daily create task/reminder
  -> POST /api/reminders/create
  -> active_reminders

Smart Daily start process
  -> POST /api/reminders/start-process
  -> intelligent_tasks

Client Dashboard create task
  -> POST /api/case-management/tasks/add/{client_id}
  -> workspace_content.db : client_tasks

Treatment plan approval / operational task generation
  -> workspace_store.create_tasks_from_operational_needs(...)
  -> workspace_content.db : client_tasks

Smart Daily read
  -> GET /api/reminders/prioritized/{case_manager_id}
  -> reminders.repository.get_prioritized_tasks(...)
  -> intelligent_tasks + active_reminders + workspace client_tasks

Client Dashboard read (current master)
  -> GET /api/case-management/tasks/list/{client_id}
  -> GET /api/clients/{client_id}/intelligent-tasks
  -> GET /api/clients/{client_id}/unified-view
  -> frontend merge only

AI read (current master)
  -> POST /api/ai/chat or /api/ai/assistant
  -> selected-client context only if request already includes client_id
  -> reminders.repository.get_prioritized_tasks(...)
  -> filtered in-memory to one client
```

## 3. Task/Reminder Stores

| Store/table | DB/source | What it contains | Client linkage | Case manager linkage | Due date | Status | Used by Smart Daily | Used by Client Dashboard | Used by AI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `active_reminders` | `databases/reminders.db` or Postgres `railway_active_reminders` | Manual reminders | Yes | Yes | Yes | Yes | Yes | Yes, through `unified-view` reminders slice and reminder edit APIs | Yes, but only when selected client context is built |
| `intelligent_tasks` | `databases/reminders.db` or Postgres `railway_intelligent_tasks` | Smart Daily / process-generated tasks | Yes | Yes | Yes | Yes | Yes | Yes, through `/api/clients/{client_id}/intelligent-tasks` | Yes, but only when selected client context is built |
| `client_tasks` | `databases/workspace_content.db` | Workspace/case-management/treatment-plan tasks | Yes | Indirect via client ownership | Optional | Yes | Yes | Yes, via `useTasks` and current dashboard merge | Yes, because Smart Daily repository merge includes workspace tasks |
| `tasks` | `databases/case_management.db` | Older case-management task rows used by `ClientDataIntegrator` | Yes | Likely | Yes | Yes | No | Present in `unified-view.client_data.tasks`, but current dashboard merge does not rely on them | No |
| `client_operational_needs` | `databases/workspace_content.db` | Needs records, not direct tasks | Yes | Indirect | No | Yes | Indirect only via generated workspace tasks | Indirect only | No direct AI task injection |

## 4. Creation Endpoints

| Endpoint | Creates what | Writes to store | Requires selected client | Uses client name or internal ID | Used by which UI |
| --- | --- | --- | --- | --- | --- |
| `POST /api/reminders/create` | Active reminder | `active_reminders` | Yes | Internal `client_id` | Smart Daily and several module reminder shortcuts |
| `POST /api/reminders/start-process` | Intelligent tasks batch | `intelligent_tasks` | Yes | Internal `client_id` | Smart Daily process actions |
| `POST /api/case-management/tasks/add/{client_id}` | Workspace client task | `client_tasks` | Yes | Internal `client_id` in route | Client Dashboard task form |
| `POST /api/clients/{client_id}/operational-tasks/generate` | Generated operational tasks | `client_tasks` | Yes | Internal `client_id` | Operational/treatment-plan flows |
| Treatment plan approval path in `backend/api/clients.py` | Generated treatment-plan tasks | `client_tasks` | Yes | Internal `client_id` | Treatment plan approval workflow |
| `UnifiedAIService.create_reminder(...)` | Active reminder | `active_reminders` via direct SQLite insert | Optional from tool-call args | Internal `client_id` | AI tool/function path |

## 5. Read/List Endpoints

| Endpoint | Reads from store(s) | Selected-client filter | Case-manager filter | Overdue filter | Used by Smart Daily | Used by Dashboard | Used by AI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `GET /api/reminders/prioritized/{case_manager_id}` | `intelligent_tasks` + `active_reminders` + workspace `client_tasks` | Indirect, frontend filters rows | Yes | Yes, by bucket | Yes | No direct backend consumption | Yes |
| `GET /api/reminders/smart-dashboard/{case_manager_id}` | Smart dashboard integrator, mostly `intelligent_tasks` dashboard data | No | Yes | Summary only | Yes | No | No |
| `GET /api/case-management/tasks/list/{client_id}` | workspace `client_tasks` | Yes | Indirect | No | No | Yes | No |
| `GET /api/clients/{client_id}/intelligent-tasks` | `intelligent_tasks` | Yes | Indirect | No | No | Yes | No direct path |
| `GET /api/clients/{client_id}/unified-view` | `case_management.db` tasks + `active_reminders` + other module data | Yes | Indirect | No explicit overdue slice | No | Yes | No |
| `POST /api/ai/chat` | selected-client task context from prioritized repository only when `client_id` exists | Yes, only if request supplies it | Auth-bound | Overdue bucket only in injected context | No | No | Yes |
| `POST /api/ai/assistant` | same as above plus popup platform guide | Yes, only if request supplies it | Auth-bound | Overdue bucket only in injected context | No | No | Yes |

## 6. Surface Trace

### Smart Daily

- Frontend: `frontend/src/pages/SmartDaily.jsx`
- Reads:
  - `GET /api/reminders/prioritized/{case_manager_id}`
  - `GET /api/reminders/smart-dashboard/{case_manager_id}`
- Backend truth source:
  - `backend/modules/reminders/routes.py`
  - `backend/modules/reminders/repository.py:get_prioritized_tasks`
- Real source of truth today:
  - `intelligent_tasks`
  - `active_reminders`
  - workspace `client_tasks`
- Merge logic:
  - intelligent tasks are loaded first
  - workspace tasks are added by `list_workspace_tasks_for_case_manager(...)`
  - active reminders are appended and normalized into task-like objects
  - items are bucketed into `overdue`, `today`, `next_3_days`, `this_week`, `treatment_plan`, `high_priority_no_date`, `later`

### Client Dashboard Tasks

- Frontend: `frontend/src/pages/ClientDashboard.jsx`
- Legacy hook: `frontend/src/hooks/useTasks.js`
- Current master behavior:
  - workspace tasks from `/api/case-management/tasks/list/{client_id}`
  - intelligent tasks from `/api/clients/{client_id}/intelligent-tasks`
  - reminders from `/api/clients/{client_id}/unified-view`
  - merged on the frontend only
- Why Smart Daily can show overdue items while Dashboard shows none:
  - the original dashboard only read workspace `client_tasks`
  - Smart Daily reads the merged reminders repository path
  - overdue active reminders and intelligent tasks never reached the dashboard until the current frontend merge

### AI Assistant

Assistant surfaces discovered:

| Frontend component | Route/location | Backend endpoint | Sends selected client? | Production notes |
| --- | --- | --- | --- | --- |
| `frontend/src/pages/AIChat.jsx` | `/ai-chat` | `POST /api/ai/chat` | Yes, via selector or `?client=` query | Explicit client-aware page |
| `frontend/src/components/AIAssistant/AIAssistantPopup.jsx` | mounted globally in `App.jsx` | `POST /api/ai/assistant` | No | Most likely the always-available assistant surface |

Backend trace:

- `backend/modules/ai_unified/unified_routes.py`
- `_build_selected_client_task_context(...)`:
  - only runs when `client_id` is present
  - calls `get_prioritized_tasks(case_manager_id, org_id=...)`
  - filters buckets to the supplied `client_id`
  - injects overdue/today/next-3-days lines into the prompt context

Answer:

- Is the live assistant receiving actual overdue work-item facts before the model responds?
  - `AIChat`: yes, but only when the request already includes a selected `client_id`
  - Popup assistant: usually no, because it sends no client context
  - Typed-name-only question: no guaranteed pre-response grounding path exists today

## 7. Fallback / Prompt Language

Observed guidance that pushes the assistant toward navigation language:

- `backend/modules/ai_unified/platform_guide.py`
  - "Open Smart Daily"
  - "Use module names as action words"
  - "If live selected-client context is missing, say so plainly and tell the user to select or open the client first."
- `backend/modules/ai_unified/platform_manual.py`
  - "Open Smart Daily to review today's tasks, reminders, and priority items."

Assessment:

- The fallback language is real.
- It is not the root cause by itself.
- The root cause is that selected-client work-item facts are missing unless the request already carries `client_id`.
- When no client facts are injected, the prompt guide nudges the model toward "Open Smart Daily" style responses.

## 8. Local Data Reality Check

Read-only local DB findings:

- `core_clients.db`
  - contains `John Smith`
  - does not contain `John Collins`
- `reminders.db`
  - `active_reminders`: 12 rows
  - `intelligent_tasks`: 62 rows
- `workspace_content.db`
  - `client_tasks`: 0 rows
  - `client_operational_needs`: 0 rows
  - `client_treatment_plans`: 0 rows

Interpretation:

- The local checkout cannot prove the reported "5 overdue Smart Daily items for John Collins."
- Several local active reminders are clearly runtime/test-looking:
  - `Runtime manual reminder rt_...`
  - `AI runtime reminder rt_...`
  - `AI fallback reminder test`
- `active_reminders` also contains orphaned client IDs not present in `core_clients.db`.
- Local `intelligent_tasks` rows are real persisted rows for `Maria Santos`, not `John Collins`.

Conclusion:

- The five reported John Collins overdue items are not verifiable from this local dataset.
- They may be production-only records, test/runtime records from another environment, or orphaned rows not present in the checked-out core client DB.

## 9. Expected vs Actual

### What happens today

- Smart Daily:
  - truthful merged read path
- Client Dashboard:
  - currently patched to merge three separate reads in the frontend
- AI page:
  - truthful only when a selected client was explicitly passed
- Popup assistant:
  - no selected-client task truth unless the backend infers it some other way, which it currently does not do before the model call

### What should happen

```text
Canonical client work-items service
  reads:
    intelligent_tasks
    active_reminders
    workspace client_tasks
  normalizes:
    source
    source_label
    title
    description
    due_date
    status
    priority
    is_overdue
  consumed by:
    Smart Daily
    Client Dashboard
    AI selected-client context
```

## 10. Data Source Decision

Recommended decision:

- Keep reminders and tasks as separate persisted objects for now.
- Normalize them at read time behind one canonical backend client work-items service.
- Do not migrate or rename tables in this task.

Why:

- Smart Daily already has a workable merge model.
- The minimal truthful fix is to expose that merge as a canonical client-scoped service and make Dashboard + AI consume it.
- This avoids DB migrations and stays inside scope.

## 11. AI / Module Relationship Decision

Recommended decision:

- AI should not build task truth by calling module-specific surfaces ad hoc.
- AI should call one canonical operational work-items context service.

Why:

- Prompt-only route guidance is not a reliable substitute for data grounding.
- If Smart Daily and AI use different pathways, they will drift again.

## 12. Backend Test Results

Executed during this audit:

```text
python -m pytest tests/test_ai_platform_tools.py tests/test_client_operational_context.py -q
14 passed, 1 warning in 6.26s
```

Frontend/build validation on current master:

```text
cmd /c npm --prefix frontend run test -- src/pages/AIChat.test.jsx src/pages/SmartDaily.test.jsx src/pages/ClientDashboard.test.jsx
46 passed

cmd /c npm --prefix frontend run build
passed
```

Current gap:

- Existing backend tests cover selected-client task injection when `client_id` is already supplied.
- They do not yet prove typed-name resolution into the Smart Daily-aligned work-item set.
- They do not yet prove popup assistant selected-client grounding.

## 13. Recommended Implementation Plan

### PR 1: Canonical backend work-items read path

- Add a backend helper and route for client-scoped Smart Daily-aligned work items.
- Reuse the same prioritized repository merge already used by Smart Daily.
- Normalize sources as:
  - `Reminder`
  - `Smart Daily Task`
  - `Client Task` / `Treatment Plan Task`

### PR 2: AI grounding repair

- Resolve selected client by:
  - explicit `client_id`
  - explicit `client_name`
  - uniquely matched full client name found in the user message
- Inject canonical client work-item facts before the model call.
- Return clarification when multiple accessible client names match.

### PR 3: Frontend alignment

- Change Client Dashboard to consume the canonical backend work-items route instead of performing a frontend-only merge.
- Update popup assistant to pass route-derived `client_id` when available.

## 14. Scope Confirmation

Not touched during this audit:

- DB files
- env/secrets
- auth logic
- billing/Stripe/SaaS
- deploy config
- SAMHSA importer
- medical referral implementation
- unrelated modules
