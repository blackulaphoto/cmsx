"""
Sober Living store — Phase 1 + Phase 2 (Rent & Payments).

Storage: Postgres when DATABASE_URL is set (Railway production),
         SQLite at databases/sober_living_ops.db for local dev.

Postgres uses %s placeholders; SQLite uses ?.  The _q() helper
swaps them so every query is written once with %s.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

SQLITE_PATH = Path("databases/sober_living_ops.db")
BED_STATUSES = {"available", "occupied", "reserved", "maintenance", "unavailable"}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def _use_postgres() -> bool:
    return bool(_database_url())


def _q(sql: str) -> str:
    """Convert %s placeholders → ? when running SQLite."""
    if _use_postgres():
        return sql
    return sql.replace("%s", "?")


# ---------------------------------------------------------------------------
# Postgres connection (psycopg2 + RealDictCursor)
# ---------------------------------------------------------------------------

@contextmanager
def _pg_conn() -> Generator:
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(_database_url(), cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# SQLite connection
# ---------------------------------------------------------------------------

@contextmanager
def _sqlite_conn() -> Generator:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Unified connection context manager
# ---------------------------------------------------------------------------

@contextmanager
def _db() -> Generator:
    if _use_postgres():
        with _pg_conn() as conn:
            yield conn
    else:
        with _sqlite_conn() as conn:
            yield conn


def _row(r) -> Optional[Dict]:
    if r is None:
        return None
    if isinstance(r, dict):
        return dict(r)
    return dict(r)


def _rows(rs) -> List[Dict]:
    return [_row(r) for r in rs]


# ---------------------------------------------------------------------------
# Schema DDL — Postgres and SQLite variants
# ---------------------------------------------------------------------------

_PG_DDL = [
    """CREATE TABLE IF NOT EXISTS sober_living_houses (
        house_id        TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        address         TEXT,
        city            TEXT,
        state           TEXT,
        zip_code        TEXT,
        phone           TEXT,
        email           TEXT,
        manager_name    TEXT,
        gender_policy   TEXT DEFAULT 'any',
        total_capacity  INTEGER DEFAULT 0,
        notes           TEXT,
        status          TEXT DEFAULT 'active',
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_rooms (
        room_id     TEXT PRIMARY KEY,
        house_id    TEXT NOT NULL REFERENCES sober_living_houses(house_id) ON DELETE CASCADE,
        room_number TEXT NOT NULL,
        floor       TEXT,
        notes       TEXT,
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_beds (
        bed_id      TEXT PRIMARY KEY,
        house_id    TEXT NOT NULL REFERENCES sober_living_houses(house_id) ON DELETE CASCADE,
        room_id     TEXT NOT NULL REFERENCES sober_living_rooms(room_id) ON DELETE CASCADE,
        bed_label   TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'available',
        notes       TEXT,
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_residents (
        resident_id TEXT PRIMARY KEY,
        client_id   TEXT,
        first_name  TEXT NOT NULL,
        last_name   TEXT NOT NULL,
        date_of_birth TEXT,
        phone       TEXT,
        email       TEXT,
        gender      TEXT,
        sobriety_date TEXT,
        emergency_contact_name  TEXT,
        emergency_contact_phone TEXT,
        notes       TEXT,
        status      TEXT DEFAULT 'active',
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_stays (
        stay_id       TEXT PRIMARY KEY,
        resident_id   TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
        house_id      TEXT NOT NULL REFERENCES sober_living_houses(house_id),
        bed_id        TEXT REFERENCES sober_living_beds(bed_id),
        move_in_date  TEXT NOT NULL,
        move_out_date TEXT,
        discharge_reason TEXT,
        discharge_notes  TEXT,
        status        TEXT NOT NULL DEFAULT 'active',
        created_at    TEXT NOT NULL,
        updated_at    TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_rent_agreements (
        agreement_id   TEXT PRIMARY KEY,
        stay_id        TEXT NOT NULL REFERENCES sober_living_stays(stay_id),
        resident_id    TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
        house_id       TEXT NOT NULL REFERENCES sober_living_houses(house_id),
        rent_amount    DOUBLE PRECISION NOT NULL,
        frequency      TEXT NOT NULL DEFAULT 'monthly',
        due_day        INTEGER,
        payment_method TEXT,
        notes          TEXT,
        status         TEXT NOT NULL DEFAULT 'active',
        created_at     TEXT NOT NULL,
        updated_at     TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_rent_payments (
        payment_id       TEXT PRIMARY KEY,
        agreement_id     TEXT NOT NULL REFERENCES sober_living_rent_agreements(agreement_id),
        stay_id          TEXT NOT NULL REFERENCES sober_living_stays(stay_id),
        resident_id      TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
        house_id         TEXT NOT NULL REFERENCES sober_living_houses(house_id),
        amount           DOUBLE PRECISION NOT NULL,
        payment_date     TEXT NOT NULL,
        period_start     TEXT,
        period_end       TEXT,
        payment_method   TEXT,
        reference_number TEXT,
        notes            TEXT,
        status           TEXT NOT NULL DEFAULT 'posted',
        recorded_by      TEXT,
        created_at       TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_sl_rooms_house    ON sober_living_rooms(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_beds_house     ON sober_living_beds(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_beds_room      ON sober_living_beds(room_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_stays_resident ON sober_living_stays(resident_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_stays_house    ON sober_living_stays(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_stays_bed      ON sober_living_stays(bed_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_ragree_stay    ON sober_living_rent_agreements(stay_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_ragree_house   ON sober_living_rent_agreements(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_rpay_agree     ON sober_living_rent_payments(agreement_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_rpay_stay      ON sober_living_rent_payments(stay_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_rpay_house     ON sober_living_rent_payments(house_id)",
]


def _setup_schema() -> None:
    if _use_postgres():
        with _pg_conn() as conn:
            cur = conn.cursor()
            for ddl in _PG_DDL:
                try:
                    cur.execute(ddl)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"DDL skipped: {e}")
    else:
        SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        # Build SQLite DDL by converting Postgres types
        for ddl in _PG_DDL:
            sq = ddl.replace("DOUBLE PRECISION", "REAL")
            try:
                conn.execute(sq)
            except Exception:
                pass
        conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# Helper: execute a query with args and return cursor/results
# ---------------------------------------------------------------------------

def _exec(conn, sql: str, args=()):
    """Execute sql with unified placeholder style."""
    return conn.cursor().execute(_q(sql), args) if _use_postgres() else conn.execute(_q(sql), args)


def _fetchone(conn, sql: str, args=()) -> Optional[Dict]:
    cur = _exec(conn, sql, args)
    r = cur.fetchone()
    return _row(r)


def _fetchall(conn, sql: str, args=()) -> List[Dict]:
    cur = _exec(conn, sql, args)
    return _rows(cur.fetchall())


# ---------------------------------------------------------------------------
# Store class — all methods use _db() context + _exec/_fetchone/_fetchall
# ---------------------------------------------------------------------------

class SoberLivingStore:
    def __init__(self):
        _setup_schema()

    # ------------------------------------------------------------------
    # Houses
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict:
        with _db() as conn:
            houses = _fetchone(conn, "SELECT COUNT(*) as c FROM sober_living_houses WHERE status = 'active'")["c"]
            total_beds = _fetchone(conn, "SELECT COUNT(*) as c FROM sober_living_beds")["c"]
            occupied   = _fetchone(conn, "SELECT COUNT(*) as c FROM sober_living_beds WHERE status = 'occupied'")["c"]
            available  = _fetchone(conn, "SELECT COUNT(*) as c FROM sober_living_beds WHERE status = 'available'")["c"]
            reserved   = _fetchone(conn, "SELECT COUNT(*) as c FROM sober_living_beds WHERE status = 'reserved'")["c"]
            active_stays = _fetchone(conn, "SELECT COUNT(*) as c FROM sober_living_stays WHERE status = 'active'")["c"]
        rate = round((occupied / total_beds * 100), 1) if total_beds else 0.0
        return {"total_houses": houses, "total_beds": total_beds, "occupied_beds": occupied,
                "available_beds": available, "reserved_beds": reserved,
                "occupancy_rate": rate, "active_stays": active_stays}

    def _bed_counts(self, conn, house_id: str) -> Dict:
        rows = _fetchall(conn,
            "SELECT status, COUNT(*) as cnt FROM sober_living_beds WHERE house_id = %s GROUP BY status",
            (house_id,))
        counts = {r["status"]: r["cnt"] for r in rows}
        return {"total": sum(counts.values()),
                "available": counts.get("available", 0),
                "occupied":  counts.get("occupied", 0),
                "reserved":  counts.get("reserved", 0),
                "maintenance": counts.get("maintenance", 0)}

    def list_houses(self) -> List[Dict]:
        with _db() as conn:
            rows = _fetchall(conn, "SELECT * FROM sober_living_houses ORDER BY name")
            for h in rows:
                h["bed_counts"] = self._bed_counts(conn, h["house_id"])
        return rows

    def get_house(self, house_id: str) -> Optional[Dict]:
        with _db() as conn:
            h = _fetchone(conn, "SELECT * FROM sober_living_houses WHERE house_id = %s", (house_id,))
            if h:
                h["bed_counts"] = self._bed_counts(conn, house_id)
        return h

    def create_house(self, data: Dict) -> Optional[Dict]:
        house_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_houses
                (house_id, name, address, city, state, zip_code, phone, email,
                 manager_name, gender_policy, total_capacity, notes, status, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (house_id, data["name"],
                 data.get("address"), data.get("city"), data.get("state"),
                 data.get("zip_code"), data.get("phone"), data.get("email"),
                 data.get("manager_name"), data.get("gender_policy", "any"),
                 data.get("total_capacity", 0), data.get("notes"),
                 data.get("status", "active"), now, now))
        return self.get_house(house_id)

    def update_house(self, house_id: str, data: Dict) -> Optional[Dict]:
        fields = ["name","address","city","state","zip_code","phone","email",
                  "manager_name","gender_policy","total_capacity","notes","status"]
        pairs = [f"{f} = %s" for f in fields if f in data]
        vals  = [data[f]     for f in fields if f in data]
        if not pairs:
            return self.get_house(house_id)
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_houses SET {', '.join(pairs)}, updated_at = %s WHERE house_id = %s",
                vals + [_now(), house_id])
        return self.get_house(house_id)

    # ------------------------------------------------------------------
    # Rooms
    # ------------------------------------------------------------------

    def list_rooms(self, house_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn,
                "SELECT * FROM sober_living_rooms WHERE house_id = %s ORDER BY room_number",
                (house_id,))

    def create_room(self, house_id: str, data: Dict) -> Dict:
        room_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_rooms
                (room_id, house_id, room_number, floor, notes, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (room_id, house_id, data["room_number"],
                 data.get("floor"), data.get("notes"), now, now))
            return _fetchone(conn, "SELECT * FROM sober_living_rooms WHERE room_id = %s", (room_id,))

    # ------------------------------------------------------------------
    # Beds
    # ------------------------------------------------------------------

    def list_beds(self, house_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn, """
                SELECT b.*, r.room_number,
                       s.stay_id,
                       res.resident_id, res.first_name, res.last_name
                FROM sober_living_beds b
                JOIN sober_living_rooms r ON b.room_id = r.room_id
                LEFT JOIN sober_living_stays s
                       ON s.bed_id = b.bed_id AND s.status = 'active'
                LEFT JOIN sober_living_residents res
                       ON res.resident_id = s.resident_id
                WHERE b.house_id = %s
                ORDER BY r.room_number, b.bed_label""", (house_id,))

    def get_bed(self, bed_id: str) -> Optional[Dict]:
        with _db() as conn:
            return _fetchone(conn, "SELECT * FROM sober_living_beds WHERE bed_id = %s", (bed_id,))

    def create_bed(self, house_id: str, data: Dict) -> Dict:
        bed_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_beds
                (bed_id, house_id, room_id, bed_label, status, notes, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (bed_id, house_id, data["room_id"], data["bed_label"],
                 data.get("status", "available"), data.get("notes"), now, now))
            return _fetchone(conn, "SELECT * FROM sober_living_beds WHERE bed_id = %s", (bed_id,))

    def update_bed(self, bed_id: str, data: Dict) -> Optional[Dict]:
        fields = ["bed_label", "status", "notes", "room_id"]
        pairs = [f"{f} = %s" for f in fields if f in data]
        vals  = [data[f]     for f in fields if f in data]
        if not pairs:
            return self.get_bed(bed_id)
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_beds SET {', '.join(pairs)}, updated_at = %s WHERE bed_id = %s",
                vals + [_now(), bed_id])
        return self.get_bed(bed_id)

    def _set_bed_status(self, conn, bed_id: str, status: str) -> None:
        _exec(conn,
            "UPDATE sober_living_beds SET status = %s, updated_at = %s WHERE bed_id = %s",
            (status, _now(), bed_id))

    # ------------------------------------------------------------------
    # Residents
    # ------------------------------------------------------------------

    def list_residents_for_house(self, house_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn, """
                SELECT res.*, s.stay_id, s.bed_id, s.move_in_date, s.status as stay_status,
                       b.bed_label, r.room_number
                FROM sober_living_stays s
                JOIN sober_living_residents res ON res.resident_id = s.resident_id
                LEFT JOIN sober_living_beds b ON b.bed_id = s.bed_id
                LEFT JOIN sober_living_rooms r ON r.room_id = b.room_id
                WHERE s.house_id = %s AND s.status = 'active'
                ORDER BY res.last_name, res.first_name""", (house_id,))

    def create_resident(self, data: Dict) -> Dict:
        resident_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_residents
                (resident_id, client_id, first_name, last_name, date_of_birth,
                 phone, email, gender, sobriety_date,
                 emergency_contact_name, emergency_contact_phone,
                 notes, status, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (resident_id, data.get("client_id"),
                 data["first_name"], data["last_name"],
                 data.get("date_of_birth"), data.get("phone"), data.get("email"),
                 data.get("gender"), data.get("sobriety_date"),
                 data.get("emergency_contact_name"), data.get("emergency_contact_phone"),
                 data.get("notes"), data.get("status", "active"), now, now))
            return _fetchone(conn,
                "SELECT * FROM sober_living_residents WHERE resident_id = %s", (resident_id,))

    # ------------------------------------------------------------------
    # Stays
    # ------------------------------------------------------------------

    def create_stay(self, data: Dict) -> Dict:
        stay_id = str(uuid.uuid4())
        now = _now()
        bed_id = data.get("bed_id")
        with _db() as conn:
            if bed_id:
                conflict = _fetchone(conn,
                    "SELECT stay_id FROM sober_living_stays WHERE bed_id = %s AND status = 'active'",
                    (bed_id,))
                if conflict:
                    raise ValueError(f"Bed {bed_id} is already occupied by an active stay")
            _exec(conn, """
                INSERT INTO sober_living_stays
                (stay_id, resident_id, house_id, bed_id, move_in_date, status, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (stay_id, data["resident_id"], data["house_id"], bed_id,
                 data.get("move_in_date", _now()[:10]), "active", now, now))
            if bed_id:
                self._set_bed_status(conn, bed_id, "occupied")
            return _fetchone(conn, "SELECT * FROM sober_living_stays WHERE stay_id = %s", (stay_id,))

    def update_stay(self, stay_id: str, data: Dict) -> Optional[Dict]:
        fields = ["move_in_date", "bed_id", "status"]
        pairs = [f"{f} = %s" for f in fields if f in data]
        vals  = [data[f]     for f in fields if f in data]
        if not pairs:
            return self._get_stay(stay_id)
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_stays SET {', '.join(pairs)}, updated_at = %s WHERE stay_id = %s",
                vals + [_now(), stay_id])
        return self._get_stay(stay_id)

    def discharge_stay(self, stay_id: str, data: Dict) -> Optional[Dict]:
        with _db() as conn:
            stay = _fetchone(conn, "SELECT * FROM sober_living_stays WHERE stay_id = %s", (stay_id,))
            if not stay:
                return None
            _exec(conn, """
                UPDATE sober_living_stays
                SET status = 'discharged', move_out_date = %s,
                    discharge_reason = %s, discharge_notes = %s, updated_at = %s
                WHERE stay_id = %s""",
                (data.get("move_out_date", _now()[:10]),
                 data.get("discharge_reason"), data.get("discharge_notes"),
                 _now(), stay_id))
            if stay.get("bed_id"):
                self._set_bed_status(conn, stay["bed_id"], "available")
            return _fetchone(conn, "SELECT * FROM sober_living_stays WHERE stay_id = %s", (stay_id,))

    def transfer_bed(self, stay_id: str, new_bed_id: str) -> Optional[Dict]:
        with _db() as conn:
            stay = _fetchone(conn,
                "SELECT * FROM sober_living_stays WHERE stay_id = %s AND status = 'active'",
                (stay_id,))
            if not stay:
                return None
            conflict = _fetchone(conn,
                "SELECT stay_id FROM sober_living_stays WHERE bed_id = %s AND status = 'active'",
                (new_bed_id,))
            if conflict:
                raise ValueError(f"Bed {new_bed_id} already occupied")
            old_bed_id = stay.get("bed_id")
            _exec(conn,
                "UPDATE sober_living_stays SET bed_id = %s, updated_at = %s WHERE stay_id = %s",
                (new_bed_id, _now(), stay_id))
            if old_bed_id:
                self._set_bed_status(conn, old_bed_id, "available")
            self._set_bed_status(conn, new_bed_id, "occupied")
            return _fetchone(conn, "SELECT * FROM sober_living_stays WHERE stay_id = %s", (stay_id,))

    def _get_stay(self, stay_id: str) -> Optional[Dict]:
        with _db() as conn:
            return _fetchone(conn, "SELECT * FROM sober_living_stays WHERE stay_id = %s", (stay_id,))

    # ------------------------------------------------------------------
    # Rent Agreements (Phase 2)
    # ------------------------------------------------------------------

    def get_rent_agreement(self, agreement_id: str) -> Optional[Dict]:
        with _db() as conn:
            return _fetchone(conn,
                "SELECT * FROM sober_living_rent_agreements WHERE agreement_id = %s",
                (agreement_id,))

    def get_rent_agreement_for_stay(self, stay_id: str) -> Optional[Dict]:
        with _db() as conn:
            return _fetchone(conn,
                "SELECT * FROM sober_living_rent_agreements WHERE stay_id = %s AND status = 'active' LIMIT 1",
                (stay_id,))

    def create_rent_agreement(self, data: Dict) -> Optional[Dict]:
        agreement_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_rent_agreements
                (agreement_id, stay_id, resident_id, house_id,
                 rent_amount, frequency, due_day, payment_method, notes, status,
                 created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (agreement_id,
                 data["stay_id"], data["resident_id"], data["house_id"],
                 data["rent_amount"], data.get("frequency", "monthly"),
                 data.get("due_day"), data.get("payment_method"),
                 data.get("notes"), "active", now, now))
        return self.get_rent_agreement(agreement_id)

    def update_rent_agreement(self, agreement_id: str, data: Dict) -> Optional[Dict]:
        fields = ["rent_amount","frequency","due_day","payment_method","notes","status"]
        pairs = [f"{f} = %s" for f in fields if f in data]
        vals  = [data[f]     for f in fields if f in data]
        if not pairs:
            return self.get_rent_agreement(agreement_id)
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_rent_agreements SET {', '.join(pairs)}, updated_at = %s WHERE agreement_id = %s",
                vals + [_now(), agreement_id])
        return self.get_rent_agreement(agreement_id)

    # ------------------------------------------------------------------
    # Rent Payments (Phase 2)
    # ------------------------------------------------------------------

    def list_payments_for_stay(self, stay_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn,
                "SELECT * FROM sober_living_rent_payments WHERE stay_id = %s ORDER BY payment_date DESC",
                (stay_id,))

    def list_payments_for_house(self, house_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn, """
                SELECT p.*, res.first_name, res.last_name
                FROM sober_living_rent_payments p
                JOIN sober_living_residents res ON res.resident_id = p.resident_id
                WHERE p.house_id = %s ORDER BY p.payment_date DESC""", (house_id,))

    def create_payment(self, data: Dict) -> Dict:
        payment_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_rent_payments
                (payment_id, agreement_id, stay_id, resident_id, house_id,
                 amount, payment_date, period_start, period_end,
                 payment_method, reference_number, notes, status, recorded_by, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (payment_id,
                 data["agreement_id"], data["stay_id"],
                 data["resident_id"], data["house_id"],
                 data["amount"],
                 data.get("payment_date", _now()[:10]),
                 data.get("period_start"), data.get("period_end"),
                 data.get("payment_method"), data.get("reference_number"),
                 data.get("notes"), data.get("status", "posted"),
                 data.get("recorded_by"), now))
            return _fetchone(conn,
                "SELECT * FROM sober_living_rent_payments WHERE payment_id = %s", (payment_id,))

    def void_payment(self, payment_id: str) -> Optional[Dict]:
        with _db() as conn:
            row = _fetchone(conn,
                "SELECT * FROM sober_living_rent_payments WHERE payment_id = %s", (payment_id,))
            if not row:
                return None
            _exec(conn,
                "UPDATE sober_living_rent_payments SET status = 'voided' WHERE payment_id = %s",
                (payment_id,))
            return _fetchone(conn,
                "SELECT * FROM sober_living_rent_payments WHERE payment_id = %s", (payment_id,))

    def get_ledger_for_stay(self, stay_id: str) -> Dict:
        agreement = self.get_rent_agreement_for_stay(stay_id)
        payments  = self.list_payments_for_stay(stay_id)
        total_paid = sum(p["amount"] for p in payments if p["status"] == "posted")
        return {"stay_id": stay_id, "agreement": agreement,
                "payments": payments, "total_paid": round(total_paid, 2)}

    def get_rent_summary_for_house(self, house_id: str) -> Dict:
        with _db() as conn:
            agreements = _fetchall(conn, """
                SELECT a.*, res.first_name, res.last_name, s.move_in_date
                FROM sober_living_rent_agreements a
                JOIN sober_living_residents res ON res.resident_id = a.resident_id
                JOIN sober_living_stays s ON s.stay_id = a.stay_id
                WHERE a.house_id = %s AND a.status = 'active' AND s.status = 'active'
                ORDER BY res.last_name""", (house_id,))
            for ag in agreements:
                paid = _fetchone(conn,
                    "SELECT COALESCE(SUM(amount),0) as total FROM sober_living_rent_payments WHERE agreement_id = %s AND status = 'posted'",
                    (ag["agreement_id"],))
                ag["total_paid"] = round(float(paid["total"]), 2)
        return {"house_id": house_id, "residents": agreements, "total_agreements": len(agreements)}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_store_instance: Optional[SoberLivingStore] = None


def get_store() -> SoberLivingStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = SoberLivingStore()
    return _store_instance
