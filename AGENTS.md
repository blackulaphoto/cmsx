# CMSX Agent Safety Rules

This repository's canonical workspace is:
`C:\Users\brandon\Downloads\cmsuite DO NOT TOUCH\case_manager_suite_production_ready(1)\case_manager_suite_deployment\CASE_MANAGER_SUITE2`

Expected GitHub remote:
`https://github.com/blackulaphoto/cmsx.git`

Production frontend:
`https://cmsx-tau.vercel.app/`

Production backend health:
`https://cmsx-production-088d.up.railway.app/health`

Correct Railway project:
`CSMX`

Important deployment boundary:
- `satisfied-radiance` is Persona Emulator and must not deploy CMSX.

## Deployment Boundary Rules

- CMSX GitHub repo is `blackulaphoto/cmsx`.
- Correct Railway project for CMSX is `CSMX`.
- Correct production frontend for CMSX is Vercel `cmsx-tau`.
- Persona Emulator is a separate project and must never deploy, check, report status on, or attach to CMSX commits, PRs, or `master`.
- If any commit status, PR check, deploy check, or integration report shows `persona emulator - cmsx` or any non-`CSMX` deploy/check attached to CMSX, stop and audit integrations before merging.
- Agents must report any non-`CSMX` deploy/check attached to CMSX commits or PRs, including the exact check name, provider, and target URL when available.
- Do not treat Persona Emulator success as CMSX deployment proof.
- Do not change Railway, Vercel, GitHub app, or deployment settings during that audit unless Brandon explicitly approves.

## Before Coding

Always verify the current repo before making edits:
- `git rev-parse --show-toplevel`
- `git remote -v`
- `git branch --show-current`
- `git log -1 --oneline`
- `git status --short`

If the repo path, remote, branch, or commit is unexpected, stop and ask Brandon.

If the repo is dirty, classify the dirty tree before coding.

## Staging And Commit Safety

- Never use `git add .`
- Stage only explicit intended files.
- Keep PR scope clean and small.
- Use small PRs.
- Report exact files changed.
- Report tests and builds actually run.

## Never Commit Local Artifacts

Do not commit:
- Local DB files
- Runtime DB files
- Cache DB files
- Test DB files
- Generated artifacts
- Virgil folders
- `job-search-system-copy`
- Personal PDFs
- Spreadsheets
- Loose research files

Examples include:
- `databases/*.db`
- `backend/databases/*.db`
- `virgil-*`
- `virgil-st/`
- `job-search-system-copy/`
- Loose local reports and assets in the repo root

## Out Of Scope Unless Explicitly Requested

Do not touch these areas unless Brandon explicitly scopes them in:
- DB files
- Env vars
- Auth logic
- Billing
- Stripe
- SaaS flags
- Railway settings
- Vercel settings
- Route paths
- Deployment settings

Also avoid unrelated feature work, refactors, or cleanup while addressing a scoped task.

## Working Rules

- Prefer the smallest change that solves the scoped task.
- Do not stage unrelated dirty files.
- If you find unexpected local artifacts or foreign project folders, report them instead of hiding them.
- If unsure, stop and ask Brandon.
