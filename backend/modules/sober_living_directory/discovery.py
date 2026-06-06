from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .database import SoberLivingDirectoryDatabase
from .importer import SoberLivingDirectoryImporter

logger = logging.getLogger(__name__)


class SoberLivingDiscoveryService:
    SUPPORTED_CCAPP_HOSTS = {"ccapprecoveryresidences.org", "www.ccapprecoveryresidences.org"}
    SUPPORTED_OXFORD_HOSTS = {"oxfordvacancies.com", "www.oxfordvacancies.com"}
    REQUEST_TIMEOUT_SECONDS = 30
    MAX_REMOTE_RESPONSE_BYTES = 2_000_000
    MAX_CCAPP_RESULTS = 25
    MAX_OXFORD_RESULTS = 100
    REMOTE_USER_AGENT = "CaseManagerSuite/1.0 (+https://github.com/blackulaphoto/cmsx)"

    def __init__(self, db: SoberLivingDirectoryDatabase):
        self.db = db
        self.importer = SoberLivingDirectoryImporter(db)
        self.workspace_root = Path(__file__).resolve().parents[3]

    def run_job(self, job_id: str, *, trigger_type: str = "manual") -> Dict[str, Any]:
        job = self.db.get_discovery_job(job_id)
        if not job:
            raise ValueError("Discovery job not found")

        source = self.db.get_source(job["source_id"])
        if not source:
            raise ValueError("Source not found for discovery job")

        if trigger_type == "scheduled":
            self.db.mark_scheduled_run_started(job_id)
        else:
            self.db.mark_manual_run_started(job_id)

        try:
            records = self._load_records_for_source(source, job)
        except Exception as exc:
            failure_notes = self._build_failure_notes(source=source, job=job)
            self.db.record_discovery_run_failure(
                job_id=job_id,
                source_id=source["source_id"],
                trigger_type=trigger_type,
                notes=failure_notes,
                error_message=str(exc),
            )
            raise
        notes = self._build_run_notes(source=source, job=job, records=records)
        return self.db.process_discovery_records(
            job_id=job_id,
            source_id=source["source_id"],
            records=records,
            trigger_type=trigger_type,
            notes=notes,
        )

    def _build_run_notes(self, *, source: Dict[str, Any], job: Dict[str, Any], records: List[Dict[str, Any]]) -> str:
        connector_name = self._connector_name(source)
        city = job.get("target_city") or "all visible cities"
        state = job.get("target_state") or "all visible states"
        return (
            f"Connector run for {connector_name} on source {source.get('source_name')}. "
            f"Visible records processed for {city}, {state}. Parsed {len(records)} records."
        )

    def _build_failure_notes(self, *, source: Dict[str, Any], job: Dict[str, Any]) -> str:
        connector_name = self._connector_name(source)
        city = job.get("target_city") or "all visible cities"
        state = job.get("target_state") or "all visible states"
        return (
            f"Connector run for {connector_name} on source {source.get('source_name')} failed "
            f"before raw review records were created. Requested scope was {city}, {state}."
        )

    def _load_records_for_source(self, source: Dict[str, Any], job: Dict[str, Any]) -> List[Dict[str, Any]]:
        if source.get("source_type") == "spreadsheet_import":
            return self._load_spreadsheet_records(source)
        if self._is_ccapp_source(source):
            return self._load_ccapp_directory_records(source, job)
        if self._is_oxford_source(source):
            return self._load_oxford_directory_records(source, job)

        raise ValueError("This discovery source is not supported by the current connector set")

    def _load_spreadsheet_records(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
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

    def _load_ccapp_directory_records(self, source: Dict[str, Any], job: Dict[str, Any]) -> List[Dict[str, Any]]:
        base_url = (source.get("base_url") or "").strip()
        if not base_url:
            raise ValueError("CCAPP discovery source requires a base_url")

        if not self._is_ccapp_source(source):
            raise ValueError("Unsupported certification directory source")

        html = self._fetch_remote_text(base_url)
        records = self._parse_ccapp_search_results(html=html, base_url=base_url)
        return self._filter_records_for_job(records=records, job=job)

    def _is_ccapp_source(self, source: Dict[str, Any]) -> bool:
        base_url = (source.get("base_url") or "").strip()
        if not base_url:
            return False
        parsed = urlparse(base_url)
        return (
            source.get("source_type") == "certification_directory"
            and parsed.scheme in {"http", "https"}
            and parsed.netloc.lower() in self.SUPPORTED_CCAPP_HOSTS
            and parsed.path.rstrip("/") == "/search"
        )

    def _is_oxford_source(self, source: Dict[str, Any]) -> bool:
        base_url = (source.get("base_url") or "").strip()
        if not base_url:
            return False
        parsed = urlparse(base_url)
        normalized_path = parsed.path.rstrip("/") or "/"
        return (
            source.get("source_type") == "public_directory"
            and parsed.scheme in {"http", "https"}
            and parsed.netloc.lower() in self.SUPPORTED_OXFORD_HOSTS
            and normalized_path in {"/", "/Default.aspx", "/Portal.aspx"}
        )

    def _connector_name(self, source: Dict[str, Any]) -> str:
        if source.get("source_type") == "spreadsheet_import":
            return "spreadsheet_import"
        if self._is_ccapp_source(source):
            return "ccapp_certification_directory"
        if self._is_oxford_source(source):
            return "oxford_house_public_directory"
        return source.get("source_type") or "unknown"

    def _fetch_remote_text(self, url: str) -> str:
        response = requests.get(
            url,
            timeout=self.REQUEST_TIMEOUT_SECONDS,
            headers={
                "User-Agent": self.REMOTE_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
        content = response.content
        if len(content) > self.MAX_REMOTE_RESPONSE_BYTES:
            raise ValueError(
                f"Remote connector response exceeded {self.MAX_REMOTE_RESPONSE_BYTES} bytes for {url}"
            )
        return content.decode(response.encoding or "utf-8", errors="replace")

    def _parse_ccapp_search_results(self, *, html: str, base_url: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        records: List[Dict[str, Any]] = []
        seen_facility_ids: set[str] = set()

        for card in soup.select("div.gh-card"):
            name_link = card.select_one("a.gh-facilities-item[id][href]")
            if not name_link:
                continue

            facility_id = (name_link.get("id") or "").strip()
            href = (name_link.get("href") or "").strip()
            if not facility_id or facility_id in seen_facility_ids:
                continue

            name = name_link.get_text(" ", strip=True)
            if not name:
                continue

            address_link = card.select_one(".facilityCard_address__1LctV a.gh-facilities-item")
            address_text = address_link.get_text(" ", strip=True) if address_link else ""
            city, state, zip_code = self._parse_city_state_zip(address_text)

            badge_texts = [
                text.strip()
                for text in card.stripped_strings
                if text and text.strip() not in {name, address_text, "mi."}
            ]
            certification_status = next(
                (text for text in badge_texts if text.lower() in {"accredited", "certified"}),
                "Accredited",
            )
            distance_miles = next(
                (text for text in badge_texts if self._looks_like_decimal(text)),
                None,
            )
            facility_url = f"{base_url.rstrip('/')}/#/facility/{facility_id}"
            notes_parts = [
                "Imported from the live CCAPP certified recovery residence search page.",
                f"Facility ID: {facility_id}.",
            ]
            if distance_miles:
                notes_parts.append(f"Visible search-card distance: {distance_miles} mi.")

            records.append(
                {
                    "name": name,
                    "operator_name": None,
                    "website": None,
                    "phone": None,
                    "email": None,
                    "address": None,
                    "city": city,
                    "state": state or "CA",
                    "zip_code": zip_code,
                    "latitude": None,
                    "longitude": None,
                    "neighborhood": None,
                    "population_served": None,
                    "house_type": "Recovery Residence",
                    "certification_status": certification_status,
                    "certification_body": "CCAPP",
                    "certification_expiration_date": None,
                    "monthly_rent_min": None,
                    "monthly_rent_max": None,
                    "deposit_required": None,
                    "accepts_insurance": None,
                    "accepts_mat": None,
                    "accepts_probation_parole": None,
                    "pets_allowed": None,
                    "bed_availability_status": "unknown",
                    "verification_method": "certification_directory",
                    "notes": " ".join(notes_parts),
                    "risk_flags_json": [],
                    "source_url": facility_url,
                    "source_urls_json": [base_url, facility_url],
                }
            )
            seen_facility_ids.add(facility_id)
            if len(records) >= self.MAX_CCAPP_RESULTS:
                break

        return records

    def _load_oxford_directory_records(self, source: Dict[str, Any], job: Dict[str, Any]) -> List[Dict[str, Any]]:
        base_url = (source.get("base_url") or "").strip()
        if not base_url:
            raise ValueError("Oxford discovery source requires a base_url")

        if not self._is_oxford_source(source):
            raise ValueError("Unsupported Oxford House directory source")

        html = self._fetch_remote_text(base_url)
        records = self._parse_oxford_vacancy_results(
            html=html,
            base_url=base_url,
            job=job,
            source_name=source.get("source_name") or "Oxford House",
        )
        return self._filter_records_for_job(records=records, job=job)

    def _parse_oxford_vacancy_results(
        self,
        *,
        html: str,
        base_url: str,
        job: Dict[str, Any],
        source_name: str,
    ) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        header_map: Dict[str, int] | None = None
        records: List[Dict[str, Any]] = []
        target_state = (job.get("target_state") or "").strip().upper() or None
        query = (job.get("query") or "").strip() or None

        for row in soup.select("tr"):
            cells = [" ".join(cell.stripped_strings) for cell in row.select("th,td")]
            cells = [cell.replace("\xa0", " ").strip() for cell in cells]
            if not cells:
                continue

            normalized_headers = [self._normalize_header_value(cell) for cell in cells]
            if "house_name" in normalized_headers and "city" in normalized_headers:
                header_map = {header: index for index, header in enumerate(normalized_headers)}
                continue

            if not header_map or len(cells) < len(header_map):
                continue

            house_name = self._cell_value(cells, header_map, "house_name")
            city = self._cell_value(cells, header_map, "city")
            if not house_name or not city:
                continue

            gender_code = self._cell_value(cells, header_map, "gender")
            house_phone = self._cell_value(cells, header_map, "house")
            county = self._cell_value(cells, header_map, "county")
            contact_name = self._cell_value(cells, header_map, "contact")
            contact_phone = self._cell_value(cells, header_map, "contact_number")
            interviews = self._cell_value(cells, header_map, "interviews")
            capacity = self._cell_value(cells, header_map, "capacity")
            vacancies = self._cell_value(cells, header_map, "vacancies")
            last_updated = self._cell_value(cells, header_map, "last_updated")

            row_text = " | ".join(value for value in cells if value)
            population_served = self._map_oxford_population(gender_code)
            availability_status = self._map_oxford_availability(vacancies)
            notes_parts = [
                "Imported from the public Oxford House vacancy locator visible results grid.",
                f"County: {county}." if county else None,
                f"Primary contact: {contact_name}." if contact_name else None,
                f"Interview schedule: {interviews}." if interviews else None,
                f"Capacity: {capacity}." if capacity else None,
                f"Vacancies shown: {vacancies}." if vacancies else None,
                f"Last updated on directory: {last_updated}." if last_updated else None,
            ]
            if target_state:
                notes_parts.append(
                    f"State set from the manual discovery job target because the visible Oxford grid row does not expose a state column: {target_state}."
                )
            if query:
                notes_parts.append(f"Manual discovery query: {query}.")

            records.append(
                {
                    "name": f"Oxford House - {house_name}",
                    "operator_name": "Oxford House",
                    "website": None,
                    "phone": contact_phone or house_phone,
                    "email": None,
                    "address": None,
                    "city": city,
                    "state": target_state,
                    "zip_code": None,
                    "latitude": None,
                    "longitude": None,
                    "neighborhood": county or None,
                    "population_served": population_served,
                    "house_type": "Oxford House",
                    "certification_status": "Listed",
                    "certification_body": "Oxford House",
                    "certification_expiration_date": None,
                    "monthly_rent_min": None,
                    "monthly_rent_max": None,
                    "deposit_required": None,
                    "accepts_insurance": None,
                    "accepts_mat": None,
                    "accepts_probation_parole": None,
                    "pets_allowed": None,
                    "bed_availability_status": availability_status,
                    "verification_method": "public_directory",
                    "notes": " ".join(part for part in notes_parts if part),
                    "risk_flags_json": [],
                    "source_url": base_url,
                    "source_urls_json": [base_url],
                    "house_name": house_name,
                    "county": county,
                    "contact_name": contact_name,
                    "contact_phone": contact_phone,
                    "house_phone": house_phone,
                    "interviews": interviews,
                    "capacity": self._parse_int(capacity),
                    "vacancies": vacancies,
                    "query_used": query,
                    "source_name": source_name,
                    "raw_row_text": row_text,
                }
            )

            if len(records) >= self.MAX_OXFORD_RESULTS:
                break

        return records

    def _filter_records_for_job(self, *, records: List[Dict[str, Any]], job: Dict[str, Any]) -> List[Dict[str, Any]]:
        target_city = (job.get("target_city") or "").strip().lower()
        target_state = (job.get("target_state") or "").strip().upper()

        filtered = records
        if target_city:
            filtered = [record for record in filtered if (record.get("city") or "").strip().lower() == target_city]
        if target_state:
            filtered = [record for record in filtered if (record.get("state") or "").strip().upper() == target_state]
        return filtered

    @staticmethod
    def _parse_city_state_zip(address_text: str) -> tuple[str | None, str | None, str | None]:
        cleaned = " ".join(address_text.replace("\xa0", " ").split())
        if not cleaned:
            return None, None, None
        parts = cleaned.split(",")
        if len(parts) >= 2:
            city_state = parts[0].strip()
            zip_code = parts[1].strip() or None
        else:
            city_state = cleaned
            zip_code = None
        city_state_parts = city_state.rsplit(" ", 1)
        if len(city_state_parts) == 2 and len(city_state_parts[1]) == 2:
            return city_state_parts[0].strip() or None, city_state_parts[1].strip().upper(), zip_code
        return city_state.strip() or None, None, zip_code

    @staticmethod
    def _looks_like_decimal(value: str) -> bool:
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _normalize_header_value(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")
        header_aliases = {
            "house_name": "house_name",
            "gender": "gender",
            "city": "city",
            "house": "house",
            "house_number": "house",
            "house_": "house",
            "county": "county",
            "contact": "contact",
            "contact_number": "contact_number",
            "interviews": "interviews",
            "capacity": "capacity",
            "vacancies": "vacancies",
            "distance": "distance",
            "last_updated": "last_updated",
        }
        return header_aliases.get(normalized, normalized)

    @staticmethod
    def _cell_value(cells: List[str], header_map: Dict[str, int], key: str) -> str | None:
        index = header_map.get(key)
        if index is None or index >= len(cells):
            return None
        value = (cells[index] or "").strip()
        return value or None

    @staticmethod
    def _map_oxford_population(gender_code: str | None) -> str | None:
        mapping = {
            "M": "Men",
            "W": "Women",
            "MC": "Men with Children",
            "WC": "Women with Children",
        }
        if not gender_code:
            return None
        return mapping.get(gender_code.strip().upper(), gender_code.strip())

    @staticmethod
    def _map_oxford_availability(vacancies: str | None) -> str:
        if not vacancies:
            return "unknown"
        normalized = vacancies.strip().lower()
        if normalized.startswith("0"):
            return "full"
        digits = re.findall(r"\d+", normalized)
        if digits and any(int(value) > 0 for value in digits):
            return "available"
        return "unknown"

    @staticmethod
    def _parse_int(value: str | None) -> int | None:
        if not value:
            return None
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits) if digits else None

    def _resolve_workspace_file(self, relative_or_absolute_path: str) -> Path:
        candidate = Path(relative_or_absolute_path)
        resolved = candidate.resolve() if candidate.is_absolute() else (self.workspace_root / candidate).resolve()
        workspace = self.workspace_root.resolve()
        if workspace != resolved and workspace not in resolved.parents:
            raise ValueError("Spreadsheet source path must stay inside the workspace")
        return resolved
