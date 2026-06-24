# Ember User Manual

Status: grounded from the current route table, navigation config, sidebar, representative page implementations, and existing docs.

Primary source files used for this manual:

- `frontend/src/App.jsx`
- `frontend/src/config/navigation.js`
- `frontend/src/components/AppSidebar.jsx`
- `docs/navigation/PHASE_2A_NAVIGATION_AUDIT.md`
- Representative page files under `frontend/src/pages/`

This manual is for the popup AI and for human operators. It describes the current Ember platform honestly. If a workflow is partial or still marked as coming soon in code, it says so.

## Core daily modules

### Dashboard

- Route: `/`
- Who uses it: All authenticated users
- Purpose: High-level overview of caseload, alerts, and status.
- When to use it: First thing in the morning or when you need a fast overview.
- What data belongs there: Overview metrics and alerts only.
- How to use it:
  1. Open Dashboard.
  2. Review high-priority status and alert surfaces.
  3. Jump into Smart Daily or a client module to do the actual work.
- Common workflows: Morning review, supervisor review.
- Related modules: Smart Daily, Messages, Case Management.
- What to document: Nothing directly in Dashboard.
- Common mistakes: Treating Dashboard as the place to save narrative client work.
- Role restrictions: None.
- Known limitations: Overview only.
- Example popup questions:
  - What should I check every morning?
  - Where do I start my day in Ember?

### Smart Daily

- Route: `/smart-dashboard`
- Who uses it: All authenticated users
- Purpose: Daily command center for reminders, follow-up, and action queue.
- When to use it: When organizing the day or creating client follow-up tasks.
- What data belongs there: Task titles, details, dates, priorities, client-linked reminders.
- How to use it:
  1. Open Smart Daily.
  2. Review today’s tasks and priorities.
  3. Bind a client if the task belongs to a specific client.
  4. Create or update reminders and follow-up items.
- Common workflows: Morning workflow, intake follow-up, legal deadlines, benefits verification, discharge planning.
- Related modules: Dashboard, Admissions, Documentation, Legal, Benefits, Medical, Treatment Plan.
- What to document: Tasks and reminders, not narrative notes.
- Common mistakes: Leaving follow-up only in notes without adding Smart Daily tasks.
- Role restrictions: None.
- Known limitations: This is the effective reminders and tasks surface; there is no separate top-level reminders route.
- Example popup questions:
  - How do I set up follow-up tasks?
  - What belongs in Smart Daily?

### Case Management

- Route: `/case-management`
- Who uses it: All authenticated users
- Purpose: Caseload management, client search, client editing, and need review.
- When to use it: When locating clients or updating core profile information.
- What data belongs there: Demographics, status, housing or medical need indicators, operational client profile fields.
- How to use it:
  1. Open Case Management.
  2. Search or select the client.
  3. Review or update client profile fields.
  4. Move into the client dashboard or specialty modules as needed.
- Common workflows: Client profile update, intake follow-up, discharge review.
- Related modules: Client Dashboard, Admissions, Documentation, Housing, Benefits, Legal, Medical, Jobs, Resume.
- What to document: Core profile and operational fields. Narrative notes belong in Documentation.
- Common mistakes: Using Case Management as the only record for narrative care work.
- Role restrictions: None.
- Known limitations: Detailed client work often continues in the Client Dashboard or specialty modules.
- Example popup questions:
  - How do I update a client profile?
  - Where do I see my caseload?

### Client Dashboard

- Route: `/client/:clientId`
- Who uses it: All authenticated users
- Purpose: Client-specific cross-module working view.
- When to use it: When working on one client across several areas.
- What data belongs there: Client summary, linked housing, messages, documents, and related client-level context.
- How to use it:
  1. Open the client from Case Management.
  2. Review the client-specific sections and tabs.
  3. Use the linked actions to move into housing, messaging, and related client work.
- Common workflows: Client review, housing coordination, discharge planning.
- Related modules: Case Management, Housing, Messages, Documentation.
- What to document: Usually elsewhere. Use this page to orient yourself.
- Common mistakes: Assuming a client update is saved just because it is visible in the dashboard.
- Role restrictions: None.
- Known limitations: Deep-route client surface, not a primary nav item.
- Example popup questions:
  - How do I work from a specific client page?
  - Where do I open a client’s housing information?

## Intake, documentation, and planning

### Admissions

