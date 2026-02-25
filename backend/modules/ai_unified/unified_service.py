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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiosqlite
from openai import AsyncOpenAI

from backend.modules.services.case_management_api import (
    get_dashboard_stats_from_db,
    get_clients_from_db,
)
from backend.modules.reminders.engine import IntelligentReminderEngine
from backend.search.coordinator import get_coordinator

logger = logging.getLogger(__name__)
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
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._initialized = False
        self._function_map = {
            "get_dashboard_stats": self.get_dashboard_stats,
            "create_reminder": self.create_reminder,
            "get_client_list": self.get_client_list,
            "search_jobs": self.search_jobs,
            "search_housing": self.search_housing,
            "search_services": self.search_services,
        }

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
            await db.commit()

        self._initialized = True
        logger.info("Unified AI SQLite memory initialized")

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
    ) -> Dict[str, Any]:
        """Process a chat message and persist conversation history."""
        await self.initialize()

        history = await self._fetch_history(case_manager_id, limit=20)
        system_prompt = ASSISTANT_SYSTEM_PROMPT
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]
        messages.extend({"role": h["role"], "content": h["content"]} for h in history)
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
        ]
        assistant_tools = [
            tool
            for tool in central_tools
            if tool["function"]["name"] != "create_reminder"
        ]
        tools = assistant_tools if mode == "assistant" else central_tools
        allowed_functions = {tool["function"]["name"] for tool in tools}

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

        await self._save_message(case_manager_id, "user", message)
        await self._save_message(case_manager_id, "assistant", assistant_text)

        return {
            "success": True,
            "response": assistant_text,
            "function_called": function_called,
        }

    async def get_conversation_history(self, case_manager_id: str) -> List[Dict[str, Any]]:
        await self.initialize()
        return await self._fetch_history(case_manager_id, limit=100)
