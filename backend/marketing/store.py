"""Marketing + Campaign Tracker storage layer (SQLite, additive, PHI-safe).

Owner-only campaign tracking. Two idempotent tables:

  * ``marketing_campaigns`` — one row per campaign (name, status, channel, UTM
    fields, landing page, planned budget, manual spend, notes).
  * ``marketing_spend_entries`` — optional itemized manual-spend log, available
    as a forward-looking store for a future "log spend" flow. v1 endpoints treat
    the campaign-level ``spend_amount`` as the canonical manual spend, but this
    table + its helpers are unit-tested so the storage layer is real, not dead.

The store resolves its database path from ``backend.shared.db_path.DB_DIR`` *at
call time* (not import time) so the SaaS harness / tests can repoint ``DB_DIR``
at a tmp dir without touching the tracked ``databases/*.db`` files.

Hard safety rules:
  * No protected client content is ever stored here. Campaign text (name / UTM /
    landing page / notes) is the owner's own marketing copy, length-capped. The
    free-text fields are PHI-risk scanned at the API boundary (rejected, not
    scrubbed) using the shared support scanner.
  * Status / channel are validated against fixed allowlists — the table only ever
    holds known values.
  * No Stripe code and no external ad-platform call is reachable from here.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

import backend.shared.db_path as db_path_mod

logger = logging.getLogger(__name__)

DB_FILENAME = "marketing.db"

# ── Controlled vocabularies ──────────────────────────────────────────────────
# Fixed allowlists. The route layer rejects anything not in these sets so the
# table only ever holds known values (no free-form status/channel).
STATUSES = ("draft", "active", "paused", "completed", "archived")
CHANNELS = (
    "google_ads",
    "meta_ads",
    "tiktok",
    "linkedin",
    "organic",
    "referral",
    "email",
    "manual",
    "other",
)

# Statuses that count a campaign as "live" for the active-campaigns metric.
ACTIVE_STATUSES = ("active",)

DEFAULT_STATUS = "draft"
DEFAULT_CHANNEL = "manual"

# ── Owner-action audit enums (safe by construction) ──────────────────────────
# The only marketing actions ever written to the audit log. No free text is
# associated with any of them — see ``record_owner_action``.
OWNER_ACTION_CAMPAIGN_CREATED = "marketing_campaign_created"
OWNER_ACTION_CAMPAIGN_STATUS_CHANGED = "marketing_campaign_status_changed"
OWNER_ACTION_CAMPAIGN_SPEND_UPDATED = "marketing_campaign_spend_updated"
MAX_EMAIL_LEN = 200
MAX_ACTION_DETAIL_LEN = 64

# ── Field caps ───────────────────────────────────────────────────────────────
MAX_NAME_LEN = 120
MAX_URL_LEN = 500
MAX_UTM_LEN = 128
MAX_NOTES_LEN = 2000
# Defensive numeric ceiling so a typo can't store an absurd budget/spend.
MAX_AMOUNT = 1_000_000_000.0
MAX_RECENT = 200


def _trim(value: Optional[str], limit: int) -> Optional[str]:
    """Trim a free-text scalar to ``limit`` chars; empty / None → None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


def _coerce_amount(value: Any) -> Optional[float]:
    """Coerce an optional numeric amount to a non-negative, capped float.

    None / blank → None. Negative values are clamped to 0. Non-numeric input
    returns None (the field is simply not set) rather than raising."""
    if value is None or value == "":
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount < 0:
        amount = 0.0
    if amount > MAX_AMOUNT:
        amount = MAX_AMOUNT
    return round(amount, 2)


def normalize_status(value: Any) -> Optional[str]:
    text = str(value or "").strip().lower()
    return text if text in STATUSES else None


def normalize_channel(value: Any) -> Optional[str]:
    text = str(value or "").strip().lower()
    return text if text in CHANNELS else None


