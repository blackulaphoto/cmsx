"""Central database directory resolver.

When RAILWAY_VOLUME_MOUNT_PATH is set (e.g. /mnt/data), all SQLite databases
are placed at <volume>/databases/ so they persist across deploys.
Falls back to the local relative 'databases/' directory for dev.
"""
from __future__ import annotations

import os
from pathlib import Path


def _resolve() -> Path:
    vol = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    if vol:
        d = Path(vol) / "databases"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return Path("databases")


DB_DIR: Path = _resolve()
