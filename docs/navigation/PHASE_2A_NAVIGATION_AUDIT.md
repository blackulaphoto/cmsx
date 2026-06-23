# Phase 2A — Navigation Architecture Audit

**Status:** Documentation / audit only. No runtime, route, auth, or shell behavior was changed in this phase.
**Date:** June 2026
**Scope owner:** Frontend (Ember / CMSX)
**Predecessors:** Phase 1A (app-shell cleanup), Phase 1B (public legal pages), Phase 1C (brand-token alignment).
**Goal of this document:** Produce a safe, evidence-based plan for replacing the top-nav `More` overflow pattern with a scalable collapsible left sidebar in a future **Phase 2B** implementation. This phase does **not** implement the sidebar.

---

## 1. Current navigation summary

The authenticated app shell is a single component, [`frontend/src/components/Layout.jsx`](../../frontend/src/components/Layout.jsx). It is the only authenticated chrome in the app and the only place navigation is defined. Public pages (Login, Onboarding, the five legal pages) render outside `Layout` and are unaffected by anything in this audit.

**Navigation surfaces that exist today (all inside `Layout.jsx`):**

1. **Top primary nav (desktop, `xl:` and up)** — renders `navigationItems.slice(0, 6)` as a horizontal row: Dashboard, Case Management, Admissions, Documentation, Housing, Sober Living.
2. **`More` dropdown (desktop)** — renders `navigationItems.slice(6)` (the remaining **16** items) in a single flat 256px-wide popover. This is the scaling problem this phase targets. It has no grouping, no scroll affordance beyond the popover height, and an active item buried inside it is only hinted at by highlighting the `More` button (`hasActiveSecondaryItem`).
3. **Mobile nav (`xl:hidden`)** — a single horizontal **overflow-scroll strip** that renders **all 22** `navigationItems` in one swipeable row beneath the header. No drawer, no grouping.
4. **Messenger icon** — always-visible quick link to `/messages` with an unread badge.
5. **Action Alerts bell** — popover (not navigation per se) summarizing reminders / FMLA / unread messages; each row deep-links to `/smart-dashboard`, `/fmla`, or `/messages`.
6. **User / Workspace menu** — dropdown with account + role + owner/platform links (see inventory). This is where Profile, Settings, Support, Supervisor, Owner Cockpit, Super Admin, and Logout live.

**Key structural facts that constrain Phase 2B:**

- Nav is **derived from one array** (`navigationItems`) plus two slices (`primaryNavigationItems`, `secondaryNavigationItems`) and one filter (`visibleNavigationItems`). A sidebar can reuse this single source of truth.
- Active state is computed with **exact match** `location.pathname === item.path`. Deep routes (e.g. `/admissions/:client_id/forms/:form_key`) therefore do **not** highlight their parent nav item today. This is relevant to both sidebar active-state and breadcrumbs.
- The root element is `min-h-screen w-full flex flex-col`; content is in `<main className="flex-1 w-full min-w-0">`. A left sidebar in Phase 2B will require changing this outer layout from a column to a row (sidebar + main) — **this is the single highest-risk structural change** and is called out in §7.
- Role gating is driven by `profile?.role === 'admin'` (`canAccessSupervisorMode`) and `isSuperAdmin` from `useAuth()`. There is no per-item `roles` field on `navigationItems` today — only `/supervisor-dashboard` is filtered, inline.
- **Route truth ≠ nav truth.** Several real routes in `App.jsx` are reachable but absent from `navigationItems` (Team, Billing, System Integrity, Integration Audit, legacy/enhanced dashboards, and all detail/sub-routes). The sidebar should not blindly surface all of them — see inventory "Belongs in sidebar?" column.

---

## 2. Current nav item inventory

### 2a. Primary top-nav items (`navigationItems[0..5]`)

