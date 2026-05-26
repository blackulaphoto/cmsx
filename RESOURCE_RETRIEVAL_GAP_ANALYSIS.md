# Resource Retrieval Gap Analysis & Fix Plan

## Problem Statement

**User Query:** "need a 7 day detox for a client then we need a residential treatment center for them after in los angeles"

### Current CMSX AI Response (FAILING)
- Arise Recovery Center (Thousand Oaks - **NOT LA**)
- All About Change Recovery (sober living, **NOT detox**)
- Bran Life Recovery (Orange County - **NOT LA**)
- 211 LA (generic referral - **NOT a provider**)

### Case Manager GPT Response (BENCHMARK)
**Detox/Residential:**
- Milton Recovery Centers (LA-based detox)
- Muse Treatment (LA-based detox + residential)
- Westwind Recovery (LA-based residential)

**MAT/Suboxone:**
- Saban Community Clinic
- St. John's Community Health
- JWCH Institute (Wesley Health Centers)
- Bicycle Health (telehealth)

---

## Root Cause Analysis

### Discovery 1: Knowledge Files EXIST But Aren't Being Used

**Evidence:**
```bash
# suboxone clinics.txt contains:
- JWCH Institute / Wesley Health Centers ✓
- Saban mentioned in dental/community resource list ✓
- St. John's Community Health ✓
- Mariposa Detox Center ✓
```

**The data is there. The system isn't loading/using it properly.**

### Discovery 2: Multiple Competing Search Systems

**Current Architecture Has 3 Different Search Paths:**

1. **Curated Resource Retrieval Engine** (NEW - what we just built)
   - Location: `backend/modules/resources/retrieval_engine.py`
   - Loads: Knowledge files, trusted providers
   - Status: ✅ Built, ⚠️ Not being called properly

2. **Virgil ST Database** (EXISTING)
   - Location: `backend/modules/services/virgil_db_service.py`
   - Searches: `virgil_st_dev.db` (treatment_centers, resources, medi_cal_providers, meetings)
   - Status: ✅ Being called FIRST, blocking our curated engine

3. **Web Search Coordinator** (EXISTING)
   - Location: `backend/search/coordinator.py`
   - Searches: External APIs (Google, Yelp, etc.)
   - Status: ✅ Being used, returning weak matches

**The Problem:**
```python
# unified_service.py line 1572-1578
curated_context = await self._build_curated_resource_context(message, location)
if curated_context:
    logger.info("Using curated resource retrieval engine")
    return curated_context

# Fallback to existing search
internal_results = await self.search_internal_resources(combined_text, location, limit=8)
```

**The curated engine returns context, but then `search_internal_resources()` is ALSO being called as an AI tool (line 1225), which searches Virgil DB + web search FIRST.**

### Discovery 3: Knowledge Loader Isn't Parsing Text Files Properly

**Current Code:**
```python
# knowledge_loader.py
def _parse_provider_text_file(self, file_path: Path, service_type: str, subtypes: List[str]):
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    entries = self._split_provider_entries(content)

    for entry in entries:
        provider = self._extract_provider_from_text(entry, service_type, subtypes)
```

**Problem:**
- `suboxone clinics.txt` uses numbered lists with markdown formatting
- `_split_provider_entries()` tries numbered pattern but gets confused by markdown
- `_extract_provider_from_text()` uses regex that misses formatted lists

**Example from suboxone clinics.txt:**
```markdown
1. **Wesley Health Centers – Skid Row / San Pedro St (JWCH Institute)**
   - Website: https://wesleyhealthcenters.com
   - Phone: (562) 867‑7999
   - Payment: Medi‑Cal, some commercial insurance
```

**Current parser:**
- Sees "1. **Wesley..." as name
- Extracts phone ✓
- Misses website (markdown link format)
- Misses insurance details (bullet format)

---

## The Fix Plan

### Phase 1: Enhance Knowledge File Parsing (HIGH PRIORITY)

**File:** `backend/modules/resources/knowledge_loader.py`

**Changes Needed:**

1. **Better Markdown Parsing:**
```python
def _parse_markdown_provider_list(self, file_path: Path, service_type: str):
    """
    Parse numbered markdown lists like:
    1. **Provider Name**
       - Website: URL
       - Phone: (123) 456-7890
       - Services: List
    """
    # Use regex to find numbered entries
    # Extract name from **bold**
    # Extract all bullet points
    # Map bullets to provider fields
```

2. **Structured Field Mapping:**
```python
FIELD_PATTERNS = {
    'phone': r'Phone:\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',
    'website': r'Website:\s*(https?://[^\s]+)',
    'services': r'Services:\s*(.+)',
    'payment': r'Payment:\s*(.+)',
    'address': r'Address:\s*(.+)',
}
```

3. **Insurance Extraction:**
```python
def _extract_insurance_from_text(self, text: str) -> List[str]:
    """
    Extract from:
    - "Payment: Medi-Cal, commercial insurance"
    - "Insurance: Medicare, Medi-Cal"
    - "Accepts: BCBS, Anthem"
    """
```

