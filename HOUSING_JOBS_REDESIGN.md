# Housing & Jobs Module Redesign
## From "Scrape Everything" to "What Case Managers Actually Do"

---

## **Problem Statement**

### Current Approach (DOESN'T MATCH REALITY):
- **Jobs**: Scraping thousands of individual job listings from multiple sites
- **Housing**: Searching for individual apartments/rentals
- **Result**: Overwhelming data, slow searches, maintenance nightmare

### What Case Managers Actually Do:
- **Jobs**: Generate search URLs (Craigslist, Indeed, etc.) and send to clients
- **Housing**: Find sober living homes and housing assistance programs (NOT apartment hunting)

---

## **Proposed Solution**

### **Jobs Module - Simplified**

#### What We Keep:
✅ Background-friendly employer database (Goodwill, Homeboy Industries, etc.)
✅ Job application tracking (what client applied for)

#### What We Change:
❌ **Remove**: Complex scrapers for Indeed, Glassdoor, Craigslist, etc.
✅ **Add**: URL generator that creates search links

#### New Job Workflow:
```
Case Manager enters: "warehouse jobs"
↓
System generates:
- Craigslist URL: https://losangeles.craigslist.org/search/jjj?query=warehouse
- Indeed URL: https://www.indeed.com/jobs?q=warehouse&l=Los+Angeles
- ZipRecruiter URL: https://www.ziprecruiter.com/jobs-search?search=warehouse
- LinkedIn URL: https://www.linkedin.com/jobs/search/?keywords=warehouse
- Background-friendly searches (adds "second chance" keywords)
- Known background-friendly employers list
↓
Case Manager texts/emails URLs to client
Client applies directly
↓
Case Manager tracks applications in system
```

**Benefits:**
- ⚡ Instant results (no scraping delays)
- 🔄 Always fresh (clients see real-time job boards)
- 🛠️ Zero maintenance (no broken scrapers)
- ✅ Matches real workflow

---

### **Housing Module - Simplified**

#### What Case Managers ACTUALLY Look Up:

1. **Sober Living Homes** (337 in database!)
   - Men's homes (215)
   - Women's homes (89)
   - Coed homes (33)
   - Filter by: gender, city, payment options (Medi-Cal accepted)

2. **Housing Assistance Programs**
   - Section 8 vouchers
   - Emergency housing vouchers
   - CalWORKs housing assistance
   - HOPWA (for HIV+ clients)
   - Coordinated Entry System (CES)

#### What Case Managers DON'T Do:
❌ Apartment hunting for clients
❌ Calling landlords
❌ Scheduling apartment viewings

#### New Housing Workflow:
```
Client needs sober living:
↓
Case Manager searches: Gender=Male, City=Long Beach, Accepts Medi-Cal
↓
System shows: 12 matching sober living homes with phone numbers
↓
Case Manager calls homes, makes referrals
```

**OR**

```
Client needs housing assistance:
↓
Case Manager searches: "Section 8"
↓
System shows: HACLA, LACDA, Emergency Vouchers, etc.
↓
Case Manager helps client apply to programs
```

---

## **Database Resources Available**

### From Virgil St Database:

**Sober Living Homes: 337**
- Full addresses, phone numbers
- Gender served (men/women/coed)
- Payment options (Medi-Cal, Medicare, private insurance)
- Services and amenities

**Housing Programs: 10+**
- Section 8 Housing Choice Voucher (LACDA, HACLA)
- Emergency Housing Vouchers (EHV)
- CalWORKs Homeless Assistance
- Housing for Health (LA County DHS)
- HOPWA (HIV/AIDS housing)

**Background-Friendly Employers: 7+**
- Goodwill Industries
- Homeboy Industries
- Amazon Warehouses
- Walmart
- Dave's Killer Bread
- And more...

---

## **Implementation Files**

### New Files Created:

1. **`backend/modules/jobs/simple_job_tools.py`**
   - `JobSearchURLGenerator` - Generates search URLs for all major job boards
   - `BackgroundFriendlyEmployerList` - Known employers who hire with records
   - `get_job_search_resources()` - Main function for case managers

2. **`backend/modules/housing/simple_housing_tools.py`**
   - `HousingResourceTools` - Queries Virgil St database
   - `search_sober_living()` - Find sober living homes by gender/location
   - `search_housing_programs()` - Find Section 8, vouchers, assistance programs
   - `get_housing_search_urls()` - Optional apartment search URLs

### Files to Deprecate:
- `backend/modules/jobs/scrapers/*` (all scrapers)
- `backend/modules/jobs/jobs_cse_integration.py`
- `backend/modules/housing/search/housing_cse_integration.py`

---

## **API Endpoint Changes**

### Jobs Endpoints:

**NEW (Recommended):**
```
GET /api/jobs/search/urls?keywords=warehouse&location=Los Angeles
→ Returns search URLs + background-friendly employers

POST /api/jobs/applications
→ Track what client applied for
```

**DEPRECATED:**
```
POST /api/jobs/search (async scraping)
GET /api/jobs/search/scrapers (scraper results)
```

### Housing Endpoints:

**NEW (Recommended):**
```
GET /api/housing/sober-living?gender=men&city=Long Beach
→ Returns sober living homes from database

GET /api/housing/programs?keywords=section 8
→ Returns housing assistance programs
```

**DEPRECATED:**
```
GET /api/housing/search (apartment searches via CSE)
```

---

## **Testing Results**

### Job Tools Test:
```
✅ Generated 6 search URLs (Craigslist, Indeed, ZipRecruiter, LinkedIn, Monster, USAJobs)
✅ Listed 7 background-friendly employers
✅ Instant response (<100ms vs 10+ seconds for scraping)
```

### Housing Tools Test:
```
✅ Found 215 men's sober living homes
✅ Found 89 women's sober living homes
✅ Found 9 housing assistance programs (Section 8, vouchers, etc.)
✅ Fast database queries (<50ms)
```

---

## **Migration Strategy**

### Phase 1: Add New Tools (No Breaking Changes)
- Deploy new job URL generator alongside existing scrapers
- Deploy new housing sober living search alongside existing searches
- A/B test with case managers

### Phase 2: Update Frontend
- Add "Get Job Search Links" button → calls new URL generator
- Add "Sober Living" tab → shows database results
- Add "Housing Programs" tab → shows assistance programs
- Keep old features for comparison

### Phase 3: Deprecate Old Tools
- Remove scraper code once new tools proven
- Archive CSE integration code
- Clean up unused dependencies

---

## **Next Steps**

1. **Review this proposal** - Does this match your workflow?
2. **Update routes** - Wire new tools into existing endpoints
3. **Update frontend** - Show search URLs and sober living results
4. **Test with real case managers** - Get feedback
5. **Deprecate old code** - Remove scrapers and CSE searches

---

## **Questions for Review**

1. ✅ Jobs: Should we generate search URLs instead of scraping?
2. ✅ Housing: Should we focus on sober living + programs (not apartments)?
3. ✅ Should we keep application tracking (what client applied for)?
4. ❓ Any other workflows I'm missing?

---

**Bottom Line:**
Make the system match how case managers actually work, not how software engineers think they should work.