| Label | Path | Icon | Role visibility | Current location | In sidebar? | Proposed group |
|---|---|---|---|---|---|---|
| Dashboard | `/` | `LayoutDashboard` | all | Top primary | Yes | Home |
| Case Management | `/case-management` | `Users` | all | Top primary | Yes | Clients & Care |
| Admissions | `/admissions` | `ClipboardCheck` | all | Top primary | Yes | Clients & Care |
| Documentation | `/documentation` | `ClipboardList` | all | Top primary | Yes | Clinical & Documentation |
| Housing | `/housing` | `MapPin` | all | Top primary | Yes | Housing & Resources |
| Sober Living | `/sober-living` | `Hotel` | all | Top primary | Yes | Housing & Resources |

### 2b. Secondary items currently inside `More` (`navigationItems[6..]`)

| Label | Path | Icon | Role visibility | Current location | In sidebar? | Proposed group |
|---|---|---|---|---|---|---|
| Groups | `/groups` | `BookOpen` | all | More | Yes | Clinical & Documentation |
| Sober Directory | `/sober-living-directory` | `Building2` | all | More | Yes | Housing & Resources |
| Benefits | `/benefits` | `Heart` | all | More | Yes | Clients & Care |
| Medical | `/medical` | `Stethoscope` | all | More | Yes | Clinical & Documentation |
| Rolodex | `/rolodex` | `Contact` | all | More | Yes | Housing & Resources |
| Legal | `/legal` | `Scale` | all | More | Yes | Clients & Care |
| FMLA | `/fmla` | `ClipboardList` | all | More | Yes | Clinical & Documentation |
| UR | `/ur` | `Bell` | all | More | Yes | Clinical & Documentation |
| Resume | `/resume` | `FileText` | all | More | Yes | Workforce & Reentry |
| Jobs | `/jobs` | `Briefcase` | all | More | Yes | Workforce & Reentry |
| Supervisor | `/supervisor-dashboard` | `BarChart3` | **admin only** (filtered via `canAccessSupervisorMode`) | More | Yes | Team & Admin |
| Services | `/services` | `Building2` | all | More | Yes | Housing & Resources |
| Messages | `/messages` | `MessageSquare` | all (also a standalone header icon) | More + header icon | Optional | Daily Work |
| AI Assistant | `/ai-chat` | `MessageSquare` | all | More | Yes | Daily Work |
| Smart Daily | `/smart-dashboard` | `Calendar` | all | More | Yes | Daily Work |
| Treatment Plan | `/treatment-plan` | `Brain` | all | More | Yes | Clinical & Documentation |

### 2c. Items in the User / Workspace dropdown (not in `navigationItems`)

| Label | Path | Icon | Role visibility | Current location | In sidebar? | Proposed group |
|---|---|---|---|---|---|---|
| My Profile | `/profile` | `User` | all | User menu | Yes | Account |
| My Caseload | `/case-management` | `Users` | all (alias of Case Management) | User menu | No (duplicate target) | — |
| Smart Daily | `/smart-dashboard` | `Calendar` | all (duplicate of nav) | User menu | No (duplicate target) | — |
| Supervisor Dashboard | `/supervisor-dashboard` | `BarChart3` | admin only | User menu | Yes (also in nav) | Team & Admin |
| Settings | `/settings` | `Settings` | all | User menu | Yes | Account |
| Help & Support | `/support` | `LifeBuoy` | all | User menu | Yes | Account |
| Owner Cockpit | `/owner` | `Landmark` | **super-admin only** (`isSuperAdmin`) | User menu (button → navigate) | Yes | Owner / Platform |
| Super Admin | `/super-admin` | `ShieldAlert` | **super-admin only** | User menu | Yes | Owner / Platform |
| Logout | — (action) | `LogOut` | all | User menu | Keep in account/user area | Account |

### 2d. Routes that exist in `App.jsx` but are NOT in any nav (reachable only by deep-link or in-page links)

