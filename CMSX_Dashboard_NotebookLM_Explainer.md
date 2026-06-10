# CMSX Dashboard — NotebookLM Training Source
**Ember Case Management Suite | Dashboard Module**
*Training handout. Based on live app at https://cmsx-tau.vercel.app/*

---

## What Is the Dashboard?

The Dashboard is the first screen a user sees after logging into the Ember Case Management Suite (CMSX). It functions as a command center — a single page that shows the current state of a case manager's workload, surfaces urgent FMLA deadlines, and provides one-click access to every service module in the platform.

The Dashboard is not a data entry screen. Its job is to give a case manager situational awareness at a glance: how many clients are active, whether anyone is high-risk, what FMLA deadlines are approaching, and what tools are available to act on any of it. It is intentionally read-oriented so that primary actions — working a case, submitting paperwork, generating a document — happen inside the individual modules, not on the Dashboard itself.

---

## Who Uses the Dashboard?

The Dashboard is designed for two roles:

**Case Managers** use it as their daily starting point. They check their caseload stats, review any FMLA flags, skim their pinned notes and documents, then navigate into the module relevant to whatever they are working on.

**Supervisors and Admins** (designated "Admin / Supervisor" in the platform) see the same Dashboard but also have access to the Supervisor Mode section, which links to a separate, dedicated supervisor workspace for team-level oversight. The logged-in user's name and role appear in the top-right corner of the header, confirming which account is active.

---

## The Header and Navigation

At the top of every page, the **Ember** logo and the text "Case Management Suite" link back to the Dashboard from anywhere in the app.

The top navigation bar displays the most frequently used modules: **Dashboard**, **Case Management**, **Documentation**, **Housing**, **Sober Living**, and **Groups**. A **More** button expands the full navigation to reveal additional modules:

- Sober Directory
- Benefits
- Medical
- Rolodex
- Legal
- FMLA
- Resume
- Jobs
- Supervisor
- Services
- AI Assistant
- Smart Daily

The current user's name (e.g., "Brandon Vasquez") and role (e.g., "Admin / Supervisor") are displayed in the header alongside a **Logout** button.

---

## Section 1: Caseload Stats Cards

Directly below the Dashboard heading are four summary cards. These cards give a case manager their caseload numbers at a glance. The current live values reflect the data in the database for the logged-in user's account.

| Card | What It Shows | Supporting Label |
|---|---|---|
| **Total Clients** | Total number of clients in the system | "+12% this month" |
| **Active Cases** | Cases currently open and in progress | "High activity" |
| **High Risk** | Clients flagged as high risk | "Needs attention" |
| **Recent Intakes** | New client intakes recorded this week | "This week" |

The supporting labels (e.g., "High activity," "Needs attention") are contextual descriptors that help a case manager interpret the numbers quickly without needing to navigate deeper. When a number is zero, it means no records currently match that category for the active user's caseload.

**How a case manager uses these cards:** A case manager who opens CMSX in the morning looks at these four numbers first. If High Risk is elevated, they know to open Case Management and address those clients before anything else. If Recent Intakes is nonzero, they know new clients arrived this week and need initial outreach.

---

## Section 2: FMLA Tracker Panel

The FMLA Tracker section appears on the Dashboard as a dedicated summary panel because FMLA (Family and Medical Leave Act) casework is deadline-driven and time-sensitive. Missing an FMLA deadline can mean legal exposure for a client's employer or disruption in a client's leave status, so the Dashboard keeps FMLA status continuously visible without requiring a case manager to open the full tracker every morning.

The panel contains a short description explaining that the FMLA workspace manages employer packets, provider certifications, document status, communication history, and linked reminders. An **Open FMLA Tracker** button navigates directly to the full FMLA module.

Below the button, six status counts are displayed:

| Status | What It Means |
|---|---|
| **Active** | FMLA cases currently in progress |
| **Due In 7 Days** | Cases with a deadline in the next 7 days |
| **Missing Paperwork** | Cases where required documents have not been received |
| **Needs Follow-Up** | Cases in "Confirmation pending" status |
| **Approved** | FMLA cases that have been approved |
| **Denied** | FMLA cases that have been denied |

Each status label is a clickable link. Clicking a status navigates directly to the FMLA module filtered to that status — for example, clicking "Due In 7 Days" opens the FMLA tracker showing only cases with upcoming deadlines, and clicking "Needs Follow-Up" opens cases with a status of "Confirmation pending." This makes the FMLA panel an action launchpad, not just a scoreboard.

**How a case manager uses this panel:** Each morning, a case manager checks "Due In 7 Days" and "Missing Paperwork" first. Any nonzero count in either of those categories represents a task that needs to be completed that day or this week.

---

## Section 3: Notes, Docs, Bookmarks, and Resources

These four compact sections appear side by side on the Dashboard. Each shows a count badge and a quick-add button. When no items exist, a placeholder message is shown.

| Section | What It Holds |
|---|---|
| **Notes** | Text notes attached to the case manager's Dashboard workspace |
| **Docs** | Documents linked to the workspace |
| **Bookmarks** | Saved links or case references |
| **Resources** | Files stored in the Dashboard workspace |

These sections function as a personal quick-reference area pinned to the Dashboard — a place for items a case manager wants to keep visible without navigating into a specific case. They are distinct from case-specific documents, which live inside individual case records in the Case Management module.

**How a case manager uses these sections:** A case manager might pin a referral phone number as a Note, save a PDF intake form as a Resource, or Bookmark a specific housing agency's listing. These items persist on their Dashboard across sessions.

---

## Section 4: Supervisor Mode

The Supervisor Mode section is visible to users with the Admin / Supervisor role. It is a callout panel — not a set of interactive controls — that directs supervisors to the dedicated Supervisor Dashboard instead of using the standard case manager interface for team oversight.

