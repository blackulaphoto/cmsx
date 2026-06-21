"""Analytics storage layer (SQLite, additive, PHI-safe).

One idempotent ``analytics_events`` table holds product-usage signals. The store
resolves its database path from ``backend.shared.db_path.DB_DIR`` *at call time*
(not import time) so the SaaS harness / tests can repoint ``DB_DIR`` at a tmp dir
without touching the tracked ``databases/*.db`` files.

Hard safety rule: metadata is sanitized before it is ever written. Any key that
looks like PHI / protected client content is dropped, values are coerced to safe
scalars, strings are length-capped, and the whole object is size-capped. There is
no code path that stores raw client data here.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import backend.shared.db_path as db_path_mod

logger = logging.getLogger(__name__)

DB_FILENAME = "analytics.db"

# ── Validation envelope ──────────────────────────────────────────────────────
#
# Event names are validated against this allowlist. Anything else is rejected by
# the endpoint so the table only ever holds known, safe signal types.
ALLOWED_EVENT_TYPES = (
    "page_view",
    "route_view",
    "module_view",
    "feature_use",
    "session_start",
    "owner_view",
    "super_admin_view",
)

# Modules we expect the frontend to track. Used to surface *least-used* modules
# (including ones with zero events) so the owner can see coverage gaps, not just
# whatever happens to have data.
KNOWN_MODULES = (
    "dashboard",
    "case_management",
    "admissions",
    "documentation",
    "housing",
    "sober_living",
    "benefits",
    "fmla",
    "owner",
    "super_admin",
)

# Substring tokens that mark a metadata key as PHI / protected content. Matching
# is case-insensitive and substring-based (so ``client_name``, ``patient_dob``,
# ``note_text`` are all caught). Aggressive on purpose — analytics never needs
# any of these.
PHI_FORBIDDEN_KEY_TOKENS = (
    "name",
    "first",
    "last",
    "ssn",
    "dob",
    "birth",
    "diagnos",
    "note",
    "message",
    "msg",
    "body",
    "content",
    "text",
    "document",
    "doc_",
    "address",
    "phone",
    "email",
    "mrn",
    "medical",
    "medication",
    "prescription",
    "client",
    "patient",
    "insurance",
    "memo",
)

# Sanitization caps.
MAX_METADATA_KEYS = 12
MAX_VALUE_LEN = 200
MAX_FIELD_LEN = 300  # route / module / source / medium / campaign / referrer


def _trim(value: Optional[str], limit: int = MAX_FIELD_LEN) -> Optional[str]:
    """Trim a free-text scalar field to ``limit`` chars; empty → None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


def _key_is_phi(key: str) -> bool:
    low = str(key).lower()
    return any(token in low for token in PHI_FORBIDDEN_KEY_TOKENS)


def sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
    """Return ``(clean, dropped)`` — a PHI-free, scalar-only, size-capped copy of
    ``metadata`` plus the list of keys that were removed.

    Rules:
      * non-dict input → ``({}, [])``
      * PHI-looking keys are dropped
      * only str/int/float/bool values survive (nested dict/list dropped)
      * strings are trimmed to ``MAX_VALUE_LEN``
      * at most ``MAX_METADATA_KEYS`` keys are kept
    """
    if not isinstance(metadata, dict):
        return {}, []
    clean: Dict[str, Any] = {}
    dropped: List[str] = []
    for raw_key, value in metadata.items():
        key = str(raw_key).strip()
        if not key:
            continue
        if _key_is_phi(key):
            dropped.append(key)
            continue
        if isinstance(value, bool) or isinstance(value, (int, float)):
            clean[key[:64]] = value
        elif isinstance(value, str):
            clean[key[:64]] = value.strip()[:MAX_VALUE_LEN]
        else:
            # Nested structures / None / unknown types are not stored.
            dropped.append(key)
            continue
        if len(clean) >= MAX_METADATA_KEYS:
            break
    return clean, dropped