class MarketingStore:
    """Thin SQLite wrapper for the owner campaign tracker."""

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
            CREATE TABLE IF NOT EXISTS marketing_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                channel TEXT NOT NULL,
                utm_source TEXT,
                utm_medium TEXT,
                utm_campaign TEXT,
                landing_page_url TEXT,
                budget_amount REAL,
                spend_amount REAL,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_marketing_status ON marketing_campaigns(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_marketing_channel ON marketing_campaigns(channel)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_marketing_utm_campaign ON marketing_campaigns(utm_campaign)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_marketing_created_at ON marketing_campaigns(created_at)")
        # Optional itemized manual-spend log (forward-looking). Carries no client
        # content — just an amount, an optional short label, and a timestamp.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS marketing_spend_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                label TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketing_spend_campaign ON marketing_spend_entries(campaign_id)"
        )
        # Owner-action audit log. Intentionally carries NO free text — only the
        # action enum, the campaign id, the acting owner's email, and a safe enum
        # detail (e.g. the new status value). Campaign names, notes, and URLs are
        # NEVER written here. Mirrors the support/super-admin owner-action pattern
        # so the unified Activity Center can aggregate all owner/admin actions.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS marketing_owner_action_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                campaign_id INTEGER,
                actor_email TEXT,
                detail TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketing_owner_action_created_at"
            " ON marketing_owner_action_events(created_at)"
        )

    # ── Row mapping ───────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "status": row["status"],
            "channel": row["channel"],
            "utm_source": row["utm_source"],
            "utm_medium": row["utm_medium"],
            "utm_campaign": row["utm_campaign"],
            "landing_page_url": row["landing_page_url"],
            "budget_amount": row["budget_amount"],
            "spend_amount": row["spend_amount"],
            "notes": row["notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ── Writes ────────────────────────────────────────────────────────────────

    def create_campaign(
        self,
        *,
        name: str,
        status: str = DEFAULT_STATUS,
        channel: str = DEFAULT_CHANNEL,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        landing_page_url: Optional[str] = None,
        budget_amount: Optional[Any] = None,
        spend_amount: Optional[Any] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Insert one campaign. ``status`` / ``channel`` are assumed validated by the
        caller (the endpoint enforces the allowlists); they are defaulted to safe
        values here as a backstop. Text fields are length-capped; amounts are
        coerced to non-negative capped floats."""
        safe_status = normalize_status(status) or DEFAULT_STATUS
        safe_channel = normalize_channel(channel) or DEFAULT_CHANNEL
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO marketing_campaigns (
                    name, status, channel, utm_source, utm_medium, utm_campaign,
                    landing_page_url, budget_amount, spend_amount, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _trim(name, MAX_NAME_LEN) or "(untitled campaign)",
                    safe_status,
                    safe_channel,
                    _trim(utm_source, MAX_UTM_LEN),
                    _trim(utm_medium, MAX_UTM_LEN),
                    _trim(utm_campaign, MAX_UTM_LEN),
                    _trim(landing_page_url, MAX_URL_LEN),
                    _coerce_amount(budget_amount),
                    _coerce_amount(spend_amount),
                    _trim(notes, MAX_NOTES_LEN),
                    now,
                    now,
                ),
            )
            conn.commit()
            campaign_id = cur.lastrowid
            row = conn.execute(
                "SELECT * FROM marketing_campaigns WHERE id = ?", (campaign_id,)
            ).fetchone()
        return self._row_to_dict(row)

    def update_campaign(
        self,
        campaign_id: int,
        *,
        name: Optional[str] = None,
        status: Optional[str] = None,
        channel: Optional[str] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        landing_page_url: Optional[str] = None,
        budget_amount: Optional[Any] = None,
        spend_amount: Optional[Any] = None,
        notes: Optional[str] = None,
        name_set: bool = False,
        status_set: bool = False,
        channel_set: bool = False,
        utm_source_set: bool = False,
        utm_medium_set: bool = False,
        utm_campaign_set: bool = False,
        landing_page_url_set: bool = False,
        budget_amount_set: bool = False,
        spend_amount_set: bool = False,
        notes_set: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Owner-only partial update. Each ``*_set`` flag lets the caller distinguish
        "field omitted" from "field explicitly cleared to null". Status/channel are
        re-validated (an invalid value is simply skipped — the route rejects them
        before reaching here). Returns the updated row, or None if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM marketing_campaigns WHERE id = ?", (int(campaign_id),)
            ).fetchone()
            if row is None:
                return None

            sets: List[str] = []
            params: List[Any] = []

            if name_set:
                sets.append("name = ?")
                params.append(_trim(name, MAX_NAME_LEN) or "(untitled campaign)")
            if status_set:
                norm = normalize_status(status)
                if norm:
                    sets.append("status = ?")
                    params.append(norm)
            if channel_set:
                norm = normalize_channel(channel)
                if norm:
                    sets.append("channel = ?")
                    params.append(norm)
            if utm_source_set:
                sets.append("utm_source = ?")
                params.append(_trim(utm_source, MAX_UTM_LEN))
            if utm_medium_set:
                sets.append("utm_medium = ?")
                params.append(_trim(utm_medium, MAX_UTM_LEN))
            if utm_campaign_set:
                sets.append("utm_campaign = ?")
                params.append(_trim(utm_campaign, MAX_UTM_LEN))
            if landing_page_url_set:
                sets.append("landing_page_url = ?")
                params.append(_trim(landing_page_url, MAX_URL_LEN))
            if budget_amount_set:
                sets.append("budget_amount = ?")
                params.append(_coerce_amount(budget_amount))
            if spend_amount_set:
                sets.append("spend_amount = ?")
                params.append(_coerce_amount(spend_amount))
            if notes_set:
                sets.append("notes = ?")
                params.append(_trim(notes, MAX_NOTES_LEN))

            if not sets:
                return self._row_to_dict(row)

            sets.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(int(campaign_id))
            conn.execute(
                f"UPDATE marketing_campaigns SET {', '.join(sets)} WHERE id = ?", params
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM marketing_campaigns WHERE id = ?", (int(campaign_id),)
            ).fetchone()
        return self._row_to_dict(updated) if updated else None

    # ── Optional itemized spend log (forward-looking, unit-tested) ────────────

    def add_spend_entry(
        self, campaign_id: int, *, amount: Any, label: Optional[str] = None
    ) -> Dict[str, Any]:
        """Append one itemized manual-spend entry for a campaign. Amount is coerced
        to a non-negative capped float; label is a short optional tag (no client
        content). Returns the new entry id + stored amount."""
        safe_amount = _coerce_amount(amount) or 0.0
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO marketing_spend_entries (campaign_id, amount, label,"
                " created_at) VALUES (?, ?, ?, ?)",
                (int(campaign_id), safe_amount, _trim(label, MAX_NAME_LEN), now),
            )
            conn.commit()
            entry_id = cur.lastrowid
        return {"entry_id": entry_id, "amount": safe_amount}

    def campaign_logged_spend(self, campaign_id: int) -> float:
        """Sum of itemized spend entries for one campaign (0.0 if none)."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM marketing_spend_entries"
                    " WHERE campaign_id = ?",
                    (int(campaign_id),),
                ).fetchone()
            return round(float(row[0]), 2) if row else 0.0
        except Exception:  # noqa: BLE001 — best-effort
            return 0.0

    # ── Reads ─────────────────────────────────────────────────────────────────

    def get_campaign(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM marketing_campaigns WHERE id = ?", (int(campaign_id),)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_campaigns(
        self,
        *,
        status: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Campaign rows for the owner tracker, newest first. Optional allowlisted
        filters; unrecognized filter values are ignored (the list still renders)."""
        conds: List[str] = []
        params: List[Any] = []
        s = normalize_status(status)
        if s:
            conds.append("status = ?")
            params.append(s)
        c = normalize_channel(channel)
        if c:
            conds.append("channel = ?")
            params.append(c)
        where = (" WHERE " + " AND ".join(conds)) if conds else ""
        sql = (
            "SELECT * FROM marketing_campaigns" + where +
            " ORDER BY id DESC LIMIT ? OFFSET ?"
        )
        params.append(max(1, min(int(limit), 500)))
        params.append(max(0, int(offset)))
        out: List[Dict[str, Any]] = []
        try:
            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()
            out = [self._row_to_dict(r) for r in rows]
        except Exception:  # noqa: BLE001
            pass
        return out

    def _group_counts(self, conn: sqlite3.Connection, column: str, allowed: tuple) -> Dict[str, int]:
        """Count by an allowlisted column, seeding every known value at 0 so the UI
        always sees the full set (not just whatever has rows)."""
        counts: Dict[str, int] = {v: 0 for v in allowed}
        rows = conn.execute(
            f"SELECT {column} v, COUNT(*) c FROM marketing_campaigns GROUP BY {column}"
        ).fetchall()
        for r in rows:
            key = r["v"]
            if key in counts:
                counts[key] = int(r["c"])
            elif key:
                counts[key] = int(r["c"])
        return counts

    def summary(self) -> Dict[str, Any]:
        """Owner campaign-tracker summary: counts by status/channel, total planned
        budget, total manual spend, and honest performance placeholders.

        Performance fields (landing_page_visits / signups / conversions /
        cost_per_signup) are NEVER fabricated — they stay null until a real data
        source exists. ``cost_per_signup`` is computed only when both total manual
        spend and a real signup count are available (they are not in v1, so it
        stays null)."""
        empty = {
            "total_campaigns": 0,
            "active_campaigns": 0,
            "by_status": {s: 0 for s in STATUSES},
            "by_channel": {c: 0 for c in CHANNELS},
            "total_budget": 0.0,
            "total_spend": 0.0,
        }
        try:
            with self._connect() as conn:
                total_row = conn.execute(
                    "SELECT COUNT(*) FROM marketing_campaigns"
                ).fetchone()
                total = int(total_row[0]) if total_row else 0
                active_row = conn.execute(
                    "SELECT COUNT(*) FROM marketing_campaigns WHERE status IN ({})".format(
                        ",".join("?" for _ in ACTIVE_STATUSES)
                    ),
                    list(ACTIVE_STATUSES),
                ).fetchone()
                active = int(active_row[0]) if active_row else 0
                by_status = self._group_counts(conn, "status", STATUSES)
                by_channel = self._group_counts(conn, "channel", CHANNELS)
                sums = conn.execute(
                    "SELECT COALESCE(SUM(budget_amount), 0), COALESCE(SUM(spend_amount), 0)"
                    " FROM marketing_campaigns"
                ).fetchone()
                total_budget = round(float(sums[0]), 2) if sums else 0.0
                total_spend = round(float(sums[1]), 2) if sums else 0.0
            return {
                "total_campaigns": total,
                "active_campaigns": active,
                "by_status": by_status,
                "by_channel": by_channel,
                "total_budget": total_budget,
                "total_spend": total_spend,
            }
        except Exception:  # noqa: BLE001 — summary is best-effort
            return empty

    def utm_campaign_values(self) -> List[str]:
        """Distinct non-empty ``utm_campaign`` values across campaigns. Used to
        correlate tracked analytics visits back to owner-defined campaigns."""
        out: List[str] = []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT utm_campaign FROM marketing_campaigns"
                    " WHERE utm_campaign IS NOT NULL AND utm_campaign != ''"
                ).fetchall()
            out = [r["utm_campaign"] for r in rows if r["utm_campaign"]]
        except Exception:  # noqa: BLE001
            pass
        return out

    # ── Owner-action audit log ────────────────────────────────────────────────

    def record_owner_action(
        self,
        action: str,
        *,
        campaign_id: Optional[int] = None,
        actor_email: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Append one safe owner-action audit event.

        ``detail`` is expected to be a safe enum value (e.g. the new status) or
        None — NEVER a campaign name, notes, URL, or other free text. The caller
        is responsible for passing only safe enum/id values; this method also
        hard-caps the detail length defensively. Best-effort: an audit failure
        must never break the underlying campaign write."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO marketing_owner_action_events (action, campaign_id,"
                    " actor_email, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        str(action)[:64],
                        int(campaign_id) if campaign_id is not None else None,
                        _trim(actor_email, MAX_EMAIL_LEN),
                        _trim(detail, MAX_ACTION_DETAIL_LEN),
                        datetime.utcnow().isoformat(),
                    ),
                )
                conn.commit()
        except Exception:  # noqa: BLE001 — audit write is best-effort
            logger.warning("Failed to record marketing owner action %s", action, exc_info=True)

    def recent_owner_actions(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        """Newest-first owner-action audit events. Safe by construction — carries
        no campaign name, notes, URL, or other free text; only action/id/enum
        metadata."""
        out: List[Dict[str, Any]] = []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT id, action, campaign_id, actor_email, detail, created_at"
                    " FROM marketing_owner_action_events ORDER BY id DESC LIMIT ?",
                    (max(1, min(int(limit), MAX_RECENT)),),
                ).fetchall()
            out = [
                {
                    "id": r["id"],
                    "action": r["action"],
                    "campaign_id": r["campaign_id"],
                    "actor_email": r["actor_email"],
                    "detail": r["detail"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        except Exception:  # noqa: BLE001 — audit read is best-effort
            pass
        return out


# Module-level singleton, mirroring analytics_store / support_store usage.
marketing_store = MarketingStore()
