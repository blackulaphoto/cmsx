from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from backend.shared.database.railway_admissions_postgres import (
    _engine,
    ensure_postgres_admissions_tables,
)

from .database import (
    AdmissionsStore,
    _FC_ALLOWED_COLUMNS,
    _calc_progress,
    _load_manifest,
    _now,
    _resolve_attachment_path,
)


class PostgresAdmissionsStore(AdmissionsStore):
    def __init__(self):
        self._engine_instance = None
        self._schema_ready = False

    def _get_engine(self):
        if self._engine_instance is None:
            self._engine_instance = _engine()
        return self._engine_instance

    def _ensure_ready(self) -> None:
        if self._schema_ready:
            return
        ensure_postgres_admissions_tables()
        self._schema_ready = True

    @contextmanager
    def _db(self):
        self._ensure_ready()
        with self._get_engine().begin() as conn:
            yield conn

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _seed_forms(self, conn, packet_id: str, now: str) -> None:
        forms = _load_manifest()
        for form in forms:
            expires_at = None
            if form.get("expires_in_days"):
                expires_at = (
                    datetime.utcnow() + timedelta(days=form["expires_in_days"])
                ).isoformat()
            conn.execute(
                text(
                    """
                    INSERT INTO railway_admission_packet_forms
                       (id, packet_id, form_key, form_name, category, status, required,
                        timing_group, timing_label, requires_signature, signatures_required,
                        allow_attachments, allow_revocation, expires_in_days, expires_at,
                        review_status, created_at, updated_at)
                    VALUES
                       (:id, :packet_id, :form_key, :form_name, :category, :status, :required,
                        :timing_group, :timing_label, :requires_signature, :signatures_required,
                        :allow_attachments, :allow_revocation, :expires_in_days, :expires_at,
                        :review_status, :created_at, :updated_at)
                    ON CONFLICT (packet_id, form_key) DO NOTHING
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "packet_id": packet_id,
                    "form_key": form["form_key"],
                    "form_name": form["form_name"],
                    "category": form.get("category", ""),
                    "status": "Not Started",
                    "required": 1 if form.get("required") else 0,
                    "timing_group": form.get("timing_group", "admission"),
                    "timing_label": form.get("timing_label", "Required at Admission"),
                    "requires_signature": 1 if form.get("requires_signature") else 0,
                    "signatures_required": json.dumps(form.get("signatures_required", [])),
                    "allow_attachments": 1 if form.get("allow_attachments") else 0,
                    "allow_revocation": 1 if form.get("allow_revocation") else 0,
                    "expires_in_days": form.get("expires_in_days"),
                    "expires_at": expires_at,
                    "review_status": "Not Reviewed",
                    "created_at": now,
                    "updated_at": now,
                },
            )

    def _get_forms(self, conn, packet_id: str) -> List[Dict[str, Any]]:
        result = conn.execute(
            text(
                """
                SELECT f.*,
                    (SELECT COUNT(*) FROM railway_admission_form_attachments a
                     WHERE a.packet_id = f.packet_id AND a.form_key = f.form_key
                    ) AS attachment_count
                FROM railway_admission_packet_forms f
                WHERE f.packet_id = :packet_id
                ORDER BY CASE f.timing_group
                    WHEN 'admission' THEN 1
                    WHEN '72_hours'  THEN 2
                    WHEN '7_days'    THEN 3
                    ELSE 4 END,
                f.form_key
                """
            ),
            {"packet_id": packet_id},
        )
        return [self._form_row_to_dict(dict(r)) for r in result.mappings().all()]

    # ── Packet operations ──────────────────────────────────────────────────────

    def get_or_create_packet(
        self, client_id: str, client_name: str, case_manager_id: str
    ) -> Dict[str, Any]:
        with self._db() as conn:
            row = conn.execute(
                text("SELECT * FROM railway_admission_packets WHERE client_id = :c"),
                {"c": client_id},
            ).mappings().first()

            if row:
                packet = dict(row)
                packet["forms"] = self._get_forms(conn, packet["id"])
                packet["progress_percent"] = _calc_progress(packet["forms"])
                conn.execute(
                    text(
                        "UPDATE railway_admission_packets "
                        "SET progress_percent = :p WHERE id = :id"
                    ),
                    {"p": packet["progress_percent"], "id": packet["id"]},
                )
                return packet

            packet_id = str(uuid.uuid4())
            now = _now()
            conn.execute(
                text(
                    """
                    INSERT INTO railway_admission_packets
                       (id, client_id, client_name, case_manager_id,
                        status, progress_percent, created_at, updated_at)
                    VALUES
                       (:id, :client_id, :client_name, :case_manager_id,
                        :status, :progress_percent, :created_at, :updated_at)
                    """
                ),
                {
                    "id": packet_id,
                    "client_id": client_id,
                    "client_name": client_name,
                    "case_manager_id": case_manager_id,
                    "status": "In Progress",
                    "progress_percent": 0,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            self._seed_forms(conn, packet_id, now)
            forms = self._get_forms(conn, packet_id)
            return {
                "id": packet_id,
                "client_id": client_id,
                "client_name": client_name,
                "case_manager_id": case_manager_id,
                "status": "In Progress",
                "progress_percent": 0,
                "created_at": now,
                "updated_at": now,
                "forms": forms,
            }

    def get_packet_by_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute(
                text("SELECT * FROM railway_admission_packets WHERE client_id = :c"),
                {"c": client_id},
            ).mappings().first()
            if not row:
                return None
            packet = dict(row)
            packet["forms"] = self._get_forms(conn, packet["id"])
            packet["progress_percent"] = _calc_progress(packet["forms"])
            conn.execute(
                text(
                    "UPDATE railway_admission_packets "
                    "SET progress_percent = :p WHERE id = :id"
                ),
                {"p": packet["progress_percent"], "id": packet["id"]},
            )
            return packet

    def get_packet_by_id(self, packet_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute(
                text("SELECT * FROM railway_admission_packets WHERE id = :id"),
                {"id": packet_id},
            ).mappings().first()
            if not row:
                return None
            packet = dict(row)
            packet["forms"] = self._get_forms(conn, packet["id"])
            packet["progress_percent"] = _calc_progress(packet["forms"])
            conn.execute(
                text(
                    "UPDATE railway_admission_packets "
                    "SET progress_percent = :p WHERE id = :id"
                ),
                {"p": packet["progress_percent"], "id": packet["id"]},
            )
            return packet

    # ── Form status ────────────────────────────────────────────────────────────

    def update_form_status(
        self, packet_id: str, form_key: str, status: str, notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        now = _now()
        with self._db() as conn:
            row = conn.execute(
                text(
                    "SELECT * FROM railway_admission_packet_forms "
                    "WHERE packet_id = :pid AND form_key = :fk"
                ),
                {"pid": packet_id, "fk": form_key},
            ).mappings().first()
            if not row:
                return None
            row = dict(row)

            completed_at = row["completed_at"]
            if status == "Completed" and not completed_at:
                completed_at = now
            elif status != "Completed":
                completed_at = None

            started_at = row["started_at"]
            if not started_at and status != "Not Started":
                started_at = now

            conn.execute(
                text(
                    """
                    UPDATE railway_admission_packet_forms
                    SET status = :status, notes = :notes, started_at = :started_at,
                        completed_at = :completed_at, updated_at = :updated_at
                    WHERE packet_id = :packet_id AND form_key = :form_key
                    """
                ),
                {
                    "status": status,
                    "notes": notes or row["notes"],
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "updated_at": now,
                    "packet_id": packet_id,
                    "form_key": form_key,
                },
            )

            forms = self._get_forms(conn, packet_id)
            progress = _calc_progress(forms)
            packet_status = "Completed" if progress == 100 else "In Progress"
            conn.execute(
                text(
                    "UPDATE railway_admission_packets "
                    "SET progress_percent = :p, status = :s, updated_at = :u "
                    "WHERE id = :id"
                ),
                {"p": progress, "s": packet_status, "u": now, "id": packet_id},
            )

            updated = conn.execute(
                text(
                    "SELECT * FROM railway_admission_packet_forms "
                    "WHERE packet_id = :pid AND form_key = :fk"
                ),
                {"pid": packet_id, "fk": form_key},
            ).mappings().first()
            return self._form_row_to_dict(dict(updated))

    # ── Form response ──────────────────────────────────────────────────────────

    def get_form_response(self, packet_id: str, form_key: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute(
                text(
                    "SELECT * FROM railway_admission_form_responses "
                    "WHERE packet_id = :pid AND form_key = :fk"
                ),
                {"pid": packet_id, "fk": form_key},
            ).mappings().first()
            if not row:
                return None
            d = dict(row)
            try:
                d["response_data"] = json.loads(d.get("response_data") or "{}")
            except (ValueError, TypeError):
                d["response_data"] = {}
            return d

    def save_form_response(
        self, packet_id: str, form_key: str, response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        now = _now()
        serialized = json.dumps(response_data)
        with self._db() as conn:
            existing = conn.execute(
                text(
                    "SELECT id FROM railway_admission_form_responses "
                    "WHERE packet_id = :pid AND form_key = :fk"
                ),
                {"pid": packet_id, "fk": form_key},
            ).mappings().first()

            if existing:
                row_id = existing["id"]
                conn.execute(
                    text(
                        """
                        UPDATE railway_admission_form_responses
                        SET response_data = :data, updated_at = :updated_at
                        WHERE packet_id = :pid AND form_key = :fk
                        """
                    ),
                    {"data": serialized, "updated_at": now, "pid": packet_id, "fk": form_key},
                )
            else:
                row_id = str(uuid.uuid4())
                conn.execute(
                    text(
                        """
                        INSERT INTO railway_admission_form_responses
                           (id, packet_id, form_key, response_data, created_at, updated_at)
                        VALUES (:id, :packet_id, :form_key, :response_data, :created_at, :updated_at)
                        """
                    ),
                    {
                        "id": row_id,
                        "packet_id": packet_id,
                        "form_key": form_key,
                        "response_data": serialized,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
        return {
            "id": row_id,
            "packet_id": packet_id,
            "form_key": form_key,
            "response_data": response_data,
            "updated_at": now,
        }

    # ── Attachments ────────────────────────────────────────────────────────────

    def get_attachments(self, packet_id: str, form_key: str) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT * FROM railway_admission_form_attachments
                    WHERE packet_id = :pid AND form_key = :fk
                    ORDER BY created_at ASC
                    """
                ),
                {"pid": packet_id, "fk": form_key},
            ).mappings().all()
            result = []
            for r in rows:
                d = dict(r)
                d["file_exists"] = _resolve_attachment_path(d["storage_path"]).exists()
                result.append(d)
            return result

    def add_attachment(
        self,
        packet_id: str,
        form_key: str,
        client_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
        storage_path: str,
        uploaded_by: str = "",
    ) -> Dict[str, Any]:
        now = _now()
        att_id = str(uuid.uuid4())
        with self._db() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO railway_admission_form_attachments
                       (id, packet_id, form_key, client_id, file_name, file_type,
                        file_size, storage_path, uploaded_by, created_at)
                    VALUES (:id, :packet_id, :form_key, :client_id, :file_name, :file_type,
                            :file_size, :storage_path, :uploaded_by, :created_at)
                    """
                ),
                {
                    "id": att_id,
                    "packet_id": packet_id,
                    "form_key": form_key,
                    "client_id": client_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_size": file_size,
                    "storage_path": storage_path,
                    "uploaded_by": uploaded_by,
                    "created_at": now,
                },
            )
        return {
            "id": att_id,
            "packet_id": packet_id,
            "form_key": form_key,
            "client_id": client_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "storage_path": storage_path,
            "uploaded_by": uploaded_by,
            "created_at": now,
        }

    def delete_attachment(self, attachment_id: str) -> bool:
        with self._db() as conn:
            result = conn.execute(
                text("DELETE FROM railway_admission_form_attachments WHERE id = :id"),
                {"id": attachment_id},
            )
            return result.rowcount > 0

    def get_attachment_by_id(self, attachment_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute(
                text("SELECT * FROM railway_admission_form_attachments WHERE id = :id"),
                {"id": attachment_id},
            ).mappings().first()
            return dict(row) if row else None

    # ── Staff review ───────────────────────────────────────────────────────────

    def update_form_review(
        self,
        packet_id: str,
        form_key: str,
        review_status: str,
        review_notes: Optional[str] = None,
        reviewed_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        now = _now()
        with self._db() as conn:
            row = conn.execute(
                text(
                    "SELECT * FROM railway_admission_packet_forms "
                    "WHERE packet_id = :pid AND form_key = :fk"
                ),
                {"pid": packet_id, "fk": form_key},
            ).mappings().first()
            if not row:
                return None
            row = dict(row)

            reviewed_at = row["reviewed_at"]
            if review_status in ("Approved", "Needs Correction"):
                reviewed_at = now

            conn.execute(
                text(
                    """
                    UPDATE railway_admission_packet_forms
                    SET review_status = :review_status,
                        review_notes = :review_notes,
                        reviewed_by = :reviewed_by,
                        reviewed_at = :reviewed_at,
                        updated_at = :updated_at
                    WHERE packet_id = :packet_id AND form_key = :form_key
                    """
                ),
                {
                    "review_status": review_status,
                    "review_notes": review_notes if review_notes is not None else row["review_notes"],
                    "reviewed_by": reviewed_by if reviewed_by is not None else row["reviewed_by"],
                    "reviewed_at": reviewed_at,
                    "updated_at": now,
                    "packet_id": packet_id,
                    "form_key": form_key,
                },
            )
            updated = conn.execute(
                text(
                    "SELECT * FROM railway_admission_packet_forms "
                    "WHERE packet_id = :pid AND form_key = :fk"
                ),
                {"pid": packet_id, "fk": form_key},
            ).mappings().first()
            return self._form_row_to_dict(dict(updated))

    # ── Task suppression ───────────────────────────────────────────────────────

    def suppress_task(
        self,
        client_id: str,
        task_key: str,
        status: str,
        reason: Optional[str] = None,
        dismissed_by: Optional[str] = None,
    ) -> None:
        now = _now()
        with self._db() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO railway_admissions_task_suppressions
                       (id, client_id, task_key, status, reason,
                        dismissed_by, dismissed_at, created_at)
                    VALUES (:id, :client_id, :task_key, :status, :reason,
                            :dismissed_by, :dismissed_at, :created_at)
                    ON CONFLICT (client_id, task_key) DO UPDATE SET
                        status       = EXCLUDED.status,
                        reason       = EXCLUDED.reason,
                        dismissed_by = EXCLUDED.dismissed_by,
                        dismissed_at = EXCLUDED.dismissed_at
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "client_id": client_id,
                    "task_key": task_key,
                    "status": status,
                    "reason": reason,
                    "dismissed_by": dismissed_by,
                    "dismissed_at": now,
                    "created_at": now,
                },
            )

    def get_task_suppressions(self, client_id: str) -> Dict[str, str]:
        with self._db() as conn:
            rows = conn.execute(
                text(
                    "SELECT task_key, status FROM railway_admissions_task_suppressions "
                    "WHERE client_id = :cid"
                ),
                {"cid": client_id},
            ).mappings().all()
            return {r["task_key"]: r["status"] for r in rows}

    # ── Task dedup tracking ────────────────────────────────────────────────────

    def record_task_key(
        self,
        client_id: str,
        task_key: str,
        reminder_id: Optional[str] = None,
        case_manager_id: Optional[str] = None,
    ) -> None:
        now = _now()
        with self._db() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO railway_admissions_created_tasks
                       (id, client_id, task_key, reminder_id, case_manager_id, created_at)
                    VALUES (:id, :client_id, :task_key, :reminder_id, :case_manager_id, :created_at)
                    ON CONFLICT (client_id, task_key) DO NOTHING
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "client_id": client_id,
                    "task_key": task_key,
                    "reminder_id": reminder_id,
                    "case_manager_id": case_manager_id,
                    "created_at": now,
                },
            )

    def get_created_task_keys(self, client_id: str) -> List[str]:
        with self._db() as conn:
            rows = conn.execute(
                text(
                    "SELECT task_key FROM railway_admissions_created_tasks "
                    "WHERE client_id = :cid"
                ),
                {"cid": client_id},
            ).mappings().all()
            return [r["task_key"] for r in rows]

    # ── Financial coordination ─────────────────────────────────────────────────

    def get_financial_coordination_readonly(self, client_id: str) -> Dict[str, Any]:
        with self._db() as conn:
            row = conn.execute(
                text(
                    "SELECT * FROM railway_admissions_financial_coordination "
                    "WHERE client_id = :cid"
                ),
                {"cid": client_id},
            ).mappings().first()
            if row:
                return self._fc_row_to_dict(dict(row))
            return {
                "exists": False,
                "billing_explained_status": "Not Started",
                "insurance_verification_status": "Not Started",
                "cob_status": "Not Needed",
                "payment_plan_status": "Not Needed",
                "std_needed": "Unknown",
                "std_status": "Not Started",
                "fmla_needed": "Unknown",
                "discharge_planning_started": False,
            }

    def get_recent_fc_events(self, client_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT * FROM railway_admissions_financial_coordination_events
                    WHERE client_id = :cid
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"cid": client_id, "limit": limit},
            ).mappings().all()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["changed_fields"] = json.loads(d.get("changed_fields_json") or "[]")
                except (ValueError, TypeError):
                    d["changed_fields"] = []
                result.append(d)
            return result

    def get_financial_coordination(self, client_id: str) -> Dict[str, Any]:
        with self._db() as conn:
            row = conn.execute(
                text(
                    "SELECT * FROM railway_admissions_financial_coordination "
                    "WHERE client_id = :cid"
                ),
                {"cid": client_id},
            ).mappings().first()
            if row:
                return self._fc_row_to_dict(dict(row))
            packet_row = conn.execute(
                text(
                    "SELECT id, case_manager_id FROM railway_admission_packets "
                    "WHERE client_id = :cid"
                ),
                {"cid": client_id},
            ).mappings().first()
            now = _now()
            fc_id = str(uuid.uuid4())
            packet_id_val = packet_row["id"] if packet_row else ""
            case_mgr = packet_row["case_manager_id"] if packet_row else ""
            conn.execute(
                text(
                    """
                    INSERT INTO railway_admissions_financial_coordination
                       (id, client_id, packet_id, case_manager_id, created_at, updated_at)
                    VALUES (:id, :client_id, :packet_id, :case_manager_id, :created_at, :updated_at)
                    ON CONFLICT (client_id) DO NOTHING
                    """
                ),
                {
                    "id": fc_id,
                    "client_id": client_id,
                    "packet_id": packet_id_val,
                    "case_manager_id": case_mgr,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            row = conn.execute(
                text(
                    "SELECT * FROM railway_admissions_financial_coordination "
                    "WHERE client_id = :cid"
                ),
                {"cid": client_id},
            ).mappings().first()
            if not row:
                return {
                    "billing_explained_status": "Not Started",
                    "insurance_verification_status": "Not Started",
                    "cob_status": "Not Needed",
                    "payment_plan_status": "Not Needed",
                    "std_needed": "Unknown",
                    "std_status": "Not Started",
                    "fmla_needed": "Unknown",
                    "discharge_planning_started": False,
                }
            return self._fc_row_to_dict(dict(row))

    def upsert_financial_coordination(
        self,
        client_id: str,
        packet_id: str,
        fields: Dict[str, Any],
        changed_by: str = "",
    ) -> Dict[str, Any]:
        now = _now()
        safe = {k: (int(v) if isinstance(v, bool) else v) for k, v in fields.items() if k in _FC_ALLOWED_COLUMNS}
        if changed_by:
            safe["last_updated_by"] = changed_by
        with self._db() as conn:
            existing = conn.execute(
                text(
                    "SELECT * FROM railway_admissions_financial_coordination "
                    "WHERE client_id = :cid"
                ),
                {"cid": client_id},
            ).mappings().first()
            existing = dict(existing) if existing else None

            _AUDIT_META = {"updated_at", "last_updated_by"}

            if existing:
                prev = existing
                if safe:
                    safe["updated_at"] = now
                    set_clause = ", ".join(f"{k} = :_s_{k}" for k in safe)
                    params: Dict[str, Any] = {f"_s_{k}": v for k, v in safe.items()}
                    params["_where_cid"] = client_id
                    conn.execute(
                        text(
                            f"UPDATE railway_admissions_financial_coordination "
                            f"SET {set_clause} WHERE client_id = :_where_cid"
                        ),
                        params,
                    )
                changed_field_names = [k for k in safe if k not in _AUDIT_META]
                if changed_field_names:
                    prev_vals = {k: prev.get(k) for k in changed_field_names}
                    new_vals = {k: safe[k] for k in changed_field_names}
                    conn.execute(
                        text(
                            """
                            INSERT INTO railway_admissions_financial_coordination_events
                               (id, client_id, packet_id, event_type, changed_by,
                                changed_fields_json, previous_values_json, new_values_json,
                                created_at)
                            VALUES (:id, :client_id, :packet_id, :event_type, :changed_by,
                                    :changed_fields_json, :previous_values_json, :new_values_json,
                                    :created_at)
                            """
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "client_id": client_id,
                            "packet_id": existing.get("packet_id") or packet_id,
                            "event_type": "update",
                            "changed_by": changed_by,
                            "changed_fields_json": json.dumps(changed_field_names),
                            "previous_values_json": json.dumps(prev_vals),
                            "new_values_json": json.dumps(new_vals),
                            "created_at": now,
                        },
                    )
            else:
                fc_id = str(uuid.uuid4())
                insert_data: Dict[str, Any] = {
                    "id": fc_id,
                    "client_id": client_id,
                    "packet_id": packet_id,
                    "created_at": now,
                    "updated_at": now,
                    **safe,
                }
                cols = list(insert_data.keys())
                vals_clause = ", ".join(f":{k}" for k in cols)
                conn.execute(
                    text(
                        f"INSERT INTO railway_admissions_financial_coordination "
                        f"({', '.join(cols)}) VALUES ({vals_clause})"
                    ),
                    insert_data,
                )
                _create_fields = [k for k in safe if k not in _AUDIT_META]
                conn.execute(
                    text(
                        """
                        INSERT INTO railway_admissions_financial_coordination_events
                           (id, client_id, packet_id, event_type, changed_by,
                            changed_fields_json, created_at)
                        VALUES (:id, :client_id, :packet_id, :event_type, :changed_by,
                                :changed_fields_json, :created_at)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "client_id": client_id,
                        "packet_id": packet_id,
                        "event_type": "create",
                        "changed_by": changed_by,
                        "changed_fields_json": json.dumps(_create_fields),
                        "created_at": now,
                    },
                )

            row = conn.execute(
                text(
                    "SELECT * FROM railway_admissions_financial_coordination "
                    "WHERE client_id = :cid"
                ),
                {"cid": client_id},
            ).mappings().first()
            return self._fc_row_to_dict(dict(row)) if row else self.get_financial_coordination(client_id)