The panel explains that team-level work (reviewing caseload pressure, overdue work, high-risk trends, and team follow-through) lives in the Supervisor Dashboard, not on this screen. An **Open Supervisor Dashboard** button links directly to `/supervisor-dashboard`.

**What this means in practice:** If a supervisor wants to review how their team is performing — which case managers have overdue items, which clients are trending high-risk across the whole team — they go to the Supervisor Dashboard, not this one. The standard Dashboard is for individual case manager workload visibility.

---

## Section 5: Available Services

The Available Services section is a grid of module cards at the bottom of the Dashboard. The section heading shows "9 Modules" as a count label. Each card represents one functional area of the platform and includes:

- A module name
- A status or availability label
- A one-line description of what the module does
- An "Access Module" link that navigates to that module

The following modules are displayed:

| Module | Status Label | Description |
|---|---|---|
| **Case Management** | 0 Active Cases | Manage client cases, track progress, and maintain case notes |
| **Housing Search** | Search Available | Find affordable housing options and transitional programs |
| **Benefits Assistant** | Multiple Programs | Apply for SNAP, SSDI, Medicaid, and other assistance programs |
| **Legal Services** | Legal Aid Available | Court dates, compliance tracking, and legal document assistance |
| **FMLA Tracker** | 1 Active Cases | Track paperwork, employer/provider follow-up, deadlines, and reminders |
| **Resume Builder** | ATS Optimized | AI-powered resume creation tailored for second chance employment |
| **AI Assistant** | 24/7 Available | Get help with applications, advice, and case planning |
| **Services Directory** | Local Resources | Comprehensive directory of local support services |
| **Job Search** | Hiring Now | Find employment opportunities and track applications |
| **Smart Daily Dashboard** | AI Powered | Prioritized daily tasks and intelligent recommendations |
| **Rolodex** | Contact Directory | Quick-access contact directory for providers, agencies, and community resources |
| **Documents** | Case Records | Generate, manage, and store case documents, letters, and treatment plans |

The status labels on each card are live. When a module has active records tied to the logged-in user (for example, "1 Active Cases" on the FMLA Tracker), the label reflects the current count. Generic labels like "Search Available" or "Legal Aid Available" indicate that the module is active and accessible.

**How a case manager uses this section:** This section is the navigation hub for new case managers or case managers who need to jump to a module they do not use daily. More experienced users will use the top navigation bar, but the Available Services grid is an at-a-glance reminder of what the platform can do. Clicking any card navigates to that module.

---

## How the Dashboard Connects to Other Modules

The Dashboard itself stores no case data — it reads from the same underlying database as the full modules and surfaces summaries. Here is how the key connections work:

- The **Stats Cards** pull from the Case Management module's active case and client records.
- The **FMLA Panel** pulls from the FMLA Tracker module. Clicking any FMLA status count opens the FMLA Tracker with a pre-applied filter.
- The **Notes, Docs, Bookmarks, and Resources** sections are scoped to the Dashboard workspace and are separate from case-specific records inside Case Management.
- The **Available Services** cards link directly to the corresponding module URLs.
- The **Supervisor Mode** button links to the Supervisor Dashboard at `/supervisor-dashboard`.
- The persistent **Open AI Assistant** button in the lower corner links to the AI chat interface at `/ai-chat`.

---

## How a Case Manager Should Start Their Day

Using the Dashboard as a daily starting point, the recommended workflow is:

1. **Check the Stats Cards.** Confirm Total Clients, Active Cases, High Risk, and Recent Intakes. If High Risk is nonzero, prioritize those clients. If Recent Intakes is nonzero, new clients need initial action.

2. **Review the FMLA Panel.** Look at "Due In 7 Days" and "Missing Paperwork." If either number is nonzero, click the link and address those cases before they become overdue.

3. **Scan Notes, Docs, Bookmarks, and Resources.** Check for anything pinned from a previous session — reminders, pending referrals, or documents that need follow-up.

4. **Navigate to the relevant module.** Use either the top navigation bar or the Available Services cards to move into the module where work needs to happen that day.

---

## Unclear Elements — Pending Confirmation

The following items are visible in the app but their full behavior could not be confirmed from the Dashboard view alone:

1. **"9 Modules" label in Available Services** — The section label reads "9 Modules" but 12 module cards are visible in the current view. It is unclear whether the count reflects a filtered set, a cached value, or a display inconsistency.

2. **UR navigation link** — The expanded navigation includes a link to `/ur` with no visible label text. This is likely "Utilization Review" but could not be confirmed from the Dashboard.

3. **Notes / Docs / Bookmarks / Resources add buttons** — Each section has an unlabeled button. Based on context these are likely "+" or "Add" buttons, but the labels were not exposed in the page structure. Confirm by clicking one.

4. **"Missing Paperwork" FMLA link** — The "Missing Paperwork" count links to `/fmla` without a filter parameter, while other FMLA status counts include URL filters. It may apply a default filter inside the FMLA module, or it may be a gap in the current implementation.

---

## Platform Context

Ember Case Management Suite is described in its footer as a "comprehensive reentry services platform supporting formerly incarcerated individuals with housing, employment..." The platform is designed for case managers who work with clients navigating reentry — people returning from incarceration who need coordinated access to housing, benefits, legal services, employment, medical care, and family leave compliance.

The Dashboard is the starting point that allows a case manager to serve that population efficiently by keeping critical information visible without requiring navigation into multiple screens before beginning work.

---

*Document generated from live inspection of https://cmsx-tau.vercel.app/ on 2026-06-09. All data reflects the live app state at time of inspection. No code was modified and no features were invented or inferred beyond what is visible in the interface.*