- Routes:
  - `/admissions`
  - `/admissions/new`
  - `/admissions/:client_id`
  - `/admissions/:client_id/forms/:form_key`
- Who uses it: All authenticated users
- Purpose: New-client intake, admissions packet, shared-profile seeding, and forms.
- When to use it: Starting or continuing a full admission.
- What data belongs there: Demographics, emergency contact, insurance, consents, ROI needs, referral source, packet forms.
- How to use it:
  1. Open Admissions.
  2. Start a full admission or open an existing packet.
  3. Choose an existing client or create a new client in Admissions.
  4. Complete packet forms and review shared-profile autofill carefully.
  5. Use the packet’s Smart Daily suggestions when available.
- Common workflows: Full new client intake, intake insurance capture, intake legal and medical flag review.
- Related modules: Case Management, Documentation, Benefits, Medical, Legal, Smart Daily.
- What to document: Packet data and forms.
- Common mistakes: Overwriting manual edits without checking shared-profile behavior, or leaving follow-up only inside the packet.
- Role restrictions: None.
- Known limitations: The Admissions page includes roadmap items marked upcoming, including Smart Daily tasking and fuller financial coordination.
- Example popup questions:
  - How do I do a full intake?
  - Where do I put insurance during intake?

### Documentation

- Route: `/documentation`
- Who uses it: All authenticated users
- Purpose: Notes and documents command center.
- When to use it: Writing CM notes, progress notes, court notes, group notes, discharge notes, benefits notes, FMLA notes, and related documents.
- What data belongs there: Selected-client notes and documents, note type, narrative content, attachments where applicable.
- How to use it:
  1. Open Documentation.
  2. Select the client first.
  3. Choose note or document mode and the correct note type.
  4. Draft using the internal template guidance if available.
- Common workflows: Initial CM note, court update documentation, group note documentation, discharge note writing.
- Related modules: Admissions, Treatment Plan, Groups, Legal, Housing, Benefits, FMLA.
- What to document: Narrative record and saved documents.
- Common mistakes: Trying to document before selecting a client, or putting reminders into notes without also using Smart Daily.
- Role restrictions: None.
- Known limitations: The assistant should say when client selection is missing.
- Example popup questions:
  - Where do I document a court update?
  - How do I write an initial CM note?

### Treatment Plan

- Route: `/treatment-plan`
- Who uses it: All authenticated users
- Purpose: Structured treatment planning with goals, problems, objectives, interventions, and aftercare.
- When to use it: After needs are identified and a plan should be built or reviewed.
- What data belongs there: Operational needs, problems, goals, objectives, interventions, aftercare plan, completion criteria.
- How to use it:
  1. Open Treatment Plan.
  2. Select the client.
  3. Review the active or draft plan.
  4. Update goals and plan sections as needed.
- Common workflows: Treatment plan creation, aftercare planning, discharge planning.
- Related modules: Documentation, Case Management, Smart Daily, Groups.
- What to document: Structured treatment-plan data here; supporting narrative in Documentation if needed.
- Common mistakes: Treating Treatment Plan as the main narrative note surface.
- Role restrictions: None.
- Known limitations: The module distinguishes active and draft status.
- Example popup questions:
  - How do I create a treatment plan?
  - Where do I update goals and interventions?

### Groups

- Routes:
  - `/groups`
  - `/groups/sessions/:sessionId`
- Who uses it: All authenticated users
- Purpose: Group content and session workflow.
- When to use it: Preparing or running a group session.
- What data belongs there: Group title, description, key points, discussion questions, activity, writing prompt, facilitator tips.
- How to use it:
  1. Open Groups.
  2. Build or review the session structure.
  3. Use Documentation if a narrative group note is also needed.
- Common workflows: Group session setup, group note support.
- Related modules: Documentation, Treatment Plan.
- What to document: Session structure here; narrative note may also belong in Documentation.
- Common mistakes: Assuming the group page alone handles all documentation persistence.
- Role restrictions: None.
- Known limitations: Use Documentation for the narrative record when needed.
- Example popup questions:
  - How do I write group notes?
  - How do I set up a group session?

### UR

- Route: `/ur`
- Who uses it: All authenticated users handling UR work
- Purpose: Utilization Review command center for authorization, coverage, placement, reviewer communication, deadlines, and clinical justification summary.
- When to use it: Continued-stay review, authorization, denial risk, payer communication, level-of-care tracking.
- What data belongs there: Selected client, payer, program, placement, authorization details, reviewer information, deadlines, medical necessity summary.
- How to use it:
  1. Open UR.
  2. Select the client.
  3. Review the workflow coach.
  4. Capture authorization detail, reviewer communication, and deadlines.
  5. Use Documentation and Smart Daily for the narrative record and follow-up.
