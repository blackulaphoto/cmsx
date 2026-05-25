# ================================================================
# @generated
# @preserve
# @readonly
# DO NOT MODIFY THIS FILE
# Purpose: Production-approved unified system
# Any changes must be approved by lead developer.
# WARNING: Modifying this file may break the application.
# ================================================================

"""
Unified AI Service
GPT-4o + SQLite conversation memory with direct function execution.
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from uuid import uuid4

import aiosqlite
from openai import AsyncOpenAI

from backend.modules.services.case_management_api import (
    get_dashboard_stats_from_db,
    get_clients_from_db,
)
from backend.modules.services.virgil_db_service import get_virgil_db
from backend.modules.reminders.engine import IntelligentReminderEngine
from backend.search.coordinator import get_coordinator
from backend.shared.database.workspace_store import workspace_store

logger = logging.getLogger(__name__)
CRISIS_TERMS = {
    "rehab", "treatment", "detox", "shelter", "housing", "homeless",
    "street", "streets", "kicked out", "insurance", "benefits", "drug",
    "drugs", "program", "sleeping on the street", "sleeping outside",
}
AGGREGATOR_DOMAINS = {
    "recovery.com",
    "rehabs.com",
    "addictions.com",
    "psychologytoday.com",
    "yelp.com",
    "findhelp.org",
    "roomies.com",
    "craigslist.org",
    "roomster.com",
    "rehabnet.com",
    "drugrehabus.org",
    "alcohol.org",
}
KNOWN_PROVIDER_BOOSTS = {
    "muse",
    "cri-help",
    "tarzana",
    "hope the mission",
    "hope of the valley",
    "la family housing",
    "211 la",
    "san fernando valley rescue mission",
    "van nuys alcohol and drug abuse treatment center",
}
RESOURCE_CATEGORY_CONFIG = {
    "housing": {
        "terms": ["housing", "shelter", "homeless", "rbh", "room and board", "transitional housing", "bridge housing", "street", "eviction"],
        "queries": ["housing assistance", "emergency shelter", "transitional housing", "rapid rehousing"],
        "verticals": ["services", "housing"],
        "preferred": {"housing", "shelter", "mission", "homeless", "rescue", "bridge"},
    },
    "substance_use": {
        "terms": ["detox", "rehab", "recovery", "substance", "addiction", "drug", "alcohol", "treatment", "sober"],
        "queries": ["detox program", "substance use treatment", "outpatient treatment", "rehab"],
        "verticals": ["services"],
        "preferred": {"detox", "rehab", "treatment", "recovery", "sobriety"},
    },
    "mental_health": {
        "terms": ["mental health", "therapy", "therapist", "psychiatry", "counseling", "counsellor", "behavioral health"],
        "queries": ["mental health counseling", "behavioral health clinic", "psychiatric services"],
        "verticals": ["services"],
        "preferred": {"mental health", "counseling", "therapy", "clinic", "behavioral"},
    },
    "medical": {
        "terms": ["medical", "primary care", "clinic", "doctor", "urgent care", "health center"],
        "queries": ["medical clinic", "primary care clinic", "community health center"],
        "verticals": ["services"],
        "preferred": {"medical", "clinic", "health", "care", "center"},
    },
    "dental": {
        "terms": ["dental", "dentist", "tooth", "teeth", "oral health"],
        "queries": ["low cost dental clinic", "community dental clinic", "dental services"],
        "verticals": ["services"],
        "preferred": {"dental", "dentist", "oral"},
    },
    "std_testing": {
        "terms": ["std", "sti", "hiv", "testing", "prep", "pep", "sexual health"],
        "queries": ["std testing clinic", "sti testing", "hiv testing", "sexual health clinic"],
        "verticals": ["services"],
        "preferred": {"std", "sti", "hiv", "testing", "sexual health", "prep"},
    },
    "food": {
        "terms": ["food", "pantry", "meals", "groceries", "hungry"],
        "queries": ["food pantry", "meal program", "food assistance"],
        "verticals": ["services"],
        "preferred": {"food", "pantry", "meal", "groceries"},
    },
    "benefits": {
        "terms": ["benefits", "calfresh", "medi-cal", "medicaid", "gr", "general relief", "ssi", "ssdi", "insurance"],
        "queries": ["benefits assistance", "medi-cal enrollment help", "calfresh help", "insurance enrollment assistance"],
        "verticals": ["services"],
        "preferred": {"benefits", "enrollment", "insurance", "medi-cal", "calfresh", "ssi"},
    },
    "legal": {
        "terms": ["legal", "expungement", "court", "citation", "record clearing", "probation", "lawyer"],
        "queries": ["legal aid", "expungement clinic", "court support", "record clearing assistance"],
        "verticals": ["services"],
        "preferred": {"legal", "aid", "expungement", "court", "record"},
    },
    "employment": {
        "terms": ["job", "employment", "work", "resume", "interview", "hiring"],
        "queries": ["employment assistance", "job center", "workforce development", "resume help"],
        "verticals": ["services", "jobs"],
        "preferred": {"employment", "job", "workforce", "resume", "career"},
    },
    "transportation": {
        "terms": ["transportation", "bus pass", "ride", "transit", "metro"],
        "queries": ["transportation assistance", "bus pass assistance", "transit help"],
        "verticals": ["services"],
        "preferred": {"transportation", "transit", "ride", "bus", "metro"},
    },
    "documents": {
        "terms": ["id", "identification", "birth certificate", "social security card", "documents", "dmv"],
        "queries": ["id assistance", "document replacement help", "birth certificate assistance"],
        "verticals": ["services"],
        "preferred": {"id", "identification", "document", "birth certificate", "social security"},
    },
}
ASSISTANT_SYSTEM_PROMPT = """Case Management Suite – AI Copilot (Popup Assistant)
ROLE & PURPOSE

You are a full-capability AI copilot embedded within the Case Management Suite, designed to support professional case managers in delivering effective, ethical, and compliant care coordination.

Your role is to augment human judgment, not replace it.

You assist with:

Research and explanation (benefits, insurance, housing, legal processes, healthcare systems)

Planning and prioritization (intake, transitions, discharge, aftercare)

Workflow guidance (what to do next, what’s due, what’s high-risk)

Documentation support (what belongs where, how to structure notes)

System navigation (understanding deadlines, dependencies, and case flow)

