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

# ---------------------------------------------------------------------------
# virgil_st_dev.db — durable path helper
# ---------------------------------------------------------------------------

# Repo-relative seed DB (committed to git, used as read-only fallback).
_REPO_SEED_DB: Path = Path(__file__).resolve().parents[2] / "databases" / "virgil_st_dev.db"


def is_durable_db_configured() -> bool:
    """Return True when a Railway volume or explicit CMSX_DB_DIR is active.

    Re-reads env vars on every call so tests can monkeypatch freely.
    """
    return bool(
        os.environ.get("CMSX_DB_DIR", "").strip() or
        os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    )


def _durable_virgil_db_path() -> Path:
    """Return the durable virgil_st_dev.db path without caching.

    The returned path may not exist yet — callers must check before use.
    Only meaningful when is_durable_db_configured() is True.
    """
    override = os.environ.get("CMSX_DB_DIR", "").strip()
    if override:
        return Path(override) / "virgil_st_dev.db"
    vol = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    if vol:
        return Path(vol) / "databases" / "virgil_st_dev.db"
    return _REPO_SEED_DB  # fallback (caller should not reach here without checking)


def resolve_virgil_db_path() -> Path:
    """Resolve virgil_st_dev.db at call time (re-reads env vars).

    Resolution order:
    1. If a durable DB_DIR is configured (Railway volume / CMSX_DB_DIR) AND the
       file exists there → return the durable path.
    2. Else → return the repo seed DB (read-only fallback).

    For import write operations use is_durable_db_configured() and
    _durable_virgil_db_path() separately to guard against writing to a
    blank DB that would hide the seed content.
    """
    if is_durable_db_configured():
        durable = _durable_virgil_db_path()
        if durable.exists():
            return durable
    return _REPO_SEED_DB
