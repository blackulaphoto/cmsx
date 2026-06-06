from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import (
    ALLOWED_DISCOVERY_RUN_STATUSES,
    ALLOWED_LISTING_STATUSES,
    ALLOWED_RAW_REVIEW_STATUSES,
    ALLOWED_SOURCE_TYPES,
    DUPLICATE_CANDIDATE_STATUSES,
    DiscoveryJobCreate,
    DiscoveryJobUpdate,
    ListingVerifyRequest,
    SoberLivingDirectorySourceCreate,
    SoberLivingDirectorySourceUpdate,
    SoberLivingDirectoryListingCreate,
    SoberLivingDirectoryListingUpdate,
    VerificationTaskCreate,
    VerificationTaskUpdate,
    utcnow_iso,
)

logger = logging.getLogger(__name__)


DUPLICATE_DIFF_FIELDS = [
    "name",
    "operator_name",
    "website",
    "phone",
    "email",
    "address",
    "city",
    "state",
    "zip_code",
    "neighborhood",
    "population_served",
    "house_type",
    "certification_status",
    "certification_body",
    "certification_expiration_date",
    "monthly_rent_min",
    "monthly_rent_max",
    "deposit_required",
    "accepts_insurance",
    "accepts_mat",
    "accepts_probation_parole",
    "pets_allowed",
    "bed_availability_status",
    "notes",
    "source_urls_json",
]
LISTING_CHANGE_LOG_FIELDS = DUPLICATE_DIFF_FIELDS + [
    "last_availability_check_date",
    "last_verified_date",
    "verification_method",
    "risk_flags_json",
    "internal_referral_notes",
    "status",
]
PROTECTED_DUPLICATE_STATUSES = {"do_not_refer", "use_caution", "archived"}
RAW_APPROVAL_REQUIRED_FIELDS = ["name", "city", "state"]


