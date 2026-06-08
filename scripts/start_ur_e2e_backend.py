from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
TEMP_DIR = ROOT_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

db_path = TEMP_DIR / "ur-e2e.db"
if db_path.exists():
    db_path.unlink()

env = os.environ.copy()
env.update(
    {
        "APP_ENV": "e2e",
        "ENVIRONMENT": "e2e",
        "RAILWAY_ENVIRONMENT": "e2e",
        "VERCEL_ENV": "e2e",
        "ENABLE_TEST_AUTH": "true",
        "UR_TEST_DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "CORS_ORIGINS": "http://127.0.0.1:5174,http://localhost:5174",
        "PYTHONUNBUFFERED": "1",
    }
)
env.pop("DATABASE_URL", None)

os.chdir(ROOT_DIR)
os.execvpe(
    sys.executable,
    [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8100",
    ],
    env,
)
