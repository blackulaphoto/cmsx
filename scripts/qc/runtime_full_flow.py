#!/usr/bin/env python3
"""
Runtime full-flow verification:
- create new client
- propagate to module DBs
- execute module actions (housing/jobs/benefits/legal/reminders)
- run AI reminder flow
- validate unified endpoints
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULE_DBS = [
    "core_clients",
    "case_management",
    "housing",
    "benefits",
    "legal",
    "employment",
    "services",
    "reminders",
    "jobs",
]


class RuntimeFlow:
    def __init__(self) -> None:
        self.run_id = f"rt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.case_manager_id = f"{self.run_id}_cm"
        self.client_id = ""
        self.results = []
        self.errors = []

    def add(self, step: str, ok: bool, detail: str) -> None:
        self.results.append({"step": step, "ok": ok, "detail": detail})
        if not ok:
            self.errors.append({"step": step, "detail": detail})

    async def run(self) -> int:
        import main

        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            await self._create_client(client)
            await self._check_propagation()
            await self._housing_flow(client)
            await self._jobs_flow(client)
            await self._benefits_flow(client)
            await self._legal_flow(client)
            await self._reminders_flow(client)
            await self._ai_reminder_flow(client)
            await self._unified_flow(client)
            self._cleanup()

        passed = len(self.errors) == 0
        report = {
            "run_id": self.run_id,
            "passed": passed,
            "errors": self.errors,
            "results": self.results,
        }
        out = ROOT / "scripts" / "qc" / f"runtime_flow_{self.run_id}.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Runtime flow report: {out}")
        print(f"Passed: {passed}")
        return 0 if passed else 1

    async def _create_client(self, client: httpx.AsyncClient) -> None:
        payload = {
            "first_name": f"Runtime{self.run_id}",
            "last_name": "Client",
            "email": f"{self.run_id}@example.test",
            "phone": "555-111-2222",
            "case_manager_id": self.case_manager_id,
            "risk_level": "medium",
            "housing_status": "unknown",
            "employment_status": "unknown",
        }
        r = await client.post("/api/clients", json=payload)
        if r.status_code != 200:
            self.add("create_client", False, f"status={r.status_code} body={r.text[:400]}")
            return
        body = r.json()
        self.client_id = body.get("client", {}).get("client_id", "")
        ok = bool(body.get("success")) and bool(self.client_id)
        self.add(
            "create_client",
            ok,
            f"client_id={self.client_id} railway_postgres={body.get('integration_results', {}).get('railway_postgres')}",
        )

    async def _check_propagation(self) -> None:
        if not self.client_id:
            self.add("propagation", False, "no client_id")
            return
        missing = []
        for name in MODULE_DBS:
            db_path = ROOT / "databases" / f"{name}.db"
            try:
                with sqlite3.connect(db_path) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                    if not cur.fetchone():
                        missing.append(f"{name}:no_clients_table")
                        continue
                    cur.execute("SELECT COUNT(*) FROM clients WHERE client_id = ?", (self.client_id,))
                    if cur.fetchone()[0] < 1:
                        missing.append(f"{name}:no_client_row")
            except Exception as exc:
                missing.append(f"{name}:{exc}")
        self.add("propagation", len(missing) == 0, "OK" if not missing else "; ".join(missing))

    async def _housing_flow(self, client: httpx.AsyncClient) -> None:
        r1 = await client.get(
            "/api/housing/search",
            params={"query": "apartment rental", "location": "Los Angeles, CA", "page": 1, "per_page": 3},
        )
        ok1 = r1.status_code == 200 and isinstance(r1.json(), dict) and r1.json().get("success") is True
        self.add("housing_search", ok1, f"status={r1.status_code}")

        r2 = await client.get("/api/housing/background-friendly")
        ok2 = r2.status_code == 200 and r2.json().get("success") is True
        self.add("housing_background_friendly", ok2, f"status={r2.status_code}")

        # Try housing assignment if a resource exists
        resource_id = None
        results = r2.json().get("results", []) if ok2 else []
        if results:
            resource_id = results[0].get("resource_id") or results[0].get("id")
        if resource_id:
            payload = {
                "client_id": self.client_id,
                "housing_resource_id": resource_id,
                "priority_level": "Medium",
                "notes": f"runtime assignment {self.run_id}",
            }
            r3 = await client.post("/api/housing/application", json=payload)
            self.add("housing_application", r3.status_code == 200 and r3.json().get("success") is True, f"status={r3.status_code}")
        else:
            self.add("housing_application", True, "skipped: no housing resource available")

    async def _jobs_flow(self, client: httpx.AsyncClient) -> None:
        r1 = await client.get(
            "/api/jobs/search/quick",
            params={"keywords": "warehouse", "location": "Los Angeles, CA", "max_results": 5},
        )
        ok1 = r1.status_code == 200 and r1.json().get("success") is True
        self.add("jobs_quick_search", ok1, f"status={r1.status_code}")

        # assignment equivalent: save a job for the created client
        payload = {"job_id": f"{self.run_id}_job_1", "client_id": self.client_id, "notes": "runtime save job"}
        r2 = await client.post("/api/jobs/save", json=payload)
        ok2 = r2.status_code == 200 and r2.json().get("success") is True
        self.add("jobs_save", ok2, f"status={r2.status_code}")

        r3 = await client.get(f"/api/jobs/saved/{self.client_id}")
        ok3 = r3.status_code == 200 and r3.json().get("success") is True
        self.add("jobs_saved_list", ok3, f"status={r3.status_code}")

    async def _benefits_flow(self, client: httpx.AsyncClient) -> None:
        payload = {
            "client_id": self.client_id,
            "benefit_type": "SNAP/CalFresh",
            "application_method": "Online",
            "assistance_received": False,
            "notes": f"runtime benefits {self.run_id}",
        }
        r1 = await client.post("/api/benefits/applications", json=payload)
        ok1 = r1.status_code == 200 and r1.json().get("success") is True
        self.add("benefits_application_create", ok1, f"status={r1.status_code}")

        r2 = await client.get("/api/benefits/applications")
        ok2 = r2.status_code == 200 and r2.json().get("success") is True
        self.add("benefits_application_list", ok2, f"status={r2.status_code}")

    async def _legal_flow(self, client: httpx.AsyncClient) -> None:
        payload = {
            "client_id": self.client_id,
            "case_number": f"RT-{self.run_id}",
            "court_name": "Los Angeles Superior Court",
            "case_type": "Misdemeanor",
            "charges": ["Test Charge"],
        }
        r1 = await client.post("/api/legal/cases", json=payload)
        ok1 = r1.status_code == 200 and r1.json().get("success") is True
        self.add("legal_case_create", ok1, f"status={r1.status_code}")

        r2 = await client.get("/api/legal/cases", params={"client_id": self.client_id})
        ok2 = r2.status_code == 200 and r2.json().get("success") is True
        self.add("legal_case_list", ok2, f"status={r2.status_code}")

    async def _reminders_flow(self, client: httpx.AsyncClient) -> None:
        due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        payload = {
            "client_id": self.client_id,
            "reminder_text": f"Runtime manual reminder {self.run_id}",
            "due_date": due,
            "case_manager_id": self.case_manager_id,
            "priority": "Medium",
        }
        r = await client.post("/api/reminders/create", json=payload)
        ok = r.status_code == 200 and r.json().get("success") is True
        self.add("reminder_create_manual", ok, f"status={r.status_code}")

    async def _ai_reminder_flow(self, client: httpx.AsyncClient) -> None:
        # central mode endpoint supports create_reminder tool calls
        due = (datetime.now(timezone.utc) + timedelta(days=3)).date().isoformat()
        msg = (
            "Create a reminder now using your tool with these exact fields: "
            f"case_manager_id={self.case_manager_id}, client_id={self.client_id}, "
            f"message='AI runtime reminder {self.run_id}', due_date={due}, priority=High."
        )
        r = await client.post("/api/ai/chat", json={"message": msg, "case_manager_id": self.case_manager_id})
        ok = r.status_code == 200 and r.json().get("success") is True
        self.add("ai_chat_request", ok, f"status={r.status_code}")

        # verify reminder row exists for this client/case manager
        found = False
        try:
            with sqlite3.connect(ROOT / "databases" / "reminders.db") as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT COUNT(*) FROM active_reminders
                    WHERE client_id = ? AND case_manager_id = ? AND message LIKE ?
                    """,
                    (self.client_id, self.case_manager_id, f"%{self.run_id}%"),
                )
                found = cur.fetchone()[0] > 0
        except Exception:
            found = False
        self.add("ai_reminder_effect", found, "AI-created reminder found in reminders.db" if found else "No AI reminder row found")

    async def _unified_flow(self, client: httpx.AsyncClient) -> None:
        for name, path in [
            ("client_get", f"/api/clients/{self.client_id}"),
            ("client_unified_view", f"/api/clients/{self.client_id}/unified-view"),
            ("client_intelligent_tasks", f"/api/clients/{self.client_id}/intelligent-tasks"),
            ("client_search_recommendations", f"/api/clients/{self.client_id}/search-recommendations"),
        ]:
            r = await client.get(path)
            self.add(name, r.status_code == 200, f"status={r.status_code}")

    def _cleanup(self) -> None:
        if not self.client_id:
            return
        for name in MODULE_DBS:
            db = ROOT / "databases" / f"{name}.db"
            if not db.exists():
                continue
            try:
                with sqlite3.connect(db) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                    if cur.fetchone():
                        cur.execute("DELETE FROM clients WHERE client_id = ?", (self.client_id,))
                        conn.commit()
            except Exception:
                pass


async def main() -> int:
    return await RuntimeFlow().run()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
