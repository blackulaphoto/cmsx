import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Path resolution: __file__ = backend/modules/admissions/template_parser.py
# parents[3] = CASE_MANAGER_SUITE2/ (project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATES_DIR = _PROJECT_ROOT / "data" / "form_templates" / "admissions"
_ADMISSION_DIR = _PROJECT_ROOT / "admission"
MANIFEST_PATH = _TEMPLATES_DIR / "manifest.json"

# Fallbacks for alternate working-directory launch contexts
if not MANIFEST_PATH.exists():
    MANIFEST_PATH = Path("data") / "form_templates" / "admissions" / "manifest.json"
    _ADMISSION_DIR = Path("admission")


def _load_manifest() -> List[Dict[str, Any]]:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("forms", [])


def _parse_metadata(lines: List[str]) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("- key:"):
            key = line[len("- key:"):].strip()
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("value:"):
                meta[key] = lines[i + 1].strip()[len("value:"):].strip()
                i += 2
                continue
        i += 1
    return meta


def _parse_section_names(lines: List[str]) -> List[str]:
    sections = []
    for line in lines:
        m = re.match(r"^\d+\.\s+(.+)$", line.strip())
        if m:
            sections.append(m.group(1).strip())
    return sections


def _parse_field_table(table_lines: List[str]) -> List[Dict[str, Any]]:
    fields = []
    for line in table_lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = [p.strip() for p in stripped.split("|")[1:-1]]
        if not parts:
            continue
        # Skip header row ("name", "label", ...) and divider row ("---")
        if parts[0] in ("name", "---") or all(p.strip("-") == "" for p in parts):
            continue
        if len(parts) < 4:
            continue
        name, label, ftype, required = parts[0], parts[1], parts[2], parts[3]
        options_raw = parts[4] if len(parts) > 4 else ""
        help_text = parts[5] if len(parts) > 5 else ""
        fields.append(
            {
                "name": name,
                "label": label,
                "type": ftype,
                "required": required.lower() in ("yes", "true", "1"),
                "options": [o.strip() for o in options_raw.split(";") if o.strip()],
                "help_text": help_text,
            }
        )
    return fields


def _parse_signatures(lines: List[str]) -> List[Dict[str, Any]]:
    sigs: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- field:"):
            if current:
                sigs.append(current)
            current = {"field": stripped[len("- field:"):].strip()}
        elif stripped.startswith("type:") and current:
            current["type"] = stripped[len("type:"):].strip()
        elif stripped.startswith("label:") and current:
            current["label"] = stripped[len("label:"):].strip()
        elif stripped.startswith("required:") and current:
            current["required"] = stripped[len("required:"):].strip().lower() in ("true", "yes")
    if current:
        sigs.append(current)
    return sigs


def _split_into_tables(lines: List[str]) -> List[List[str]]:
    """Split field block lines into individual table chunks, separated by blank lines."""
    tables: List[List[str]] = []
    current: List[str] = []
    in_table = False
    for line in lines:
        if line.strip().startswith("|"):
            current.append(line)
            in_table = True
        else:
            if in_table and current:
                tables.append(current)
                current = []
                in_table = False
    if current:
        tables.append(current)
    return tables


def parse_template(form_key: str) -> Optional[Dict[str, Any]]:
    """
    Parse an admission form Markdown template by form_key.

    Returns a structured dict with grouped_fields (section → fields) and signatures,
    or None if the form_key is unknown or the source file is missing.
    """
    try:
        forms = _load_manifest()
    except Exception as exc:
        logger.error(f"[PARSER] Could not load manifest: {exc}")
        return None

    form_def = next((x for x in forms if x["form_key"] == form_key), None)
    if not form_def:
        return None

    source_path = _ADMISSION_DIR / form_def["source_file"]
    if not source_path.exists():
        logger.error(f"[PARSER] Source file not found: {source_path}")
        return None

    try:
        content = source_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.error(f"[PARSER] Failed to read {source_path}: {exc}")
        return None

    lines = content.split("\n")

    # Parse title from "# Form: <title>"
    title = ""
    for line in lines:
        if line.startswith("# Form:"):
            title = line[len("# Form:"):].strip()
            break

    # Split content into named blocks by "## <Heading>"
    blocks: Dict[str, List[str]] = {}
    current_key: Optional[str] = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_key = stripped[3:].strip().lower().replace(" ", "_")
            blocks[current_key] = []
        elif current_key is not None:
            blocks[current_key].append(line)

    metadata = _parse_metadata(blocks.get("metadata", []))
    section_names = _parse_section_names(blocks.get("sections", []))
    signatures = _parse_signatures(blocks.get("signatures", []))

    raw_tables = _split_into_tables(blocks.get("fields", []))
    parsed_tables = [_parse_field_table(t) for t in raw_tables]
    parsed_tables = [t for t in parsed_tables if t]  # remove empties

    n_tables = len(parsed_tables)
    n_sections = len(section_names)

    grouped_fields: List[Dict[str, Any]] = []

    if n_sections == 0 or n_tables < n_sections:
        # Flat — no per-section grouping
        all_fields: List[Dict[str, Any]] = []
        for t in parsed_tables:
            all_fields.extend(t)
        grouped_fields.append({"section": None, "fields": all_fields})
    elif n_tables == n_sections:
        # Perfect 1:1 — zip sections to tables
        for sec, fields in zip(section_names, parsed_tables):
            grouped_fields.append({"section": sec, "fields": fields})
    else:
        # More tables than sections — leading tables are intro (no section header)
        extra = n_tables - n_sections
        intro_fields: List[Dict[str, Any]] = []
        for t in parsed_tables[:extra]:
            intro_fields.extend(t)
        if intro_fields:
            grouped_fields.append({"section": None, "fields": intro_fields})
        for sec, fields in zip(section_names, parsed_tables[extra:]):
            grouped_fields.append({"section": sec, "fields": fields})

    return {
        "form_key": form_key,
        "form_name": form_def["form_name"],
        "title": title,
        "category": form_def.get("category", ""),
        "description": form_def.get("description", ""),
        "metadata": metadata,
        "section_names": section_names,
        "grouped_fields": grouped_fields,
        "signatures": signatures,
        "requires_signature": form_def.get("requires_signature", False),
        "signatures_required": form_def.get("signatures_required", []),
        "allow_revocation": form_def.get("allow_revocation", False),
        "timing_group": form_def.get("timing_group", "admission"),
        "timing_label": form_def.get("timing_label", ""),
        "required": form_def.get("required", False),
    }
