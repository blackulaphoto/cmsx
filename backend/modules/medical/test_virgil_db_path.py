"""
Tests for virgil_st_dev.db durable path resolution.

Run with:
    python -m pytest backend/modules/medical/test_virgil_db_path.py -v
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.shared.db_path import (
    _REPO_SEED_DB,
    _durable_virgil_db_path,
    is_durable_db_configured,
    resolve_virgil_db_path,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_virgil_env(base: dict) -> dict:
    """Return env dict with CMSX_DB_DIR and RAILWAY_VOLUME_MOUNT_PATH removed."""
    return {k: v for k, v in base.items()
            if k not in ("CMSX_DB_DIR", "RAILWAY_VOLUME_MOUNT_PATH")}


def _seed_db(path: Path) -> None:
    """Create a minimal seeded treatment_centers DB at *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS treatment_centers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, type TEXT, city TEXT, isPublished INTEGER DEFAULT 1
        )"""
    )
    conn.execute("INSERT INTO treatment_centers (name, type, city) VALUES (?,?,?)",
                 ("Seed Facility", "residential", "Los Angeles"))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 1. is_durable_db_configured()
# ---------------------------------------------------------------------------

class TestIsDurableConfigured:
    def test_no_env_vars_returns_false(self):
        with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
            assert is_durable_db_configured() is False

    def test_cmsx_db_dir_set_returns_true(self):
        with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
            with patch.dict(os.environ, {"CMSX_DB_DIR": "/tmp/testdb"}):
                assert is_durable_db_configured() is True

    def test_railway_volume_set_returns_true(self):
        with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
            with patch.dict(os.environ, {"RAILWAY_VOLUME_MOUNT_PATH": "/mnt/data"}):
                assert is_durable_db_configured() is True

    def test_blank_env_var_returns_false(self):
        with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
            with patch.dict(os.environ, {"CMSX_DB_DIR": "   "}):
                assert is_durable_db_configured() is False


# ---------------------------------------------------------------------------
# 2. _durable_virgil_db_path()
# ---------------------------------------------------------------------------

class TestDurableVirgilDbPath:
    def test_cmsx_db_dir_returns_correct_path(self):
        with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
            with patch.dict(os.environ, {"CMSX_DB_DIR": "/mydir"}):
                p = _durable_virgil_db_path()
                assert p == Path("/mydir") / "virgil_st_dev.db"

    def test_railway_volume_returns_correct_path(self):
        with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
            with patch.dict(os.environ, {"RAILWAY_VOLUME_MOUNT_PATH": "/mnt/data"}):
                p = _durable_virgil_db_path()
                assert p == Path("/mnt/data") / "databases" / "virgil_st_dev.db"

    def test_cmsx_db_dir_takes_priority_over_railway(self):
        with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
            with patch.dict(os.environ, {
                "CMSX_DB_DIR": "/override",
                "RAILWAY_VOLUME_MOUNT_PATH": "/mnt/data",
            }):
                p = _durable_virgil_db_path()
                assert p == Path("/override") / "virgil_st_dev.db"


# ---------------------------------------------------------------------------
# 3. resolve_virgil_db_path()
# ---------------------------------------------------------------------------

class TestResolveVirgilDbPath:
    def test_no_env_falls_back_to_repo_seed(self):
        """With no env vars, always return the repo seed DB path."""
        with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
            p = resolve_virgil_db_path()
            assert p == _REPO_SEED_DB
            assert p.name == "virgil_st_dev.db"

    def test_durable_configured_and_exists_returns_durable(self):
        """When durable is configured AND the file exists, return the durable path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            durable_path = Path(tmpdir) / "virgil_st_dev.db"
            _seed_db(durable_path)
            with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
                with patch.dict(os.environ, {"CMSX_DB_DIR": tmpdir}):
                    p = resolve_virgil_db_path()
                    assert p == durable_path

    def test_durable_configured_but_missing_falls_back_to_seed(self):
        """When durable is configured but file is absent, fall back to seed (read-only)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Do NOT create the DB file inside tmpdir
            with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
                with patch.dict(os.environ, {"CMSX_DB_DIR": tmpdir}):
                    p = resolve_virgil_db_path()
                    assert p == _REPO_SEED_DB

    def test_railway_volume_durable_exists_returns_durable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            durable_path = Path(tmpdir) / "databases" / "virgil_st_dev.db"
            _seed_db(durable_path)
            with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
                with patch.dict(os.environ, {"RAILWAY_VOLUME_MOUNT_PATH": tmpdir}):
                    p = resolve_virgil_db_path()
                    assert p == durable_path

    def test_repo_seed_path_exists(self):
        """The repo seed DB must exist for local dev / fallback to work."""
        assert _REPO_SEED_DB.exists(), (
            f"Repo seed DB not found at {_REPO_SEED_DB}. "
            "Ensure databases/virgil_st_dev.db is present in the repo."
        )


# ---------------------------------------------------------------------------
# 4. routes.py and importer_samhsa.py use the same helper
# ---------------------------------------------------------------------------

class TestConsistencyBetweenModules:
    def test_importer_exports_virgil_db_path(self):
        from backend.modules.medical import importer_samhsa
        assert hasattr(importer_samhsa, "VIRGIL_DB_PATH")
        assert isinstance(importer_samhsa.VIRGIL_DB_PATH, Path)

    def test_routes_exports_virgil_db_path(self):
        from backend.modules.medical import routes
        assert hasattr(routes, "VIRGIL_DB_PATH")
        assert isinstance(routes.VIRGIL_DB_PATH, Path)

    def test_importer_does_not_hardcode_repo_relative_path(self):
        """Importer must not fall back to raw parents[3] resolution."""
        import inspect
        from backend.modules.medical import importer_samhsa
        src = inspect.getsource(importer_samhsa)
        # The old hardcoded pattern must be gone
        assert 'parents[3] / "databases" / "virgil_st_dev.db"' not in src

    def test_routes_does_not_hardcode_repo_relative_path(self):
        import inspect
        from backend.modules.medical import routes
        src = inspect.getsource(routes)
        assert 'parents[3] / "databases" / "virgil_st_dev.db"' not in src


# ---------------------------------------------------------------------------
# 5. Import mode: guard against blank DB creation
# ---------------------------------------------------------------------------

class TestImportModeGuard:
    def test_import_mode_exits_when_durable_configured_but_missing(self, capsys):
        """run_import() must sys.exit(1) when durable is configured but DB file absent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Durable configured but NO DB file created
            with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
                with patch.dict(os.environ, {"CMSX_DB_DIR": tmpdir}):
                    from backend.modules.medical.importer_samhsa import run_import
                    with pytest.raises(SystemExit) as exc_info:
                        run_import(max_rows=5)
                    assert exc_info.value.code == 1
                    captured = capsys.readouterr()
                    assert "ERROR" in captured.out
                    assert "durable" in captured.out.lower() or "configured" in captured.out.lower()

    def test_import_mode_proceeds_when_durable_configured_and_exists(self, capsys, monkeypatch):
        """run_import() must NOT exit when durable is configured AND file exists.

        We monkeypatch fetch_page to avoid hitting the real SAMHSA API.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            durable_path = Path(tmpdir) / "virgil_st_dev.db"
            _seed_db(durable_path)

            # Reload VIRGIL_DB_PATH so it picks up our temp dir
            import backend.modules.medical.importer_samhsa as imp
            monkeypatch.setattr(imp, "VIRGIL_DB_PATH", durable_path)

            # Fake API response: empty (no rows to insert)
            monkeypatch.setattr(
                imp, "fetch_page",
                lambda *a, **kw: {"rows": [], "recordCount": 0, "totalPages": 1},
            )

            with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
                with patch.dict(os.environ, {"CMSX_DB_DIR": tmpdir}):
                    # Should NOT raise SystemExit (guard passes, import runs to completion)
                    imp.run_import(max_rows=5)

            captured = capsys.readouterr()
            assert "ERROR" not in captured.out

    def test_import_mode_no_blank_db_created_when_guard_fires(self, capsys):
        """After guard fires, the durable path must NOT exist as an empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            durable_path = Path(tmpdir) / "virgil_st_dev.db"
            with patch.dict(os.environ, _clear_virgil_env(os.environ), clear=True):
                with patch.dict(os.environ, {"CMSX_DB_DIR": tmpdir}):
                    from backend.modules.medical.importer_samhsa import run_import
                    with pytest.raises(SystemExit):
                        run_import(max_rows=5)
                    assert not durable_path.exists(), (
                        "Guard fired but an empty DB was still created at the durable path."
                    )