Strategic thinking (barriers, options, tradeoffs)

You have full access to your general domain knowledge (e.g., Medi-Cal, SSI, housing systems, employment pathways, legal and healthcare processes) and awareness of the Case Management Suite’s structure, workflows, and priorities.

You operate as a senior case management advisor, operations guide, and research assistant, always in service of the case manager using the system.

SCOPE OF AUTHORITY

You may assist with the following domains as they relate to case management work:

1. Case Management & Care Coordination

Intake and assessment support

Treatment transitions and continuity of care

Discharge and aftercare planning

Housing, employment, benefits, and social services navigation

Family coordination and reunification planning

Barrier identification and problem-solving

2. Research & Knowledge Support

Explaining public benefits (e.g., Medi-Cal, SSI/SSDI, CalFresh, General Relief)

Describing housing pathways (sober living, transitional housing, independent living)

Clarifying employment pathways and documentation needs

Explaining healthcare, insurance, and referral systems

Summarizing best practices in case management and recovery support

3. Workflow & Compliance Awareness

Highlighting documentation requirements and deadlines

Guiding where and how information should be recorded

Flagging potential compliance risks or missing elements

Supporting audit-safe, professional documentation practices

4. Planning & Decision Support

Helping case managers think through options and consequences

Identifying tradeoffs and risks

Suggesting next steps and timelines

Structuring action plans

You do not act independently, initiate actions, or make final determinations.

HARD BOUNDARIES (NON-NEGOTIABLE)

You must not:

Provide medical diagnoses or treatment decisions

Provide legal advice framed as authoritative or definitive

Replace licensed clinical judgment

Make decisions on behalf of staff or clients

Present yourself as a clinician, attorney, or authority figure

Instruct actions that bypass ethical, legal, or organizational safeguards

When a topic crosses into medical, legal, or clinical territory:

Provide high-level, educational information

Clearly recommend escalation to appropriate professionals

OPERATING PRINCIPLES
Case Manager–First Thinking

Always answer from the perspective of:

“What would help a competent case manager do their job better right now?”

Safety & Stability First

Prioritize:

Client safety and stability

Housing and medical continuity

Legal and compliance considerations

Long-term recovery and independence

Clarity Over Volume

Be structured

Be actionable

Avoid unnecessary jargon

Use step-by-step guidance when helpful

Transparency

Acknowledge uncertainty when information depends on jurisdiction, policy changes, or missing details

Ask clarifying questions when needed (county, age, income, insurance, legal status, etc.)

RESPONSE STRUCTURE (DEFAULT)

When appropriate, structure responses using:

Summary – Clear explanation of the issue or process

Key Steps – What typically needs to happen

Considerations – Common barriers, risks, or variations

Documentation Notes – What to capture in the case record

Next Actions – Practical, realistic next steps

Not every response needs all five, but this is your default reasoning frame.

TONE & STYLE

Professional, calm, and supportive

Practical rather than theoretical

Respectful of the complexity of human lives

Never condescending, alarmist, or dismissive

You are a trusted copilot, not a chatbot and not a compliance cop.

CONTEXT AWARENESS

You are always operating within the Case Management Suite environment.

Assume:

The user is a working professional

Time, workload, and liability matter

Documentation accuracy matters

Clients are complex and non-linear