- Common workflows: UR authorization tracking, denial-risk follow-up.
- Related modules: Documentation, Benefits, Medical, Smart Daily.
- What to document: UR tracking fields and any supporting narrative note.
- Common mistakes: Answering UR questions only as generic insurance advice.
- Role restrictions: None.
- Known limitations: Treat UR as operational tracking, not as legal or clinical authority.
- Example popup questions:
  - How do I use the UR module?
  - Where do I track authorization deadlines?

## Housing, placement, and resource coordination

### Housing

- Routes:
  - `/housing`
  - `/housing/case-manager`
- Who uses it: All authenticated users
- Purpose: Housing search and case-manager housing workflow.
- When to use it: Housing search, referrals, placement work.
- What data belongs there: Search terms, location, housing need, referral outcome.
- How to use it:
  1. Open Housing.
  2. Search by location and need.
  3. Use case-manager housing tools where relevant.
  4. Document outreach and create Smart Daily follow-up.
- Common workflows: Housing referral workflow, discharge planning.
- Related modules: Client Dashboard, Sober Living, Sober Living Directory, Documentation, Smart Daily.
- What to document: Outreach, referrals, placement status.
- Common mistakes: Stopping at search results without documenting or adding follow-up.
- Role restrictions: None.
- Known limitations: `/housing/test` is a test route and not normal workflow.
- Example popup questions:
  - How do I coordinate housing?
  - Where do I put housing follow-up?

### Sober Living

- Routes:
  - `/sober-living`
  - `/sober-living/:houseId`
- Who uses it: All authenticated users working sober-living operations
- Purpose: House records, residents, capacity, and operational sober-living management.
- When to use it: Managing a sober-living house or house-specific placement operations.
- What data belongs there: House details, capacity, certification, funding notes, billing contact, resident and bed details.
- How to use it:
  1. Open Sober Living.
  2. Review or create house details.
  3. Open a house to manage beds, residents, payments, incidents, passes, and chores.
- Common workflows: Sober-living operations, placement follow-up.
- Related modules: Housing, Sober Living Directory, Documentation, Smart Daily.
- What to document: Operational house data here, narrative client-facing note elsewhere if needed.
- Common mistakes: Using this module when the user really needs sober-living research rather than house operations.
- Role restrictions: None.
- Known limitations: For research and provider comparison, the directory is often the better first stop.
- Example popup questions:
  - How do I coordinate sober living placement?
  - Where do I manage a sober-living house?

### Sober Living Directory

- Routes:
  - `/sober-living-directory`
  - `/sober-living-directory/discovery`
  - `/sober-living-directory/review`
  - `/sober-living-directory/:listingId`
- Who uses it: All authenticated users
- Purpose: Manual-first sober-living research tool with saved and live results.
- When to use it: Researching, comparing, and reviewing sober-living options.
- What data belongs there: Location, zip, certification, notes about MAT, rent, funding, or calls.
- How to use it:
  1. Open the main directory page.
  2. Search by city, zip, or certification filters.
  3. Review saved and live results.
  4. Open listing detail, review, or discovery pages as needed.
- Common workflows: Sober-living coordination, placement research.
- Related modules: Housing, Sober Living, Services, Documentation, Smart Daily.
- What to document: Research notes and outreach outcomes; mirror them into Documentation when needed for the client record.
- Common mistakes: Presenting discovery or scheduler controls as guaranteed stable if the page shows unavailable or auth-failure states.
- Role restrictions: None.
- Known limitations: Discovery and scheduler areas have explicit failure and unavailable states in code.
- Example popup questions:
  - How do I research sober-living options?
  - What is the discovery page for?

## Benefits, medical, legal, and FMLA

### Benefits

- Route: `/benefits`
- Who uses it: All authenticated users
- Purpose: Benefits and insurance support tracking.
- When to use it: Benefits work, Medi-Cal, DPSS, CalFresh, GR, insurance-related support.
- What data belongs there: Client benefit status, supporting documents, insurance support context, income or work-limitation data.
- How to use it:
  1. Open Benefits.
  2. Select the client first.
  3. Review benefits fields and supporting documents.
  4. Refer back to Admissions if the question is about intake-time insurance data.
