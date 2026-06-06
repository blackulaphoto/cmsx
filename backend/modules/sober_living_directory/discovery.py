from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from .database import SoberLivingDirectoryDatabase
from .importer import SoberLivingDirectoryImporter

logger = logging.getLogger(__name__)


class SoberLivingDiscoveryService:
    def __init__(self, db: SoberLivingDirectoryDatabase):
        self.db = db
        self.importer = SoberLivingDirectoryImporter(db)
        self.workspace_root = Path(__file__).resolve().parents[3]

    def run_job(self, job_id: str) -> Dict[str, Any]:
        job = self.db.get_discovery_job(job_id)
        if not job:
            raise ValueError("Discovery job not found")

        source = self.db.get_source(job["source_id"])
        if not source:
            raise ValueError("Source not found for discovery job")

        records = self._load_records_for_source(source)
        notes = f"Connector run for source {source['source_name']}"
        return self.db.process_discovery_records(
            job_id=job_id,
            source_id=source["source_id"],
            records=records,
            notes=notes,
        )

    def _load_records_for_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if source.get("source_type") != "spreadsheet_import":
            raise ValueError("Only spreadsheet_import sources are supported in Phase 4B")

        if not source.get("base_url"):
            raise ValueError("Spreadsheet source requires a base_url file path")

        file_path = self._resolve_workspace_file(source["base_url"])
        if not file_path.exists() or not file_path.is_file():
            raise ValueError(f"Spreadsheet source file not found: {source['base_url']}")

        suffix = file_path.suffix.lower()
        if suffix not in {".xlsx", ".csv"}:
            raise ValueError("Spreadsheet source must be a .xlsx or .csv file")

        content = file_path.read_bytes()
        rows = list(self.importer._extract_rows(file_name=file_path.name, content=content))
        normalized_records: List[Dict[str, Any]] = []
        for row in rows:
            if not row:
                continue
            normalized = self.importer._normalize_row(row, file_name=file_path.name)
            if normalized.get("name") and normalized.get("city"):
                normalized_records.append(normalized)
        return normalized_records

    def _resolve_workspace_file(self, relative_or_absolute_path: str) -> Path:
        candidate = Path(relative_or_absolute_path)
        resolved = candidate.resolve() if candidate.is_absolute() else (self.workspace_root / candidate).resolve()
        workspace = self.workspace_root.resolve()
        if workspace != resolved and workspace not in resolved.parents:
            raise ValueError("Spreadsheet source path must stay inside the workspace")
        return resolved