| Path | Component | Notes / recommendation |
|---|---|---|
| `/enhanced-dashboard` | `EnhancedDashboard` | Backward-compat alias of `/`. Do **not** add to sidebar. |
| `/legacy-dashboard` | `Dashboard` | Legacy. Do **not** add to sidebar. |
| `/team` | `TeamManagement` | **admin only** (`roles={['admin']}`). **Candidate to surface** in Team & Admin group — currently orphaned from nav. |
| `/billing` | `Billing` | Reachable but unlinked from nav. **Candidate** for Account or Owner/Platform. SaaS/Stripe is dormant — surface cautiously, no behavior change. |
| `/system-integrity` | `SystemIntegrity` | Admin/diagnostic. Consider Owner/Platform, low priority. |
| `/integration-audit` | `IntegrationAudit` | Diagnostic. Consider Owner/Platform, low priority. |
| `/housing/case-manager` | `CaseManagerHousing` | Sub-page of Housing — belongs under Housing as a child/breadcrumb, not a top sidebar item. |
| `/housing/test` | `HousingTest` | Dev/test page. Do **not** surface. |
| `/client/:clientId` | `ClientDashboard` | Detail route — breadcrumb target, not a nav item. |
| `/case-management/:clientId` | redirect → `/client/:clientId` | Redirect only. |
| `/sober-living-directory/discovery` `/review` `/:listingId` | directory sub-pages | Children of Sober Directory — breadcrumb targets. |
| `/sober-living/:houseId` | `SoberLivingHouse` | Detail — breadcrumb target. |
| `/groups/sessions/:sessionId` | `GroupSessionDetail` | Detail — breadcrumb target. |
| `/admissions/new` | `AdmissionsNew` | Child of Admissions — breadcrumb target. |
| `/admissions/:client_id` | `AdmissionsPacket` | Detail — breadcrumb target. |
| `/admissions/:client_id/forms/:form_key` | `AdmissionsForm` | Deepest route in app — primary breadcrumb target. |

**Counts:** 22 items in `navigationItems` (6 primary + 16 in `More`); 9 entries in the user dropdown (2 are duplicate targets); ~16 additional routed pages/detail routes not in nav.

---

## 3. Proposed sidebar group structure

Grouped, collapsible left sidebar. Order top-to-bottom. Each group is a labeled section; items keep their existing icon + gradient. **No routes change** — every item points at its current path.

1. **Home**
   - Dashboard → `/` (executive / caseload overview — see §4)

2. **Daily Work**
   - Smart Daily → `/smart-dashboard` (morning command center — see §4)
   - Messages → `/messages`
   - AI Assistant → `/ai-chat`

3. **Clients & Care**
   - Case Management → `/case-management`
   - Admissions → `/admissions`
   - Benefits → `/benefits`
   - Legal → `/legal`

4. **Clinical & Documentation**
   - Documentation → `/documentation`
   - Treatment Plan → `/treatment-plan`
   - Groups → `/groups`
   - Medical → `/medical`
   - FMLA → `/fmla`
   - UR → `/ur`

5. **Housing & Resources**
   - Housing → `/housing`
   - Sober Living → `/sober-living`
   - Sober Directory → `/sober-living-directory`
   - Services → `/services`
   - Rolodex → `/rolodex`

6. **Workforce & Reentry**
   - Resume → `/resume`
   - Jobs → `/jobs`

7. **Team & Admin** *(admin only)*
   - Supervisor → `/supervisor-dashboard`
   - Team → `/team` *(currently orphaned from nav; recommended to surface here)*

8. **Owner / Platform** *(super-admin only)*
   - Owner Cockpit → `/owner`
   - Super Admin → `/super-admin`
   - *(optional, low priority)* System Integrity → `/system-integrity`, Integration Audit → `/integration-audit`

9. **Account** *(bottom-anchored, near user identity)*
   - My Profile → `/profile`
   - Settings → `/settings`
   - Billing → `/billing` *(optional; SaaS/Stripe dormant — surface as plain link only)*
   - Help & Support → `/support`
   - Logout *(action)*

**Notes on dedupe:** "My Caseload" and the user-menu "Smart Daily" are duplicate link targets; in the sidebar model they collapse into the single Case Management / Smart Daily entries. The standalone Messenger header icon and Action Alerts bell can remain in the top bar even after the sidebar lands (they are utility affordances, not primary navigation), or move into "Daily Work" — that is a Phase 2B design decision, not required for the architecture.

