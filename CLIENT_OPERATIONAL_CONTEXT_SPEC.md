# Client Operational Context Spec

Generated: 2026-06-07

## Purpose

Client Operational Context is the shared client payload every module should consume when a case manager selects a client. It separates intake facts from the treatment plan, then uses both to prefill forms, route data to the correct module, and create actionable tasks.

The operating rule is:

- Intake captures the client's current state at admission.
- The first treatment plan becomes the operational source of truth for where the client is going.
- The unified client dropdown is the activation point in each module.
- Needs identified in intake or treatment planning must become module context and daily work, not passive notes.

## Current Code Anchors

These are the current implementation seams this spec should build on:

- `frontend/src/pages/CaseManagement.jsx` stores intake form fields including program, housing, employment, benefits, legal, medical, goals, barriers, and notes.
- `backend/api/clients.py` stores and normalizes core client fields, including contact info, intake date, statuses, medical conditions, needs, and background.
- `frontend/src/components/ClientSelector.jsx` fetches a selected client with `/api/clients/{clientId}` and passes the selected client object to the consuming module.
- `backend/modules/case_management/routes.py` currently has `_generate_initial_tasks`, but task/reminder generation is still only a TODO.
- `backend/modules/ai_documentation/service.py` already consumes shared intake context for document generation and treatment-plan placeholders.
- `frontend/src/pages/Benefits.jsx`, `Medical.jsx`, `Legal.jsx`, `Resume.jsx`, `Jobs.jsx`, `HousingSearch.jsx`, and `CaseManagerHousing.jsx` already react to selected clients, but the consumed fields are inconsistent by module.

## Definitions

### Intake Context

The current state at admission. Intake is factual and should not imply that a service has been completed.

Examples:

- Current legal status
- Current medical conditions
- Current housing status
- Current benefits status
- Current employment status
- Transportation barriers
- Client-reported goals and barriers
- Admission date and program type

### Treatment Plan Context

The operational plan created after intake. This should be treated as the client service bible.

Examples:

- Problems
- Goals
- Objectives
- Interventions
- Assigned modules
- Target dates
- Aftercare plan
- Completion criteria
- Generated tasks and reminders

### Operational Need

A normalized need that can be routed to modules and tasks.

Examples:

- `dental`
- `primary_care`
- `psychiatry`
- `benefits_screening`
- `medi_cal`
- `disability`
- `housing`
- `sober_living_aftercare`
- `legal_follow_up`
- `job_search`
- `resume`
- `transportation`

## Shared Payload Shape

Every module should receive the same base object when a client is selected.

```json
{
  "client": {
    "client_id": "uuid",
    "first_name": "string",
    "last_name": "string",
    "full_name": "string",
    "date_of_birth": "YYYY-MM-DD",
    "phone": "string",
    "email": "string",
    "address": "string",
    "city": "string",
    "state": "string",
    "zip_code": "string",
    "case_manager_id": "string",
    "risk_level": "Low|Medium|High",
    "case_status": "Active|Inactive|Closed",
    "intake_date": "YYYY-MM-DD",
    "admission_date": "YYYY-MM-DD",
    "program_type": "string"
  },
  "intake": {
    "housing_status": "string",
    "employment_status": "string",
    "benefits_status": "string",
    "legal_status": "string",
    "prior_convictions": "string",
    "substance_abuse_history": "string",
    "mental_health_status": "string",
    "medical_conditions": "string",
    "special_needs": "string",
    "transportation": "string",
    "referral_source": "string",
    "goals": "string",
    "barriers": "string",
    "notes": "string",
    "needs": ["string"],
    "background": {}
  },
  "treatment_plan": {
    "plan_id": "uuid",
    "status": "draft|active|review_due|completed",
    "created_at": "ISO datetime",
    "approved_at": "ISO datetime",
    "problems": [],
    "goals": [],
    "objectives": [],
    "interventions": [],
    "target_dates": [],
    "aftercare_plan": {},
    "completion_criteria": [],
    "operational_needs": []
  },
  "module_context": {
    "legal": {},
    "medical": {},
    "benefits": {},
    "housing": {},
    "sober_living": {},
    "employment": {},
    "resume": {},
    "documentation": {},
    "reminders": {}
  },
  "open_tasks": [],
  "daily_priority": {}
}
```

## Intake Field Routing