### Phase 2: Prioritize Curated Retrieval Over Virgil DB

**File:** `backend/modules/ai_unified/unified_service.py`

**Current Problem:**
```python
# Tool definition (line 1225)
{
    "name": "search_internal_resources",
    "description": "PRIMARY TOOL. Search internal verified local programs...",
}
```

This calls `search_internal_resources()` → `virgil_db` → web search.
Our curated engine is only called during context building, not as a tool.

**Solution Option A: Replace Virgil DB with Curated Engine**
```python
async def search_internal_resources(self, query, location, limit=8):
    # NEW: Try curated engine first
    resource_engine = get_resource_engine()
    scored_providers = resource_engine.search(query, limit=limit)

    if scored_providers:
        # Format as existing tool output
        return self._format_curated_results(scored_providers)

    # Fallback to Virgil DB
    virgil_result = get_virgil_db().search_services(query, location, 1, limit)
    ...
```

**Solution Option B: Add Separate Curated Tool**
```python
{
    "name": "search_curated_providers",
    "description": "PREFERRED TOOL. Search curated, verified treatment/medical/housing providers with location-aware ranking. Use this FIRST before search_internal_resources.",
    "parameters": {
        "query": {"type": "string"},
        "location": {"type": "string"},
        "limit": {"type": "integer"}
    }
}
```

**Recommendation: Option A** - Replace the internals, keep same interface

### Phase 3: Expand Trusted Provider Database

**File:** `backend/modules/resources/knowledge_loader.py`

**Add Missing Providers from Case Manager GPT:**

```python
def _load_treatment_providers(self):
    trusted_providers = [
        # EXISTING
        {"name": "Muse Treatment Center", ...},
        {"name": "CRI-Help, Inc.", ...},

        # NEW - Add these from suboxone clinics.txt
        {
            "name": "JWCH Institute",
            "alternate_names": ["Wesley Health Centers"],
            "service_type": "medical",
            "service_subtypes": ["mat", "primary_care"],
            "phone": "(562) 867-7999",
            "website": "https://wesleyhealthcenters.com",
            "city": "Los Angeles",
            "neighborhood": "Downtown",
            "insurance_accepted": ["medi_cal", "sliding_scale"],
            "specializations": ["mat", "homeless", "low_income"],
            "internal_rating": 0.90,
            "is_trusted": True,
            "notes": "JWCH Institute serving Skid Row, strong MAT program"
        },
        {
            "name": "Saban Community Clinic",
            "service_type": "medical",
            "service_subtypes": ["mat", "primary_care"],
            "phone": "(323) 653-1990",
            "insurance_accepted": ["medi_cal", "sliding_scale"],
            "internal_rating": 0.90,
            "is_trusted": True,
        },
        {
            "name": "St. John's Community Health",
            "service_type": "medical",
            "service_subtypes": ["mat", "primary_care", "dental"],
            "phone": "(323) 541-1411",
            "insurance_accepted": ["medi_cal", "uninsured"],
            "internal_rating": 0.90,
            "is_trusted": True,
        },
        {
            "name": "Milton Recovery Centers",
            "service_type": "treatment",
            "service_subtypes": ["detox", "residential"],
            "city": "Los Angeles",
            "insurance_accepted": ["medi_cal", "private"],
            "internal_rating": 0.85,
            "is_trusted": True,
            "notes": "Good for short detox placement and transition to residential"
        },
    ]
```

### Phase 4: Load Text Files Properly

**Current Issue:**
```python
# knowledge_loader.py line 116-124
text_files = {
    "suboxone clinics.txt": ("treatment", ["mat", "outpatient"]),
    # ^^^ WRONG - these are MEDICAL providers, not treatment centers
}
```

**Fix:**
```python
text_files = {
    "suboxone clinics.txt": ("medical", ["mat", "primary_care"]),  # CORRECT
    "Urgent cares.txt": ("medical", ["urgent_care"]),
    "Los Angeles Free & Low-Cost Dental.txt": ("medical", ["dental"]),
}
```

### Phase 5: Add Markdown List Parser

**New Method Needed:**
```python
def _parse_numbered_markdown_list(self, file_path: Path, service_type: str) -> List[Provider]:
    """
    Parse markdown files with numbered provider lists.

    Format:
    1. **Provider Name**
       - Field: Value
       - Field: Value

    2. **Next Provider**
       ...
    """
    content = file_path.read_text(encoding='utf-8')

    # Regex to match numbered entries
    pattern = r'(\d+)\.\s*\*\*(.+?)\*\*\s*((?:^\s*-\s*.+$\n?)+)'

    providers = []
    for match in re.finditer(pattern, content, re.MULTILINE):
        number = match.group(1)
        name = match.group(2)
        details = match.group(3)

        # Parse bullet points
        fields = self._parse_bullet_points(details)

        # Create provider
        provider = Provider(
            name=name,
            service_type=service_type,
            phone=fields.get('phone'),
            website=fields.get('website'),
            services_offered=fields.get('services', []),
            insurance_accepted=self._parse_insurance(fields.get('payment', '')),
            source_file=file_path.name,
        )
        providers.append(provider)

    return providers
```