---

## 4. Dashboard vs Smart Daily positioning (documentation only — no rename, no rewrite)

These pages already exist and are **not** to be renamed or rewritten in Phase 2B. The sidebar should *position* them to make their distinct purposes legible:

- **Dashboard (`/`, `EnhancedDashboard`)** → place under **Home**, top of the sidebar. Position it as the **executive / caseload overview** — the landing surface and "where am I across everything" view.
- **Smart Daily (`/smart-dashboard`, `SmartDaily`)** → place at the **top of Daily Work**. Position it as the **morning command center / daily work queue** — the "what do I do today" surface. Action Alerts already deep-link here, reinforcing this role.

No copy, headings, or component logic change in this phase or in 2B's navigation work. Positioning is purely the grouping/order above.

---

## 5. Breadcrumb recommendations

Today, active highlighting is exact-match only, so deep routes appear "nowhere" in nav. Breadcrumbs (not nav highlighting) are the right fix. Recommended breadcrumb trails for the nested routes found in `App.jsx`:

| Route | Recommended breadcrumb trail |
|---|---|
| `/admissions/:client_id/forms/:form_key` | Admissions › {Client} › Forms › {Form} |
| `/admissions/:client_id` | Admissions › {Client} (packet) |
| `/admissions/new` | Admissions › New |
| `/client/:clientId` | Case Management › {Client} |
| `/sober-living-directory/:listingId` | Sober Directory › {Listing} |
| `/sober-living-directory/discovery` | Sober Directory › Discovery |
| `/sober-living-directory/review` | Sober Directory › Review |
| `/sober-living/:houseId` | Sober Living › {House} |
| `/groups/sessions/:sessionId` | Groups › Session {id} |
| `/housing/case-manager` | Housing › Case Manager Tools |
| `/settings`, `/support`, `/profile`, `/billing` | Account › {Page} (shallow; breadcrumb optional) |

**Recommendation:** Breadcrumbs should be a **separate, additive Phase 2B (or 2C) component** rendered at the top of `<main>`, driven by a small route→label map (dynamic segments resolved from already-loaded page data where available, otherwise shown as the raw id). They do **not** require changes to the route table. Keep them out of the initial sidebar PR to limit blast radius.

---

## 6. Mobile navigation recommendation

**Current mobile behavior:** a single horizontal overflow-scroll strip (`xl:hidden`) rendering **all 22** items in one swipe row. It works and is low-risk, but does not scale and has no grouping.

**Recommended Phase 2B mobile model — hamburger drawer:**

- **Trigger:** a hamburger button in the header (visible `< xl`).
- **Drawer:** the same grouped sidebar content slides in from the left as an overlay (`fixed`, above content, `z` above header), with a dimmed backdrop.
- **Overlay behavior:** clicking the backdrop or pressing **Escape** closes the drawer (reuse the existing outside-click / Escape pattern already implemented for `openMenu` in `Layout.jsx`, lines ~218–234).
- **Active route state:** highlight the active item using the same logic the desktop sidebar uses (exact match, plus optional `startsWith` for parent groups so deep routes highlight their parent).
- **Close after navigation:** close the drawer on route change — `Layout.jsx` already has a `useEffect(..., [location.pathname])` that closes `isMoreOpen` and `openMenu`; extend the same pattern to the drawer.
- **Role-based visibility:** the drawer renders the exact same filtered group list as desktop (admin / super-admin groups hidden for non-privileged users).

**Safer short-term option (recommended sequencing):** ship the **desktop sidebar first** and **keep the existing mobile scroll strip unchanged** in the same PR, then convert mobile to the drawer in a fast follow. This de-risks the largest layout change (desktop column→row) from the mobile interaction change. The scroll strip is already proven and regression-tested by manual use, so leaving it untouched initially is the lower-risk path.

---

## 7. Risks and regression concerns

