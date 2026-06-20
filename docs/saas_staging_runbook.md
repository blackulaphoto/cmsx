# SaaS Staging + Rollback Runbook

Manual steps to stand up a **staging** environment with multi-tenancy turned on,
prove org isolation there, and roll back safely. Brandon executes these in
Railway/Vercel by hand — **nothing in this file is run automatically**, and no
code here flips production.

> ⚠️ **Stop condition / golden rule:** Do **NOT** set `MULTI_TENANT_ENABLED=true`
> in **production** until staging has passed every check in §4 and §5. Production
> stays single-org (flag unset/false) until that gate is met.

Related artifacts:
- `scripts/saas_harness.py` — local 2-org isolation validator (run before you even touch staging).
- `tests/test_tenancy_two_org_wall.py` — the same wall, as a CI test.
- `backend/shared/db_path.py` — `CMSX_DB_DIR` override used to isolate storage.
- `backend/shared/tenancy.py` — `multi_tenant_enabled()` reads `MULTI_TENANT_ENABLED`.

---

## 0. Pre-flight (local, before any cloud change)

```bash
# From repo root, with the feature branch checked out:
python scripts/saas_harness.py            # expect: RESULT: PASS, exit 0
python -m pytest tests/test_tenancy_*.py  # expect: all green
```

If the harness does not print **PASS**, stop — do not provision staging.

---

## 1. Create the staging environment (Railway)

You want a **separate** backend instance with its **own database volume**, so
staging data never mixes with production data.

Pick one of:

**Option A — New Railway environment (recommended).**
1. Railway → your project → **Environments** → **New Environment** (e.g. `staging`),
   duplicating `production`.
2. In the `staging` environment, confirm the backend service deploys from the
   intended branch (use `feat/saas-activation-harness-v1` or `master` after merge —
   your choice; staging should track whatever you want to validate).
3. Ensure the staging service has its **own Volume** (do not share the production
   volume). Note its mount path (e.g. `/mnt/data`).

**Option B — New service in the same project.**
1. Add a new service from the same GitHub repo; set its branch.
2. Attach a **fresh** Volume (new mount path). Never point it at production's volume.

Either way, the result is: a staging backend URL (e.g.
`https://cmsx-staging-XXXX.up.railway.app`) backed by an **empty, isolated** volume.

---

## 2. Staging environment variables

Set these on the **staging** service only (Railway → service → **Variables**):

| Variable | Staging value | Notes |
|---|---|---|
| `MULTI_TENANT_ENABLED` | `true` | **Staging only.** This is the whole point of staging. |
| `RAILWAY_VOLUME_MOUNT_PATH` | `/mnt/data` (or your staging volume mount) | DBs persist at `<mount>/databases/`. Keep distinct from prod. |
| `AUTH_ADMIN_EMAILS` | your test admin email(s) | Lets you register an admin in staging. |
| Firebase / OpenAI / other secrets | mirror production | Copy the rest of prod's vars so the app boots identically. |

Optional (only if you want to force a custom DB dir instead of the volume default):

| Variable | Value |
|---|---|
| `CMSX_DB_DIR` | absolute path to an isolated dir | Takes precedence over `RAILWAY_VOLUME_MOUNT_PATH`. |

**Do not** add `MULTI_TENANT_ENABLED` to the production service. Leave production's
variable list untouched.

Frontend (Vercel), if you want a staging UI: point a staging deployment's
`VITE_API_BASE_URL` (or same-origin proxy rewrite) at the staging backend URL.
This is optional — you can validate the API directly with the steps below.

---

## 3. Seed two orgs in staging

Two organizations with one user + one client each is enough to prove the wall.
The cleanest way that exercises the real signup/registration path:

1. **Org A user:** sign up / log in through the staging app (or Firebase) with an
   admin email listed in `AUTH_ADMIN_EMAILS`. The backend assigns them an
   `org_id` (default `org_default` unless org provisioning sets one).
2. **Org B user:** repeat with a *different* account that resolves to a *different*
   `org_id`.
3. As each user, create a client (and a reminder / message thread if you want to
   exercise those modules) through the normal UI/API.

> Org provisioning UI (assigning distinct `org_id`s per signup) is **not built yet**
> — it is the next milestone after this gate. For staging validation you may need
> to set the two test users' `org_id` directly in the staging `auth.db`
> (`user_profiles.org_id`) to `org_a` / `org_b`. This is a manual staging-only step;
> never edit production data this way.

---

## 4. Prove isolation in staging

Run the **local** harness first (it already proves the code path):

```bash
python scripts/saas_harness.py   # RESULT: PASS
```

Then verify the **hosted** staging instance behaves the same, manually:

1. Log in as **Org A**. Confirm the client list, reminders, and messages show only
   Org A's records.
2. Log in as **Org B**. Confirm you see only Org B's records — **never** Org A's.
3. Try to open an Org A record's URL/ID while logged in as Org B → expect **404**
   (not 403, not the record).
4. **Admin status panel:** as an admin, open the **Supervisor Dashboard**. The
   "System / SaaS Status" card must show **SaaS mode: ON**, plus your `org_id`,
   `org_role`, `role`, `case_manager_id`, and email.

✅ **Pass = every cross-org check returns nothing/404 AND the status card reads ON.**
Any leak (Org B sees Org A) is a hard fail — go to §6.

---

## 5. Confirm staging health

```bash
# Backend health (expect HTTP 200 + module list):
curl -s https://cmsx-staging-XXXX.up.railway.app/api/health

# AI endpoints must reject unauthenticated calls with 401 (not 500):
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://cmsx-staging-XXXX.up.railway.app/api/ai/assistant
```

Check the Railway deploy log shows the expected module count loaded and no startup
errors. Compare against production's `/api/health` for parity (same modules).

---

## 6. Rollback (if staging fails)

Rolling back staging is low-risk because production was never touched:

1. Railway → **staging** service → Variables → set `MULTI_TENANT_ENABLED=false`
   (or delete the variable). Redeploy.
2. Verify `/api/health` is green and the status panel now reads **SaaS mode: OFF**.
3. If staging data got into a bad state, wipe the staging **volume** (it is
   isolated and disposable) and re-seed per §3. Never touch the production volume.
4. File what failed (which module leaked, which check) before re-attempting.

Because production never had the flag set, **no production rollback is required** —
production was single-org the entire time.

---

## 7. Production decision (out of scope for v1 — do NOT do this yet)

Only after §4 and §5 pass cleanly, and after org-provisioning/seat management exist,
is it appropriate to *consider* `MULTI_TENANT_ENABLED=true` in production. That is a
separate, deliberate decision with its own change record — it is **not** part of this
harness and must not be done as a side effect of staging work.