Your job is to reduce friction, increase clarity, and help humans make better decisions.
"""


class UnifiedAIService:
    """Unified AI service with SQLite conversation memory."""

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        self.db_path = project_root / "databases" / "ai_assistant.db"
        self.model = "gpt-4o"
        self.api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self._initialized = False
        self._function_map = {
            "get_dashboard_stats": self.get_dashboard_stats,
            "create_reminder": self.create_reminder,
            "get_client_list": self.get_client_list,
            "search_jobs": self.search_jobs,
            "search_housing": self.search_housing,
            "search_services": self.search_services,
            "search_internal_resources": self.search_internal_resources,
        }
        if not self.client:
            logger.warning("OPENAI_API_KEY missing: Unified AI running in degraded mode.")

    async def initialize(self) -> None:
        """Initialize SQLite storage for conversation memory."""
        if self._initialized:
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_manager_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            await self._ensure_conversation_schema(db)
            await db.commit()

        self._initialized = True
        logger.info("Unified AI SQLite memory initialized")

    async def _ensure_conversation_schema(self, db: aiosqlite.Connection) -> None:
        """Migrate legacy conversation table variants to the canonical schema."""
        required_columns = {"id", "case_manager_id", "role", "content", "timestamp"}
        async with db.execute("PRAGMA table_info(conversations)") as cursor:
            rows = await cursor.fetchall()
        existing_columns = {row[1] for row in rows}

        if required_columns.issubset(existing_columns):
            return

        logger.warning(
            "Migrating legacy conversations schema. Existing columns: %s",
            sorted(existing_columns),
        )

        case_manager_expr = (
            "case_manager_id"
            if "case_manager_id" in existing_columns
            else ("user_id" if "user_id" in existing_columns else "'default_cm'")
        )
        role_expr = "role" if "role" in existing_columns else "'assistant'"
        content_expr = (
            "content"
            if "content" in existing_columns
            else ("message" if "message" in existing_columns else ("response" if "response" in existing_columns else "''"))
        )
        timestamp_expr = (
            "timestamp"
            if "timestamp" in existing_columns
            else ("created_at" if "created_at" in existing_columns else "CURRENT_TIMESTAMP")
        )

        await db.execute("DROP TABLE IF EXISTS conversations_v2")
        await db.execute(
            """
            CREATE TABLE conversations_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_manager_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        await db.execute(
            f"""
            INSERT INTO conversations_v2 (case_manager_id, role, content, timestamp)
            SELECT {case_manager_expr}, {role_expr}, {content_expr}, {timestamp_expr}
            FROM conversations
            """
        )
        await db.execute("DROP TABLE conversations")
        await db.execute("ALTER TABLE conversations_v2 RENAME TO conversations")

    async def _save_message(self, case_manager_id: str, role: str, content: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO conversations (case_manager_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (case_manager_id, role, content, timestamp),
            )
            await db.commit()

    async def _fetch_history(self, case_manager_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT role, content, timestamp
                FROM conversations
                WHERE case_manager_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (case_manager_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
        history = [dict(row) for row in reversed(rows)]
        return history

    async def execute_function(
        self,
        name: str,
        params: Dict[str, Any],
        allowed_functions: Optional[set] = None,
    ) -> Any:
        """Execute a registered function directly (no HTTP)."""
        if name not in self._function_map:
            raise ValueError(f"Function '{name}' not available")
        if allowed_functions is not None and name not in allowed_functions:
            raise ValueError(f"Function '{name}' not permitted in this mode")
        return await self._function_map[name](**params)

    async def get_dashboard_stats(self, case_manager_id: str) -> Dict[str, Any]:
        return await asyncio.to_thread(get_dashboard_stats_from_db, case_manager_id)

    async def get_client_list(self, case_manager_id: str) -> Dict[str, Any]:
        return await asyncio.to_thread(get_clients_from_db, case_manager_id)

    async def search_jobs(
        self,
        query: str,
        location: str = "Los Angeles, CA",
        page: int = 1,
        per_page: int = 10,
    ) -> Dict[str, Any]:
        coordinator = get_coordinator()
        return await coordinator.search_jobs(query, location, page, per_page)

    async def search_housing(
        self,
        query: str,
        location: str = "Los Angeles, CA",
        page: int = 1,
        per_page: int = 10,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        coordinator = get_coordinator()
        return await coordinator.search_housing(query, location, page, per_page, force_refresh=force_refresh)

    async def search_services(
        self,
        query: str,
        location: str = "Los Angeles, CA",
        page: int = 1,
        per_page: int = 10,
    ) -> Dict[str, Any]:
        coordinator = get_coordinator()
        return await coordinator.search_services(query, location, page, per_page)

    async def search_internal_resources(
        self,
        query: str,
        location: str = "Los Angeles, CA",
        limit: int = 8,
    ) -> Dict[str, Any]:
        """Search internal service and resource data before using the web."""
        try:
            location_city = (location or "").split(",")[0].strip()
            queries = self._derive_resource_queries(query)
            seen = set()
            results: List[Dict[str, Any]] = []
            project_root = Path(__file__).resolve().parents[3]
            try:
                virgil_result = get_virgil_db().search_services(query, location, 1, limit)
                for item in virgil_result.get("results", [])[:limit]:
                    dedupe_key = ("virgil_st_db", item.get("title", ""), item.get("address", ""))
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    results.append({
                        "title": item.get("title", ""),
                        "provider_name": item.get("title", ""),
                        "service_category": item.get("service_type", ""),
                        "service_type": item.get("service_type", ""),
                        "description": item.get("description", ""),
                        "location": item.get("location") or item.get("address", ""),
                        "phone": item.get("phone", ""),
                        "email": "",
                        "website": item.get("url") or item.get("link", ""),
                        "current_availability": "",
                        "waitlist_status": "",
                        "background_policy": "",
                        "accepts_medicaid": "medi-cal" in f"{item.get('description', '')} {item.get('relevance_reason', '')}".lower(),
                        "sliding_scale_available": "sliding" in item.get("description", "").lower(),
                        "eligibility_criteria": "",
                        "cost": "",
                        "source": item.get("source", "virgil_st_db"),
                    })
                    if len(results) >= limit:
                        break
            except Exception as virgil_error:
                logger.warning("Virgil internal resource search failed: %s", virgil_error)

            results.extend(
                self._search_services_directory_db(
                    project_root / "databases" / "services.db",
                    queries,
                    location_city,
                    max(limit - len(results), 0),
                    seen,
                )
            )
            if len(results) < limit:
                results.extend(
                    self._search_social_services_db(
                        project_root / "databases" / "social_services.db",
                        queries,
                        location_city,
                        limit - len(results),
                        seen,
                    )
                )

            dashboard_resources = workspace_store.list_dashboard_items("dashboard_resources", "cm_001")
            query_tokens = {token for token in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(token) > 2}
            matched_resources = []
            for resource in dashboard_resources:
                haystack = f"{resource.get('name', '')} {resource.get('type', '')}".lower()
                if not query_tokens or any(token in haystack for token in query_tokens):
                    matched_resources.append({
                        "title": resource.get("name", ""),
                        "type": resource.get("type", ""),
                        "download_path": f"/api/dashboard/resources/{resource.get('id')}/download",
                        "uploaded_at": resource.get("uploaded_at", ""),
                        "source": "dashboard_resources",
                    })

            return {
                "success": True,
                "query": query,
                "location": location,
                "services": results[:limit],
                "resource_files": matched_resources[:5],
                "source": "internal_resource_library",
                "total_count": len(results),
            }
        except Exception as exc:
            logger.error("Internal resource search failed: %s", exc)
            return {
                "success": False,
                "query": query,
                "location": location,
                "services": [],
                "resource_files": [],
                "source": "internal_resource_library",
                "error": str(exc),
                "total_count": 0,
            }

    def _search_services_directory_db(
        self,
        db_path: Path,
        queries: List[str],
        location_city: str,
        limit: int,
        seen: set,
    ) -> List[Dict[str, Any]]:
        if limit <= 0 or not db_path.exists():
            return []

        results: List[Dict[str, Any]] = []
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            for search_term in queries:
                keyword_param = f"%{search_term.lower()}%"
                params: List[Any] = [keyword_param, keyword_param, keyword_param, keyword_param]
                query_sql = """
                    SELECT
                        service_id,
                        service_name,
                        service_type,
                        provider_name,
                        provider_address,
                        provider_phone,
                        provider_email,
                        provider_website,
                        description,
                        eligibility_criteria,
                        cost,
                        availability
                    FROM service_directory
                    WHERE
                        LOWER(COALESCE(service_name, '')) LIKE ?
                        OR LOWER(COALESCE(service_type, '')) LIKE ?
                        OR LOWER(COALESCE(provider_name, '')) LIKE ?
                        OR LOWER(COALESCE(description, '')) LIKE ?
                """
                query_sql += " ORDER BY service_type, provider_name LIMIT ?"
                params.append(limit)

                rows = conn.execute(query_sql, params).fetchall()
                for row in rows:
                    dedupe_key = ("service_directory", row["service_id"])
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    results.append({
                        "title": f"{row['provider_name'] or 'Provider'} - {row['service_name'] or row['service_type'] or 'Service'}",
                        "provider_name": row["provider_name"] or "",
                        "service_category": row["service_type"] or "",
                        "service_type": row["service_name"] or "",
                        "description": row["description"] or "",
                        "location": row["provider_address"] or "",
                        "phone": row["provider_phone"] or "",
                        "email": row["provider_email"] or "",
                        "website": row["provider_website"] or "",
                        "current_availability": row["availability"] or "",
                        "waitlist_status": "",
                        "background_policy": "",
                        "accepts_medicaid": "insurance" in (row["cost"] or "").lower() or "insurance" in (row["description"] or "").lower(),
                        "sliding_scale_available": "sliding" in (row["cost"] or "").lower(),
                        "eligibility_criteria": row["eligibility_criteria"] or "",
                        "cost": row["cost"] or "",
                        "source": "services_directory_db",
                    })
                    if len(results) >= limit:
                        return results
        return results

    def _search_social_services_db(
        self,
        db_path: Path,
        queries: List[str],
        location_city: str,
        limit: int,
        seen: set,
    ) -> List[Dict[str, Any]]:
        if limit <= 0 or not db_path.exists():
            return []

        results: List[Dict[str, Any]] = []
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            provider_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(service_providers)").fetchall()
            }
            service_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(social_services)").fetchall()
            }

            provider_name_col = "name" if "name" in provider_columns else "provider_name"
            phone_col = "phone_main" if "phone_main" in provider_columns else "phone_number"
            service_type_col = "service_type" if "service_type" in service_columns else "service_name"
            waitlist_col = "waitlist_status" if "waitlist_status" in service_columns else None
            accepts_medicaid_col = "accepts_medicaid" if "accepts_medicaid" in provider_columns else None
            sliding_scale_col = "sliding_scale_available" if "sliding_scale_available" in provider_columns else None
            is_active_provider_filter = "p.is_active = 1 AND " if "is_active" in provider_columns else ""
            is_active_service_filter = "(s.is_active = 1 OR s.is_active IS NULL) AND " if "is_active" in service_columns else ""

            for search_term in queries:
                params: List[Any] = []
                query_sql = f"""
                    SELECT
                        p.provider_id,
                        p.{provider_name_col} AS provider_name,
                        p.city,
                        p.county,
                        p.email,
                        p.website,
                        p.background_check_policy,
                        p.{phone_col} AS phone_value,
                        s.service_category,
                        s.{service_type_col} AS service_type,
                        s.description,
                        s.current_availability
                        {', p.' + accepts_medicaid_col + ' AS accepts_medicaid' if accepts_medicaid_col else ''}
                        {', p.' + sliding_scale_col + ' AS sliding_scale_available' if sliding_scale_col else ''}
                        {', s.' + waitlist_col + ' AS waitlist_status' if waitlist_col else ''}
                    FROM service_providers p
                    LEFT JOIN social_services s ON p.provider_id = s.provider_id
                    WHERE {is_active_provider_filter}{is_active_service_filter}(
                        LOWER(COALESCE(p.{provider_name_col}, '')) LIKE ?
                        OR LOWER(COALESCE(s.service_category, '')) LIKE ?
                        OR LOWER(COALESCE(s.{service_type_col}, '')) LIKE ?
                        OR LOWER(COALESCE(s.description, '')) LIKE ?
                    )
                """
                keyword_param = f"%{search_term.lower()}%"
                params.extend([keyword_param, keyword_param, keyword_param, keyword_param])
                if location_city and "city" in provider_columns:
                    query_sql += " AND LOWER(COALESCE(p.city, '')) LIKE ?"
                    params.append(f"%{location_city.lower()}%")
                query_sql += f" ORDER BY p.{provider_name_col}, s.service_category LIMIT ?"
                params.append(limit)

                rows = conn.execute(query_sql, params).fetchall()
                for row in rows:
                    provider_id = row["provider_id"]
                    service_type = row["service_type"]
                    dedupe_key = ("social_services", provider_id, service_type)
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    results.append({
                        "title": f"{row['provider_name']} - {service_type or row['service_category'] or 'Service'}",
                        "provider_name": row["provider_name"],
                        "service_category": row["service_category"] or "",
                        "service_type": service_type or "",
                        "description": row["description"] or "",
                        "location": ", ".join(part for part in [row["city"] or "", row["county"] or ""] if part),
                        "phone": row["phone_value"] or "",
                        "email": row["email"] or "",
                        "website": row["website"] or "",
                        "current_availability": row["current_availability"] or "",
                        "waitlist_status": row["waitlist_status"] if "waitlist_status" in row.keys() else "",
                        "background_policy": row["background_check_policy"] or "",
                        "accepts_medicaid": bool(row["accepts_medicaid"]) if "accepts_medicaid" in row.keys() else False,
                        "sliding_scale_available": bool(row["sliding_scale_available"]) if "sliding_scale_available" in row.keys() else False,
                        "source": "social_services_db",
                    })
                    if len(results) >= limit:
                        return results
        return results

    async def create_reminder(
        self,
        case_manager_id: str,
        client_id: str,
        message: str,
        due_date: Optional[str] = None,
        priority: str = "Medium",
        reminder_type: str = "custom",
    ) -> Dict[str, Any]:
        engine = IntelligentReminderEngine()
        reminder_db = engine.reminder_db

        if not reminder_db.connection:
            reminder_db.connect()

        reminder_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        cursor = reminder_db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO active_reminders (
                reminder_id,
                client_id,
                case_manager_id,
                reminder_type,
                message,
                priority,
                due_date,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reminder_id,
                client_id,
                case_manager_id,
                reminder_type,
                message,
                priority,
                due_date,
                "Active",
                created_at,
            ),
        )
        reminder_db.connection.commit()

        return {
            "success": True,
            "reminder_id": reminder_id,
            "client_id": client_id,
            "case_manager_id": case_manager_id,
            "message": message,
            "priority": priority,
            "due_date": due_date,
            "status": "Active",
            "created_at": created_at,
        }

    async def process_message(
        self,
        message: str,
        case_manager_id: str,
        mode: str = "central",
        injected_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a chat message and persist conversation history."""
        await self.initialize()
        if not self.client:
            fallback = (
                "AI responses are unavailable because OPENAI_API_KEY is not configured. "
                "Core app features remain available."
            )
            await self._save_message(case_manager_id, "user", message)
            await self._save_message(case_manager_id, "assistant", fallback)
            return {
                "success": False,
                "response": fallback,
                "function_called": "",
                "error": "missing_openai_api_key",
            }

        history = await self._fetch_history(case_manager_id, limit=20)
        system_prompt = self._build_system_prompt(mode)
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]
        messages.extend({"role": h["role"], "content": h["content"]} for h in history)
        if injected_context:
            messages.append({"role": "system", "content": injected_context})
        resource_context = await self._maybe_build_case_manager_resource_context(message, history)
        if resource_context:
            messages.append({"role": "system", "content": resource_context})
        else:
            internal_context = await self._maybe_build_internal_resource_context(message)
            if internal_context:
                messages.append({"role": "system", "content": internal_context})
        messages.append({"role": "user", "content": message})

        central_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_dashboard_stats",
                    "description": "Get dashboard statistics for a case manager",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_manager_id": {"type": "string"}
                        },
                        "required": ["case_manager_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_reminder",
                    "description": "Create a reminder for a client",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_manager_id": {"type": "string"},
                            "client_id": {"type": "string"},
                            "message": {"type": "string"},
                            "due_date": {"type": "string"},
                            "priority": {"type": "string"},
                            "reminder_type": {"type": "string"},
                        },
                        "required": ["case_manager_id", "client_id", "message"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_client_list",
                    "description": "Get client list for a case manager",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_manager_id": {"type": "string"}
                        },
                        "required": ["case_manager_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_jobs",
                    "description": "Search jobs using the unified search coordinator",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "location": {"type": "string"},
                            "page": {"type": "integer"},
                            "per_page": {"type": "integer"}
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_housing",
                    "description": "Search housing using the unified search coordinator",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "location": {"type": "string"},
                            "page": {"type": "integer"},
                            "per_page": {"type": "integer"},
                            "force_refresh": {"type": "boolean"}
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_services",
                    "description": "Search services using the unified search coordinator",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "location": {"type": "string"},
                            "page": {"type": "integer"},
                            "per_page": {"type": "integer"}
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_internal_resources",
                    "description": "Search the internal services database and dashboard resource library for local programs before using web search",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "location": {"type": "string"},
                            "limit": {"type": "integer"}
                        },
                        "required": ["query"],
                    },
                },
            },
        ]
        assistant_tools = [
            tool
            for tool in central_tools
            if tool["function"]["name"] != "create_reminder"
        ]
        tools = assistant_tools if mode == "assistant" else central_tools
        allowed_functions = {tool["function"]["name"] for tool in tools}

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=800,
            )

            function_called = ""
            assistant_message = response.choices[0].message

            if assistant_message.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_message.content or "",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments,
                                },
                            }
                            for tool_call in assistant_message.tool_calls
                        ],
                    }
                )
                for tool_call in assistant_message.tool_calls:
                    function_called = tool_call.function.name
                    params = json.loads(tool_call.function.arguments or "{}")
                    result = await self.execute_function(
                        function_called,
                        params,
                        allowed_functions=allowed_functions,
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result),
                        }
                    )

                follow_up = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=800,
                )
                assistant_text = follow_up.choices[0].message.content or ""
            else:
                assistant_text = assistant_message.content or ""

            assistant_text = self._polish_response_text(assistant_text)
        except Exception as exc:
            logger.warning("Unified AI provider failure in %s mode: %s", mode, exc)
            degraded = await self._handle_provider_failure(
                message=message,
                case_manager_id=case_manager_id,
                mode=mode,
                error=str(exc),
            )
            await self._save_message(case_manager_id, "user", message)
            await self._save_message(case_manager_id, "assistant", degraded["response"])
            return degraded

        await self._save_message(case_manager_id, "user", message)
        await self._save_message(case_manager_id, "assistant", assistant_text)

        return {
            "success": True,
            "response": assistant_text,
            "function_called": function_called,
        }

    def _build_system_prompt(self, mode: str) -> str:
        role_line = (
            "You can also create reminders directly when the user asks."
            if mode == "central"
            else "You are in assistant mode. Do not imply you changed records unless a tool confirms it."
        )
        return (
            "You are the Case Management Suite AI copilot for working case managers.\n\n"
            "Your job is to help staff move faster, think clearly, document accurately, and keep client transitions from falling apart.\n"
            "Act like an experienced case manager and operations partner, not a generic help bot.\n"
            "Default to concrete action planning, documentation awareness, and follow-through.\n\n"
            f"{role_line}\n\n"
            "Priorities:\n"
            "- Lead with the answer.\n"
            "- Give concrete next steps with dates, deadlines, or sequence when possible.\n"
            "- Prefer short checklists and decision points over essays.\n"
            "- When discussing a client situation, focus on what the case manager should do next today, this week, and before discharge or transition if relevant.\n"
            "- Treat documentation as operational work: tell the user what should be documented, what follow-up should be tracked, and what deadlines matter.\n"
            "- For housing, treatment, benefits, or urgent support requests, use internal resources first when available.\n"
            "- When provider names, phone numbers, addresses, or websites are available, include them directly.\n"
            "- Do not send users to generic directory pages when provider-level options are available.\n"
            "- For resource lookups, respond like a case-manager research tool: give 3 to 5 specific provider options, then who to call first.\n"
            "- For documentation questions, use the internal templates and provide structure the case manager can actually paste into notes, treatment plans, discharge planning, FMLA, or referrals.\n"
            "- For LOC changes, discharge planning, housing, employment, benefits, legal, and aftercare issues, think in terms of continuity and risk reduction.\n"
            "- If something depends on jurisdiction, policy, or a licensed professional, say that plainly.\n\n"
            "Boundaries:\n"
            "- No medical diagnosis or treatment advice.\n"
            "- No definitive legal advice.\n"
            "- Do not replace licensed clinical judgment.\n"
            "- Do not invent actions, outcomes, or integrations.\n\n"
            "When helpful, structure the response in this order:\n"
            "1. Immediate action items\n"
            "2. Timeline or deadlines\n"
            "3. Resources or contacts\n"
            "4. Documentation note\n"
            "5. Follow-up or watchouts\n\n"
            "If the user asks for templates, documentation help, treatment plans, group notes, discharge summaries, referrals, or FMLA workflow, never say you lack access to templates if internal template guidance is available.\n\n"
            "Tone:\n"
            "- Calm\n"
            "- Direct\n"
            "- Competent\n"
            "- Human\n"
            "- Never preachy, robotic, overly formal, or vague\n\n"
            "Preferred structure when helpful:\n"
            "- Immediate action items\n"
            "- Timeline\n"
            "- Resources or contacts\n"
            "- Documentation note\n"
            "- Follow-up or watchouts\n"
        )

    def _polish_response_text(self, text: str) -> str:
        if not text:
            return text

        cleaned = text.strip()
        replacements = {
            "Summary –": "Bottom line:",
            "Summary -": "Bottom line:",
            "Key Steps –": "Next steps:",
            "Key Steps -": "Next steps:",
            "Considerations –": "Watchouts:",
            "Considerations -": "Watchouts:",
            "Documentation Notes –": "Documentation note:",
            "Documentation Notes -": "Documentation note:",
            "Next Actions –": "Next steps:",
            "Next Actions -": "Next steps:",
            "Immediate Steps –": "Immediate action items:",
            "Immediate Steps -": "Immediate action items:",
            "Immediate Action Items –": "Immediate action items:",
            "Immediate Action Items -": "Immediate action items:",
            "Timeline –": "Timeline:",
            "Timeline -": "Timeline:",
            "Resources –": "Resources:",
            "Resources -": "Resources:",
            "Follow-Up –": "Follow-up:",
            "Follow-Up -": "Follow-up:",
            "Follow Up –": "Follow-up:",
            "Follow Up -": "Follow-up:",
        }
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)

        cleaned = re.sub(r"\bAs an AI\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bI don't have access to external templates or documents\.?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bI do not have access to external templates or documents\.?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\btrusted copilot\b", "copilot", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bWould you like me to help you search\b", "If you want, I can search", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _derive_resource_queries(self, message: str) -> List[str]:
        text = (message or "").lower()
        queries = [message]
        if any(term in text for term in ["rehab", "treatment", "detox", "sobriety", "sober", "addiction", "substance"]):
            queries.extend([
                "substance abuse",
                "outpatient treatment",
                "medication-assisted treatment",
                "mental health",
                "counseling",
                "treatment",
                "rehab",
            ])
        if any(term in text for term in ["street", "homeless", "shelter", "kicked out", "housing", "on the streets"]):
            queries.extend([
                "housing services",
                "emergency shelter",
                "transitional housing",
                "housing",
                "shelter",
            ])
        if any(term in text for term in ["insurance", "bcbs", "medical", "health"]):
            queries.extend([
                "medical services",
                "benefits coordination",
                "insurance",
                "medical",
                "health",
            ])
        seen = set()
        ordered = []
        for query in queries:
            normalized = query.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                ordered.append(query)
        return ordered

    async def _maybe_build_internal_resource_context(self, message: str) -> Optional[str]:
        text = (message or "").lower()
        urgent_terms = list(CRISIS_TERMS) + ["legal aid"]
        if not any(term in text for term in urgent_terms):
            return None

        resource_results = await self.search_internal_resources(message, "Los Angeles, CA", limit=6)
        services = resource_results.get("services", [])
        resource_files = resource_results.get("resource_files", [])
        if not services and not resource_files:
            return None

        lines = [
            "Internal resource context is available. Use it before giving generic advice.",
            "If a local option appears relevant, mention the provider name and contact details directly.",
        ]
        if services:
            lines.append("Internal service matches:")
            for service in services[:6]:
                lines.append(
                    f"- {service.get('title')}; availability: {service.get('current_availability') or 'unknown'}; "
                    f"phone: {service.get('phone') or 'not listed'}; website: {service.get('website') or 'not listed'}; "
                    f"background policy: {service.get('background_policy') or 'not listed'}"
                )
        if resource_files:
            lines.append("Matching uploaded resource files:")
            for resource in resource_files[:5]:
                lines.append(f"- {resource.get('title')} ({resource.get('type')})")
        return "\n".join(lines)

    async def _maybe_build_case_manager_resource_context(
        self,
        message: str,
        history: List[Dict[str, Any]],
    ) -> Optional[str]:
        categories = self._classify_resource_categories(message, history)
        if not categories:
            return None

        location = self._extract_location_from_conversation(message, history) or "Los Angeles, CA"
        combined_text = " ".join([h.get("content", "") for h in history[-6:]] + [message]).lower()
        internal_results = await self.search_internal_resources(combined_text, location, limit=8)
        lines = [
            "This is a case-manager resource lookup.",
            f"Return specific provider options for {location}.",
            "Use provider names, phone numbers, websites, addresses, eligibility notes, and hours when available.",
            "Avoid generic directories when direct providers are available.",
        ]

        internal_services = internal_results.get("services", [])
        if internal_services:
            lines.append("Internal directory matches:")
            for service in internal_services[:5]:
                lines.append(
                    f"- {service.get('title')}; phone: {service.get('phone') or 'not listed'}; "
                    f"website: {service.get('website') or 'not listed'}; "
                    f"eligibility: {service.get('eligibility_criteria') or 'not listed'}; "
                    f"availability: {service.get('current_availability') or 'unknown'}"
                )

        for category in categories[:3]:
            provider_cards = await self._collect_category_resource_cards(category, message, combined_text, location)
            if not provider_cards:
                continue
            lines.append(f"{category.replace('_', ' ').title()} provider matches:")
            for item in provider_cards[:4]:
                lines.append(
                    f"- {item.get('title')}; phone: {item.get('phone') or 'not listed'}; "
                    f"website: {item.get('link') or item.get('url') or item.get('website') or 'not listed'}; "
                    f"address: {item.get('address') or item.get('location') or location}; "
                    f"notes: {item.get('insurance_notes') or item.get('hours') or item.get('description') or ''}"
                )

        if len(lines) <= 4:
            return None
        return "\n".join(lines)

    def _classify_resource_categories(
        self,
        message: str,
        history: List[Dict[str, Any]],
    ) -> List[str]:
        text = " ".join([h.get("content", "") for h in history[-6:]] + [message]).lower()
        categories: List[str] = []
        for category, config in RESOURCE_CATEGORY_CONFIG.items():
            if any(term in text for term in config["terms"]):
                categories.append(category)
        return categories

    async def _collect_category_resource_cards(
        self,
        category: str,
        message: str,
        combined_text: str,
        location: str,
    ) -> List[Dict[str, Any]]:
        config = RESOURCE_CATEGORY_CONFIG.get(category)
        if not config:
            return []

        queries = self._build_category_queries(category, message, combined_text)
        results: List[Dict[str, Any]] = []
        preferred_terms = set(config["preferred"])
        for query in queries[:3]:
            search_tasks = []
            if "services" in config["verticals"]:
                search_tasks.append(self.search_services(query, location, 1, 6))
            if "housing" in config["verticals"]:
                search_tasks.append(self.search_housing(query, location, 1, 6))
            if "jobs" in config["verticals"]:
                search_tasks.append(self.search_jobs(query, location, 1, 6))
            raw_sets = await asyncio.gather(*search_tasks) if search_tasks else []
            merged_items: List[Dict[str, Any]] = []
            for payload in raw_sets:
                merged_items.extend(payload.get("results", []))
                merged_items.extend(payload.get("housing_listings", []))
            ranked = self._rank_crisis_results(merged_items, location, preferred_terms)
            enriched = await self._enrich_ranked_results(ranked, location, category, 4)
            results.extend(enriched)
            if results:
                break

        deduped: List[Dict[str, Any]] = []
        seen = set()
        for item in results:
            key = (item.get("title"), item.get("link") or item.get("url"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[:4]

    def _build_category_queries(self, category: str, message: str, combined_text: str) -> List[str]:
        config = RESOURCE_CATEGORY_CONFIG.get(category, {})
        queries = [message]
        queries.extend(config.get("queries", []))
        if category == "benefits" and "bcbs" in combined_text:
            queries.insert(1, "bcbs insurance assistance")
        if category == "housing" and "rbh" in combined_text:
            queries.insert(1, "rbh housing")
        if category == "employment":
            queries.append("second chance employment")
        seen = set()
        ordered: List[str] = []
        for query in queries:
            normalized = query.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                ordered.append(query)
        return ordered

    async def _maybe_build_crisis_support_context(
        self,
        message: str,
        history: List[Dict[str, Any]],
    ) -> Optional[str]:
        if not self._is_crisis_support_request(message, history):
            return None

        location = self._extract_location_from_conversation(message, history) or "Los Angeles, CA"
        combined_text = " ".join([h.get("content", "") for h in history[-6:]] + [message]).lower()
        detox_query = "detox rehab program"
        if "bcbs" in combined_text or "blue cross" in combined_text or "insurance" in combined_text:
            detox_query += " bcbs insurance"

        internal_results, detox_results, shelter_service_results, shelter_housing_results = await asyncio.gather(
            self.search_internal_resources(combined_text, location, limit=6),
            self.search_services(detox_query, location, 1, 8),
            self.search_services("emergency shelter homeless", location, 1, 8),
            self.search_housing("emergency shelter homeless", location, 1, 8),
        )

        detox_candidates = self._rank_crisis_results(
            detox_results.get("results", []),
            location,
            {"detox", "rehab", "treatment", "recovery"},
        )
        shelter_candidates = self._rank_crisis_results(
            shelter_service_results.get("results", []) + shelter_housing_results.get("housing_listings", []),
            location,
            {"shelter", "housing", "mission", "homeless", "rescue"},
        )
        detox_candidates, shelter_candidates = await asyncio.gather(
            self._enrich_ranked_results(detox_candidates, location, "detox", 4),
            self._enrich_ranked_results(shelter_candidates, location, "shelter", 4),
        )

        internal_services = internal_results.get("services", [])
        lines = [
            "This is a crisis housing or detox request.",
            f"Use the following local options for {location} before giving generic guidance.",
            "Give specific provider names, direct links, and contact numbers when available.",
            "Keep the response short, practical, and action-oriented.",
        ]
        if internal_services:
            lines.append("Internal directory matches:")
            for service in internal_services[:4]:
                lines.append(
                    f"- {service.get('title')}; phone: {service.get('phone') or 'not listed'}; "
                    f"website: {service.get('website') or 'not listed'}; "
                    f"availability: {service.get('current_availability') or 'unknown'}"
                )
        if detox_candidates:
            lines.append("Detox or treatment web matches:")
            for item in detox_candidates[:4]:
                lines.append(
                    f"- {item.get('title')}; phone: {item.get('phone') or 'not listed'}; "
                    f"website: {item.get('link') or item.get('url') or item.get('website') or 'not listed'}; "
                    f"address: {item.get('address') or item.get('location') or location}; "
                    f"notes: {item.get('insurance_notes') or item.get('hours') or item.get('description') or ''}"
                )
        if shelter_candidates:
            lines.append("Emergency housing or shelter web matches:")
            for item in shelter_candidates[:4]:
                lines.append(
                    f"- {item.get('title')}; phone: {item.get('phone') or 'not listed'}; "
                    f"website: {item.get('link') or item.get('url') or item.get('website') or 'not listed'}; "
                    f"address: {item.get('address') or item.get('location') or location}; "
                    f"notes: {item.get('insurance_notes') or item.get('hours') or item.get('description') or ''}"
                )

        if len(lines) <= 4:
            return None
        return "\n".join(lines)

    def _is_crisis_support_request(self, message: str, history: List[Dict[str, Any]]) -> bool:
        text = " ".join([h.get("content", "") for h in history[-6:]] + [message]).lower()
        return any(term in text for term in CRISIS_TERMS)

    def _extract_location_from_conversation(
        self,
        message: str,
        history: List[Dict[str, Any]],
    ) -> Optional[str]:
        texts = [message] + [h.get("content", "") for h in reversed(history[-6:])]
        patterns = [
            r"\b(?:i am in|i'm in|im in|in|near)\s+([a-z][a-z\s]+?)\s*(?:,\s*| )ca\b",
            r"\b([a-z][a-z\s]+),\s*ca\b",
        ]
        for text in texts:
            lowered = text.lower()
            for pattern in patterns:
                match = re.search(pattern, lowered)
                if match:
                    location = match.group(1).strip()
                    location = re.sub(r"\b(client|needs|need|cheap|testing|help|with|for)\b", "", location).strip()
                    location = re.sub(r"\s{2,}", " ", location)
                    return self._title_case_location(location)
        return None

    def _title_case_location(self, location: str) -> str:
        parts = [part.strip() for part in location.split(",") if part.strip()]
        if not parts:
            return location
        city = parts[0].title()
        state = parts[1].upper() if len(parts) > 1 else "CA"
        return f"{city}, {state}"

    def _rank_crisis_results(
        self,
        items: List[Dict[str, Any]],
        location: str,
        preferred_terms: set,
    ) -> List[Dict[str, Any]]:
        scored: List[tuple] = []
        location_l = (location or "").lower()
        for item in items:
            title = (item.get("title") or "").lower()
            description = (item.get("description") or "").lower()
            url = item.get("link") or item.get("url") or ""
            hostname = (urlparse(url).hostname or "").lower().replace("www.", "")
            score = 0
            if hostname and hostname not in AGGREGATOR_DOMAINS:
                score += 4
            else:
                score -= 3
            if any(boost in title for boost in KNOWN_PROVIDER_BOOSTS):
                score += 5
            if any(term in title for term in preferred_terms):
                score += 3
            if any(term in description for term in preferred_terms):
                score += 2
            if location_l and location_l.split(",")[0] in f"{title} {description}":
                score += 2
            if any(bad in title for bad in ["directory", "centers near", "best", "find rehabs", "rooms for rent"]):
                score -= 3
            if hostname and hostname in AGGREGATOR_DOMAINS:
                score -= 2
            scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)

        deduped: List[Dict[str, Any]] = []
        seen_titles = set()
        for _, item in scored:
            title = item.get("title") or ""
            if title in seen_titles:
                continue
            seen_titles.add(title)
            deduped.append(item)
        return deduped

    async def _enrich_ranked_results(
        self,
        items: List[Dict[str, Any]],
        location: str,
        category: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        enriched: List[Dict[str, Any]] = []
        for item in items[:limit]:
            merged = dict(item)
            merged.update(self._extract_contact_fields(item))
            if not merged.get("phone") or not merged.get("address"):
                follow_up_query = self._provider_follow_up_query(merged, category, location)
                try:
                    follow_up = await self.search_services(follow_up_query, location, 1, 3)
                    follow_up_items = self._rank_crisis_results(
                        follow_up.get("results", []),
                        location,
                        {"detox", "rehab", "treatment", "recovery"} if category == "detox" else {"shelter", "housing", "mission", "homeless", "rescue"},
                    )
                    if follow_up_items:
                        merged.update({k: v for k, v in self._extract_contact_fields(follow_up_items[0]).items() if v})
                        if follow_up_items[0].get("link") and not merged.get("link"):
                            merged["link"] = follow_up_items[0]["link"]
                            merged["url"] = follow_up_items[0]["link"]
                except Exception as exc:
                    logger.warning("Follow-up enrichment failed for %s: %s", follow_up_query, exc)
            enriched.append(merged)
        return enriched

    def _provider_follow_up_query(self, item: Dict[str, Any], category: str, location: str) -> str:
        title = item.get("title") or ""
        if category == "detox":
            return f"{title} phone official {location}"
        return f"{title} phone address official {location}"

    def _extract_contact_fields(self, item: Dict[str, Any]) -> Dict[str, str]:
        description = item.get("description") or ""
        title = item.get("title") or ""
        text = f"{title} {description}"

        phone_match = re.search(r"(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\d{3}-\d{2}-[A-Z]+)", text, re.IGNORECASE)
        address_match = re.search(
            r"(\d{2,6}\s+[A-Za-z0-9.\-#'\s]+,\s*[A-Za-z\s]+,\s*CA\s*\d{5})",
            text,
        )
        hours_match = re.search(
            r"(Hours:\s*[^.]+(?:\.)?|Mon(?:day)?[^.]+|Tue(?:sday)?[^.]+|Open\s*24/7[^.]*)",
            text,
            re.IGNORECASE,
        )

        return {
            "phone": phone_match.group(1).strip() if phone_match else item.get("phone", ""),
            "address": address_match.group(1).strip() if address_match else item.get("address", ""),
            "hours": hours_match.group(1).strip() if hours_match else item.get("hours", ""),
        }

    async def get_conversation_history(self, case_manager_id: str) -> List[Dict[str, Any]]:
        await self.initialize()
        return await self._fetch_history(case_manager_id, limit=100)

    async def _handle_provider_failure(
        self,
        message: str,
        case_manager_id: str,
        mode: str,
        error: str,
    ) -> Dict[str, Any]:
        """Gracefully degrade when OpenAI is unavailable."""
        direct_action = (
            await self._try_direct_reminder_fallback(message, case_manager_id)
            if mode == "central"
            else None
        )
        if direct_action:
            reminder = direct_action["result"]
            response = (
                "AI provider unavailable. The requested reminder was still created directly. "
                f"Reminder ID: {reminder.get('reminder_id', 'unknown')}."
            )
            return {
                "success": True,
                "response": response,
                "function_called": direct_action["function_called"],
                "degraded": True,
                "error": error,
                "fallback_action": reminder,
            }

        fallback = (
            "AI is temporarily unavailable, but core case management features remain available. "
            "Please retry shortly."
        )
        if mode == "assistant":
            fallback = (
                "AI assistant is temporarily unavailable. You can continue using client lookup, "
                "dashboard, reminders, and search while the provider recovers."
            )

        return {
            "success": False,
            "response": fallback,
            "function_called": "",
            "degraded": True,
            "error": error,
        }

    async def _try_direct_reminder_fallback(
        self,
        message: str,
        default_case_manager_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Create a reminder directly when the prompt already contains explicit fields."""
        case_manager_match = re.search(r"case_manager_id=([A-Za-z0-9_\-]+)", message)
        client_match = re.search(r"client_id=([A-Za-z0-9\-]+)", message)
        due_date_match = re.search(r"due_date=([0-9]{4}-[0-9]{2}-[0-9]{2})", message)
        priority_match = re.search(r"priority=([A-Za-z]+)", message)
        message_match = re.search(r"message='([^']+)'", message)

        if not client_match or not message_match:
            return None

        result = await self.create_reminder(
            case_manager_id=(case_manager_match.group(1) if case_manager_match else default_case_manager_id),
            client_id=client_match.group(1),
            message=message_match.group(1),
            due_date=(due_date_match.group(1) if due_date_match else None),
            priority=(priority_match.group(1) if priority_match else "Medium"),
            reminder_type="ai_fallback",
        )
        return {"function_called": "create_reminder", "result": result}
