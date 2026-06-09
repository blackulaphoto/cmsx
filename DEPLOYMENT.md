# Railway + Vercel Deployment

## Backend (Railway)
1. Deploy from repo root.
2. Use `railway.json` start command.
3. Configure environment variables from `.env.example`.
4. Run smoke checks before deploy:
   ```bash
   python scripts/predeploy_smoke.py
   ```
5. Configure persistent storage for:
   - `/app/databases`
   - `/app/uploads`
   - `/app/logs`

## Frontend (Vercel)
1. Deploy from `frontend/`.
2. Set `VITE_API_BASE_URL` to your Railway backend URL, or leave blank to use `/api` rewrites.
3. Ensure `frontend/vercel.json` rewrite destination points to the backend.
4. Add these Firebase web env vars in Vercel Project Settings for the frontend:
   - `VITE_FIREBASE_API_KEY`
   - `VITE_FIREBASE_AUTH_DOMAIN`
   - `VITE_FIREBASE_PROJECT_ID`
   - `VITE_FIREBASE_STORAGE_BUCKET`
   - `VITE_FIREBASE_MESSAGING_SENDER_ID`
   - `VITE_FIREBASE_APP_ID`
   - `VITE_FIREBASE_MEASUREMENT_ID`
5. Add these backend auth env vars to the backend deployment:
   - `FIREBASE_ADMIN_SERVICE_ACCOUNT_JSON`
   - `FIREBASE_PROJECT_ID`
   - `AUTH_ADMIN_EMAILS`
   - `DEEPGRAM_API_KEY`

## Voice Transcription
- Set `DEEPGRAM_API_KEY` only in the backend server environment. Do not add it to Vercel frontend env vars.
- The frontend uploads recorded audio to `POST /api/transcribe`; the backend sends the audio to Deepgram and does not persist raw audio in v1.
- `DEEPGRAM_API_KEY` must never appear in browser bundles, browser storage, or API responses.

## Diagnosing 401 Errors

A 401 response almost always means an auth/configuration problem, **not** a missing API route.
Work through these checks in order:

### 1. Missing Vercel Firebase env vars (most common)
If any of the four required frontend Firebase env vars are absent, `firebase.js` sets
`auth = null` and `apiFetch` throws `"No Firebase user is signed in"` **before** any
network request is made. The browser shows this as a 401-style error even though the
backend was never contacted.

**Required keys** (set in Vercel → Project → Settings → Environment Variables):

| Variable | Required | Notes |
|---|---|---|
| `VITE_FIREBASE_API_KEY` | Yes | |
| `VITE_FIREBASE_AUTH_DOMAIN` | Yes | |
| `VITE_FIREBASE_PROJECT_ID` | Yes | |
| `VITE_FIREBASE_APP_ID` | Yes | |
| `VITE_FIREBASE_STORAGE_BUCKET` | No | Needed for Storage features |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | No | Needed for Cloud Messaging |
| `VITE_FIREBASE_MEASUREMENT_ID` | No | Needed for Analytics |

After setting or changing any `VITE_*` variable on Vercel, **trigger a new deployment**
(Vercel bakes env vars into the build artifact; changing the value alone is not enough).

### 2. User not signed in
If Firebase is configured but `auth.currentUser` is null (not logged in, token expired,
or the auth provider rejected the credential), `apiFetch` throws the same error.
Check: open the app → Network tab → look for a 401 on an `/api/*` request. If you see
no network request at all, the error originated in the frontend — the user needs to log in.

### 3. Token expired
Firebase ID tokens expire after 1 hour. The SDK auto-refreshes them in the background, but
if the browser tab is paused/offline too long, `currentUser` may be non-null while the
cached token is expired. A page reload forces a fresh token fetch.

### 4. Backend Firebase config missing (Railway)
The backend auth middleware verifies tokens using either:
- Firebase Admin SDK (`FIREBASE_ADMIN_SERVICE_ACCOUNT_JSON` + `FIREBASE_PROJECT_ID`), OR
- Google public certs fallback (`google.oauth2.id_token.verify_firebase_token`) which
  reads the `aud` claim from the JWT and does **not** require backend env vars.

The fallback means most 401s are frontend config issues, not backend config issues.
If you do need the Admin SDK (for advanced features), set both:
- `FIREBASE_ADMIN_SERVICE_ACCOUNT_JSON` — full service account JSON as a single-line string
- `FIREBASE_PROJECT_ID` — must match the `projectId` in your frontend Firebase config

### 5. What NOT to do
- Do not add `authRequired: false` to `apiFetch` calls to silence a 401. That bypasses
  auth for all users and exposes the endpoint publicly.
- Do not change the backend auth middleware or route exception handlers to suppress 401s.
- Do not rewrite API route code unless the endpoint itself is broken. Auth errors are
  configuration problems, not code problems.

### Quick checklist
```
[ ] VITE_FIREBASE_API_KEY set in Vercel
[ ] VITE_FIREBASE_AUTH_DOMAIN set in Vercel
[ ] VITE_FIREBASE_PROJECT_ID set in Vercel
[ ] VITE_FIREBASE_APP_ID set in Vercel
[ ] Vercel redeploy triggered after setting vars
[ ] User is signed in (check auth.currentUser in browser console)
[ ] No token-expiry issues (try a hard refresh)
```

## PostgreSQL Migration Note
- `DATABASE_URL` is now first-class for SQLAlchemy services, including async Postgres URLs.
- Existing module-level SQLite code paths still need phased migration to SQLAlchemy/Postgres.
- Recommended order:
  1. Core clients + reminders + case management
  2. AI memory + dashboard analytics
  3. Domain modules (housing, benefits, legal, jobs, services)
