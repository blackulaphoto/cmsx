"""
Sober Living SQLite store — Phase 1 MVP.

Database file: databases/sober_living_ops.db
Pattern mirrors backend/modules/fmla/store.py exactly.
"""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path("databases/sober_living_ops.db")

BED_STATUSES = {"available", "occupied", "reserved", "maintenance", "unavailable"}


def _now() -> str:
    return datetime.utcnow().isoformat()


class SoberLivingStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._setup()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _db(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        with self._db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sober_living_houses (
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
                );

                CREATE TABLE IF NOT EXISTS sober_living_rooms (
                    room_id     TEXT PRIMARY KEY,
                    house_id    TEXT NOT NULL REFERENCES sober_living_houses(house_id) ON DELETE CASCADE,
                    room_number TEXT NOT NULL,
                    floor       TEXT,
                    notes       TEXT,
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sober_living_beds (
                    bed_id      TEXT PRIMARY KEY,
                    house_id    TEXT NOT NULL REFERENCES sober_living_houses(house_id) ON DELETE CASCADE,
                    room_id     TEXT NOT NULL REFERENCES sober_living_rooms(room_id) ON DELETE CASCADE,
                    bed_label   TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'available',
                    notes       TEXT,
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sober_living_residents (
                    resident_id TEXT PRIMARY KEY,
                    client_id   TEXT,
                    first_name  TEXT NOT NULL,
                    last_name   TEXT NOT NULL,
                    date_of_birth TEXT,
                    phone       TEXT,
                    email       TEXT,
                    gender      TEXT,
                    sobriety_date TEXT,
                    emergency_contact_name TEXT,
                    emergency_contact_phone TEXT,
                    notes       TEXT,
                    status      TEXT DEFAULT 'active',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sober_living_stays (
                    stay_id     TEXT PRIMARY KEY,
                    resident_id TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
                    house_id    TEXT NOT NULL REFERENCES sober_living_houses(house_id),
                    bed_id      TEXT REFERENCES sober_living_beds(bed_id),
                    move_in_date TEXT NOT NULL,
                    move_out_date TEXT,
                    discharge_reason TEXT,
                    discharge_notes TEXT,
                    status      TEXT NOT NULL DEFAULT 'active',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_rooms_house    ON sober_living_rooms(house_id);
                CREATE INDEX IF NOT EXISTS idx_beds_house     ON sober_living_beds(house_id);
                CREATE INDEX IF NOT EXISTS idx_beds_room      ON sober_living_beds(room_id);
                CREATE INDEX IF NOT EXISTS idx_stays_resident ON sober_living_stays(resident_id);
                CREATE INDEX IF NOT EXISTS idx_stays_house    ON sober_living_stays(house_id);
                CREATE INDEX IF NOT EXISTS idx_stays_bed      ON sober_living_stays(bed_id);
            """)

    # ------------------------------------------------------------------
    # Houses
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        with self._db() as conn:
            houses = conn.execute(
                "SELECT COUNT(*) FROM sober_living_houses WHERE status = 'active'"
            ).fetchone()[0]
            total_beds = conn.execute(
                "SELECT COUNT(*) FROM sober_living_beds"
            ).fetchone()[0]
            occupied = conn.execute(
                "SELECT COUNT(*) FROM sober_living_beds WHERE status = 'occupied'"
            ).fetchone()[0]
            available = conn.execute(
                "SELECT COUNT(*) FROM sober_living_beds WHERE status = 'available'"
            ).fetchone()[0]
            reserved = conn.execute(
                "SELECT COUNT(*) FROM sober_living_beds WHERE status = 'reserved'"
            ).fetchone()[0]
            active_stays = conn.execute(
                "SELECT COUNT(*) FROM sober_living_stays WHERE status = 'active'"
            ).fetchone()[0]
        occupancy_rate = round((occupied / total_beds * 100), 1) if total_beds else 0
        return {
            "total_houses": houses,
            "total_beds": total_beds,
            "occupied_beds": occupied,
            "available_beds": available,
            "reserved_beds": reserved,
            "occupancy_rate": occupancy_rate,
            "active_stays": active_stays,
        }

    def list_houses(self) -> List[Dict]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM sober_living_houses ORDER BY name"
            ).fetchall()
            houses = [dict(r) for r in rows]
            for h in houses:
                h["bed_counts"] = self._bed_counts_for_house(conn, h["house_id"])
        return houses

    def _bed_counts_for_house(self, conn: sqlite3.Connection, house_id: str) -> Dict:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM sober_living_beds WHERE house_id = ? GROUP BY status",
            (house_id,),
        ).fetchall()
        counts = {r["status"]: r["cnt"] for r in rows}
        total = sum(counts.values())
        return {
            "total": total,
            "available": counts.get("available", 0),
            "occupied": counts.get("occupied", 0),
            "reserved": counts.get("reserved", 0),
            "maintenance": counts.get("maintenance", 0),
        }

    def get_house(self, house_id: str) -> Optional[Dict]:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM sober_living_houses WHERE house_id = ?", (house_id,)
            ).fetchone()
            if not row:
                return None
            h = dict(row)
            h["bed_counts"] = self._bed_counts_for_house(conn, house_id)
        return h

    def create_house(self, data: Dict) -> Dict:
        house_id = str(uuid.uuid4())
        now = _now()
        with self._db() as conn:
            conn.execute(
                """INSERT INTO sober_living_houses
                   (house_id, name, address, city, state, zip_code, phone, email,
                    manager_name, gender_policy, total_capacity, notes, status,
                    created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    house_id, data["name"],
                    data.get("address"), data.get("city"), data.get("state"),
                    data.get("zip_code"), data.get("phone"), data.get("email"),
                    data.get("manager_name"), data.get("gender_policy", "any"),
                    data.get("total_capacity", 0), data.get("notes"),
                    data.get("status", "active"), now, now,
                ),
            )
        return self.get_house(house_id)

    def update_house(self, house_id: str, data: Dict) -> Optional[Dict]:
        now = _now()
        fields = ["name", "address", "city", "state", "zip_code", "phone", "email",
                  "manager_name", "gender_policy", "total_capacity", "notes", "status"]
        sets = ", ".join(f"{f} = ?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if not sets:
            return self.get_house(house_id)
        with self._db() as conn:
            conn.execute(
                f"UPDATE sober_living_houses SET {sets}, updated_at = ? WHERE house_id = ?",
                vals + [now, house_id],
            )
        return self.get_house(house_id)

    # ------------------------------------------------------------------
    # Rooms
    # ------------------------------------------------------------------

    def list_rooms(self, house_id: str) -> List[Dict]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM sober_living_rooms WHERE house_id = ? ORDER BY room_number",
                (house_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def create_room(self, house_id: str, data: Dict) -> Dict:
        room_id = str(uuid.uuid4())
        now = _now()
        with self._db() as conn:
            conn.execute(
                """INSERT INTO sober_living_rooms
                   (room_id, house_id, room_number, floor, notes, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (room_id, house_id, data["room_number"],
                 data.get("floor"), data.get("notes"), now, now),
            )
            row = conn.execute(
                "SELECT * FROM sober_living_rooms WHERE room_id = ?", (room_id,)
            ).fetchone()
        return dict(row)

    # ------------------------------------------------------------------
    # Beds
    # ------------------------------------------------------------------

    def list_beds(self, house_id: str) -> List[Dict]:
        with self._db() as conn:
            rows = conn.execute(
                """SELECT b.*, r.room_number,
                          s.stay_id,
                          res.resident_id, res.first_name, res.last_name
                   FROM sober_living_beds b
                   JOIN sober_living_rooms r ON b.room_id = r.room_id
                   LEFT JOIN sober_living_stays s
                          ON s.bed_id = b.bed_id AND s.status = 'active'
                   LEFT JOIN sober_living_residents res
                          ON res.resident_id = s.resident_id
                   WHERE b.house_id = ?
                   ORDER BY r.room_number, b.bed_label""",
                (house_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_bed(self, bed_id: str) -> Optional[Dict]:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM sober_living_beds WHERE bed_id = ?", (bed_id,)
            ).fetchone()
        return dict(row) if row else None

    def create_bed(self, house_id: str, data: Dict) -> Dict:
        bed_id = str(uuid.uuid4())
        now = _now()
        with self._db() as conn:
            conn.execute(
                """INSERT INTO sober_living_beds
                   (bed_id, house_id, room_id, bed_label, status, notes, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    bed_id, house_id, data["room_id"], data["bed_label"],
                    data.get("status", "available"), data.get("notes"), now, now,
                ),
            )
            row = conn.execute(
                "SELECT * FROM sober_living_beds WHERE bed_id = ?", (bed_id,)
            ).fetchone()
        return dict(row)

    def update_bed(self, bed_id: str, data: Dict) -> Optional[Dict]:
        now = _now()
        fields = ["bed_label", "status", "notes", "room_id"]
        sets = ", ".join(f"{f} = ?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if not sets:
            return self.get_bed(bed_id)
        with self._db() as conn:
            conn.execute(
                f"UPDATE sober_living_beds SET {sets}, updated_at = ? WHERE bed_id = ?",
                vals + [now, bed_id],
            )
        return self.get_bed(bed_id)

    def _set_bed_status(self, conn: sqlite3.Connection, bed_id: str, status: str) -> None:
        conn.execute(
            "UPDATE sober_living_beds SET status = ?, updated_at = ? WHERE bed_id = ?",
            (status, _now(), bed_id),
        )

    # ------------------------------------------------------------------
    # Residents
    # ------------------------------------------------------------------

    def list_residents_for_house(self, house_id: str) -> List[Dict]:
        with self._db() as conn:
            rows = conn.execute(
                """SELECT res.*, s.stay_id, s.bed_id, s.move_in_date, s.status as stay_status,
                          b.bed_label, r.room_number
                   FROM sober_living_stays s
                   JOIN sober_living_residents res ON res.resident_id = s.resident_id
                   LEFT JOIN sober_living_beds b ON b.bed_id = s.bed_id
                   LEFT JOIN sober_living_rooms r ON r.room_id = b.room_id
                   WHERE s.house_id = ? AND s.status = 'active'
                   ORDER BY res.last_name, res.first_name""",
                (house_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def create_resident(self, data: Dict) -> Dict:
        resident_id = str(uuid.uuid4())
        now = _now()
        with self._db() as conn:
            conn.execute(
                """INSERT INTO sober_living_residents
                   (resident_id, client_id, first_name, last_name, date_of_birth,
                    phone, email, gender, sobriety_date,
                    emergency_contact_name, emergency_contact_phone,
                    notes, status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    resident_id, data.get("client_id"),
                    data["first_name"], data["last_name"],
                    data.get("date_of_birth"), data.get("phone"), data.get("email"),
                    data.get("gender"), data.get("sobriety_date"),
                    data.get("emergency_contact_name"), data.get("emergency_contact_phone"),
                    data.get("notes"), data.get("status", "active"), now, now,
                ),
            )
            row = conn.execute(
                "SELECT * FROM sober_living_residents WHERE resident_id = ?", (resident_id,)
            ).fetchone()
        return dict(row)

    # ------------------------------------------------------------------
    # Stays
    # ------------------------------------------------------------------

    def create_stay(self, data: Dict) -> Dict:
        stay_id = str(uuid.uuid4())
        now = _now()
        bed_id = data.get("bed_id")
        with self._db() as conn:
            # Ensure no other active stay on same bed
            if bed_id:
                conflict = conn.execute(
                    "SELECT stay_id FROM sober_living_stays WHERE bed_id = ? AND status = 'active'",
                    (bed_id,),
                ).fetchone()
                if conflict:
                    raise ValueError(f"Bed {bed_id} is already occupied by an active stay")
            conn.execute(
                """INSERT INTO sober_living_stays
                   (stay_id, resident_id, house_id, bed_id, move_in_date, status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    stay_id, data["resident_id"], data["house_id"], bed_id,
                    data.get("move_in_date", _now()[:10]), "active", now, now,
                ),
            )
            if bed_id:
                self._set_bed_status(conn, bed_id, "occupied")
            row = conn.execute(
                "SELECT * FROM sober_living_stays WHERE stay_id = ?", (stay_id,)
            ).fetchone()
        return dict(row)

    def update_stay(self, stay_id: str, data: Dict) -> Optional[Dict]:
        now = _now()
        fields = ["move_in_date", "bed_id", "status"]
        sets = ", ".join(f"{f} = ?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if not sets:
            return self._get_stay(stay_id)
        with self._db() as conn:
            conn.execute(
                f"UPDATE sober_living_stays SET {sets}, updated_at = ? WHERE stay_id = ?",
                vals + [now, stay_id],
            )
        return self._get_stay(stay_id)

    def discharge_stay(self, stay_id: str, data: Dict) -> Optional[Dict]:
        now = _now()
        with self._db() as conn:
            stay = conn.execute(
                "SELECT * FROM sober_living_stays WHERE stay_id = ?", (stay_id,)
            ).fetchone()
            if not stay:
                return None
            conn.execute(
                """UPDATE sober_living_stays
                   SET status = 'discharged', move_out_date = ?,
                       discharge_reason = ?, discharge_notes = ?, updated_at = ?
                   WHERE stay_id = ?""",
                (
                    data.get("move_out_date", _now()[:10]),
                    data.get("discharge_reason"),
                    data.get("discharge_notes"),
                    now, stay_id,
                ),
            )
            if stay["bed_id"]:
                self._set_bed_status(conn, stay["bed_id"], "available")
            row = conn.execute(
                "SELECT * FROM sober_living_stays WHERE stay_id = ?", (stay_id,)
            ).fetchone()
        return dict(row)

    def transfer_bed(self, stay_id: str, new_bed_id: str) -> Optional[Dict]:
        now = _now()
        with self._db() as conn:
            stay = conn.execute(
                "SELECT * FROM sober_living_stays WHERE stay_id = ? AND status = 'active'",
                (stay_id,),
            ).fetchone()
            if not stay:
                return None
            conflict = conn.execute(
                "SELECT stay_id FROM sober_living_stays WHERE bed_id = ? AND status = 'active'",
                (new_bed_id,),
            ).fetchone()
            if conflict:
                raise ValueError(f"Bed {new_bed_id} already occupied")
            old_bed_id = stay["bed_id"]
            conn.execute(
                "UPDATE sober_living_stays SET bed_id = ?, updated_at = ? WHERE stay_id = ?",
                (new_bed_id, now, stay_id),
            )
            if old_bed_id:
                self._set_bed_status(conn, old_bed_id, "available")
            self._set_bed_status(conn, new_bed_id, "occupied")
            row = conn.execute(
                "SELECT * FROM sober_living_stays WHERE stay_id = ?", (stay_id,)
            ).fetchone()
        return dict(row)

    def _get_stay(self, stay_id: str) -> Optional[Dict]:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM sober_living_stays WHERE stay_id = ?", (stay_id,)
            ).fetchone()
        return dict(row) if row else None


# Module-level singleton — matches fmla store_factory pattern
_store: Optional[SoberLivingStore] = None


def get_store() -> SoberLivingStore:
    global _store
    if _store is None:
        _store = SoberLivingStore()
    return _store