1. **Outer layout flip (highest risk).** `Layout.jsx` root is currently `flex flex-col` (header on top, `<main flex-1>` below). A persistent left sidebar requires a row layout (sidebar + main column). This touches the single most-rendered component in the app and every page renders inside it. Mitigation: introduce the sidebar as a sibling of `<main>` inside a new flex-row wrapper, preserve the sticky header, and verify `min-w-0` is retained on `<main>` to prevent flex overflow blowouts on wide tables (Housing, directories).
2. **Active-state semantics.** Switching from exact-match to `startsWith` for parent highlighting can cause false positives (e.g. `/` matching everything). Must anchor `/` to exact-match only.
3. **Existing Layout test coupling.** [`frontend/src/pages/OwnerCockpit.test.jsx`](../../frontend/src/pages/OwnerCockpit.test.jsx) renders `<Layout>` directly and asserts on the **Owner Cockpit** button (found via "button whose text includes 'Owner'", then by accessible name `/Owner Cockpit/i`) and super-admin gating. If the Owner Cockpit control moves from the user dropdown into a sidebar group, **these three tests must be updated in lockstep** or they break. This is the main test-fragility hotspot.
4. **Duplicate-target confusion.** "My Caseload" → `/case-management` and user-menu "Smart Daily" → `/smart-dashboard` duplicate sidebar items. Removing them from the user menu is fine, but if any test or muscle-memory relies on them, note it.
5. **Z-index / sticky stacking.** Header is `sticky top-0 z-50`. A mobile drawer overlay and its backdrop must sit above that; a desktop sidebar must not fight the sticky header. Audit z-layers when implementing.
6. **Role gating drift.** Today gating is ad-hoc (`canAccessSupervisorMode`, `isSuperAdmin`, inline filter). Moving to a declarative per-item/`per-group` `roles` field is cleaner but must reproduce the exact current visibility (only `/supervisor-dashboard`, `/owner`, `/super-admin`, and `/team` are privileged).
7. **Wide-content pages.** Housing, Sober Directory, and tables assume near-full viewport width. A persistent sidebar reduces content width; verify these pages don't horizontally clip. A collapsible (icon-only) sidebar mode mitigates this.
8. **Scope creep into routes/auth/backend.** Surfacing orphaned routes (Team, Billing) is tempting but must remain link-only; no route, guard, billing, Stripe, or SaaS-flag changes.

---

## 8. Proposed Phase 2B implementation steps

1. **Extract nav config.** Move `navigationItems` into a shared config module (e.g. `frontend/src/config/navigation.js`) and add `group` + optional `roles` metadata per item. Keep paths/icons/gradients identical. (Pure refactor, no behavior change.)
2. **Build `<Sidebar>` (new component).** A new grouped, collapsible sidebar that consumes the config and `useAuth()` for role filtering. Do **not** reuse the legacy `Sidebar.jsx` (see §10) — author fresh in Ember styling. Desktop-only visibility first (`hidden xl:flex`).
3. **Re-layout `Layout.jsx`.** Wrap header + a new flex-row (`<Sidebar>` + `<main>`). Preserve sticky header, `flex-1`, `min-w-0`. Keep the `More` dropdown removed/replaced by the sidebar on desktop.
4. **Active state + collapse.** Exact-match for `/`, `startsWith` for parents; persist collapsed/expanded state (local state or `localStorage`).
5. **Update Layout-coupled tests** (see §9) in the same PR as any element that moves (esp. Owner Cockpit control).
6. **Mobile drawer (fast follow or same PR, see §6).** Hamburger + overlay drawer reusing the existing outside-click/Escape/route-change close effects; optionally keep the scroll strip until the drawer is verified.
7. **(Separate PR) Breadcrumbs.** Additive component at top of `<main>`, route→label map; no route changes.
8. **Cleanup pass.** Remove duplicate user-menu targets if desired; optionally surface orphaned admin routes (Team) — link-only.

Sequencing recommendation: **PR1 = config extraction + desktop sidebar + Layout re-layout + test updates** (keep mobile strip as-is). **PR2 = mobile drawer.** **PR3 = breadcrumbs.** Small, reversible PRs.

---

## 9. Testing plan for Phase 2B

