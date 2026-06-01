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

## PostgreSQL Migration Note
- `DATABASE_URL` is now first-class for SQLAlchemy services, including async Postgres URLs.
- Existing module-level SQLite code paths still need phased migration to SQLAlchemy/Postgres.
- Recommended order:
  1. Core clients + reminders + case management
  2. AI memory + dashboard analytics
  3. Domain modules (housing, benefits, legal, jobs, services)