| Intake Field | Module Targets | Required Behavior |
|---|---|---|
| `client_id` | All modules | Primary join key across modules and tasks. |
| `first_name`, `last_name`, `full_name` | All modules, docs, resume, jobs | Auto-fill names on client selection. |
| `date_of_birth` | Docs, Benefits, Medical, FMLA | Auto-fill age/DOB fields and eligibility calculations. |
| `phone`, `email` | All modules, Resume, Services | Auto-fill contact fields and provider/referral forms. |
| `address`, `city`, `state`, `zip_code` | Housing, Resume, Docs, Benefits, Medical | Auto-fill residence, local search area, benefit geography, resume contact info. |
| `intake_date`, `admission_date` | Docs, UR, Treatment Plan, FMLA | Anchor program timeline, letters, reviews, and deadlines. |
| `program_type` | Docs, Treatment Plan, UR | Auto-fill program references and service level context. |
| `housing_status` | Housing, Sober Living, Docs, Tasks | Trigger housing/sober living needs and search context. |
| `employment_status` | Jobs, Resume, Benefits, Tasks | Trigger resume/job search workflows and benefits income questions. |
| `benefits_status` | Benefits, Smart Daily, Docs | Pre-fill benefit workflow status and follow-up tasks. |
| `legal_status` | Legal, Docs, Tasks | Create legal context and court/probation follow-up tasks. |
| `prior_convictions` | Legal, Jobs, Resume | Legal context and background-friendly employment/resume strategy. |
| `medical_conditions` | Medical, Benefits, Docs, Tasks | Trigger medical referrals, disability screening, and health-related benefits checks. |
| `mental_health_status` | Medical, Benefits, Treatment Plan | Inform behavioral health, disability screening, treatment planning, and safety checks. |
| `substance_abuse_history` | Treatment Plan, Docs, Medical | Inform treatment plan, aftercare, recovery supports, and clinical documentation. |
| `transportation` | Services, Medical, Legal, Housing, Tasks | Trigger transport assistance tasks for appointments, court, housing viewings. |
| `special_needs` | Medical, Benefits, Housing, Services | Trigger accommodation, disability, accessibility, and support referrals. |
| `goals` | Treatment Plan, Docs, Tasks | Seed first treatment plan and progress tracking. |
| `barriers` | Treatment Plan, Smart Daily, Tasks | Generate operational tasks and risk prioritization. |
| `needs` | All service modules, Smart Daily | Drive module activation and daily task queue. |
| `notes` | Docs, Treatment Plan, Client Dashboard | Provide narrative context but should not replace structured needs. |

## Treatment Plan as the Operational Bible

The first treatment plan should become a first-class record, not only a generated document. It should be created from intake plus case-manager review.

### Required Treatment Plan Fields

```json
{
  "plan_id": "uuid",
  "client_id": "uuid",
  "status": "draft|active|review_due|completed",
  "created_by": "case_manager_id",
  "created_at": "ISO datetime",
  "approved_at": "ISO datetime",
  "review_due_date": "YYYY-MM-DD",
  "problems": [
    {
      "problem_id": "uuid",
      "domain": "housing|medical|benefits|legal|employment|recovery|transportation|documentation",
      "description": "string",
      "source": "intake|case_manager|ai_suggestion"
    }
  ],
  "goals": [
    {
      "goal_id": "uuid",
      "problem_id": "uuid",
      "description": "string",
      "target_date": "YYYY-MM-DD",
      "status": "active|completed|deferred"
    }
  ],
  "objectives": [
    {
      "objective_id": "uuid",
      "goal_id": "uuid",
      "description": "string",
      "measure": "string",
      "target_date": "YYYY-MM-DD",
      "status": "active|completed|deferred"
    }
  ],
  "interventions": [
    {
      "intervention_id": "uuid",
      "objective_id": "uuid",
      "description": "string",
      "assigned_module": "medical|benefits|legal|housing|sober_living|jobs|resume|services|documentation",
      "assigned_to": "case_manager_id",
      "frequency": "one_time|weekly|monthly|as_needed"
    }
  ],
  "aftercare_plan": {
    "sober_living_needed": false,
    "outpatient_needed": false,
    "medical_follow_up_needed": false,
    "psychiatry_follow_up_needed": false,
    "employment_follow_up_needed": false,
    "benefits_follow_up_needed": false,
    "legal_follow_up_needed": false,
    "notes": "string"
  },
  "operational_needs": [
    {
      "need_key": "dental",
      "domain": "medical",
      "source": "treatment_plan",
      "priority": "urgent|high|medium|low",
      "status": "open|in_progress|completed|deferred",
      "target_date": "YYYY-MM-DD"
    }
  ]
}
```

