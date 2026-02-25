# Case Management Suite v2.0

A comprehensive case management platform for reentry services, consolidating the best features from multiple codebases.

## Project Structure

```
CASE_MANAGER_SUITE2/
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── backend/               # Backend modules
│   ├── main_backend.py    # Original unified backend (reference)
│   ├── modules/           # Feature modules
│   │   ├── housing/       # Housing search and resources
│   │   ├── benefits/      # Benefits assistance
│   │   ├── legal/         # Legal services
│   │   ├── resume/        # Resume builder
│   │   ├── ai/           # AI assistant
│   │   ├── services/     # Social services directory
│   │   ├── jobs/         # Job search and placement
│   │   └── reminders/    # Task management and reminders
│   ├── api/              # API routes
│   ├── services/         # Business logic services
│   └── utils/            # Utility functions
│       ├── database.py   # Database utilities
│       └── simple_search_replacement.py
├── frontend/             # Frontend application (to be added)
├── config/               # Configuration files
│   ├── config.py         # Main configuration
│   └── main_config.py    # Original config (reference)
├── databases/            # SQLite database files
├── static/               # Static assets (CSS, JS, images)
├── templates/            # HTML templates
│   ├── unified_case_manager_platform.html
│   ├── case_management_dashboard.html
│   ├── housing_search_dashboard.html
│   ├── benefits_dashboard.html
│   ├── resume_builder_dashboard.html
│   ├── legal_services_dashboard.html
│   ├── ai_chat_assistant.html
│   ├── services_directory_dashboard.html
│   └── smart_daily_dashboard.html
├── logs/                 # Application logs
└── 2nd chance ui/        # Legacy UI files (migrated)
```

## ✅ Completed Features

- **✅ Base Framework**: FastAPI application with modular router structure
- **✅ Configuration**: Centralized config management
- **✅ Database Utilities**: Database connection management
- **✅ Module Integration**: All core modules imported and routed
- **✅ Frontend Templates**: HTML dashboards migrated and integrated
- **✅ Static Assets**: CSS, JS, and other assets copied
- **✅ Database Files**: All SQLite databases copied

## 🔧 Current Status

**Loaded Modules:**
- ✅ Benefits module
- ✅ Legal module  
- ✅ Resume module
- ✅ AI module
- ✅ Reminders module

**Modules with Dependencies:**
- ⚠️ Housing module (missing simple_search_replacement - FIXED)
- ⚠️ Services module (missing simple_search_replacement - FIXED)
- ⚠️ Jobs module (missing simple_search_replacement - FIXED)

## Features

- **Case Management**: Complete client management system
- **Housing Resources**: Housing search and referral system
- **Benefits Assistance**: Benefits application and tracking
- **Legal Services**: Legal case management
- **Resume Builder**: AI-powered resume creation
- **AI Assistant**: Intelligent case management assistance
- **Job Search**: Employment services integration
- **Task Management**: Smart reminders and task optimization

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Run the application:
   ```bash
   python main.py
   ```

4. Access the application at: http://localhost:8000

## API Endpoints

- `/api/health` - Health check with module status
- `/api/housing/*` - Housing resources
- `/api/benefits/*` - Benefits assistance
- `/api/legal/*` - Legal services
- `/api/resume/*` - Resume builder
- `/api/ai/*` - AI assistant
- `/api/services/*` - Social services
- `/api/jobs/*` - Job search
- `/api/reminders/*` - Task management

## Frontend Pages

- `/` - Main unified dashboard
- `/case-management` - Case management dashboard
- `/housing` - Housing search dashboard
- `/benefits` - Benefits dashboard
- `/resume` - Resume builder dashboard
- `/legal` - Legal services dashboard
- `/ai-chat` - AI chat assistant
- `/services` - Services directory dashboard
- `/smart-dashboard` - Smart daily dashboard

## Development Status

This is a consolidated platform combining features from:
- ✅ Main case management codebase (modules copied)
- ✅ Second-chance platform (frontend templates integrated)

## Next Steps

- [ ] Test all API endpoints
- [ ] Verify database connectivity
- [ ] Add authentication system
- [ ] Implement React frontend integration
- [ ] Add comprehensive testing
- [ ] Performance optimization 

## Deployment (Railway + Vercel)

### Railway (Backend)
1. Deploy from repo root.
2. Start command is defined in `railway.json`.
3. Set required environment variables in Railway (see `.env.example`).
4. Configure persistent storage for `databases/`, `uploads/`, and `logs/` to avoid data loss on restarts.
5. Run predeploy smoke checks:
   ```bash
   python scripts/predeploy_smoke.py
   ```
6. PostgreSQL migration path:
   - Set `DATABASE_URL` to Railway Postgres for SQLAlchemy-backed services.
   - The app still contains module-level SQLite paths; those modules should be migrated incrementally to SQLAlchemy/Postgres.

### Vercel (Frontend)
1. Deploy from `frontend/`.
2. Set `VITE_API_BASE_URL` to your Railway backend URL (e.g. `https://your-railway-app.up.railway.app`) or leave blank to use `/api` rewrites.
3. Ensure `frontend/vercel.json` rewrite destination points to your Railway backend.