class AnalyticsStore:
    """Thin SQLite wrapper for the analytics event log."""

    def _db_path(self):
        # Resolve dynamically so a monkeypatched/redirected DB_DIR is honored.
        return db_path_mod.DB_DIR / DB_FILENAME

    def _connect(self) -> sqlite3.Connection:
        path = self._db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        self._ensure_schema(conn)
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                route TEXT,
                module TEXT,
                org_id TEXT,
                case_manager_id TEXT,
                source TEXT,
                medium TEXT,
                campaign TEXT,
                referrer TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analytics_events_module ON analytics_events(module)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analytics_events_event_type ON analytics_events(event_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at)"
        )

    # ── Writes ───────────────────────────────────────────────────────────────

    def record_event(
        self,
        *,
        event_type: str,
        route: Optional[str] = None,
        module: Optional[str] = None,
        org_id: Optional[str] = None,
        case_manager_id: Optional[str] = None,
        source: Optional[str] = None,
        medium: Optional[str] = None,
        campaign: Optional[str] = None,
        referrer: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Insert one sanitized event. ``event_type`` is assumed already validated
        by the caller (the endpoint enforces the allowlist). Metadata is always
        sanitized here as a defense-in-depth backstop."""
        clean_metadata, dropped = sanitize_metadata(metadata)
        module_norm = _trim(module)
        if module_norm:
            module_norm = module_norm.lower()
        created_at = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO analytics_events (
                    event_type, route, module, org_id, case_manager_id,
                    source, medium, campaign, referrer, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event_type).strip()[:64],
                    _trim(route),
                    module_norm,
                    _trim(org_id, 128),
                    _trim(case_manager_id, 128),
                    _trim(source),
                    _trim(medium),
                    _trim(campaign),
                    _trim(referrer),
                    json.dumps(clean_metadata) if clean_metadata else None,
                    created_at,
                ),
            )
            conn.commit()
            event_id = cur.lastrowid
        if dropped:
            logger.info(
                "analytics: dropped %d unsafe metadata key(s) from %s event",
                len(dropped),
                event_type,
            )
        return {"event_id": event_id, "dropped_metadata_keys": dropped}

    # ── Reads (aggregates only — never raw rows to callers) ──────────────────

    def total_events(self) -> int:
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT COUNT(*) FROM analytics_events").fetchone()
            return int(row[0]) if row else 0
        except Exception:  # noqa: BLE001 — best-effort metric
            return 0

    def module_usage(self) -> Dict[str, int]:
        """Counts per module, including KNOWN_MODULES that have zero events."""
        counts: Dict[str, int] = {m: 0 for m in KNOWN_MODULES}
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT module, COUNT(*) c FROM analytics_events
                    WHERE module IS NOT NULL AND module != ''
                    GROUP BY module
                    """
                ).fetchall()
            for r in rows:
                counts[r["module"]] = int(r["c"])
        except Exception:  # noqa: BLE001
            pass
        return counts

    def marketing_source_breakdown(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT source, COUNT(*) c FROM analytics_events
                    WHERE source IS NOT NULL AND source != ''
                    GROUP BY source ORDER BY c DESC
                    """
                ).fetchall()
            out = {r["source"]: int(r["c"]) for r in rows}
        except Exception:  # noqa: BLE001
            pass
        return out

    def recent_activity_by_day(self, *, days: int = 14) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT substr(created_at, 1, 10) day, COUNT(*) c
                    FROM analytics_events
                    GROUP BY day ORDER BY day DESC LIMIT ?
                    """,
                    (max(1, int(days)),),
                ).fetchall()
            out = [{"day": r["day"], "count": int(r["c"])} for r in rows]
        except Exception:  # noqa: BLE001
            pass
        return out

    def usage_summary(self, *, top_n: int = 5) -> Dict[str, Any]:
        """Assemble the usage portion of the owner analytics summary."""
        usage = self.module_usage()
        # top_modules: only modules that actually have events, highest first.
        active = [
            {"module": m, "count": c} for m, c in usage.items() if c > 0
        ]
        active.sort(key=lambda x: (-x["count"], x["module"]))
        top_modules = active[: max(0, int(top_n))]
        # least_used_modules: known modules ascending (zeros surface coverage gaps).
        least = [{"module": m, "count": usage[m]} for m in KNOWN_MODULES]
        least.sort(key=lambda x: (x["count"], x["module"]))
        least_used_modules = least[: max(0, int(top_n))]
        return {
            "total_events": self.total_events(),
            "module_usage": usage,
            "top_modules": top_modules,
            "least_used_modules": least_used_modules,
            "marketing_source_breakdown": self.marketing_source_breakdown(),
            "recent_activity": self.recent_activity_by_day(),
        }


# Module-level singleton, mirroring ``auth_service`` / ``billing`` usage.
analytics_store = AnalyticsStore()