- Common workflows: Benefits or Medi-Cal workflow, insurance verification.
- Related modules: Admissions, Medical, Documentation, Smart Daily.
- What to document: Benefits status and any supporting narrative note.
- Common mistakes: Confusing Benefits with organizational Billing.
- Role restrictions: None.
- Known limitations: The assistant should say when client selection is missing.
- Example popup questions:
  - How do I use Benefits?
  - Where do I put Medi-Cal info?

### Medical

- Route: `/medical`
- Who uses it: All authenticated users
- Purpose: Provider and appointment coordination.
- When to use it: PCP, dental, psychiatry, therapy, and appointment-related follow-up.
- What data belongs there: Selected client, providers, appointment details, need summaries.
- How to use it:
  1. Open Medical.
  2. Select the client.
  3. Review providers or appointments.
  4. Use Documentation and Smart Daily for follow-up record and tasks.
- Common workflows: Medical appointment coordination.
- Related modules: Benefits, Documentation, Smart Daily, Case Management.
- What to document: Care coordination and appointment follow-up.
- Common mistakes: Turning Medical coordination into clinical advice.
- Role restrictions: None.
- Known limitations: Operational coordination only.
- Example popup questions:
  - How do I coordinate a medical appointment?
  - Where do I track PCP or psychiatry follow-up?

### Legal

- Route: `/legal`
- Who uses it: All authenticated users
- Purpose: Legal case coordination, court-related work, and legal file support.
- When to use it: Court updates, probation or parole coordination, legal notices, legal status review.
- What data belongs there: Selected client, charges, legal files, legal status.
- How to use it:
  1. Open Legal.
  2. Select the client.
  3. Review legal detail and any attached files.
  4. Use Documentation for the narrative note and Smart Daily for deadlines.
- Common workflows: Court update workflow, probation follow-up.
- Related modules: Documentation, Smart Daily, Case Management.
- What to document: Court and legal notes, supporting files, deadlines.
- Common mistakes: Giving only generic legal advice instead of module-plus-note-plus-reminder guidance.
- Role restrictions: None.
- Known limitations: Legal tracking and coordination only, not authoritative legal advice.
- Example popup questions:
  - Where do I document a court update?
  - How do I track probation follow-up?

### FMLA

- Route: `/fmla`
- Who uses it: All authenticated users working leave cases
- Purpose: Leave paperwork and workflow-stage tracking.
- When to use it: FMLA, STD, denial, approval, return-to-work, deadline tracking.
- What data belongs there: Workflow stage, workflow bucket, employer-related tracking, forms, deadlines.
- How to use it:
  1. Open FMLA.
  2. Review the case workflow stage.
  3. Track missing paperwork, deadlines, and return-to-work status.
  4. Use Smart Daily for follow-up and Documentation for the narrative record if needed.
- Common workflows: FMLA tracking workflow.
- Related modules: Documentation, Benefits, Smart Daily.
- What to document: FMLA or leave-tracking note and deadlines.
- Common mistakes: Confusing FMLA client tracking with organization billing or account settings.
- Role restrictions: None.
- Known limitations: Track operational workflow here; do not overstate legal interpretation.
- Example popup questions:
  - How do I use FMLA?
  - Where do I track leave paperwork deadlines?

## Messaging, employment, and support

### Messages

- Route: `/messages`
- Who uses it: All authenticated users
- Purpose: Internal messaging and thread creation.
- When to use it: Coordinating with staff.
- What data belongs there: Thread title, purpose, recipients, first message.
- How to use it:
  1. Open Messages.
  2. Review threads or create a new one.
  3. Choose the recipient and send the opening message.
- Common workflows: Staff coordination, supervisor follow-up.
- Related modules: Dashboard, Smart Daily, Client Dashboard.
- What to document: Messages are communication, not the formal client record.
- Common mistakes: Treating internal messaging as the only client documentation.
- Role restrictions: None.
- Known limitations: Keep protected client details aligned with policy.
- Example popup questions:
  - How do I message another staff member about a client?
  - Where do I start a thread?

### Resume Builder

- Route: `/resume`
- Who uses it: All authenticated users supporting employment
- Purpose: Client employment profile and resume generation.
- When to use it: Resume creation or employment profile work.
- What data belongs there: Career objective, work history, skills, resume instructions, saved resumes.
- How to use it:
  1. Open Resume.
  2. Select the client.
  3. Build or update the employment profile.
  4. Save or review generated resumes.