---

## Implementation Order

### ✅ DONE (from previous work)
1. Built retrieval engine architecture
2. Built location intelligence
3. Built service matcher
4. Built quality scorer
5. Integrated with unified AI

### 🔴 TO DO (this fix)

**Priority 1: Fix Knowledge File Parsing**
- [ ] Add markdown numbered list parser
- [ ] Fix service type mapping (suboxone = medical, not treatment)
- [ ] Better insurance extraction
- [ ] Parse bullet-point formatted details

**Priority 2: Add Missing Trusted Providers**
- [ ] JWCH Institute / Wesley Health Centers
- [ ] Saban Community Clinic
- [ ] St. John's Community Health
- [ ] Milton Recovery Centers
- [ ] Mariposa Detox Center

**Priority 3: Route Curated Engine Properly**
- [ ] Modify `search_internal_resources()` to call curated engine first
- [ ] Only fallback to Virgil DB if no curated matches
- [ ] Update tool description to emphasize curated providers

**Priority 4: Test Against Benchmark**
- [ ] Query: "7 day detox then residential in Los Angeles"
- [ ] Expected: Muse, Milton, Westwind
- [ ] Query: "suboxone clinics in LA"
- [ ] Expected: JWCH, Saban, St. John's

---

## Expected Outcome After Fix

**Query:** "need a 7 day detox for a client then we need a residential treatment center for them after in los angeles"

**New Response Should Include:**
1. **Milton Recovery Centers** (LA-based detox + residential transition)
2. **Muse Treatment Center** (Sherman Oaks, detox + residential continuum)
3. **Westwind Recovery** (LA-based residential)
4. **Tarzana Treatment Centers** (Tarzana, detox + dual diagnosis)

**Query:** "suboxone clinics in LA"

**New Response Should Include:**
1. **JWCH Institute / Wesley Health Centers** (Downtown, Medi-Cal)
2. **Saban Community Clinic** (Medi-Cal, integrated care)
3. **St. John's Community Health** (Medi-Cal, uninsured)
4. **BAART Programs** (Beverly, Southeast locations)
5. **LA Suboxone** (Sublocade provider)

---

## Why Current System Failed

1. **Knowledge files exist but parsing is broken**
   - Markdown formatting not handled
   - Bullet points not parsed
   - Insurance details missed

2. **Service type misclassification**
   - MAT clinics tagged as "treatment" not "medical"
   - Location scoring can't work without proper city/neighborhood

3. **Virgil DB gets called first as AI tool**
   - Curated engine only runs during context building
   - Virgil DB has incomplete/outdated data
   - Web search returns aggregators

4. **Missing trusted providers in database**
   - Milton, JWCH, Saban, St. John's not in trusted list
   - Can't get quality boost without being in trusted list

---

## Success Criteria

### Test 1: Detox + Residential Query
```
Query: "need a 7 day detox for a client then we need a residential treatment center for them after in los angeles"

Expected Top 3:
1. Milton Recovery Centers ✓
2. Muse Treatment Center ✓
3. Westwind Recovery ✓

Must NOT include:
- Arise Recovery (Thousand Oaks - too far)
- 211 LA (not a provider)
- Orange County providers
```

### Test 2: MAT/Suboxone Query
```
Query: "suboxone clinics in LA"

Expected Top 5:
1. JWCH Institute ✓
2. Saban Community Clinic ✓
3. St. John's Community Health ✓
4. BAART Programs ✓
5. LA Suboxone ✓

Must NOT include:
- Generic directories
- Orange County providers (unless LA full)
```

### Test 3: Location Filtering
```
Query: "detox in North Hollywood with Medi-Cal"

Expected:
- North Hollywood / Van Nuys providers first
- Sherman Oaks / Burbank second tier
- West LA / DTLA third tier
- Orange County last resort only

Medi-Cal accepting providers boosted
```

---

## Files That Need Changes

### 1. `backend/modules/resources/knowledge_loader.py`
- Add `_parse_numbered_markdown_list()` method
- Fix service type mapping for suboxone clinics
- Enhance insurance extraction
- Add missing trusted providers

### 2. `backend/modules/ai_unified/unified_service.py`
- Modify `search_internal_resources()` to prioritize curated engine
- Update tool description
- Remove/reduce Virgil DB priority

### 3. Test files
- Update `test_resource_retrieval.py` with new benchmark queries
- Add MAT/suboxone test cases

---

## Timeline Estimate

- **Priority 1 (Parsing)**: 2-3 hours
- **Priority 2 (Trusted Providers)**: 1 hour
- **Priority 3 (Routing)**: 1 hour
- **Priority 4 (Testing)**: 1 hour

**Total**: 5-6 hours of focused work

---

*Analysis complete - ready for implementation when approved*
