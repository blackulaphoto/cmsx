# SAMHSA FindTreatment.gov Importer Runbook

## Source

**API:** `POST https://findtreatment.gov/locator/listing`
**robots.txt:** `User-agent: *  Disallow:` (empty Disallow — all paths allowed)
**Auth:** None. Federal public domain data (17 U.S.C. § 105).

Request body (form-encoded):

| Param | Required | Notes |
|---|---|---|
| `sType` | yes | `SA` (substance abuse), `MH` (mental health), `BOTH` |
| `sAddr` | yes | `lat,long` center point for radius search |
| `distance` | yes | Miles radius |
| `pageSize` | yes | Records per page |
| `page` | yes | 1-based page number |
| `sort` | yes | `0` (default) |

## DB target

`databases/virgil_st_dev.db` → `treatment_centers` table

The importer adds three optional columns on first run:
- `source_name TEXT`
- `source_url TEXT`
- `image_url TEXT`

These are added via `ALTER TABLE ADD COLUMN` (safe — idempotent if columns already exist).

## Importer modes

### 1. Dry run (default — no DB writes)

```bash
python -m backend.modules.medical.importer_samhsa
# or explicitly:
python -m backend.modules.medical.importer_samhsa --dry-run
```

Fetches 2 pages (50 records) from the SAMHSA API, normalizes, filters, dedupes,
and prints a detailed inspection report. No DB writes occur.

Report includes:
- API total count and filter summary (included / excluded with reason counts)
- All excluded records listed with their exclusion reason
- First N would-insert rows with name, type, city, phone, website, insurance flags,
  population, Joint Commission flag, services, and source URL
- DB row count before (read-only) and confirmation of no writes

**Dry-run flags:**

| Flag | Default | Description |
|---|---|---|
| `--sample-size N` | 10 | Number of would-insert rows to show in the report |
| `--include-court-programs` | off | Also show/include DUI / court-evaluation programs |

```bash
# Show 20 sample rows in dry-run
python -m backend.modules.medical.importer_samhsa --dry-run --sample-size 20

# Include court/DUI programs in the dry-run report (for inspection)
python -m backend.modules.medical.importer_samhsa --dry-run --include-court-programs
```

### 2. Offline fixture mode (for tests / offline work)

```bash
python -m backend.modules.medical.importer_samhsa \
  --fixture backend/modules/medical/fixtures/samhsa_sample.json
```

Reads the local fixture JSON, normalizes, filters, dedupes against an empty
baseline, and prints all qualifying rows as JSON. Does not touch the DB.

### 3. Small capped import (approved rows only)

```bash
python -m backend.modules.medical.importer_samhsa --import-mode
# Default: max 2 pages × 25 rows = 50 rows fetched; max 50 inserted.
```

With custom caps:

```bash
python -m backend.modules.medical.importer_samhsa \
  --import-mode \
  --max-pages 4 \
  --page-size 25 \
  --max-rows 100
```

Prints DB path, pre-import count, and post-import count before exiting.

### 4. Large import (requires explicit flag)

```bash
python -m backend.modules.medical.importer_samhsa \
  --import-mode \
  --max-pages 20 \
  --max-rows 500 \
  --confirm-large-import
```

`--confirm-large-import` is required when `--max-rows > 200`. This prevents
accidental large imports.

**Do not run a large import in this PR.** Await explicit approval from Brandon.

## Inspect counts before / after

```bash
# Before
python -c "
import sqlite3; conn = sqlite3.connect('databases/virgil_st_dev.db')
print('total:', conn.execute('SELECT COUNT(*) FROM treatment_centers').fetchone()[0])
print('samhsa:', conn.execute(\"SELECT COUNT(*) FROM treatment_centers WHERE source_name='SAMHSA FindTreatment.gov'\").fetchone()[0])
"

# Run dry-run to see net new count
python -m backend.modules.medical.importer_samhsa --dry-run

# After import
python -c "
import sqlite3; conn = sqlite3.connect('databases/virgil_st_dev.db')
print('total:', conn.execute('SELECT COUNT(*) FROM treatment_centers').fetchone()[0])
print('samhsa:', conn.execute(\"SELECT COUNT(*) FROM treatment_centers WHERE source_name='SAMHSA FindTreatment.gov'\").fetchone()[0])
"
```

## Exclusion reasons

The importer categorizes excluded records into three buckets:

| Reason | Meaning |
|---|---|
| `non_qualifying_setting` | SET field contains only "Regular outpatient treatment" / "Brief intervention" — too broad (primary-care offices, etc.) |
| `wrong_facility_type` | `typeFacility` is not `SA` — mental-health-only facility |
| `court_or_dui_program` | Name signals a court-mandated DUI/evaluation program without residential or detox settings |

The court/DUI filter **does not** exclude facilities that merely serve justice-involved clients
(a legitimate clinical treatment population). It only excludes records whose name strongly signals
they are court compliance / evaluation programs (e.g., "Escuela Latina — Evaluaciones Alcohol Drugs").
Facilities with residential or detox settings are never excluded by this filter, even if the name
contains DUI/court signals.

Use `--include-court-programs` to bypass the court/DUI filter and see those records in reports
or include them in an import.

## Why the result count is high (and how it's handled safely)

The SAMHSA API reports ~12,000+ SA facilities within 10 miles of downtown LA.
This is suspicious for a CMSX directory that currently has 29 treatment center
rows. Likely causes:

1. **Broad outpatient offices:** Primary care and counseling offices that offer
   brief SUD screening are included by SAMHSA. The importer **filters these out**:
   records whose SET block contains only "Regular outpatient treatment" or
   "Brief intervention" are excluded.

2. **Court/DUI programs:** Some IOP-qualified facilities are primarily DUI evaluation
   or driver-education programs, not clinical treatment centers. The importer
   **filters these out** by default via name-pattern matching.

3. **Duplicate reporting:** Some facilities report the same address under multiple
   program names. The importer dedupes by `frid` (SAMHSA's unique SHA256 hash per
   facility) and by normalized name + city as a fallback.

4. **MH crossover:** When using `sType=BOTH`, SAMHSA merges SA and MH facilities.
   v1 imports `sType=SA` only.

5. **Hard caps:** Default mode inserts at most 50 rows across 2 pages. Exceeding
   200 requires `--confirm-large-import`.

Even after filtering, expect 40–60% of raw rows to qualify. A 25-mile radius
full import is a future-phase decision, not part of this PR.

## What is NOT in v1

- `sType=MH` (mental health facilities) — excluded
- `sType=BOTH` — excluded
- Full 25-mile import (12K+ records) — requires Brandon's explicit approval
- Patient reviews or copyrighted descriptions — SAMHSA data is factual/public domain
- Image/logo enrichment — SAMHSA API provides no image URLs; frontend uses icon fallback
- Automatic scheduling or cron — import is run manually

## Safety rules

- Never commit `databases/virgil_st_dev.db`
- Never commit large SAMHSA API dumps (keep fixtures to 5–10 sample rows)
- Never run `--import-mode` against production without Brandon's approval
- Do not change Railway, Vercel, or env settings
- Do not use `git add .`

## Running tests

```bash
python -m pytest backend/modules/medical/test_importer_samhsa.py -v
```
