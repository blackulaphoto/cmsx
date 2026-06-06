from __future__ import annotations

import csv
import io
import json
import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .database import SoberLivingDirectoryDatabase
from .models import SoberLivingDirectoryListingUpdate

logger = logging.getLogger(__name__)


class SoberLivingDirectoryImporter:
    NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}

    def __init__(self, db: SoberLivingDirectoryDatabase):
        self.db = db

    def import_file(
        self,
        *,
        file_name: str,
        content: bytes,
        source_name: str,
        source_type: str = "manual_import",
    ) -> Dict[str, Any]:
        source_id = self.db.get_or_create_source(
            source_name=source_name,
            source_type=source_type,
            trust_level="medium",
            requires_manual_review=True,
        )

        rows = list(self._extract_rows(file_name=file_name, content=content))
        stats = {
            "source_id": source_id,
            "source_name": source_name,
            "file_name": file_name,
            "rows_read": len(rows),
            "raw_created": 0,
            "listings_created": 0,
            "listings_updated": 0,
            "duplicates_detected": 0,
            "errors": [],
        }

        for row in rows:
            try:
                normalized = self._normalize_row(row, file_name=file_name)
                if not normalized.get("name") or not normalized.get("city"):
                    continue

                duplicate = self.db.find_possible_duplicate(
                    name=normalized.get("name"),
                    city=normalized.get("city"),
                    phone=normalized.get("phone"),
                    website=normalized.get("website"),
                )

                raw_id = self.db.create_raw_listing(
                    source_id=source_id,
                    source_url=normalized.get("website"),
                    raw_name=normalized.get("name"),
                    raw_address=normalized.get("address"),
                    raw_phone=normalized.get("phone"),
                    raw_email=normalized.get("email"),
                    raw_website=normalized.get("website"),
                    raw_text=json.dumps(row, ensure_ascii=True),
                    extracted_json=normalized,
                    matched_listing_id=duplicate["listing_id"] if duplicate else None,
                    review_status="possible_duplicate" if duplicate else "approved",
                )
                stats["raw_created"] += 1

                if duplicate:
                    stats["duplicates_detected"] += 1
                    confidence_score, match_reasons = self.db.score_duplicate_candidate(
                        name=normalized.get("name"),
                        city=normalized.get("city"),
                        phone=normalized.get("phone"),
                        website=normalized.get("website"),
                        existing_listing=duplicate,
                    )
                    self.db.create_duplicate_candidate(
                        raw_id=raw_id,
                        existing_listing_id=duplicate["listing_id"],
                        proposed_name=normalized.get("name"),
                        existing_name=duplicate.get("name"),
                        match_reasons=match_reasons or ["possible_duplicate"],
                        confidence_score=confidence_score,
                    )
                    continue

                created = self.db.create_listing_from_import_data(normalized)
                self.db._insert_change_log(  # noqa: SLF001 - phase 2 importer needs initial raw linkage
                    listing_id=created["listing_id"],
                    raw_id=raw_id,
                    change_type="imported_from_file",
                    old_value=None,
                    new_value=file_name,
                    source_id=source_id,
                )
                self.db.connect().commit()
                stats["listings_created"] += 1
            except Exception as exc:
                logger.warning("Failed to import sober living row: %s", exc)
                stats["errors"].append(str(exc))

        return stats

    def _extract_rows(self, *, file_name: str, content: bytes) -> Iterable[Dict[str, Any]]:
        lower_name = file_name.lower()
        if lower_name.endswith(".csv"):
            yield from self._extract_csv_rows(content)
            return
        if lower_name.endswith(".xlsx"):
            yield from self._extract_xlsx_rows(content)
            return
        raise ValueError("Unsupported import file type. Use .xlsx or .csv")

    def _extract_csv_rows(self, content: bytes) -> Iterable[Dict[str, Any]]:
        text = content.decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            yield dict(row)

    def _extract_xlsx_rows(self, content: bytes) -> Iterable[Dict[str, Any]]:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            shared_strings = self._read_shared_strings(archive)
            workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
            sheets = [
                (sheet.attrib.get("name"), sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
                for sheet in workbook_root.findall("a:sheets/a:sheet", self.NS)
            ]
            rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_root}

            seen_records = set()
            for sheet_name, rel_id in sheets:
                if not rel_id:
                    continue
                target = relmap[rel_id].lstrip("/")
                if not target.startswith("xl/"):
                    target = f"xl/{target}"
                sheet_root = ET.fromstring(archive.read(target))
                rows = sheet_root.findall(".//a:sheetData/a:row", self.NS)
                if not rows:
                    continue

                headers = self._extract_row_values(rows[0], shared_strings)
                if not headers:
                    continue

                for row in rows[1:]:
                    values = self._extract_row_values(row, shared_strings)
                    if not any(values):
                        continue
                    record = {headers[index]: values[index] if index < len(values) else None for index in range(len(headers))}
                    record["_sheet_name"] = sheet_name
                    fingerprint = (
                        str(record.get("Name") or "").strip().lower(),
                        str(record.get("Location") or "").strip().lower(),
                        str(record.get("Phone") or "").strip().lower(),
                    )
                    if fingerprint in seen_records:
                        continue
                    seen_records.add(fingerprint)
                    yield record

    def _read_shared_strings(self, archive: zipfile.ZipFile) -> List[str]:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        values = []
        for item in root.findall("a:si", self.NS):
            values.append("".join(node.text or "" for node in item.findall(".//a:t", self.NS)))
        return values

    def _extract_row_values(self, row_node: ET.Element, shared_strings: List[str]) -> List[Optional[str]]:
        values: List[Optional[str]] = []
        for cell in row_node.findall("a:c", self.NS):
            ref = cell.attrib.get("r", "")
            column_index = self._column_index_from_ref(ref)
            while len(values) < column_index:
                values.append(None)
            cell_type = cell.attrib.get("t")
            value_node = cell.find("a:v", self.NS)
            if value_node is None:
                inline_node = cell.find("a:is", self.NS)
                if inline_node is None:
                    values.append(None)
                    continue
                values.append("".join(t.text or "" for t in inline_node.findall(".//a:t", self.NS)))
                continue
            if cell_type == "s":
                values.append(shared_strings[int(value_node.text)])
            else:
                values.append(value_node.text)
        return values

    @staticmethod
    def _column_index_from_ref(ref: str) -> int:
        letters = "".join(ch for ch in ref if ch.isalpha()).upper()
        index = 0
        for char in letters:
            index = index * 26 + (ord(char) - 64)
        return max(index - 1, 0)

    def _normalize_row(self, row: Dict[str, Any], *, file_name: str) -> Dict[str, Any]:
        name = self._clean_text(row.get("Name") or row.get("name"))
        city = self._clean_text(row.get("Location") or row.get("City") or row.get("city"))
        population_served = self._clean_text(row.get("Serves") or row.get("Gender") or row.get("population_served"))
        phone = self._clean_text(row.get("Phone") or row.get("phone"))
        website = self._clean_text(row.get("Website") or row.get("website"))
        contact = self._clean_text(row.get("Contact") or row.get("contact"))
        price = self._clean_text(row.get("Price") or row.get("price"))
        sheet_name = self._clean_text(row.get("_sheet_name"))

        rent_min, rent_max = self._extract_price_range(price)
        status = "pending_review"
        notes = f"Imported from {file_name}"
        if price:
            notes = f"{notes}. Price column value: {price}"
        if sheet_name:
            notes = f"{notes}. Source sheet: {sheet_name}"

        source_urls = [website] if website else []
        risk_flags = []
        if not phone:
            risk_flags.append("missing_phone")
        if not website:
            risk_flags.append("missing_website")

        certification_status, certification_body = self._infer_certification(row, website)
        if certification_status is None:
            certification_status = "Unverified"

        return {
            "name": name,
            "operator_name": contact,
            "website": website,
            "phone": phone,
            "email": None,
            "address": None,
            "city": city,
            "state": "CA",
            "zip_code": None,
            "latitude": None,
            "longitude": None,
            "neighborhood": None,
            "population_served": population_served,
            "house_type": "Sober Living",
            "certification_status": certification_status,
            "certification_body": certification_body,
            "certification_expiration_date": None,
            "monthly_rent_min": rent_min,
            "monthly_rent_max": rent_max,
            "deposit_required": None,
            "accepts_insurance": None,
            "accepts_mat": None,
            "accepts_probation_parole": None,
            "pets_allowed": None,
            "bed_availability_status": "unknown",
            "last_availability_check_date": None,
            "last_verified_date": None,
            "verification_method": "import",
            "risk_flags_json": risk_flags,
            "notes": notes,
            "internal_referral_notes": None,
            "source_urls_json": source_urls,
            "status": status,
        }

    @staticmethod
    def _clean_text(value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned or cleaned.lower() in {"none", "n/a", "null"}:
            return None
        return cleaned

    @staticmethod
    def _extract_price_range(value: Optional[str]) -> tuple[Optional[float], Optional[float]]:
        if not value:
            return None, None
        matches = [float(num.replace(",", "")) for num in re.findall(r"\d[\d,]*", value)]
        if not matches:
            return None, None
        if len(matches) == 1:
            return matches[0], matches[0]
        return min(matches), max(matches)

    @staticmethod
    def _infer_certification(row: Dict[str, Any], website: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        combined = " ".join(
            str(row.get(key) or "")
            for key in ("Name", "Website", "Contact", "Serves", "Gender", "_sheet_name")
        ).lower()
        if "oxford" in combined:
            return "Certified", "Oxford House"
        if "ccapp" in combined:
            return "Certified", "CCAPP"
        if website and "soberlivingnetwork" in website.lower():
            return "Listed", "Sober Living Network"
        return None, None
