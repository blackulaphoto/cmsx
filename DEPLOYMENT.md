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

## PostgreSQL Migration Note
- `DATABASE_URL` is now first-class for SQLAlchemy services, including async Postgres URLs.
- Existing module-level SQLite code paths still need phased migration to SQLAlchemy/Postgres.
- Recommended order:
  1. Core clients + reminders + case management
  2. AI memory + dashboard analytics
  3. Domain modules (housing, benefits, legal, jobs, services)