class SoberLivingDirectoryDatabase:
    def __init__(self, db_path: str = "databases/sober_living_directory.db"):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.setup_database()

    def connect(self):
        if self.connection:
            return self.connection
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        return self.connection

    def setup_database(self):
        conn = self.connect()
        tables = [
            """
            CREATE TABLE IF NOT EXISTS sober_living_directory_sources (
                source_id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                base_url TEXT,
                trust_level TEXT,
                supports_scraping INTEGER DEFAULT 0,
                supports_api INTEGER DEFAULT 0,
                requires_manual_review INTEGER DEFAULT 1,
                last_checked_at TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sober_living_directory_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                operator_name TEXT,
                website TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                city TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'CA',
                zip_code TEXT,
                latitude REAL,
                longitude REAL,
                neighborhood TEXT,
                population_served TEXT,
                house_type TEXT,
                certification_status TEXT,
                certification_body TEXT,
                certification_expiration_date TEXT,
                monthly_rent_min REAL,
                monthly_rent_max REAL,
                deposit_required INTEGER,
                accepts_insurance INTEGER,
                accepts_mat INTEGER,
                accepts_probation_parole INTEGER,
                pets_allowed INTEGER,
                bed_availability_status TEXT,
                last_availability_check_date TEXT,
                last_verified_date TEXT,
                verification_method TEXT,
                trust_score INTEGER NOT NULL DEFAULT 0,
                risk_flags_json TEXT NOT NULL DEFAULT '[]',
                notes TEXT,
                internal_referral_notes TEXT,
                primary_source_id TEXT,
                source_urls_json TEXT NOT NULL DEFAULT '[]',
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_review',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (primary_source_id) REFERENCES sober_living_directory_sources(source_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sober_living_raw_listings (
                raw_id TEXT PRIMARY KEY,
                source_id TEXT,
                run_id TEXT,
                source_url TEXT,
                raw_name TEXT,
                raw_address TEXT,
                raw_phone TEXT,
                raw_email TEXT,
                raw_website TEXT,
                raw_text TEXT,
                extracted_json TEXT NOT NULL DEFAULT '{}',
                content_hash TEXT,
                discovered_at TEXT NOT NULL,
                matched_listing_id TEXT,
                review_status TEXT NOT NULL DEFAULT 'new',
                review_notes TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sober_living_discovery_jobs (
                job_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                job_name TEXT NOT NULL,
                job_type TEXT NOT NULL,
                target_city TEXT,
                target_state TEXT,
                query TEXT,
                schedule_label TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                last_run_at TEXT,
                next_run_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES sober_living_directory_sources(source_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sober_living_discovery_runs (
                run_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                records_found INTEGER NOT NULL DEFAULT 0,
                raw_records_created INTEGER NOT NULL DEFAULT 0,
                duplicates_detected INTEGER NOT NULL DEFAULT 0,
                errors_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                notes TEXT,
                FOREIGN KEY (job_id) REFERENCES sober_living_discovery_jobs(job_id),
                FOREIGN KEY (source_id) REFERENCES sober_living_directory_sources(source_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sober_living_directory_change_log (
                change_id TEXT PRIMARY KEY,
                listing_id TEXT,
                raw_id TEXT,
                change_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                source_id TEXT,
                detected_at TEXT NOT NULL,
                reviewed_by TEXT,
                reviewed_at TEXT,
                action_taken TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sober_living_verification_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                listing_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'medium',
                assigned_to TEXT,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                result_notes TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (listing_id) REFERENCES sober_living_directory_listings(listing_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sober_living_duplicate_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT UNIQUE NOT NULL,
                raw_id TEXT NOT NULL,
                existing_listing_id TEXT NOT NULL,
                proposed_name TEXT,
                existing_name TEXT,
                confidence_score INTEGER NOT NULL DEFAULT 0,
                match_reasons_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'open',
                resolution_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY (raw_id) REFERENCES sober_living_raw_listings(raw_id),
                FOREIGN KEY (existing_listing_id) REFERENCES sober_living_directory_listings(listing_id)
            )
            """,
        ]
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_sld_listings_status ON sober_living_directory_listings(status)",
            "CREATE INDEX IF NOT EXISTS idx_sld_listings_city ON sober_living_directory_listings(city)",
            "CREATE INDEX IF NOT EXISTS idx_sld_listings_population ON sober_living_directory_listings(population_served)",
            "CREATE INDEX IF NOT EXISTS idx_sld_tasks_listing ON sober_living_verification_tasks(listing_id)",
            "CREATE INDEX IF NOT EXISTS idx_sld_tasks_status ON sober_living_verification_tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_sld_change_log_listing ON sober_living_directory_change_log(listing_id)",
            "CREATE INDEX IF NOT EXISTS idx_sld_duplicates_status ON sober_living_duplicate_candidates(status)",
            "CREATE INDEX IF NOT EXISTS idx_sld_duplicates_existing ON sober_living_duplicate_candidates(existing_listing_id)",
            "CREATE INDEX IF NOT EXISTS idx_sld_raw_review_status ON sober_living_raw_listings(review_status)",
            "CREATE INDEX IF NOT EXISTS idx_sld_raw_run ON sober_living_raw_listings(run_id)",
            "CREATE INDEX IF NOT EXISTS idx_sld_sources_type ON sober_living_directory_sources(source_type)",
            "CREATE INDEX IF NOT EXISTS idx_sld_jobs_source ON sober_living_discovery_jobs(source_id)",
            "CREATE INDEX IF NOT EXISTS idx_sld_jobs_active ON sober_living_discovery_jobs(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_sld_runs_job ON sober_living_discovery_runs(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_sld_runs_status ON sober_living_discovery_runs(status)",
        ]
        try:
            for statement in tables + indexes:
                conn.execute(statement)
            self._ensure_column(
                conn,
                table_name="sober_living_raw_listings",
                column_name="run_id",
                column_sql="TEXT",
            )
            self._ensure_column(
                conn,
                table_name="sober_living_raw_listings",
                column_name="review_notes",
                column_sql="TEXT",
            )
            conn.commit()
        except Exception as exc:
            logger.error("Failed setting up sober living directory database: %s", exc)
            raise

    def _ensure_column(self, conn: sqlite3.Connection, *, table_name: str, column_name: str, column_sql: str):
        existing_columns = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")

    def _row_to_listing(self, row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        item["risk_flags_json"] = self._parse_json_list(item.get("risk_flags_json"))
        item["source_urls_json"] = self._parse_json_list(item.get("source_urls_json"))
        for key in [
            "deposit_required",
            "accepts_insurance",
            "accepts_mat",
            "accepts_probation_parole",
            "pets_allowed",
        ]:
            value = item.get(key)
            item[key] = None if value is None else bool(value)
        item["missing_verification_fields"] = self._missing_verification_fields(item)
        item["is_stale"] = self._is_stale(item.get("last_verified_date"))
        return item

    def _row_to_task(self, row: sqlite3.Row) -> Dict[str, Any]:
        return dict(row)

    def _row_to_duplicate_candidate(self, row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        item["match_reasons_json"] = self._parse_json_list(item.get("match_reasons_json"))
        return item

    def _row_to_source(self, row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        for key in ["supports_scraping", "supports_api", "requires_manual_review", "is_active"]:
            item[key] = bool(item.get(key))
        return item

    def _row_to_discovery_job(self, row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        item["is_active"] = bool(item.get("is_active"))
        return item

    def _row_to_discovery_run(self, row: sqlite3.Row) -> Dict[str, Any]:
        return dict(row)

    def _row_to_raw_listing(self, row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        try:
            item["extracted_json"] = json.loads(item.get("extracted_json") or "{}")
        except json.JSONDecodeError:
            item["extracted_json"] = {}
        return item

    @staticmethod
    def _parse_json_list(value: Optional[str]) -> List[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _serialize_json_list(value: Optional[List[str]]) -> str:
        return json.dumps(value or [])

    @staticmethod
    def _has_value(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, list):
            return any(str(item).strip() for item in value)
        return True

    @staticmethod
    def _serialize_change_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, list):
            return json.dumps(value)
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _values_equal(self, left: Any, right: Any) -> bool:
        if isinstance(left, list) or isinstance(right, list):
            return sorted(left or []) == sorted(right or [])
        return left == right

    @staticmethod
    def _to_db_bool(value: Optional[bool]) -> Optional[int]:
        if value is None:
            return None
        return 1 if value else 0

    @staticmethod
    def _parse_iso_date(date_value: Optional[str]) -> Optional[datetime]:
        if not date_value:
            return None
        normalized = date_value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _is_certified(self, data: Dict[str, Any]) -> bool:
        status = (data.get("certification_status") or "").strip().lower()
        body = (data.get("certification_body") or "").strip().lower()
        return any(
            token in status or token in body
            for token in ["certified", "active", "ccapp", "narr", "oxford"]
        )

    def _is_recently_verified(self, last_verified_date: Optional[str]) -> bool:
        parsed = self._parse_iso_date(last_verified_date)
        if not parsed:
            return False
        return parsed >= datetime.utcnow() - timedelta(days=30)

    def _is_stale(self, last_verified_date: Optional[str]) -> bool:
        parsed = self._parse_iso_date(last_verified_date)
        if not parsed:
            return True
        return parsed < datetime.utcnow() - timedelta(days=30)

    def _missing_verification_fields(self, data: Dict[str, Any]) -> List[str]:
        missing = []
        if not data.get("phone"):
            missing.append("phone")
        if not data.get("address"):
            missing.append("address")
        if not data.get("website"):
            missing.append("website")
        if not data.get("last_verified_date"):
            missing.append("last_verified_date")
        if not data.get("verification_method"):
            missing.append("verification_method")
        return missing

    def calculate_trust_score(self, data: Dict[str, Any]) -> int:
        score = 0
        if self._is_certified(data):
            score += 25
        if self._is_recently_verified(data.get("last_verified_date")):
            score += 20
        if data.get("phone"):
            score += 15
        if data.get("address"):
            score += 15
        if data.get("website"):
            score += 10
        if data.get("population_served"):
            score += 10

        status = data.get("status")
        if status == "needs_reverification":
            score -= 20
        elif status == "use_caution":
            score -= 40
        elif status == "do_not_refer":
            score -= 100

        return max(-100, min(100, score))

    def list_listings(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        conn = self.connect()
        where_clauses = []
        params: List[Any] = []

        search = (filters.get("search") or "").strip().lower()
        if search:
            where_clauses.append(
                "(LOWER(name) LIKE ? OR LOWER(COALESCE(operator_name, '')) LIKE ? OR LOWER(COALESCE(address, '')) LIKE ? OR LOWER(COALESCE(phone, '')) LIKE ?)"
            )
            like = f"%{search}%"
            params.extend([like, like, like, like])

        if filters.get("city"):
            where_clauses.append("LOWER(city) = ?")
            params.append(str(filters["city"]).strip().lower())
        if filters.get("population_served"):
            where_clauses.append("LOWER(COALESCE(population_served, '')) LIKE ?")
            params.append(f"%{str(filters['population_served']).strip().lower()}%")
        if filters.get("certification"):
            where_clauses.append("(LOWER(COALESCE(certification_status, '')) LIKE ? OR LOWER(COALESCE(certification_body, '')) LIKE ?)")
            token = f"%{str(filters['certification']).strip().lower()}%"
            params.extend([token, token])
        if filters.get("status") and filters["status"] in ALLOWED_LISTING_STATUSES:
            where_clauses.append("status = ?")
            params.append(filters["status"])
        accepts_mat = filters.get("accepts_mat")
        if accepts_mat is not None and accepts_mat != "":
            where_clauses.append("accepts_mat = ?")
            params.append(1 if str(accepts_mat).lower() == "true" else 0)
        min_trust = filters.get("min_trust_score")
        if min_trust not in (None, ""):
            where_clauses.append("trust_score >= ?")
            params.append(int(min_trust))

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        rows = conn.execute(
            f"""
            SELECT *
            FROM sober_living_directory_listings
            {where_sql}
            ORDER BY
                CASE status
                    WHEN 'pending_review' THEN 1
                    WHEN 'needs_reverification' THEN 2
                    WHEN 'use_caution' THEN 3
                    WHEN 'approved' THEN 4
                    WHEN 'do_not_refer' THEN 5
                    WHEN 'archived' THEN 6
                    ELSE 7
                END,
                LOWER(name)
            """,
            params,
        ).fetchall()
        return [self._row_to_listing(row) for row in rows]

    def get_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM sober_living_directory_listings WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
        if not row:
            return None
        listing = self._row_to_listing(row)
        listing["change_log"] = self.get_change_log(listing_id)
        listing["verification_tasks"] = self.list_tasks(listing_id=listing_id)
        return listing

    def create_listing(self, payload: SoberLivingDirectoryListingCreate) -> Dict[str, Any]:
        conn = self.connect()
        listing_id = f"sld_{uuid.uuid4().hex[:12]}"
        timestamp = utcnow_iso()
        data = payload.model_dump()
        data["listing_id"] = listing_id
        data["first_seen_at"] = data.get("first_seen_at") or timestamp
        data["last_seen_at"] = data.get("last_seen_at") or timestamp
        data["created_at"] = timestamp
        data["updated_at"] = timestamp
        data["trust_score"] = self.calculate_trust_score(data)

        conn.execute(
            """
            INSERT INTO sober_living_directory_listings (
                listing_id, name, operator_name, website, phone, email, address, city, state, zip_code,
                latitude, longitude, neighborhood, population_served, house_type, certification_status,
                certification_body, certification_expiration_date, monthly_rent_min, monthly_rent_max,
                deposit_required, accepts_insurance, accepts_mat, accepts_probation_parole, pets_allowed,
                bed_availability_status, last_availability_check_date, last_verified_date, verification_method,
                trust_score, risk_flags_json, notes, internal_referral_notes, primary_source_id, source_urls_json,
                first_seen_at, last_seen_at, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                listing_id,
                data["name"],
                data.get("operator_name"),
                data.get("website"),
                data.get("phone"),
                data.get("email"),
                data.get("address"),
                data["city"],
                data.get("state", "CA"),
                data.get("zip_code"),
                data.get("latitude"),
                data.get("longitude"),
                data.get("neighborhood"),
                data.get("population_served"),
                data.get("house_type"),
                data.get("certification_status"),
                data.get("certification_body"),
                data.get("certification_expiration_date"),
                data.get("monthly_rent_min"),
                data.get("monthly_rent_max"),
                self._to_db_bool(data.get("deposit_required")),
                self._to_db_bool(data.get("accepts_insurance")),
                self._to_db_bool(data.get("accepts_mat")),
                self._to_db_bool(data.get("accepts_probation_parole")),
                self._to_db_bool(data.get("pets_allowed")),
                data.get("bed_availability_status"),
                data.get("last_availability_check_date"),
                data.get("last_verified_date"),
                data.get("verification_method"),
                data["trust_score"],
                self._serialize_json_list(data.get("risk_flags_json")),
                data.get("notes"),
                data.get("internal_referral_notes"),
                data.get("primary_source_id"),
                self._serialize_json_list(data.get("source_urls_json")),
                timestamp,
                timestamp,
                data.get("status", "pending_review"),
                timestamp,
                timestamp,
            ),
        )
        self._insert_change_log(
            listing_id=listing_id,
            change_type="new_listing",
            old_value=None,
            new_value=data["name"],
        )
        conn.commit()
        return self.get_listing(listing_id)

    def create_listing_from_import_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = SoberLivingDirectoryListingCreate(**data)
        return self.create_listing(payload)

    def update_listing(self, listing_id: str, payload: SoberLivingDirectoryListingUpdate) -> Optional[Dict[str, Any]]:
        existing = self.get_listing(listing_id)
        if not existing:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        merged = {**existing, **update_data}
        merged["updated_at"] = utcnow_iso()
        merged["trust_score"] = self.calculate_trust_score(merged)

        conn = self.connect()
        conn.execute(
            """
            UPDATE sober_living_directory_listings
            SET name = ?, operator_name = ?, website = ?, phone = ?, email = ?, address = ?, city = ?, state = ?,
                zip_code = ?, latitude = ?, longitude = ?, neighborhood = ?, population_served = ?, house_type = ?,
                certification_status = ?, certification_body = ?, certification_expiration_date = ?, monthly_rent_min = ?,
                monthly_rent_max = ?, deposit_required = ?, accepts_insurance = ?, accepts_mat = ?, accepts_probation_parole = ?,
                pets_allowed = ?, bed_availability_status = ?, last_availability_check_date = ?, last_verified_date = ?,
                verification_method = ?, trust_score = ?, risk_flags_json = ?, notes = ?, internal_referral_notes = ?, primary_source_id = ?,
                source_urls_json = ?, last_seen_at = ?, status = ?, updated_at = ?
            WHERE listing_id = ?
            """,
            (
                merged["name"],
                merged.get("operator_name"),
                merged.get("website"),
                merged.get("phone"),
                merged.get("email"),
                merged.get("address"),
                merged["city"],
                merged.get("state", "CA"),
                merged.get("zip_code"),
                merged.get("latitude"),
                merged.get("longitude"),
                merged.get("neighborhood"),
                merged.get("population_served"),
                merged.get("house_type"),
                merged.get("certification_status"),
                merged.get("certification_body"),
                merged.get("certification_expiration_date"),
                merged.get("monthly_rent_min"),
                merged.get("monthly_rent_max"),
                self._to_db_bool(merged.get("deposit_required")),
                self._to_db_bool(merged.get("accepts_insurance")),
                self._to_db_bool(merged.get("accepts_mat")),
                self._to_db_bool(merged.get("accepts_probation_parole")),
                self._to_db_bool(merged.get("pets_allowed")),
                merged.get("bed_availability_status"),
                merged.get("last_availability_check_date"),
                merged.get("last_verified_date"),
                merged.get("verification_method"),
                merged["trust_score"],
                self._serialize_json_list(merged.get("risk_flags_json")),
                merged.get("notes"),
                merged.get("internal_referral_notes"),
                merged.get("primary_source_id"),
                self._serialize_json_list(merged.get("source_urls_json")),
                merged.get("last_seen_at") or utcnow_iso(),
                merged.get("status"),
                merged["updated_at"],
                listing_id,
            ),
        )

        tracked_field_types = {
            "phone": "phone_changed",
            "address": "address_changed",
            "website": "website_changed",
            "certification_status": "certification_changed",
            "status": "status_changed",
            "notes": "notes_changed",
        }
        for field_name in LISTING_CHANGE_LOG_FIELDS:
            old_value = existing.get(field_name)
            new_value = merged.get(field_name)
            if not self._values_equal(old_value, new_value):
                self._insert_change_log(
                    listing_id=listing_id,
                    change_type=tracked_field_types.get(field_name, f"{field_name}_changed"),
                    old_value=self._serialize_change_value(old_value),
                    new_value=self._serialize_change_value(new_value),
                )
        conn.commit()
        return self.get_listing(listing_id)

    def verify_listing(self, listing_id: str, payload: ListingVerifyRequest) -> Optional[Dict[str, Any]]:
        existing = self.get_listing(listing_id)
        if not existing:
            return None

        update_payload = SoberLivingDirectoryListingUpdate(
            last_verified_date=utcnow_iso(),
            verification_method=payload.verification_method,
            status="approved" if existing.get("status") == "pending_review" else existing.get("status"),
            notes=self._merge_notes(existing.get("notes"), payload.result_notes),
        )
        updated = self.update_listing(listing_id, update_payload)
        self._insert_change_log(
            listing_id=listing_id,
            change_type="verification_updated",
            old_value=existing.get("last_verified_date"),
            new_value=updated.get("last_verified_date") if updated else None,
        )
        self.connect().commit()
        return updated

    def archive_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        return self.update_listing(listing_id, SoberLivingDirectoryListingUpdate(status="archived"))

    def get_review_queue(self) -> List[Dict[str, Any]]:
        rows = self.list_listings()
        reviewable = []
        for listing in rows:
            if listing["status"] not in {"pending_review", "needs_reverification", "use_caution"}:
                continue
            reviewable.append(
                {
                    "listing_id": listing["listing_id"],
                    "name": listing["name"],
                    "status": listing["status"],
                    "city": listing["city"],
                    "state": listing["state"],
                    "trust_score": listing["trust_score"],
                    "missing_verification_fields": listing["missing_verification_fields"],
                    "is_stale": listing["is_stale"],
                    "last_verified_date": listing.get("last_verified_date"),
                    "updated_at": listing["updated_at"],
                    "phone": listing.get("phone"),
                    "certification_status": listing.get("certification_status"),
                    "source_urls_json": listing.get("source_urls_json", []),
                }
            )
        return reviewable

    def get_raw_review_queue(self) -> List[Dict[str, Any]]:
        return self.list_raw_records(
            review_statuses=["new", "possible_duplicate", "changed", "error"]
        )

    def get_duplicate_candidates(self, status: str = "open") -> List[Dict[str, Any]]:
        conn = self.connect()
        params: List[Any] = []
        where_sql = ""
        if status:
            where_sql = "WHERE dc.status = ?"
            params.append(status)
        rows = conn.execute(
            f"""
            SELECT dc.*, rl.extracted_json, rl.raw_text, rl.source_url, rl.review_status,
                   l.city AS existing_city, l.state AS existing_state, l.phone AS existing_phone,
                   l.website AS existing_website, l.population_served AS existing_population_served,
                   l.status AS existing_status, l.trust_score AS existing_trust_score
            FROM sober_living_duplicate_candidates dc
            JOIN sober_living_raw_listings rl ON rl.raw_id = dc.raw_id
            JOIN sober_living_directory_listings l ON l.listing_id = dc.existing_listing_id
            {where_sql}
            ORDER BY dc.created_at DESC
            """,
            params,
        ).fetchall()
        candidates = []
        for row in rows:
            item = self._row_to_duplicate_candidate(row)
            try:
                item["extracted_json"] = json.loads(item.get("extracted_json") or "{}")
            except json.JSONDecodeError:
                item["extracted_json"] = {}
            candidates.append(item)
        return candidates

    def get_duplicate_candidate_detail(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute(
            """
            SELECT *
            FROM sober_living_duplicate_candidates
            WHERE candidate_id = ?
            """,
            (candidate_id,),
        ).fetchone()
        if not row:
            return None

        candidate = self._row_to_duplicate_candidate(row)
        raw_row = conn.execute(
            "SELECT * FROM sober_living_raw_listings WHERE raw_id = ?",
            (candidate["raw_id"],),
        ).fetchone()
        if not raw_row:
            return None

        raw_listing = self._row_to_raw_listing(raw_row)
        existing_listing = self.get_listing(candidate["existing_listing_id"])
        if not existing_listing:
            return None

        normalized_imported_fields = self._normalize_duplicate_import_fields(raw_listing.get("extracted_json"))
        return {
            "candidate": candidate,
            "existing_listing": existing_listing,
            "raw_record": raw_listing,
            "normalized_imported_fields": normalized_imported_fields,
            "match_reasons": candidate.get("match_reasons_json", []),
            "confidence_score": candidate.get("confidence_score", 0),
            "field_diff": self._build_duplicate_field_diff(existing_listing, normalized_imported_fields),
        }

    def list_sources(self) -> List[Dict[str, Any]]:
        conn = self.connect()
        rows = conn.execute(
            """
            SELECT *
            FROM sober_living_directory_sources
            ORDER BY LOWER(source_name), created_at DESC
            """
        ).fetchall()
        return [self._row_to_source(row) for row in rows]

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM sober_living_directory_sources WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        return self._row_to_source(row) if row else None

    def create_source(self, payload: SoberLivingDirectorySourceCreate) -> Dict[str, Any]:
        conn = self.connect()
        source_id = f"src_{uuid.uuid4().hex[:12]}"
        timestamp = utcnow_iso()
        data = payload.model_dump()
        conn.execute(
            """
            INSERT INTO sober_living_directory_sources (
                source_id, source_name, source_type, base_url, trust_level, supports_scraping,
                supports_api, requires_manual_review, last_checked_at, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                data["source_name"],
                data["source_type"],
                data.get("base_url"),
                data["trust_level"],
                1 if data.get("supports_scraping") else 0,
                1 if data.get("supports_api") else 0,
                1 if data.get("requires_manual_review", True) else 0,
                data.get("last_checked_at"),
                1 if data.get("is_active", True) else 0,
                timestamp,
                timestamp,
            ),
        )
        conn.commit()
        return self.get_source(source_id)

    def update_source(self, source_id: str, payload: SoberLivingDirectorySourceUpdate) -> Optional[Dict[str, Any]]:
        existing = self.get_source(source_id)
        if not existing:
            return None

        merged = {**existing, **payload.model_dump(exclude_unset=True)}
        merged["updated_at"] = utcnow_iso()
        conn = self.connect()
        conn.execute(
            """
            UPDATE sober_living_directory_sources
            SET source_name = ?, source_type = ?, base_url = ?, trust_level = ?, supports_scraping = ?,
                supports_api = ?, requires_manual_review = ?, last_checked_at = ?, is_active = ?, updated_at = ?
            WHERE source_id = ?
            """,
            (
                merged["source_name"],
                merged["source_type"],
                merged.get("base_url"),
                merged.get("trust_level"),
                1 if merged.get("supports_scraping") else 0,
                1 if merged.get("supports_api") else 0,
                1 if merged.get("requires_manual_review", True) else 0,
                merged.get("last_checked_at"),
                1 if merged.get("is_active", True) else 0,
                merged["updated_at"],
                source_id,
            ),
        )
        conn.commit()
        return self.get_source(source_id)

    def list_discovery_jobs(self) -> List[Dict[str, Any]]:
        conn = self.connect()
        rows = conn.execute(
            """
            SELECT j.*, s.source_name
            FROM sober_living_discovery_jobs j
            JOIN sober_living_directory_sources s ON s.source_id = j.source_id
            ORDER BY j.created_at DESC
            """
        ).fetchall()
        return [self._row_to_discovery_job(row) for row in rows]

    def get_discovery_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute(
            """
            SELECT j.*, s.source_name
            FROM sober_living_discovery_jobs j
            JOIN sober_living_directory_sources s ON s.source_id = j.source_id
            WHERE j.job_id = ?
            """,
            (job_id,),
        ).fetchone()
        return self._row_to_discovery_job(row) if row else None

    def create_discovery_job(self, payload: DiscoveryJobCreate) -> Dict[str, Any]:
        if not self.get_source(payload.source_id):
            raise ValueError("Source not found for discovery job")

        conn = self.connect()
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        timestamp = utcnow_iso()
        data = payload.model_dump()
        conn.execute(
            """
            INSERT INTO sober_living_discovery_jobs (
                job_id, source_id, job_name, job_type, target_city, target_state, query,
                schedule_label, is_active, last_run_at, next_run_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                data["source_id"],
                data["job_name"],
                data["job_type"],
                data.get("target_city"),
                data.get("target_state"),
                data.get("query"),
                data.get("schedule_label"),
                1 if data.get("is_active", True) else 0,
                data.get("last_run_at"),
                data.get("next_run_at"),
                timestamp,
                timestamp,
            ),
        )
        conn.commit()
        return self.get_discovery_job(job_id)

    def update_discovery_job(self, job_id: str, payload: DiscoveryJobUpdate) -> Optional[Dict[str, Any]]:
        existing = self.get_discovery_job(job_id)
        if not existing:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        if update_data.get("source_id") and not self.get_source(update_data["source_id"]):
            raise ValueError("Source not found for discovery job")

        merged = {**existing, **update_data}
        merged["updated_at"] = utcnow_iso()
        conn = self.connect()
        conn.execute(
            """
            UPDATE sober_living_discovery_jobs
            SET source_id = ?, job_name = ?, job_type = ?, target_city = ?, target_state = ?, query = ?,
                schedule_label = ?, is_active = ?, last_run_at = ?, next_run_at = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (
                merged["source_id"],
                merged["job_name"],
                merged["job_type"],
                merged.get("target_city"),
                merged.get("target_state"),
                merged.get("query"),
                merged.get("schedule_label"),
                1 if merged.get("is_active", True) else 0,
                merged.get("last_run_at"),
                merged.get("next_run_at"),
                merged["updated_at"],
                job_id,
            ),
        )
        conn.commit()
        return self.get_discovery_job(job_id)

    def list_discovery_runs(self, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self.connect()
        params: List[Any] = []
        where_sql = ""
        if job_id:
            where_sql = "WHERE r.job_id = ?"
            params.append(job_id)
        rows = conn.execute(
            f"""
            SELECT r.*, j.job_name, s.source_name
            FROM sober_living_discovery_runs r
            JOIN sober_living_discovery_jobs j ON j.job_id = r.job_id
            JOIN sober_living_directory_sources s ON s.source_id = r.source_id
            {where_sql}
            ORDER BY r.started_at DESC
            """,
            params,
        ).fetchall()
        return [self._row_to_discovery_run(row) for row in rows]

    def get_discovery_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute(
            """
            SELECT r.*, j.job_name, s.source_name
            FROM sober_living_discovery_runs r
            JOIN sober_living_discovery_jobs j ON j.job_id = r.job_id
            JOIN sober_living_directory_sources s ON s.source_id = r.source_id
            WHERE r.run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if not row:
            return None
        run = self._row_to_discovery_run(row)
        run["raw_records"] = self.list_raw_records(run_id=run_id)
        return run

    def _create_discovery_run(
        self,
        *,
        job_id: str,
        source_id: str,
        status: str = "running",
        notes: Optional[str] = None,
    ) -> str:
        if status not in ALLOWED_DISCOVERY_RUN_STATUSES:
            raise ValueError("Invalid discovery run status")
        conn = self.connect()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        conn.execute(
            """
            INSERT INTO sober_living_discovery_runs (
                run_id, job_id, source_id, started_at, finished_at, status, records_found,
                raw_records_created, duplicates_detected, errors_count, error_message, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                job_id,
                source_id,
                utcnow_iso(),
                None,
                status,
                0,
                0,
                0,
                0,
                None,
                notes,
            ),
        )
        conn.commit()
        return run_id

    def _finish_discovery_run(
        self,
        run_id: str,
        *,
        status: str,
        records_found: int,
        raw_records_created: int,
        duplicates_detected: int,
        errors_count: int,
        error_message: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        if status not in ALLOWED_DISCOVERY_RUN_STATUSES:
            raise ValueError("Invalid discovery run status")
        conn = self.connect()
        conn.execute(
            """
            UPDATE sober_living_discovery_runs
            SET finished_at = ?, status = ?, records_found = ?, raw_records_created = ?,
                duplicates_detected = ?, errors_count = ?, error_message = ?, notes = ?
            WHERE run_id = ?
            """,
            (
                utcnow_iso(),
                status,
                records_found,
                raw_records_created,
                duplicates_detected,
                errors_count,
                error_message,
                notes,
                run_id,
            ),
        )
        conn.commit()

    def list_raw_records(
        self,
        *,
        review_statuses: Optional[List[str]] = None,
        run_id: Optional[str] = None,
        source_id: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn = self.connect()
        where_clauses: List[str] = []
        params: List[Any] = []
        if review_statuses:
            placeholders = ",".join("?" for _ in review_statuses)
            where_clauses.append(f"rl.review_status IN ({placeholders})")
            params.extend(review_statuses)
        if run_id:
            where_clauses.append("rl.run_id = ?")
            params.append(run_id)
        if source_id:
            where_clauses.append("rl.source_id = ?")
            params.append(source_id)
        if city:
            where_clauses.append("LOWER(COALESCE(json_extract(rl.extracted_json, '$.city'), '')) = ?")
            params.append(city.strip().lower())
        if state:
            where_clauses.append("LOWER(COALESCE(json_extract(rl.extracted_json, '$.state'), '')) = ?")
            params.append(state.strip().lower())
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        rows = conn.execute(
            f"""
            SELECT rl.*, s.source_name, s.source_type, COUNT(dc.candidate_id) AS duplicate_candidate_count
            FROM sober_living_raw_listings rl
            LEFT JOIN sober_living_directory_sources s ON s.source_id = rl.source_id
            LEFT JOIN sober_living_duplicate_candidates dc ON dc.raw_id = rl.raw_id AND dc.status = 'open'
            {where_sql}
            GROUP BY rl.raw_id
            ORDER BY rl.discovered_at DESC
            """,
            params,
        ).fetchall()
        records = []
        for row in rows:
            item = self._row_to_raw_listing(row)
            normalized_preview = self._normalize_raw_record_to_listing_fields(item)
            item["normalized_preview"] = normalized_preview
            item["missing_required_fields"] = self._missing_raw_approval_fields(normalized_preview)
            item["duplicate_candidate_count"] = item.get("duplicate_candidate_count", 0)
            records.append(item)
        return records

    def get_raw_record(self, raw_id: str) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute(
            """
            SELECT rl.*, s.source_name, s.source_type, s.base_url, s.trust_level, s.requires_manual_review,
                   r.status AS run_status, r.started_at AS run_started_at, r.finished_at AS run_finished_at,
                   j.job_name, j.job_type,
                   COUNT(dc.candidate_id) AS duplicate_candidate_count
            FROM sober_living_raw_listings rl
            LEFT JOIN sober_living_directory_sources s ON s.source_id = rl.source_id
            LEFT JOIN sober_living_discovery_runs r ON r.run_id = rl.run_id
            LEFT JOIN sober_living_discovery_jobs j ON j.job_id = r.job_id
            LEFT JOIN sober_living_duplicate_candidates dc ON dc.raw_id = rl.raw_id AND dc.status = 'open'
            WHERE rl.raw_id = ?
            GROUP BY rl.raw_id
            """,
            (raw_id,),
        ).fetchone()
        if not row:
            return None

        raw_record = self._row_to_raw_listing(row)
        source_info = self.get_source(raw_record["source_id"]) if raw_record.get("source_id") else None
        run_info = self.get_discovery_run(raw_record["run_id"]) if raw_record.get("run_id") else None
        duplicate_candidates = self.get_duplicate_candidates_for_raw(raw_id)
        normalized_preview = self._normalize_raw_record_to_listing_fields(raw_record)
        missing_required_fields = self._missing_raw_approval_fields(normalized_preview)
        return {
            "raw_record": raw_record,
            "source": source_info,
            "discovery_run": run_info,
            "original_raw_fields": {
                "raw_name": raw_record.get("raw_name"),
                "raw_address": raw_record.get("raw_address"),
                "raw_phone": raw_record.get("raw_phone"),
                "raw_email": raw_record.get("raw_email"),
                "raw_website": raw_record.get("raw_website"),
                "raw_text": raw_record.get("raw_text"),
            },
            "extracted_json": raw_record.get("extracted_json", {}),
            "normalized_preview_fields": normalized_preview,
            "duplicate_candidates": duplicate_candidates,
            "review_status": raw_record.get("review_status"),
            "missing_required_fields": missing_required_fields,
            "errors": missing_required_fields,
        }

    def get_duplicate_candidates_for_raw(self, raw_id: str, *, status: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self.connect()
        params: List[Any] = [raw_id]
        where_status = ""
        if status:
            where_status = "AND dc.status = ?"
            params.append(status)
        rows = conn.execute(
            f"""
            SELECT dc.*, l.name AS existing_listing_name, l.status AS existing_listing_status
            FROM sober_living_duplicate_candidates dc
            LEFT JOIN sober_living_directory_listings l ON l.listing_id = dc.existing_listing_id
            WHERE dc.raw_id = ?
            {where_status}
            ORDER BY dc.created_at DESC
            """,
            params,
        ).fetchall()
        return [self._row_to_duplicate_candidate(row) for row in rows]

    def approve_raw_record(
        self,
        raw_id: str,
        *,
        direct_approve: bool = False,
        force: bool = False,
        review_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        raw_detail = self.get_raw_record(raw_id)
        if not raw_detail:
            raise ValueError("Raw record not found")

        raw_record = raw_detail["raw_record"]
        if raw_record["review_status"] in {"merged", "rejected", "approved"}:
            raise ValueError(f"Raw record cannot be approved from status {raw_record['review_status']}")

        open_duplicates = [candidate for candidate in raw_detail["duplicate_candidates"] if candidate.get("status") == "open"]
        if open_duplicates and not force:
            raise ValueError("Raw record has an open duplicate candidate. Resolve duplicate review first or force approval explicitly.")

        normalized = raw_detail["normalized_preview_fields"]
        missing_required_fields = raw_detail["missing_required_fields"]
        if missing_required_fields:
            raise ValueError(f"Raw record is missing required fields: {', '.join(missing_required_fields)}")

        payload_data = {
            **normalized,
            "primary_source_id": raw_record.get("source_id"),
            "status": "approved" if direct_approve else "pending_review",
        }
        listing = self.create_listing_from_import_data(payload_data)

        conn = self.connect()
        updated_notes = self._merge_notes(raw_record.get("review_notes"), review_notes)
        conn.execute(
            """
            UPDATE sober_living_raw_listings
            SET review_status = ?, matched_listing_id = ?, review_notes = ?
            WHERE raw_id = ?
            """,
            ("approved", listing["listing_id"], updated_notes, raw_id),
        )
        if open_duplicates and force:
            conn.execute(
                """
                UPDATE sober_living_duplicate_candidates
                SET status = 'kept_separate', resolution_notes = ?, updated_at = ?, resolved_at = ?
                WHERE raw_id = ? AND status = 'open'
                """,
                ("Force-approved into separate listing", utcnow_iso(), utcnow_iso(), raw_id),
            )
        self._insert_change_log(
            listing_id=listing["listing_id"],
            raw_id=raw_id,
            change_type="raw_record_approved",
            old_value=raw_record.get("review_status"),
            new_value=listing["listing_id"],
            source_id=raw_record.get("source_id"),
        )
        conn.commit()
        detail = self.get_raw_record(raw_id)
        return {"listing": self.get_listing(listing["listing_id"]), "raw_record": detail["raw_record"]}

    def reject_raw_record(self, raw_id: str, *, review_notes: Optional[str] = None) -> Dict[str, Any]:
        return self._update_raw_record_review_status(raw_id, status="rejected", review_notes=review_notes, change_type="raw_record_rejected")

    def mark_raw_record_error(self, raw_id: str, *, review_notes: Optional[str] = None) -> Dict[str, Any]:
        return self._update_raw_record_review_status(raw_id, status="error", review_notes=review_notes, change_type="raw_record_marked_error")

    def _update_raw_record_review_status(
        self,
        raw_id: str,
        *,
        status: str,
        review_notes: Optional[str],
        change_type: str,
    ) -> Dict[str, Any]:
        if status not in ALLOWED_RAW_REVIEW_STATUSES:
            raise ValueError("Invalid raw record review status")
        raw_detail = self.get_raw_record(raw_id)
        if not raw_detail:
            raise ValueError("Raw record not found")
        raw_record = raw_detail["raw_record"]
        if raw_record["review_status"] in {"merged", "approved"} and status != raw_record["review_status"]:
            raise ValueError(f"Raw record cannot move from {raw_record['review_status']} to {status}")

        conn = self.connect()
        updated_notes = self._merge_notes(raw_record.get("review_notes"), review_notes)
        conn.execute(
            """
            UPDATE sober_living_raw_listings
            SET review_status = ?, review_notes = ?
            WHERE raw_id = ?
            """,
            (status, updated_notes, raw_id),
        )
        self._insert_change_log(
            listing_id=raw_record.get("matched_listing_id"),
            raw_id=raw_id,
            change_type=change_type,
            old_value=raw_record.get("review_status"),
            new_value=status,
            source_id=raw_record.get("source_id"),
        )
        conn.commit()
        return self.get_raw_record(raw_id)

    def run_manual_discovery_job_test(self, job_id: str) -> Dict[str, Any]:
        job = self.get_discovery_job(job_id)
        if not job:
            raise ValueError("Discovery job not found")

        source = self.get_source(job["source_id"])
        if not source:
            raise ValueError("Source not found for discovery job")

        notes = "Manual Phase 4A fake connector run"
        records = self._build_fake_discovery_records(job)
        return self.process_discovery_records(
            job_id=job_id,
            source_id=job["source_id"],
            records=records,
            notes=notes,
        )

    def process_discovery_records(
        self,
        *,
        job_id: str,
        source_id: str,
        records: List[Dict[str, Any]],
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        job = self.get_discovery_job(job_id)
        if not job:
            raise ValueError("Discovery job not found")

        run_id = self._create_discovery_run(
            job_id=job_id,
            source_id=source_id,
            notes=notes,
        )

        records_found = 0
        raw_records_created = 0
        duplicates_detected = 0
        errors_count = 0
        try:
            for record in records:
                records_found += 1
                duplicate = self.find_possible_duplicate(
                    name=record.get("name"),
                    city=record.get("city"),
                    phone=record.get("phone"),
                    website=record.get("website"),
                )
                raw_id = self.create_raw_listing(
                    source_id=source_id,
                    run_id=run_id,
                    source_url=record.get("website"),
                    raw_name=record.get("name"),
                    raw_address=record.get("address"),
                    raw_phone=record.get("phone"),
                    raw_email=record.get("email"),
                    raw_website=record.get("website"),
                    raw_text=json.dumps(record),
                    extracted_json=record,
                    matched_listing_id=duplicate["listing_id"] if duplicate else None,
                    review_status="possible_duplicate" if duplicate else "new",
                )
                raw_records_created += 1
                if duplicate:
                    duplicates_detected += 1
                    confidence_score, match_reasons = self.score_duplicate_candidate(
                        name=record.get("name"),
                        city=record.get("city"),
                        phone=record.get("phone"),
                        website=record.get("website"),
                        existing_listing=duplicate,
                    )
                    self.create_duplicate_candidate(
                        raw_id=raw_id,
                        existing_listing_id=duplicate["listing_id"],
                        proposed_name=record.get("name"),
                        existing_name=duplicate.get("name"),
                        match_reasons=match_reasons or ["possible_duplicate"],
                        confidence_score=confidence_score,
                    )

            now = utcnow_iso()
            self.update_discovery_job(
                job_id,
                DiscoveryJobUpdate(last_run_at=now),
            )
            self.update_source(
                source_id,
                SoberLivingDirectorySourceUpdate(last_checked_at=now),
            )
            self._finish_discovery_run(
                run_id,
                status="completed",
                records_found=records_found,
                raw_records_created=raw_records_created,
                duplicates_detected=duplicates_detected,
                errors_count=errors_count,
                notes=notes,
            )
        except Exception as exc:
            errors_count += 1
            self._finish_discovery_run(
                run_id,
                status="failed",
                records_found=records_found,
                raw_records_created=raw_records_created,
                duplicates_detected=duplicates_detected,
                errors_count=errors_count,
                error_message=str(exc),
                notes=notes,
            )
            raise

        return self.get_discovery_run(run_id)

    def _normalize_raw_record_to_listing_fields(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        extracted = raw_record.get("extracted_json") or {}
        source_url = raw_record.get("source_url")
        source_urls = extracted.get("source_urls_json") or ([source_url] if source_url else [])
        return {
            "name": extracted.get("name") or raw_record.get("raw_name"),
            "operator_name": extracted.get("operator_name"),
            "website": extracted.get("website") or raw_record.get("raw_website"),
            "phone": extracted.get("phone") or raw_record.get("raw_phone"),
            "email": extracted.get("email") or raw_record.get("raw_email"),
            "address": extracted.get("address") or raw_record.get("raw_address"),
            "city": extracted.get("city"),
            "state": extracted.get("state").upper() if self._has_value(extracted.get("state")) else None,
            "zip_code": extracted.get("zip_code"),
            "latitude": extracted.get("latitude"),
            "longitude": extracted.get("longitude"),
            "neighborhood": extracted.get("neighborhood"),
            "population_served": extracted.get("population_served"),
            "house_type": extracted.get("house_type"),
            "certification_status": extracted.get("certification_status"),
            "certification_body": extracted.get("certification_body"),
            "certification_expiration_date": extracted.get("certification_expiration_date"),
            "monthly_rent_min": extracted.get("monthly_rent_min"),
            "monthly_rent_max": extracted.get("monthly_rent_max"),
            "deposit_required": extracted.get("deposit_required"),
            "accepts_insurance": extracted.get("accepts_insurance"),
            "accepts_mat": extracted.get("accepts_mat"),
            "accepts_probation_parole": extracted.get("accepts_probation_parole"),
            "pets_allowed": extracted.get("pets_allowed"),
            "bed_availability_status": extracted.get("bed_availability_status"),
            "verification_method": extracted.get("verification_method") or "raw_review",
            "notes": extracted.get("notes"),
            "risk_flags_json": extracted.get("risk_flags_json") or [],
            "source_urls_json": source_urls,
            "first_seen_at": raw_record.get("discovered_at"),
            "last_seen_at": raw_record.get("discovered_at"),
        }

    def _missing_raw_approval_fields(self, normalized_preview: Dict[str, Any]) -> List[str]:
        missing = []
        for field in RAW_APPROVAL_REQUIRED_FIELDS:
            if not self._has_value(normalized_preview.get(field)):
                missing.append(field)
        return missing

    def list_tasks(self, listing_id: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self.connect()
        params: List[Any] = []
        where_sql = ""
        if listing_id:
            where_sql = "WHERE listing_id = ?"
            params.append(listing_id)
        rows = conn.execute(
            f"SELECT * FROM sober_living_verification_tasks {where_sql} ORDER BY created_at DESC",
            params,
        ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def create_task(self, payload: VerificationTaskCreate) -> Dict[str, Any]:
        if not self.get_listing(payload.listing_id):
            raise ValueError("Listing not found for verification task")

        conn = self.connect()
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        timestamp = utcnow_iso()
        conn.execute(
            """
            INSERT INTO sober_living_verification_tasks (
                task_id, listing_id, task_type, priority, assigned_to, due_date, status,
                result_notes, created_at, completed_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                payload.listing_id,
                payload.task_type,
                payload.priority,
                payload.assigned_to,
                payload.due_date,
                payload.status,
                payload.result_notes,
                timestamp,
                timestamp if payload.status == "completed" else None,
                timestamp,
            ),
        )
        conn.commit()
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM sober_living_verification_tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return self._row_to_task(row) if row else None

    def update_task(self, task_id: str, payload: VerificationTaskUpdate) -> Optional[Dict[str, Any]]:
        existing = self.get_task(task_id)
        if not existing:
            return None

        merged = {**existing, **payload.model_dump(exclude_unset=True)}
        merged["updated_at"] = utcnow_iso()
        if merged.get("status") == "completed" and not merged.get("completed_at"):
            merged["completed_at"] = utcnow_iso()
        if merged.get("status") != "completed":
            merged["completed_at"] = None

        conn = self.connect()
        conn.execute(
            """
            UPDATE sober_living_verification_tasks
            SET task_type = ?, priority = ?, assigned_to = ?, due_date = ?, status = ?,
                result_notes = ?, completed_at = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (
                merged["task_type"],
                merged["priority"],
                merged.get("assigned_to"),
                merged.get("due_date"),
                merged["status"],
                merged.get("result_notes"),
                merged.get("completed_at"),
                merged["updated_at"],
                task_id,
            ),
        )
        conn.commit()
        return self.get_task(task_id)

    def get_change_log(self, listing_id: str) -> List[Dict[str, Any]]:
        conn = self.connect()
        rows = conn.execute(
            """
            SELECT *
            FROM sober_living_directory_change_log
            WHERE listing_id = ?
            ORDER BY detected_at DESC
            """,
            (listing_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def create_duplicate_candidate(
        self,
        *,
        raw_id: str,
        existing_listing_id: str,
        proposed_name: Optional[str],
        existing_name: Optional[str],
        match_reasons: List[str],
        confidence_score: int,
    ) -> Dict[str, Any]:
        conn = self.connect()
        existing = conn.execute(
            """
            SELECT *
            FROM sober_living_duplicate_candidates
            WHERE raw_id = ? AND existing_listing_id = ? AND status = 'open'
            """,
            (raw_id, existing_listing_id),
        ).fetchone()
        if existing:
            return self._row_to_duplicate_candidate(existing)

        candidate_id = f"dup_{uuid.uuid4().hex[:12]}"
        timestamp = utcnow_iso()
        conn.execute(
            """
            INSERT INTO sober_living_duplicate_candidates (
                candidate_id, raw_id, existing_listing_id, proposed_name, existing_name,
                confidence_score, match_reasons_json, status, resolution_notes, created_at, updated_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                raw_id,
                existing_listing_id,
                proposed_name,
                existing_name,
                confidence_score,
                self._serialize_json_list(match_reasons),
                "open",
                None,
                timestamp,
                timestamp,
                None,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sober_living_duplicate_candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        return self._row_to_duplicate_candidate(row)

    def resolve_duplicate_candidate(
        self,
        candidate_id: str,
        *,
        action: str,
        resolution_notes: Optional[str] = None,
        selected_imported_fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        if action not in DUPLICATE_CANDIDATE_STATUSES - {"open"}:
            raise ValueError("Invalid duplicate resolution action")

        conn = self.connect()
        candidate_row = conn.execute(
            "SELECT * FROM sober_living_duplicate_candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        if not candidate_row:
            return None

        candidate = self._row_to_duplicate_candidate(candidate_row)
        raw_row = conn.execute(
            "SELECT * FROM sober_living_raw_listings WHERE raw_id = ?",
            (candidate["raw_id"],),
        ).fetchone()
        if not raw_row:
            return None

        extracted_json = json.loads(raw_row["extracted_json"] or "{}")
        existing_listing = self.get_listing(candidate["existing_listing_id"])
        if not existing_listing:
            return None

        timestamp = utcnow_iso()
        if action == "merged":
            if "status" in set(selected_imported_fields or []):
                raise ValueError("Status cannot be overwritten during duplicate merge")
            merged_data = self._build_duplicate_merge_updates(
                existing_listing=existing_listing,
                incoming=extracted_json,
                selected_imported_fields=selected_imported_fields or [],
            )
            updated = self.update_listing(
                existing_listing["listing_id"],
                SoberLivingDirectoryListingUpdate(**merged_data),
            ) if merged_data else existing_listing
            conn.execute(
                "UPDATE sober_living_raw_listings SET review_status = ?, matched_listing_id = ? WHERE raw_id = ?",
                ("merged", existing_listing["listing_id"], candidate["raw_id"]),
            )
            self._insert_change_log(
                listing_id=existing_listing["listing_id"],
                raw_id=candidate["raw_id"],
                change_type="duplicate_merged",
                old_value=existing_listing["name"],
                new_value=updated["name"] if updated else existing_listing["name"],
            )
        elif action == "kept_separate":
            created = self.create_listing_from_import_data(extracted_json)
            conn.execute(
                "UPDATE sober_living_raw_listings SET review_status = ?, matched_listing_id = ? WHERE raw_id = ?",
                ("approved", created["listing_id"], candidate["raw_id"]),
            )
            self._insert_change_log(
                listing_id=created["listing_id"],
                raw_id=candidate["raw_id"],
                change_type="duplicate_kept_separate",
                old_value=None,
                new_value=created["name"],
            )
        elif action == "rejected":
            conn.execute(
                "UPDATE sober_living_raw_listings SET review_status = ? WHERE raw_id = ?",
                ("rejected", candidate["raw_id"]),
            )

        conn.execute(
            """
            UPDATE sober_living_duplicate_candidates
            SET status = ?, resolution_notes = ?, updated_at = ?, resolved_at = ?
            WHERE candidate_id = ?
            """,
            (action, resolution_notes, timestamp, timestamp, candidate_id),
        )
        conn.commit()

        resolved_row = conn.execute(
            "SELECT * FROM sober_living_duplicate_candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        return self._row_to_duplicate_candidate(resolved_row) if resolved_row else None

    def create_raw_listing(
        self,
        *,
        source_id: Optional[str],
        run_id: Optional[str] = None,
        source_url: Optional[str],
        raw_name: Optional[str],
        raw_address: Optional[str],
        raw_phone: Optional[str],
        raw_email: Optional[str],
        raw_website: Optional[str],
        raw_text: str,
        extracted_json: Dict[str, Any],
        matched_listing_id: Optional[str] = None,
        review_status: str = "new",
        review_notes: Optional[str] = None,
    ) -> str:
        if review_status not in ALLOWED_RAW_REVIEW_STATUSES:
            raise ValueError("Invalid raw listing review status")
        conn = self.connect()
        raw_id = f"raw_{uuid.uuid4().hex[:12]}"
        content_hash = hashlib.sha256(raw_text.encode("utf-8", errors="ignore")).hexdigest()
        conn.execute(
            """
            INSERT INTO sober_living_raw_listings (
                raw_id, source_id, run_id, source_url, raw_name, raw_address, raw_phone, raw_email,
                raw_website, raw_text, extracted_json, content_hash, discovered_at,
                matched_listing_id, review_status, review_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raw_id,
                source_id,
                run_id,
                source_url,
                raw_name,
                raw_address,
                raw_phone,
                raw_email,
                raw_website,
                raw_text,
                json.dumps(extracted_json or {}),
                content_hash,
                utcnow_iso(),
                matched_listing_id,
                review_status,
                review_notes,
            ),
        )
        conn.commit()
        return raw_id

    def get_or_create_source(
        self,
        *,
        source_name: str,
        source_type: str,
        base_url: Optional[str] = None,
        trust_level: str = "medium",
        supports_scraping: bool = False,
        supports_api: bool = False,
        requires_manual_review: bool = True,
    ) -> str:
        normalized_source_type = "spreadsheet_import" if source_type == "manual_import" else source_type
        if normalized_source_type not in ALLOWED_SOURCE_TYPES:
            raise ValueError("Invalid source type")
        conn = self.connect()
        row = conn.execute(
            """
            SELECT source_id
            FROM sober_living_directory_sources
            WHERE LOWER(source_name) = LOWER(?) AND LOWER(source_type) = LOWER(?)
            """,
            (source_name, normalized_source_type),
        ).fetchone()
        if row:
            return row["source_id"]

        source_id = f"src_{uuid.uuid4().hex[:12]}"
        timestamp = utcnow_iso()
        conn.execute(
            """
            INSERT INTO sober_living_directory_sources (
                source_id, source_name, source_type, base_url, trust_level, supports_scraping,
                supports_api, requires_manual_review, last_checked_at, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                source_name,
                normalized_source_type,
                base_url,
                trust_level,
                1 if supports_scraping else 0,
                1 if supports_api else 0,
                1 if requires_manual_review else 0,
                None,
                1,
                timestamp,
                timestamp,
            ),
        )
        conn.commit()
        return source_id

    def find_possible_duplicate(
        self,
        *,
        name: Optional[str],
        city: Optional[str],
        phone: Optional[str],
        website: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not name:
            return None

        normalized_name = self._normalize_lookup(name)
        normalized_city = self._normalize_lookup(city)
        normalized_phone = self._normalize_phone(phone)
        normalized_website = self._normalize_website(website)

        for candidate in self.list_listings():
            candidate_name = self._normalize_lookup(candidate.get("name"))
            candidate_city = self._normalize_lookup(candidate.get("city"))
            candidate_phone = self._normalize_phone(candidate.get("phone"))
            candidate_website = self._normalize_website(candidate.get("website"))

            if normalized_phone and candidate_phone and normalized_phone == candidate_phone:
                return candidate
            if normalized_website and candidate_website and normalized_website == candidate_website:
                return candidate
            if normalized_name == candidate_name and normalized_city and normalized_city == candidate_city:
                return candidate
        return None

    def score_duplicate_candidate(
        self,
        *,
        name: Optional[str],
        city: Optional[str],
        phone: Optional[str],
        website: Optional[str],
        existing_listing: Dict[str, Any],
    ) -> tuple[int, List[str]]:
        score = 0
        reasons: List[str] = []
        normalized_name = self._normalize_lookup(name)
        normalized_city = self._normalize_lookup(city)
        normalized_phone = self._normalize_phone(phone)
        normalized_website = self._normalize_website(website)

        existing_name = self._normalize_lookup(existing_listing.get("name"))
        existing_city = self._normalize_lookup(existing_listing.get("city"))
        existing_phone = self._normalize_phone(existing_listing.get("phone"))
        existing_website = self._normalize_website(existing_listing.get("website"))

        if normalized_phone and existing_phone and normalized_phone == existing_phone:
            score += 45
            reasons.append("phone_match")
        if normalized_website and existing_website and normalized_website == existing_website:
            score += 35
            reasons.append("website_match")
        if normalized_name and existing_name and normalized_name == existing_name:
            score += 30
            reasons.append("name_match")
        if normalized_city and existing_city and normalized_city == existing_city:
            score += 15
            reasons.append("city_match")

        return min(score, 100), reasons

    def _normalize_duplicate_import_fields(self, incoming: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        incoming = incoming or {}
        normalized: Dict[str, Any] = {}
        for field in DUPLICATE_DIFF_FIELDS:
            value = incoming.get(field)
            if field == "source_urls_json":
                value = [str(item).strip() for item in (value or []) if str(item).strip()]
            normalized[field] = value
        return normalized

    def _build_duplicate_field_diff(
        self,
        existing_listing: Dict[str, Any],
        normalized_imported_fields: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        diff: List[Dict[str, Any]] = []

        for field in DUPLICATE_DIFF_FIELDS:
            existing_value = existing_listing.get(field)
            imported_value = normalized_imported_fields.get(field)
            if self._values_equal(existing_value, imported_value):
                status = "same"
                recommended_action = "no_change"
            elif not self._has_value(existing_value) and self._has_value(imported_value):
                status = "existing_empty"
                recommended_action = "use_imported"
            elif self._has_value(existing_value) and not self._has_value(imported_value):
                status = "imported_empty"
                recommended_action = "keep_existing"
            else:
                status = "conflict"
                recommended_action = "manual_review"

            diff.append(
                {
                    "field": field,
                    "existing_value": existing_value,
                    "imported_value": imported_value,
                    "status": status,
                    "recommended_action": recommended_action,
                }
            )
        return diff

    def _build_duplicate_merge_updates(
        self,
        *,
        existing_listing: Dict[str, Any],
        incoming: Dict[str, Any],
        selected_imported_fields: List[str],
    ) -> Dict[str, Any]:
        if existing_listing.get("status") in PROTECTED_DUPLICATE_STATUSES and "status" in selected_imported_fields:
            raise ValueError("Protected listing status cannot be overwritten during duplicate merge")

        normalized_imported_fields = self._normalize_duplicate_import_fields(incoming)
        diff = self._build_duplicate_field_diff(existing_listing, normalized_imported_fields)
        selected_fields = {field for field in selected_imported_fields if field in DUPLICATE_DIFF_FIELDS}
        updates: Dict[str, Any] = {}

        for entry in diff:
            field = entry["field"]
            existing_value = existing_listing.get(field)
            imported_value = normalized_imported_fields.get(field)

            if field == "source_urls_json":
                if field in selected_fields and not self._values_equal(existing_value, imported_value):
                    updates[field] = imported_value
                else:
                    merged_sources = self._merge_string_lists(existing_value, imported_value)
                    if not self._values_equal(existing_value, merged_sources):
                        updates[field] = merged_sources
                continue

            if field == "notes" and field in selected_fields and self._has_value(imported_value):
                if imported_value != existing_value:
                    updates[field] = imported_value
                continue

            if field in selected_fields:
                if field == "status" and existing_listing.get("status") in PROTECTED_DUPLICATE_STATUSES:
                    raise ValueError("Protected listing status cannot be overwritten during duplicate merge")
                if not self._values_equal(existing_value, imported_value):
                    updates[field] = imported_value
                continue

            if entry["status"] == "existing_empty" and self._has_value(imported_value):
                updates[field] = imported_value

        updates.pop("internal_referral_notes", None)
        updates.pop("status", None)
        return updates

    def _build_fake_discovery_records(self, job: Dict[str, Any]) -> List[Dict[str, Any]]:
        city = job.get("target_city") or "Los Angeles"
        state = job.get("target_state") or "CA"
        query = (job.get("query") or "sober living").strip()
        base_slug = self._normalize_lookup(query).replace(" ", "-") or "sober-living"
        existing_match = self._find_listing_for_manual_test(city=city)
        records: List[Dict[str, Any]] = []

        if existing_match:
            records.append(
                {
                    "name": existing_match["name"],
                    "operator_name": existing_match.get("operator_name"),
                    "website": existing_match.get("website") or f"https://{base_slug}.example.com",
                    "phone": existing_match.get("phone") or "555-200-0000",
                    "email": existing_match.get("email"),
                    "address": existing_match.get("address"),
                    "city": existing_match.get("city") or city,
                    "state": existing_match.get("state") or state,
                    "zip_code": existing_match.get("zip_code"),
                    "population_served": existing_match.get("population_served"),
                    "house_type": existing_match.get("house_type") or "Sober Living",
                    "certification_status": existing_match.get("certification_status"),
                    "certification_body": existing_match.get("certification_body"),
                    "bed_availability_status": "unknown",
                    "notes": f"Manual discovery test match for {query}",
                    "source_urls_json": [existing_match.get("website") or f"https://{base_slug}.example.com"],
                }
            )

        for index in range(1, 3):
            records.append(
                {
                    "name": f"{city} {query.title()} Test Home {index}",
                    "operator_name": "Manual Test Connector",
                    "website": f"https://{base_slug}-{index}.example.com",
                    "phone": f"555-30{index}-00{index}",
                    "email": f"intake{index}@{base_slug}.example.com",
                    "address": f"{100 + index} Test Avenue",
                    "city": city,
                    "state": state,
                    "zip_code": None,
                    "population_served": "Men" if index == 1 else "Women",
                    "house_type": "Sober Living",
                    "certification_status": "Unverified",
                    "certification_body": None,
                    "bed_availability_status": "unknown",
                    "notes": f"Manual discovery test record for {query}",
                    "source_urls_json": [f"https://{base_slug}-{index}.example.com"],
                }
            )

        return records[:3]

    def _find_listing_for_manual_test(self, *, city: str) -> Optional[Dict[str, Any]]:
        listings = self.list_listings({"city": city}) or self.list_listings()
        return listings[0] if listings else None

    @staticmethod
    def _merge_string_lists(existing: Optional[List[str]], incoming: Optional[List[str]]) -> List[str]:
        values: List[str] = []
        for item in (existing or []) + (incoming or []):
            normalized = str(item or "").strip()
            if normalized and normalized not in values:
                values.append(normalized)
        return values

    @staticmethod
    def _normalize_lookup(value: Optional[str]) -> str:
        return "".join(ch.lower() for ch in str(value or "") if ch.isalnum() or ch.isspace()).strip()

    @staticmethod
    def _normalize_phone(value: Optional[str]) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    @staticmethod
    def _normalize_website(value: Optional[str]) -> str:
        website = str(value or "").strip().lower()
        for prefix in ("https://", "http://"):
            if website.startswith(prefix):
                website = website[len(prefix):]
        if website.startswith("www."):
            website = website[4:]
        return website.rstrip("/")

    def _insert_change_log(
        self,
        listing_id: Optional[str],
        change_type: str,
        old_value: Optional[str],
        new_value: Optional[str],
        raw_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ):
        conn = self.connect()
        conn.execute(
            """
            INSERT INTO sober_living_directory_change_log (
                change_id, listing_id, raw_id, change_type, old_value, new_value, source_id, detected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"chg_{uuid.uuid4().hex[:12]}",
                listing_id,
                raw_id,
                change_type,
                old_value,
                new_value,
                source_id,
                utcnow_iso(),
            ),
        )

    @staticmethod
    def _merge_notes(existing_notes: Optional[str], new_notes: Optional[str]) -> Optional[str]:
        if not new_notes:
            return existing_notes
        if not existing_notes:
            return new_notes
        return f"{existing_notes}\n\n{new_notes}"