### Treatment Plan Rules

- Intake can suggest needs, but the active treatment plan confirms operational priorities.
- AI may draft suggested goals, objectives, interventions, and tasks, but a case manager must approve the treatment plan before it becomes active.
- Once approved, active treatment-plan needs create or update tasks.
- Completion letters and aftercare plans must cite the active treatment plan when available.
- Weekly notes should update progress against treatment-plan goals and should be able to add new needs.
- New needs that arise after intake should update the treatment plan or create a treatment-plan review task.

## Task Generation Rules

Tasks should be generated from structured needs, not from arbitrary prose alone.

### Need-to-Task Examples

| Need | Module | Auto-generated Task |
|---|---|---|
| `dental` | Medical | Book dental appointment; verify coverage; add appointment reminder. |
| `primary_care` | Medical | Schedule primary care intake; collect insurance/ID documents. |
| `psychiatry` | Medical | Schedule psychiatry evaluation; verify medication list. |
| `medi_cal` | Benefits | Start Medi-Cal eligibility screening; collect income/residency documents. |
| `disability` | Benefits | Start disability eligibility screen; collect medical evidence. |
| `food_assistance` | Benefits | Start CalFresh screening; collect income and household details. |
| `legal_follow_up` | Legal | Record legal matter; add court/probation follow-up date. |
| `court_date` | Legal, Reminders | Create court reminder; create document/prep task. |
| `housing` | Housing | Start housing search; identify budget/location/eligibility constraints. |
| `sober_living_aftercare` | Sober Living | Search sober living options; schedule facility contact/viewing. |
| `resume` | Resume | Create resume profile using client contact info and employment goals. |
| `job_search` | Jobs | Start job search; match jobs to client goals and resume status. |
| `transportation` | Services, Reminders | Arrange transportation for appointments/court/services. |
| `id_documents` | Services, Benefits, Legal | Start ID/document rebuild workflow. |

### Task Object

```json
{
  "task_id": "uuid",
  "client_id": "uuid",
  "case_manager_id": "string",
  "source": "intake|treatment_plan|weekly_note|manual|module_event|ai_suggestion",
  "source_id": "uuid",
  "module": "medical|benefits|legal|housing|sober_living|jobs|resume|services|documentation",
  "need_key": "dental",
  "title": "Book dental appointment",
  "description": "Client reported dental need during intake/treatment planning.",
  "priority": "urgent|high|medium|low",
  "due_date": "YYYY-MM-DD",
  "status": "pending|in_progress|completed|deferred|cancelled",
  "ai_generated": true,
  "requires_case_manager_approval": false
}
```

### Task Safety Rules

- Auto-created tasks may be generated from approved treatment-plan needs.
- Tasks generated only from intake should be marked `source=intake` and can be created immediately when low-risk, but sensitive legal/medical actions should be reviewable.
- AI-generated tasks should be transparent: show source, need key, and reason.
- Duplicate prevention must match on `client_id + need_key + module + open status`.
- Completed tasks should remain linked to the need and treatment-plan objective.
- Smart Daily should rank tasks by due date, risk level, medical/legal urgency, and treatment-plan priority.

## Module Contracts

Each module should implement the same contract:

1. Accept `client_id` from URL, dropdown, or parent navigation.
2. Fetch Client Operational Context.
3. Prefill module-specific forms from `client`, `intake`, and `treatment_plan`.
4. Show active needs relevant to that module.
5. Create module events/tasks that update the shared context.
6. Return users to the client dashboard with updated status.

### Documentation

Consumes:

- `client`
- `intake`
- `treatment_plan`
- `open_tasks`

Required behavior:

- Completion letters use treatment-plan completion criteria.
- Aftercare plans use active aftercare plan fields.
- Court/probation letters use legal context.
- Proof of residence uses address/housing/sober living context.
- Treatment plan drafts must update structured plan records, not only saved document text.

### Legal

Consumes:

- `legal_status`
- `prior_convictions`
- `background.legal`
- treatment-plan legal needs

Required behavior:

- Selecting a client preloads legal intake facts.
- Active legal needs create legal follow-up tasks.
- Court dates create reminders.
- Legal module should not silently create a legal case from intake without user confirmation.

### Medical

Consumes:

- `medical_conditions`
- `mental_health_status`
- `special_needs`
- medical treatment-plan needs