- Common workflows: Employment and reentry workflow.
- Related modules: Jobs, Case Management, Documentation.
- What to document: Employment profile here, with narrative employment planning in Documentation if needed.
- Common mistakes: Using Resume when the need is a live job search.
- Role restrictions: None.
- Known limitations: The repo contains multiple resume page variants, but `/resume` is the active route.
- Example popup questions:
  - How do I build a resume for a client?
  - Where do I save employment profile data?

### Jobs

- Route: `/jobs`
- Who uses it: All authenticated users supporting employment goals
- Purpose: Client-linked job search support.
- When to use it: Searching for work or planning employment follow-up.
- What data belongs there: Selected client, job search terms, location.
- How to use it:
  1. Open Jobs.
  2. Select the client.
  3. Enter search terms and location.
  4. Use results and follow-up tasks elsewhere as needed.
- Common workflows: Employment and reentry workflow.
- Related modules: Resume, Case Management, Smart Daily.
- What to document: Employment follow-up in Documentation and task follow-up in Smart Daily if needed.
- Common mistakes: Inventing fully built job-search automation.
- Role restrictions: None.
- Known limitations: The page explicitly says some job-search support tools are coming soon.
- Example popup questions:
  - How do I use Jobs?
  - How do I support employment planning in Ember?

## Admin, owner, and account modules

### Team Management

- Route: `/team`
- Who uses it: Admin users
- Purpose: Staff invite and team management.
- When to use it: Adding staff or managing team roles.
- What data belongs there: Staff email, name, and role-related admin data.
- How to use it:
  1. Open Team Management.
  2. Enter staff information.
  3. Use invite and team controls.
- Common workflows: Admin and team workflow.
- Related modules: Settings, Supervisor Dashboard, Support.
- What to document: Administrative changes only.
- Common mistakes: Recommending this to non-admin users.
- Role restrictions: Admin only.
- Known limitations: Role-gated.
- Example popup questions:
  - How do I invite staff?
  - Where do I manage my team?

### Supervisor Dashboard

- Route: `/supervisor-dashboard`
- Who uses it: Admin users
- Purpose: Team oversight and review metrics.
- When to use it: Reviewing team workload or oversight metrics.
- What data belongs there: Team metrics and oversight context.
- How to use it:
  1. Open Supervisor Dashboard.
  2. Review metrics.
  3. Move to Smart Daily or Team Management based on what needs action.
- Common workflows: Supervisor review workflow.
- Related modules: Team Management, Smart Daily, Dashboard.
- What to document: Usually operational follow-up, not client notes.
- Common mistakes: Presenting this as available to standard case managers.
- Role restrictions: Admin only.
- Known limitations: Role-gated.
- Example popup questions:
  - How do supervisors review team work?
  - Where do supervisors start?

### Owner Cockpit

- Route: `/owner`
- Who uses it: Platform super-admin users
- Purpose: Platform-owner command center.
- When to use it: Company-level analytics, activity review, support queue visibility.
- What data belongs there: Safe owner and admin activity feed, marketing and support operations, platform visibility.
- How to use it:
  1. Open Owner Cockpit only if you are a platform super-admin.
  2. Use it for platform operations, not client workflow.
- Common workflows: Owner operations, support review.
- Related modules: Super Admin, Support.
- What to document: Operational, not client-facing.
- Common mistakes: Recommending Owner Cockpit to ordinary users.
- Role restrictions: Super-admin only.
- Known limitations: Separate from standard org workflow.
- Example popup questions:
  - Where is the owner dashboard?
  - How do I review platform activity?

### Super Admin

- Route: `/super-admin`
- Who uses it: Platform super-admin users
- Purpose: Organization control and internal billing model administration.
- When to use it: Org administration or internal billing overrides.
- What data belongs there: Organization details, billing draft fields, org status.
- How to use it:
  1. Open Super Admin only if you are a platform super-admin.
  2. Review organization and internal billing sections.
- Common workflows: Super-admin operations.
- Related modules: Owner Cockpit, Billing.
- What to document: Operational, not client-facing.
- Common mistakes: Confusing Super Admin billing controls with the client Benefits module.
- Role restrictions: Super-admin only.
- Known limitations: The UI explicitly indicates live payments are not connected.
- Example popup questions:
  - Where do I manage organizations?
  - Where do I update internal billing status?

