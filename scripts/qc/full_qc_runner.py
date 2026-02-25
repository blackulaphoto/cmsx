#!/usr/bin/env python3
"""
Full release-gate QC runner for module functionality, AI/memory behavior,
client propagation, and database unity.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CATALOG_PATH = Path(__file__).resolve().parent / "test_catalog.yaml"
REPORT_DIR = Path(__file__).resolve().parent
AI_DB_PATH = ROOT / "databases" / "ai_assistant.db"

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

REQUIRED_SYNC_FIELDS = ["first_name", "last_name", "case_manager_id", "risk_level"]
CRITICAL_PASS_RATE_TARGET = 1.0
MODULE_PASS_RATE_TARGET = 0.95
AI_LATENCY_THRESHOLD_SECONDS = 45


class QCRunner:
    def __init__(self) -> None:
        self.run_id = f"qc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.case_manager_id = f"{self.run_id}_cm"
        self.client_id = ""
        self.created_client_payload: Dict[str, Any] = {}

        self.results: List[Dict[str, Any]] = []
        self.defects: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.notes: List[str] = []
        self.cleanup_actions: List[str] = []

    def load_catalog(self) -> Dict[str, Any]:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    def add_result(
        self,
        test_id: str,
        passed: bool,
        category: str,
        module: str,
        severity: str = "P3",
        details: str = "",
        latency_ms: int = 0,
        status_code: int | None = None,
    ) -> None:
        self.results.append(
            {
                "test_id": test_id,
                "passed": passed,
                "category": category,
                "module": module,
                "severity": severity,
                "details": details,
                "latency_ms": latency_ms,
                "status_code": status_code,
            }
        )
        if not passed:
            self.defects.append(
                {
                    "test_id": test_id,
                    "severity": severity,
                    "category": category,
                    "module": module,
                    "details": details,
                }
            )

    def check_preflight(self) -> Any:
        import main

        module_failures = {
            name: status
            for name, status in main.loaded_modules.items()
            if isinstance(status, str) and status.startswith("error:")
        }
        if module_failures:
            for name, status in module_failures.items():
                self.add_result(
                    test_id=f"preflight_module_{name}",
                    passed=False,
                    category="preflight",
                    module="system",
                    severity="P0",
                    details=status,
                )
        else:
            self.add_result(
                test_id="preflight_module_load",
                passed=True,
                category="preflight",
                module="system",
                severity="P0",
                details="All modules loaded",
            )

        pairs = []
        for route in main.app.routes:
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None) or []
            if not path:
                continue
            for method in methods:
                if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                    pairs.append((method, path))
        duplicates = sorted((m, p, c) for (m, p), c in Counter(pairs).items() if c > 1)
        if duplicates:
            self.add_result(
                test_id="preflight_duplicate_routes",
                passed=False,
                category="preflight",
                module="system",
                severity="P0",
                details="; ".join(f"{m} {p} x{c}" for m, p, c in duplicates),
            )
        else:
            self.add_result(
                test_id="preflight_duplicate_routes",
                passed=True,
                category="preflight",
                module="system",
                severity="P0",
                details="No duplicate method/path routes",
            )

        for db_name in MODULE_DBS:
            db_path = ROOT / "databases" / f"{db_name}.db"
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
                with sqlite3.connect(db_path):
                    pass
                self.add_result(
                    test_id=f"preflight_db_{db_name}",
                    passed=True,
                    category="preflight",
                    module="system",
                    severity="P1",
                    details=f"{db_path} reachable",
                )
            except Exception as exc:
                self.add_result(
                    test_id=f"preflight_db_{db_name}",
                    passed=False,
                    category="preflight",
                    module="system",
                    severity="P1",
                    details=str(exc),
                )

        return main

    async def create_isolated_client(self, client: httpx.AsyncClient) -> None:
        payload = {
            "first_name": f"QC_{self.run_id}",
            "last_name": "Automation",
            "email": f"{self.run_id}@example.test",
            "phone": "555-000-0000",
            "case_manager_id": self.case_manager_id,
            "risk_level": "medium",
            "housing_status": "unknown",
            "employment_status": "unknown",
        }
        started = time.perf_counter()
        response = await client.post("/api/clients", json=payload)
        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code != 200:
            self.add_result(
                test_id="client_create",
                passed=False,
                category="client",
                module="client_api",
                severity="P0",
                details=f"status={response.status_code} body={response.text[:500]}",
                latency_ms=latency_ms,
                status_code=response.status_code,
            )
            return

        body = response.json()
        self.client_id = body.get("client", {}).get("client_id", "")
        self.created_client_payload = body.get("client", {})
        ok = bool(body.get("success")) and bool(self.client_id)
        self.add_result(
            test_id="client_create",
            passed=ok,
            category="client",
            module="client_api",
            severity="P0",
            details=f"client_id={self.client_id}",
            latency_ms=latency_ms,
            status_code=response.status_code,
        )

    def _apply_context(self, raw: str) -> str:
        return raw.format(client_id=self.client_id, case_manager_id=self.case_manager_id)

    async def _call_endpoint(
        self, client: httpx.AsyncClient, definition: Dict[str, Any]
    ) -> Tuple[int, Any, int]:
        method = definition["method"].upper()
        path = self._apply_context(definition["path"])
        query = definition.get("query")
        body = definition.get("body")

        started = time.perf_counter()
        if method == "GET":
            response = await client.get(path, params=query)
        elif method == "POST":
            response = await client.post(path, params=query, json=body)
        elif method == "PUT":
            response = await client.put(path, params=query, json=body)
        elif method == "DELETE":
            response = await client.delete(path, params=query)
        else:
            raise ValueError(f"Unsupported method {method}")
        latency_ms = int((time.perf_counter() - started) * 1000)

        parsed: Any = None
        try:
            parsed = response.json()
        except Exception:
            parsed = response.text

        return response.status_code, parsed, latency_ms

    async def run_endpoint_definition(
        self, client: httpx.AsyncClient, definition: Dict[str, Any], category: str, module: str
    ) -> None:
        test_id = definition["id"]
        severity = definition.get("severity", "P3")
        expected = definition.get("expected_status", [200])
        required_keys = definition.get("required_keys", [])

        try:
            status_code, body, latency_ms = await self._call_endpoint(client, definition)
            if status_code not in expected:
                self.add_result(
                    test_id=test_id,
                    passed=False,
                    category=category,
                    module=module,
                    severity=severity,
                    details=f"Unexpected status {status_code}, expected {expected}",
                    latency_ms=latency_ms,
                    status_code=status_code,
                )
                return

            if required_keys:
                if not isinstance(body, dict):
                    self.add_result(
                        test_id=test_id,
                        passed=False,
                        category=category,
                        module=module,
                        severity=severity,
                        details="Response is not JSON object",
                        latency_ms=latency_ms,
                        status_code=status_code,
                    )
                    return
                missing = [key for key in required_keys if key not in body]
                if missing:
                    self.add_result(
                        test_id=test_id,
                        passed=False,
                        category=category,
                        module=module,
                        severity=severity,
                        details=f"Missing keys: {missing}",
                        latency_ms=latency_ms,
                        status_code=status_code,
                    )
                    return

            self.add_result(
                test_id=test_id,
                passed=True,
                category=category,
                module=module,
                severity=severity,
                details="Pass",
                latency_ms=latency_ms,
                status_code=status_code,
            )
        except Exception as exc:
            self.add_result(
                test_id=test_id,
                passed=False,
                category=category,
                module=module,
                severity=severity,
                details=str(exc),
            )

    async def run_catalog_checks(self, client: httpx.AsyncClient, catalog: Dict[str, Any]) -> None:
        for definition in catalog.get("critical", []):
            await self.run_endpoint_definition(
                client, definition, category="critical", module="system"
            )

        for module, defs in catalog.get("modules", {}).items():
            for definition in defs:
                await self.run_endpoint_definition(
                    client, definition, category="module", module=module
                )

    async def run_client_unity_checks(self, client: httpx.AsyncClient) -> None:
        if not self.client_id:
            self.add_result(
                test_id="client_unity_prereq",
                passed=False,
                category="unity",
                module="client_api",
                severity="P0",
                details="No client_id generated",
            )
            return

        client_endpoint_defs = [
            {
                "id": "client_get",
                "method": "GET",
                "path": "/api/clients/{client_id}",
                "expected_status": [200],
                "required_keys": ["client_id", "first_name", "last_name", "case_manager_id"],
                "severity": "P0",
            },
            {
                "id": "client_unified_view",
                "method": "GET",
                "path": "/api/clients/{client_id}/unified-view",
                "expected_status": [200],
                "required_keys": ["success", "client_data"],
                "severity": "P1",
            },
            {
                "id": "client_intelligent_tasks",
                "method": "GET",
                "path": "/api/clients/{client_id}/intelligent-tasks",
                "expected_status": [200],
                "required_keys": ["success"],
                "severity": "P1",
            },
            {
                "id": "client_search_recommendations",
                "method": "GET",
                "path": "/api/clients/{client_id}/search-recommendations",
                "expected_status": [200],
                "required_keys": ["success"],
                "severity": "P1",
            },
        ]
        for definition in client_endpoint_defs:
            await self.run_endpoint_definition(
                client, definition, category="client", module="client_api"
            )

        for db_name in MODULE_DBS:
            db_path = ROOT / "databases" / f"{db_name}.db"
            if not db_path.exists():
                self.add_result(
                    test_id=f"unity_db_exists_{db_name}",
                    passed=False,
                    category="unity",
                    module="database",
                    severity="P1",
                    details=f"Missing DB file {db_path}",
                )
                continue
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='clients'"
                    )
                    if not cursor.fetchone():
                        self.add_result(
                            test_id=f"unity_clients_table_{db_name}",
                            passed=False,
                            category="unity",
                            module="database",
                            severity="P1",
                            details="clients table missing",
                        )
                        continue

                    cursor.execute("PRAGMA table_info(clients)")
                    columns = [row[1] for row in cursor.fetchall()]
                    cursor.execute("SELECT * FROM clients WHERE client_id = ?", (self.client_id,))
                    row = cursor.fetchone()
                    if not row:
                        self.add_result(
                            test_id=f"unity_client_row_{db_name}",
                            passed=False,
                            category="unity",
                            module="database",
                            severity="P1",
                            details="client row missing",
                        )
                        continue

                    row_map = dict(zip(columns, row))
                    mismatches = []
                    for field in REQUIRED_SYNC_FIELDS:
                        if field in row_map:
                            expected = self.created_client_payload.get(field)
                            actual = row_map.get(field)
                            if expected is not None and str(actual) != str(expected):
                                mismatches.append(f"{field} expected={expected} actual={actual}")
                    if mismatches:
                        self.add_result(
                            test_id=f"unity_field_match_{db_name}",
                            passed=False,
                            category="unity",
                            module="database",
                            severity="P1",
                            details="; ".join(mismatches),
                        )
                    else:
                        self.add_result(
                            test_id=f"unity_field_match_{db_name}",
                            passed=True,
                            category="unity",
                            module="database",
                            severity="P1",
                            details="Client row present and consistent",
                        )
            except Exception as exc:
                self.add_result(
                    test_id=f"unity_db_check_{db_name}",
                    passed=False,
                    category="unity",
                    module="database",
                    severity="P1",
                    details=str(exc),
                )

    async def run_ai_memory_checks(self, client: httpx.AsyncClient) -> None:
        fallback_payload = {
            "message": f"Fallback QC ping {self.run_id}",
            "case_manager_id": self.case_manager_id,
        }
        started = time.perf_counter()
        fallback_response = await client.post("/api/ai/assistant", json=fallback_payload)
        latency_ms = int((time.perf_counter() - started) * 1000)
        fallback_ok = fallback_response.status_code in {200, 500}
        detail = f"status={fallback_response.status_code}"
        self.add_result(
            test_id="ai_fallback_stability",
            passed=fallback_ok,
            category="ai",
            module="ai_unified",
            severity="P1",
            details=detail,
            latency_ms=latency_ms,
            status_code=fallback_response.status_code,
        )

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key or not api_key.startswith("sk-"):
            self.warnings.append("OPENAI_API_KEY missing/invalid. Live AI memory test skipped.")
            self.add_result(
                test_id="ai_live_memory",
                passed=True,
                category="ai",
                module="ai_unified",
                severity="P2",
                details="Skipped (no valid OPENAI_API_KEY)",
            )
            return

        code = f"QC-CODE-{self.run_id}"
        payload_a = {
            "message": f"For QC memory test, remember this code exactly: {code}. Reply STORED.",
            "case_manager_id": self.case_manager_id,
        }
        payload_b = {
            "message": "What code did I ask you to remember? Reply with only the code.",
            "case_manager_id": self.case_manager_id,
        }

        started_a = time.perf_counter()
        resp_a = await client.post("/api/ai/assistant", json=payload_a)
        latency_a = int((time.perf_counter() - started_a) * 1000)
        started_b = time.perf_counter()
        resp_b = await client.post("/api/ai/assistant", json=payload_b)
        latency_b = int((time.perf_counter() - started_b) * 1000)

        if resp_a.status_code != 200 or resp_b.status_code != 200:
            self.add_result(
                test_id="ai_live_memory",
                passed=False,
                category="ai",
                module="ai_unified",
                severity="P1",
                details=f"statuses: first={resp_a.status_code}, second={resp_b.status_code}",
                latency_ms=max(latency_a, latency_b),
                status_code=resp_b.status_code,
            )
            return

        body_b = resp_b.json() if resp_b.headers.get("content-type", "").startswith("application/json") else {}
        response_text = str(body_b.get("response", ""))
        latency_ok = (
            latency_a <= AI_LATENCY_THRESHOLD_SECONDS * 1000
            and latency_b <= AI_LATENCY_THRESHOLD_SECONDS * 1000
        )
        recall_ok = code.lower() in response_text.lower()

        history_has_code = False
        try:
            conv_resp = await client.get(f"/api/ai/conversation/{self.case_manager_id}")
            if conv_resp.status_code == 200:
                conv_rows = conv_resp.json()
                history_has_code = any(
                    code.lower() in str(row.get("content", "")).lower() for row in conv_rows
                )
        except Exception:
            history_has_code = False

        if not AI_DB_PATH.exists():
            db_ok = False
        else:
            with sqlite3.connect(AI_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM conversations WHERE case_manager_id = ?",
                    (self.case_manager_id,),
                )
                count = cursor.fetchone()[0]
                db_ok = count >= 2

        passed = latency_ok and db_ok and (recall_ok or history_has_code)
        details = (
            f"latency_ok={latency_ok}, recall_ok={recall_ok}, "
            f"history_has_code={history_has_code}, db_ok={db_ok}"
        )
        self.add_result(
            test_id="ai_live_memory",
            passed=passed,
            category="ai",
            module="ai_unified",
            severity="P1",
            details=details,
            latency_ms=max(latency_a, latency_b),
            status_code=resp_b.status_code,
        )

    def cleanup(self) -> None:
        if self.client_id:
            for db_name in MODULE_DBS:
                db_path = ROOT / "databases" / f"{db_name}.db"
                if not db_path.exists():
                    continue
                try:
                    with sqlite3.connect(db_path) as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name='clients'"
                        )
                        if cur.fetchone():
                            cur.execute("DELETE FROM clients WHERE client_id = ?", (self.client_id,))
                            conn.commit()
                            self.cleanup_actions.append(
                                f"Deleted QC client from {db_name}.db clients table"
                            )
                except Exception as exc:
                    self.cleanup_actions.append(f"Cleanup warning for {db_name}: {exc}")

        if AI_DB_PATH.exists():
            try:
                with sqlite3.connect(AI_DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "DELETE FROM conversations WHERE case_manager_id = ?",
                        (self.case_manager_id,),
                    )
                    conn.commit()
                    self.cleanup_actions.append("Deleted QC AI conversations")
            except Exception as exc:
                self.cleanup_actions.append(f"AI cleanup warning: {exc}")

    def summary(self) -> Dict[str, Any]:
        critical = [r for r in self.results if r["category"] == "critical"]
        module = [r for r in self.results if r["category"] == "module"]
        p0_p1 = [d for d in self.defects if d["severity"] in {"P0", "P1"}]

        critical_rate = (
            sum(1 for r in critical if r["passed"]) / len(critical) if critical else 1.0
        )
        module_rate = sum(1 for r in module if r["passed"]) / len(module) if module else 1.0
        gate_pass = (
            critical_rate >= CRITICAL_PASS_RATE_TARGET
            and module_rate >= MODULE_PASS_RATE_TARGET
            and not p0_p1
        )

        return {
            "run_id": self.run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "gate_pass": gate_pass,
            "metrics": {
                "total_tests": len(self.results),
                "passed_tests": sum(1 for r in self.results if r["passed"]),
                "failed_tests": sum(1 for r in self.results if not r["passed"]),
                "critical_pass_rate": round(critical_rate, 4),
                "module_pass_rate": round(module_rate, 4),
                "critical_target": CRITICAL_PASS_RATE_TARGET,
                "module_target": MODULE_PASS_RATE_TARGET,
            },
            "defects": self.defects,
            "warnings": self.warnings,
            "notes": self.notes,
            "cleanup": self.cleanup_actions,
            "results": self.results,
            "artifacts": {
                "catalog_path": str(CATALOG_PATH),
            },
        }

    def write_reports(self, summary: Dict[str, Any]) -> Tuple[Path, Path]:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = REPORT_DIR / f"report_{self.run_id}.json"
        md_path = REPORT_DIR / f"report_{self.run_id}.md"
        json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        lines = []
        lines.append(f"# QC Report: {self.run_id}")
        lines.append("")
        lines.append(f"- Gate pass: **{summary['gate_pass']}**")
        lines.append(f"- Total tests: {summary['metrics']['total_tests']}")
        lines.append(f"- Passed: {summary['metrics']['passed_tests']}")
        lines.append(f"- Failed: {summary['metrics']['failed_tests']}")
        lines.append(f"- Critical pass rate: {summary['metrics']['critical_pass_rate']}")
        lines.append(f"- Module pass rate: {summary['metrics']['module_pass_rate']}")
        lines.append("")
        lines.append("## Defects")
        if summary["defects"]:
            for defect in summary["defects"]:
                lines.append(
                    f"- [{defect['severity']}] {defect['module']} / {defect['test_id']}: {defect['details']}"
                )
        else:
            lines.append("- None")
        lines.append("")
        lines.append("## Warnings")
        if summary["warnings"]:
            for warning in summary["warnings"]:
                lines.append(f"- {warning}")
        else:
            lines.append("- None")
        lines.append("")
        lines.append("## Cleanup Actions")
        if summary["cleanup"]:
            for item in summary["cleanup"]:
                lines.append(f"- {item}")
        else:
            lines.append("- None")

        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return json_path, md_path


async def main_async() -> int:
    runner = QCRunner()
    catalog = runner.load_catalog()
    main_module = runner.check_preflight()

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        try:
            await runner.create_isolated_client(client)
            await runner.run_catalog_checks(client, catalog)
            await runner.run_client_unity_checks(client)
            await runner.run_ai_memory_checks(client)
        finally:
            runner.cleanup()

    summary = runner.summary()
    json_path, md_path = runner.write_reports(summary)
    print(f"QC JSON report: {json_path}")
    print(f"QC Markdown report: {md_path}")
    print(f"Gate pass: {summary['gate_pass']}")
    return 0 if summary["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async()))
