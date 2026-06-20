"""Central database directory resolver.

Resolution order:
1. CMSX_DB_DIR (explicit override) — used by the SaaS activation harness and the
   staging runbook to point every SQLite database at a throwaway/isolated dir so
   no tracked `databases/*.db` files are mutated. Created if missing.
2. RAILWAY_VOLUME_MOUNT_PATH (e.g. /mnt/data) — databases live at
   <volume>/databases/ so they persist across deploys.
3. Fallback: the local relative 'databases/' directory for dev.
"""
from __future__ import annotations

import os
from pathlib import Path


def _resolve() -> Path:
    override = os.environ.get("CMSX_DB_DIR", "").strip()
    if override:
        d = Path(override)
        d.mkdir(parents=True, exist_ok=True)
        return d
    vol = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    if vol:
        d = Path(vol) / "databases"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return Path("databases")


DB_DIR: Path = _resolve()