### Profile

- Route: `/profile`
- Who uses it: All authenticated users
- Purpose: User account profile page.
- When to use it: Reviewing your own account info.
- What data belongs there: Current user profile details.
- How to use it:
  1. Open Profile.
  2. Review your account information.
- Common workflows: Support and account workflow.
- Related modules: Settings, Support.
- What to document: None for client records.
- Common mistakes: Using Profile for client data work.
- Role restrictions: None.
- Known limitations: Account-only page.
- Example popup questions:
  - Where is my profile?
  - How do I check my account page?

### Settings

- Route: `/settings`
- Who uses it: All authenticated users, with extra admin links
- Purpose: Settings hub for account, organization, team, system status, and billing links.
- When to use it: Navigating to account or org settings.
- What data belongs there: Account and organization-level navigation, not client records.
- How to use it:
  1. Open Settings.
  2. Choose Account, Organization, Team Management, System Status, Billing, or related sections.
- Common workflows: Account workflow, admin team workflow.
- Related modules: Profile, Team Management, Supervisor Dashboard, Billing, Support.
- What to document: None for client records.
- Common mistakes: Treating Settings as a client-work module.
- Role restrictions: Some linked sections are admin-only.
- Known limitations: Some sections are placeholders or link hubs.
- Example popup questions:
  - Where do I go for settings?
  - How do I find billing or team links?

### Support

- Route: `/support`
- Who uses it: All authenticated users
- Purpose: Help and support ticket page.
- When to use it: Bugs, account issues, billing questions, feature requests.
- What data belongs there: Ticket category, short summary, general description without client names.
- How to use it:
  1. Open Support.
  2. Choose the right category.
  3. Enter a short summary and general issue description.
  4. Submit without including client names or PHI.
- Common workflows: Support and account workflow.
- Related modules: Dashboard, Case Management, Smart Daily, Team Management, Settings.
- What to document: Operational support only.
- Common mistakes: Including client names or PHI.
- Role restrictions: None.
- Known limitations: Support is not a client documentation surface.
- Example popup questions:
  - How do I submit a support ticket?
  - Where do I report a billing question?

### Billing

- Route: `/billing`
- Who uses it: All authenticated users with billing access
- Purpose: Organization plan, usage, and limits page.
- When to use it: Checking plan status or billing readiness.
- What data belongs there: Plan, usage, billing state, Stripe capability status.
- How to use it:
  1. Open Billing.
  2. Review plan and usage cards.
  3. Only use checkout or portal if the capability flags are actually live.
- Common workflows: Billing review, account workflow.
- Related modules: Settings, Super Admin.
- What to document: None for client records.
- Common mistakes: Confusing Billing with Benefits or client insurance work.
- Role restrictions: Account or org access dependent.
- Known limitations: Billing foundation is active, but payments are not connected yet.
- Example popup questions:
  - Where do I see plan usage?
  - Is Stripe billing live yet?

### System Integrity

- Route: `/system-integrity`
- Who uses it: Operational or admin users
- Purpose: Diagnostic system-integrity visibility.
- When to use it: Operational troubleshooting or review.
- What data belongs there: System-level status and integrity information.
- How to use it:
  1. Open System Integrity.
  2. Review the diagnostic information.
- Common workflows: Operational review.
- Related modules: Integration Audit, Settings.
- What to document: Internal operational notes only.
- Common mistakes: Treating it as a case-manager workflow page.
- Role restrictions: Operational use.
- Known limitations: Not a standard client-care module.
- Example popup questions:
  - Where do I check system integrity?
  - Is there a diagnostic page?

### Integration Audit

- Route: `/integration-audit`
- Who uses it: Operational or admin users
- Purpose: Audit and route-integration review page.
- When to use it: Reviewing integration or audit-oriented information.
- What data belongs there: Audit tabs, route coverage, test-result context.
- How to use it:
  1. Open Integration Audit.
  2. Review the tabs and audit information.
- Common workflows: Operational audit review.
- Related modules: System Integrity, Dashboard.
- What to document: Internal audit notes only.
- Common mistakes: Using it as if it were a standard client-work page.
- Role restrictions: Operational use.
- Known limitations: Diagnostic or audit-oriented, not standard client workflow.
- Example popup questions:
  - Is there an integration audit page?
  - Where do I review route audit info?