**Existing tests that will be affected / must be re-verified:**
- `frontend/src/pages/OwnerCockpit.test.jsx` — renders `<Layout>` and asserts Owner Cockpit button presence, super-admin gating, and navigation to `/owner`. **Will need updating** if the Owner Cockpit control relocates into the sidebar. (3 tests in the "Owner Cockpit nav visibility" describe block.)
- Any other test importing `Layout` (currently only OwnerCockpit.test.jsx does).

**New tests to add in Phase 2B:**
1. **Sidebar renders all expected groups/items** for a standard case-manager profile (no admin/super-admin groups).
2. **Role gating:** admin sees Team & Admin group; non-admin does not. Super-admin sees Owner / Platform group; others do not. (Mirror existing `useAuth` mock pattern from OwnerCockpit.test.jsx.)
3. **Active state:** the item matching `location.pathname` gets the active class; `/` does not falsely match other routes.
4. **Mobile drawer:** opens on hamburger click; closes on backdrop click, Escape, and route change.
5. **No-duplicate / link-integrity:** every sidebar item's `to` resolves to a real route in `App.jsx` (guards against dead links).
6. **(Breadcrumb PR)** breadcrumb trail renders correct labels for representative deep routes (`/admissions/:client_id/forms/:form_key`, `/client/:clientId`).

Test harness mirrors the existing convention: `@testing-library/react` + `MemoryRouter` with `initialEntries`, `useAuth` mocked.

---

## 10. Legacy `Sidebar.jsx` disposition

[`frontend/src/components/Sidebar.jsx`](../../frontend/src/components/Sidebar.jsx) exists but is **imported nowhere** (dead component). It is **not suitable for reuse**:
- Uses the **light theme** (`bg-white`, `text-gray-700`, `bg-primary-gradient`) — clashes with Ember's dark slate/purple shell.
- Uses the legacy `Home` icon and a **stale, hardcoded** menu (only ~10 items, wrong labels like "Case Management" → `/`, "Job Search" → `/jobs`) plus **fake hardcoded "Quick Stats"** (`24`, `12`, `156`, `3`).
- Predates the current `navigationItems` source of truth and role gating.

**Recommendation: ignore / replace, do not reuse.** Phase 2B should author a fresh `Sidebar` component in Ember styling driven by the extracted nav config. The legacy file can be deleted in the Phase 2B cleanup pass (it is unreferenced, so deletion is zero-risk), but deleting it is out of scope for this audit phase.

---

## 11. Explicit list of files likely to change in Phase 2B

| File | Expected change |
|---|---|
| `frontend/src/components/Layout.jsx` | Re-layout to row (sidebar + main); remove/replace desktop `More` dropdown; add hamburger trigger; reuse close-on-route-change effects. |
| `frontend/src/config/navigation.js` *(new)* | Extracted nav config with `group` + `roles` metadata (single source of truth). |
| `frontend/src/components/Sidebar.jsx` | New Ember-styled grouped sidebar (legacy file replaced, not reused; likely deleted in cleanup). |
| `frontend/src/components/MobileNavDrawer.jsx` *(new, PR2)* | Mobile overlay drawer. |
| `frontend/src/components/Breadcrumbs.jsx` *(new, PR3)* | Additive breadcrumb component. |
| `frontend/src/pages/OwnerCockpit.test.jsx` | Update Owner Cockpit control assertions if that control relocates. |
| `frontend/src/components/Sidebar.test.jsx` / `MobileNavDrawer.test.jsx` *(new)* | New nav tests per §9. |

**Not expected to change:** `App.jsx` route table, `ProtectedRoute`, `AuthContext`, any backend, DB, env, billing/Stripe, SaaS flags, or auth logic.

---

## 12. Validation (this phase)

This is a **documentation-only** phase. No `.jsx`, `.js`, config, route, or auth files were modified — only this Markdown file under `docs/navigation/` was added. Frontend tests and build were therefore **not run** for this phase, because no runtime code changed and there is nothing for them to validate; the existing 129-test suite remains valid as-is. The app builds exactly as it did before this document was added.