Required behavior:

- Selecting a client displays medical conditions and open medical needs.
- Dental, primary care, psychiatry, medication, and specialty needs become referral/appointment tasks.
- Booked appointments update Smart Daily and client dashboard.

### Benefits

Consumes:

- `benefits_status`
- `medical_conditions`
- `mental_health_status`
- `special_needs`
- employment/income context
- treatment-plan benefits needs

Required behavior:

- Selecting a client preloads eligibility screening fields.
- Health needs should set healthcare screening context.
- Disability needs should request functional limitation and medical evidence fields.
- Benefits applications create reminders for document collection and deadlines.

### Housing

Consumes:

- `housing_status`
- `address/city/state/zip_code`
- `transportation`
- `needs`
- treatment-plan housing needs

Required behavior:

- Selecting a client preloads location and client needs.
- Housing search ranks options by need, budget, location, and barriers.
- Saved leads create follow-up tasks.

### Sober Living

Consumes:

- aftercare plan
- sober living need
- recovery context
- housing status

Required behavior:

- Sober living should be driven by aftercare/treatment-plan need, not only directory browsing.
- Selecting a client should show aftercare target, placement barriers, and follow-up tasks.

### Resume

Consumes:

- `first_name`, `last_name`, `phone`, `email`, `address`, `city`, `state`, `zip_code`
- `employment_status`
- `prior_convictions`
- employment goals from treatment plan

Required behavior:

- Selecting a client auto-fills identity and contact fields.
- Employment goals and background-friendly positioning seed the resume profile.
- Resume creation updates Jobs module readiness.

### Jobs

Consumes:

- employment goal
- resume readiness
- location/transportation
- background constraints

Required behavior:

- Selecting a client shows whether a resume exists.
- If no resume exists, create task: `Create resume before applying`.
- Saved jobs and applications update client dashboard and Smart Daily.

### Smart Daily / Reminders

Consumes:

- all open tasks
- treatment-plan needs
- risk level
- due dates
- module status

Required behavior:

- Show treatment-plan tasks first when due/urgent.
- Surface intake-derived tasks until resolved.
- Add new tasks from weekly notes and module events.
- Daily priority should explain why each item appears.

## Client Dropdown Contract

The unified client dropdown is effectively the module activation button.

When a client is selected:

1. Fetch `/api/clients/{client_id}/operational-context`.
2. Set module local state with the shared context.
3. Prefill all safe fields.
4. Show active module-specific needs.
5. Preserve `?client={client_id}` in the URL.
6. Let users open the full client dashboard.

Safe auto-fill fields:

- Name
- DOB
- Phone
- Email
- Address
- Program
- Admission date
- Status fields
- Existing goals/barriers

Review-before-action fields:

- Legal case creation
- Medical referral submission
- Benefits application submission
- External provider contact
- Court/probation letter finalization
- Any AI-generated task marked high-risk

## Proposed Backend Endpoints

### Get Operational Context

`GET /api/clients/{client_id}/operational-context`

Returns the shared payload described above.

### Create or Update Treatment Plan

`POST /api/clients/{client_id}/treatment-plan`

Creates the first treatment plan or updates an existing draft.

`PUT /api/clients/{client_id}/treatment-plan/{plan_id}`

Updates structured treatment plan fields.

`POST /api/clients/{client_id}/treatment-plan/{plan_id}/approve`

Marks the treatment plan active and triggers approved task generation.

### Generate Tasks from Needs

`POST /api/clients/{client_id}/operational-tasks/generate`

Inputs:

```json
{
  "source": "intake|treatment_plan|weekly_note",
  "source_id": "uuid",
  "needs": ["dental", "housing", "resume"],
  "approval_mode": "auto|review"
}
```

Returns created tasks and duplicates skipped.

### Update Need Status

`PATCH /api/clients/{client_id}/needs/{need_key}`

Updates a need as open, in progress, completed, deferred, or cancelled.

## Data Model Additions

### `client_operational_needs`

```sql
CREATE TABLE client_operational_needs (
  need_id TEXT PRIMARY KEY,
  client_id TEXT NOT NULL,
  need_key TEXT NOT NULL,
  domain TEXT NOT NULL,
  source TEXT NOT NULL,
  source_id TEXT,
  priority TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'open',
  description TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  target_date TEXT
);
```

### `client_treatment_plans`

