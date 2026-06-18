# Multi-Tenancy Foundation (Phases 0–2)

This documents the additive multi-tenancy work on the `feat/tenancy-phase0-foundation`
branch. It is **additive and reversible**: with `MULTI_TENANT_ENABLED=false` (the
default) the app behaves as the existing single-agency product.

## The flag

`MULTI_TENANT_ENABLED` (env var, default `false`) is read by
`backend/shared/tenancy.py`:

- **false (default, "one-org mode"):** org isolation is dormant. `resolve_org_id(user)`
  always returns `DEFAULT_ORG_ID` (`org_default`). Every existing row is backfilled
  into the default org. Behavior matches the pre-tenancy app.
- **true:** `resolve_org_id(user)` returns the user's `org_id`; client access is
  isolated per org.

## Phase summary

- **Phase 0 — Foundation** (`organizations` + `invites` tables, `org_id`/`org_role`
  on `user_profiles`, default-org seed + backfill, org fields on `AuthenticatedUser`).
- **Phase 1 — Client root** (`org_id` on the `clients` table + backfill; `create`
  stamps org; `list` filters by org only when the flag is on; org isolation enforced
  in `assert_client_access`, failing closed with `404` on cross-org/missing-org).
- **Phase 2 — Guard coverage** (central `require_user` / `require_org_admin` guards;
  documented route classification; client-data endpoints in housing/jobs/resume
  guarded with `require_user` + `assert_client_access`; mixed routes guard only the
  client-specific branch; global search/reference + services routes left exempt).
- **Phase 3A — Messages** (`org_id` on `message_threads` only; threads, message
  reads/writes, and the `/case-managers` picker are org-scoped when the flag is on;
  **announcements are org-scoped** (not broadcast across customers); cross-org thread
  access returns `404`; cross-org participants are rejected, not silently dropped).
- **Phase 3B — Dashboard aggregates** (no schema change; `/dashboard/stats`,
  `/clients`, `/case/{id}`, and the supervisor `/overview` are org-scoped when the
  flag is on — admin/supervisor means "all in my org"; cross-org `case_manager_id`
  params yield empty, cross-org `case_id` returns `404`. The `workspace_content.db`
  admin-bypass on notes/docs/bookmarks/resources is **deferred** to a later phase).
- **Phase 3C — Workspace content** (`org_id` on dashboard items + rolodex, plus
  defense-in-depth `org_id` on client-linked tables; backfilled to `org_default`.
  When the flag is on, dashboard notes/docs/bookmarks/resources enforce org on the
  admin-bypass by-id paths (cross-org → 404) and the rolodex becomes org-scoped
  (each org its own shared rolodex). Client-linked tables keep relying on
  `assert_client_access`. `documentation_brand_resources` enforcement is deferred).

## IMPORTANT: what Phase 2 does and does NOT do

Phase 2 added `require_user` + `assert_client_access` to previously-unguarded
client-data endpoints in housing/jobs/resume. As a result, **existing
case-manager/client ownership rules now apply to those endpoints even when
`MULTI_TENANT_ENABLED=false`.**

> **This does not activate multi-tenancy.** It only applies the existing
> case-manager/admin client-ownership rules (already enforced across the rest of
> the app and the core clients API) to client-data endpoints that were previously
> unguarded. Org isolation remains dormant until `MULTI_TENANT_ENABLED=true`.

Concretely, with the flag **off**:
- org isolation is dormant; default-org behavior is preserved;
- a case manager still cannot use these endpoints against another case manager's
  client (closing a pre-existing gap), and admins retain full access.

## Intentionally deferred (not in Phases 0–2)

- Resume endpoints keyed by `resume_id` (`view`, `preview-html`, `generate-pdf`,
  `download`) and `GET /api/resume/clients` — these need a resume→client→org
  resolution and the resume DB bridge to be org-aware. Deferred to a later phase.
- `org_id` on workspace/domain module tables (Phase 3 inventory pending).
- Invite endpoints/UI, org-admin UI, billing — not built yet.

## Route classification

The authoritative classification lives in `backend/auth/authorization.py`
(`TENANCY_GUARDED_ROUTES`, `TENANCY_MIXED_ROUTES`, `TENANCY_CROSS_ORG_EXEMPT`).
A doc-drift test in `tests/test_tenancy_guard_coverage.py` asserts the guarded set
matches reality.
