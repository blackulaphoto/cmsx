"""
Food resources seed - batch 1 (20 enriched LA food resources).
Reads from seeds/food_resources_batch1.json, applies normalization, and imports
into resource_library. Safe to run multiple times — deduplicates by
provider_name + service_name.

Run: python -m backend.modules.resource_library.food_seed
"""
import json
import logging
from pathlib import Path
from .database import initialize_db, insert_resource, resource_exists, get_resource_count

logger = logging.getLogger(__name__)

_SEEDS_FILE = Path(__file__).parent / "seeds" / "food_resources_batch1.json"

# Stable referral/navigation resources that stay 'verified'.
# Direct pantry/meal sites are all set to 'needs_review' regardless of source value.
_STABLE_REFERRAL_KEYS = {
    ("Los Angeles Regional Food Bank", "Pantry Locator"),
    ("Los Angeles County / 211LA / LA Regional Food Bank", "Food assistance guidance"),
    ("211LA", "Food resources referral line"),
    ("California WIC", "California WIC / StartWIC"),
    ("Los Angeles Regional Food Bank / LA County / City of LA", "Senior meals referral line"),
}

# Resources with suspicious or incomplete address data — add needs_address_verification tag
_NEEDS_ADDRESS_VERIFICATION = {
    "Inland Valley Hope Partners",   # "209 W Peral Suite 103 Ave" is likely a typo
    "First Church of the Nazarene of Pasadena",  # ZIP is blank
}

# Columns that exist in the resource_library schema (excludes id / created_at / updated_at)
_SCHEMA_COLUMNS = {
    "provider_name", "service_name", "display_name", "primary_category",
    "secondary_categories", "pathways", "tags", "description",
    "services_offered", "people_served", "eligibility", "documents_required",
    "cost", "languages", "phone", "email", "website", "locations",
    "coverage_area", "cmsx_notes", "verification_status", "source",
    "source_url", "active",
}


def _normalize(resource: dict) -> dict:
    """
    Apply normalization rules and return a clean dict ready for insert_resource.
    - Enforces verification_status rules (verified only for stable referral resources)
    - Adds needs_address_verification tag where flagged
    - Appends import metadata to cmsx_notes
    - Strips fields not in the DB schema
    """
    rec = dict(resource)
    key = (rec.get("provider_name", ""), rec.get("service_name", ""))

    # Verification status: verified only for stable referral/navigation resources
    rec["verification_status"] = (
        "verified" if key in _STABLE_REFERRAL_KEYS else "needs_review"
    )

    # Address verification flag
    if rec.get("provider_name") in _NEEDS_ADDRESS_VERIFICATION:
        tags = list(rec.get("tags") or [])
        if "needs_address_verification" not in tags:
            tags.append("needs_address_verification")
        rec["tags"] = tags

    # Enforce primary_category
    rec["primary_category"] = "food_support"

    # Enrich cmsx_notes with import metadata so it's preserved in the DB
    meta_parts = []
    for field in ("verification_confidence", "import_recommendation", "reason"):
        if rec.get(field):
            meta_parts.append(f"{field}: {rec[field]}")
    if rec.get("verification_source_urls"):
        urls = rec["verification_source_urls"]
        meta_parts.append(f"verification_source_urls: {urls}")
    if meta_parts:
        base = (rec.get("cmsx_notes") or "").rstrip()
        rec["cmsx_notes"] = base + "\n\n[Import metadata] " + " | ".join(meta_parts)

    # Strip any fields not in the schema to avoid INSERT errors
    return {k: v for k, v in rec.items() if k in _SCHEMA_COLUMNS}


def run_seed() -> dict:
    """
    Import food resources batch 1.
    Skips records that already exist (matched by provider_name + service_name).
    Returns a summary dict.
    """
    initialize_db()

    if not _SEEDS_FILE.exists():
        msg = f"Seeds file not found: {_SEEDS_FILE}"
        logger.error(msg)
        return {"error": msg, "inserted": 0, "skipped": 0, "verified": 0,
                "needs_review": 0, "suspicious_records": [], "errors": [msg], "total_in_db": 0}

    with open(_SEEDS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("resources", [])
    inserted = 0
    skipped = 0
    verified_count = 0
    needs_review_count = 0
    suspicious: list = []
    errors: list = []

    for resource in resources:
        provider = resource.get("provider_name", "")
        service = resource.get("service_name", "")
        display = resource.get("display_name") or f"{provider} - {service}"

        try:
            if resource_exists(provider, service):
                logger.info(f"Skipping existing: {display}")
                skipped += 1
                continue

            rec = _normalize(resource)

            # Track records with suspicious or incomplete data
            tags = rec.get("tags") or []
            flag_tags = [t for t in tags if t.startswith("needs_")]
            if flag_tags:
                suspicious.append({"name": display, "flags": flag_tags})

            insert_resource(rec)

            if rec["verification_status"] == "verified":
                verified_count += 1
            else:
                needs_review_count += 1

            logger.info(f"Imported [{rec['verification_status']}]: {display}")
            inserted += 1

        except Exception as e:
            msg = f"Error importing {display}: {e}"
            logger.error(msg)
            errors.append(msg)

    total = get_resource_count()
    return {
        "inserted": inserted,
        "skipped": skipped,
        "verified": verified_count,
        "needs_review": needs_review_count,
        "suspicious_records": suspicious,
        "errors": errors,
        "total_in_db": total,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_seed()
    print(json.dumps(result, indent=2))