```sql
CREATE TABLE client_treatment_plans (
  plan_id TEXT PRIMARY KEY,
  client_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  created_by TEXT,
  created_at TEXT NOT NULL,
  approved_at TEXT,
  review_due_date TEXT,
  plan_json TEXT NOT NULL,
  updated_at TEXT
);
```

### `client_operational_tasks`

This can either become a new table or map into the existing reminders/task table. The preferred approach is to map into the existing reminder/task system and add these fields if missing:

- `source`
- `source_id`
- `need_key`
- `module`
- `ai_generated`
- `requires_case_manager_approval`

## AI Responsibilities

AI should support the workflow, not silently make operational decisions.

AI may:

- Draft treatment-plan goals/objectives/interventions from intake.
- Suggest operational needs from intake and notes.
- Generate task suggestions.
- Explain why a task was recommended.
- Draft documentation using treatment-plan context.

AI must not:

- Submit benefits applications.
- Create external referrals without user confirmation.
- Invent diagnoses, legal facts, appointments, or completion status.
- Mark treatment-plan goals complete without case-manager action.
- Create legal cases without user confirmation.

## Acceptance Criteria

### Intake

- Creating a client stores all intake fields in core client records.
- Creating or updating a client propagates shared intake facts to module databases.
- Selecting the client in any module returns the same base identity/contact/program data.

### Treatment Plan

- A first treatment plan can be created from intake.
- The plan stores structured goals, objectives, interventions, needs, and aftercare.
- Approving the plan creates linked tasks.
- Completion letters and aftercare documents use the active treatment plan.

### Module Prefill

- Resume pre-fills name, phone, email, address.
- Benefits pre-fills DOB/age, medical context, healthcare/disability indicators where known.
- Medical pre-fills medical conditions and open medical needs.
- Legal pre-fills legal status and prior conviction context.
- Housing pre-fills location and housing/sober-living needs.
- Jobs sees resume readiness and employment goals.

### Reminders / Smart Daily

- Initial needs create or suggest tasks.
- Treatment-plan needs create approved tasks.
- Smart Daily shows open treatment-plan and intake tasks.
- Tasks remain linked to needs and treatment-plan objectives.

## Implementation Phases

### Phase 1: Operational Context Read Model

- Add `/api/clients/{client_id}/operational-context`.
- Merge existing core client fields, module summaries, active tasks, and treatment-plan draft if present.
- Update `ClientSelector` consumers to optionally request operational context.

### Phase 2: Treatment Plan First-Class Record

- Add treatment-plan tables/store.
- Convert existing AI treatment-plan suggestions into structured draft treatment plans.
- Add approve flow.
- Route active treatment plan into documentation generation.

### Phase 3: Need Normalization and Routing

- Add normalized `client_operational_needs`.
- Convert intake statuses/goals/barriers into suggested needs.
- Add duplicate-safe task generation from needs.
- Link tasks to modules.

### Phase 4: Module Prefill

- Resume: prefill identity/contact/employment goal/background-safe context.
- Medical: prefill medical conditions and medical needs.
- Benefits: prefill age, health, disability, healthcare needs.
- Legal: prefill legal intake and court/probation context.
- Housing/Sober Living: prefill location, aftercare, housing needs.
- Jobs: prefill employment goal and resume readiness.

### Phase 5: Smart Daily Integration

- Rank tasks by treatment-plan priority, risk, due date, and module urgency.
- Explain why each task is shown.
- Add daily review workflow for new needs discovered in notes/modules.

### Phase 6: Documentation Compliance

- Completion letters use active treatment plan completion criteria.
- Aftercare plans use active aftercare plan.
- Progress notes reference active goals/objectives.
- AI must flag missing diagnosis/treatment-plan/aftercare data instead of inventing it.

## Open Decisions

- Should intake-derived tasks be auto-created immediately, or shown in a review queue first?
- Should treatment-plan approval be required before any AI-generated tasks hit Smart Daily?
- Should legal/medical high-risk needs always require explicit human confirmation?
- Should every module write back to `client_operational_needs`, or only to module-specific tables plus a shared event log?
- Should the treatment plan be managed in Documentation, Case Management, or a dedicated Treatment Plan workspace?

## Recommended Decision

Use this governance model:

- Intake creates suggested needs.
- The first treatment plan confirms active needs.
- Approved treatment-plan needs create tasks automatically.
- High-risk legal/medical actions require confirmation before external workflow creation.
- All modules consume Client Operational Context and write back module events.
- Smart Daily becomes the execution queue for active treatment-plan and intake-derived work.
