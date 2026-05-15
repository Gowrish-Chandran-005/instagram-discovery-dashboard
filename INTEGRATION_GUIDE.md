# Instagram Discovery & Extraction Pipeline - Integration Guide

## Overview

The system now features a complete integrated pipeline with three modular components:

```
Discovery Module
       ↓ (duckduckgo_instagram_discovery.py)
   discovered_profiles.json
       ↓
Orchestration Module
       ↓ (batch_discovery_and_extraction.py)
       ├─→ Loads discovered usernames
       ├─→ Extracts metadata for each
       ├─→ Applies rate limiting (3-6s delays)
       └─→ Saves to extracted_profiles.json
       ↓
Extraction Results
   (extracted_profiles.json)
```

## Components

### 1. Discovery Module: `duckduckgo_instagram_discovery.py`

**Purpose**: Find Instagram profiles matching a keyword

**Features**:
- DuckDuckGo search with pagination (up to 5 pages)
- Random 2-5 second delays between page requests
- Smart stop: halts if no new profiles found
- Deduplication across all pages
- Per-page and cumulative statistics

**Usage**:
```bash
python duckduckgo_instagram_discovery.py
```

**Output**: `discovered_profiles.json`
```json
{
  "timestamp": "2026-05-14T...",
  "method": "duckduckgo",
  "count": 25,
  "usernames": ["@user1", "@user2", ...]
}
```

**Console Output Example**:
```
========================================================================
PAGE 1
========================================================================
[STATS] Page 1 Results:
  → Profiles found on page: 15
  → New profiles (not seen before): 15
  → Cumulative total: 15

[STATS] Page 2 Results:
  → Profiles found on page: 18
  → New profiles (not seen before): 12
  → Cumulative total: 27
```

---

### 2. Extraction Module: `demo_playwright_extract.py`

**Purpose**: Extract structured metadata from individual Instagram profiles

**Key Functions**:
- `extract_instagram_profile(page, username)` - Main orchestrator
- Uses 4-method priority cascade:
  1. JSON-LD structured data
  2. OpenGraph meta tags
  3. Internal page state
  4. DOM fallback selectors

**Extracted Fields**:
- `username` - Profile username
- `bio` - Profile biography
- `followers` - Follower count (parsed, normalized)
- `following` - Following count
- `posts` - Post count
- `website` - Profile website URL
- `profile_image` - Profile picture URL
- `extraction_methods` - Methods used (for debugging)
- `field_sources` - Source of each field (for verification)
- `_timing` - Page load and extraction duration

**Features**:
- Professional colored logging (INFO, SUCCESS, WARNING, FAILED)
- Timing measurements
- Error recovery (falls back through methods)
- Meta tag bio cleaning (removes follower counts)

---

### 3. Orchestration Module: `batch_discovery_and_extraction.py` (NEW)

**Purpose**: Tie discovery and extraction together with batch processing

**Architecture**:
- Imports functions from `demo_playwright_extract.py`
- Loads discovered usernames from `discovered_profiles.json`
- Extracts metadata for each username
- Applies rate limiting (3-6s random delays)
- Saves results to `extracted_profiles.json`
- Prints professional summary statistics

**Key Functions**:
- `load_discovered_profiles()` - Load usernames from discovery JSON
- `extract_batch_profiles()` - Extract metadata for all usernames
- `save_extracted_profiles()` - Save results to JSON
- `print_final_summary()` - Print batch statistics
- `run_batch_pipeline()` - Main orchestrator

**Features**:
- Single browser instance for efficiency
- Progress indicators: `[3/25] Extracting @username...`
- Formatted profile output with separators
- Graceful error handling (skips failed profiles)
- Professional colored terminal output
- Extraction timing per profile
- Final summary with success rate

---

## Usage Workflow

### Step 1: Run Discovery

Find Instagram profiles using DuckDuckGo search:

```bash
python duckduckgo_instagram_discovery.py
```

Enter a keyword: `photographers`

Output: `discovered_profiles.json` (e.g., 25 usernames)

**Expected Output**:
```
========================================================================
INSTAGRAM PROFILE DISCOVERY VIA DUCKDUCKGO (PAGINATED)
========================================================================
Enter discovery keyword (e.g. posters): photographers

[INFO] Searching DuckDuckGo for: site:instagram.com photographers
[INFO] Scraping up to 5 pages with random 2-5 second delays...

[STATS] Page 1 Results:
  → Profiles found on page: 15
  → New profiles (not seen before): 15
  → Cumulative total: 15

[INFO] Rate limiting: waiting 3.42s...

[STATS] Page 2 Results:
  → Profiles found on page: 18
  → New profiles (not seen before): 12
  → Cumulative total: 27

[SUCCESS] Saved 27 usernames to discovered_profiles.json
```

### Step 2: Run Batch Extraction

Extract metadata for all discovered profiles:

```bash
python batch_discovery_and_extraction.py
```

Output: `extracted_profiles.json` (full profiles with metadata)

**Expected Output**:
```
================================================================================
INSTAGRAM PROFILE DISCOVERY & EXTRACTION PIPELINE
================================================================================

[INFO] Phase 1: Loading discovered profiles...
[SUCCESS] Loaded 27 discovered usernames

[INFO] Phase 2: Launching browser and extracting metadata...

================================================================================
BATCH EXTRACTION PHASE
================================================================================

[1/27] Extracting @photographer1...
[SUCCESS] Extracted @photographer1 in 7.23s

[1/27] PROFILE: @photographer1
--------------------------------------------------------------------------------
  Username:          photographer1
  Bio:               Professional landscape and portrait photography
  Followers:        45,230
  Following:        1,203
  Posts:            523
  Website:          https://photographer1.com
  Profile Image:    https://instagram.fcom/...
  Extraction Methods: meta_tags, dom_fallback
  Page Load Time:    6.51s
  Extraction Time:   0.72s
--------------------------------------------------------------------------------

[INFO] Rate limiting: waiting 4.15s before next extraction...

[2/27] Extracting @photographer2...
[SUCCESS] Extracted @photographer2 in 6.89s

...

================================================================================
BATCH PROCESSING SUMMARY
================================================================================

Discovery Phase:
  Total profiles discovered:    27

Extraction Phase:
  Total extracted successfully: 25
  Total extraction failures:    2
  Success rate:                 92.6%

Successfully Extracted (25):
   1. @photographer1
   2. @photographer2
   ... (23 more)

Failed Extractions (2):
   1. @private_account
   2. @deleted_account

================================================================================
```

### Step 3: Access Results

**File**: `extracted_profiles.json`

**Structure**:
```json
{
  "timestamp": "2026-05-14T12:34:56.789Z",
  "discovery_method": "duckduckgo",
  "extraction_count": 25,
  "usernames_extracted": ["@photographer1", "@photographer2", ...],
  "profiles": [
    {
      "username": "photographer1",
      "bio": "Professional landscape photography",
      "followers": 45230,
      "following": 1203,
      "posts": 523,
      "website": "https://photographer1.com",
      "profile_image": "https://instagram.fcom/...",
      "extraction_methods": ["meta_tags", "dom_fallback"],
      "field_sources": {
        "username": "meta_tags",
        "bio": "meta_tags",
        "followers": "meta_tags",
        ...
      },
      "_timing": {
        "page_load_seconds": 6.51,
        "extraction_seconds": 0.72
      }
    },
    ...
  ]
}
```

---

## Architecture Diagram

```
User Interaction Flow:
========================

1. Keyword Input
   ↓
2. duckduckgo_instagram_discovery.py
   ├─ Searches DuckDuckGo (5 pages)
   ├─ Filters Instagram profiles
   ├─ Deduplicates usernames
   └─ Outputs: discovered_profiles.json (25 usernames)
   ↓
3. batch_discovery_and_extraction.py
   ├─ Loads discovered_profiles.json
   ├─ For each username (with 3-6s delays):
   │  ├─ Create browser page
   │  ├─ Call extract_instagram_profile()
   │  │  ├─ Extract JSON-LD
   │  │  ├─ Extract meta tags
   │  │  ├─ Extract internal state
   │  │  └─ Extract DOM fallback
   │  ├─ Merge all methods
   │  ├─ Print formatted profile
   │  └─ Close page
   ├─ Collect success/failure stats
   └─ Outputs: extracted_profiles.json (25 profiles)
   ↓
4. Results Ready
   ├─ extracted_profiles.json (structured data)
   ├─ Console summary (success rate, timing)
   └─ Ready for storage/API/display
```

---

## Rate Limiting

**Discovery Phase** (duckduckgo_instagram_discovery.py):
- Random 2-5 second delays between page requests
- Prevents DuckDuckGo rate limiting

**Extraction Phase** (batch_discovery_and_extraction.py):
- Random 3-6 second delays between profile extractions
- Reduces Instagram server load
- Professional behavior (not aggressive scraping)

---

## Error Handling

**Discovery Phase**:
- Failed page loads: Gracefully stop pagination
- No links found: Print warning, stop
- Parse errors: Continue with available data

**Extraction Phase**:
- Failed profile extraction: Skip profile, continue batch
- Page load timeout: Try extraction with available data
- Network error: Log and skip profile
- Each profile wrapped in try-except for resilience

**Final Summary**:
- Shows which profiles failed
- Calculates success rate
- Allows iterative retry/refinement

---

## Modular Reusability

Each component can be used independently:

```python
# Use just discovery
python duckduckgo_instagram_discovery.py
# Output: discovered_profiles.json

# Use just extraction (single profile)
python demo_playwright_extract.py
# Prompts for username, extracts

# Use batch processing
python batch_discovery_and_extraction.py
# Discovery JSON → Extraction JSON
```

Or import functions in your code:

```python
from demo_playwright_extract import extract_instagram_profile
from batch_discovery_and_extraction import load_discovered_profiles

profiles = load_discovered_profiles('discovered_profiles.json')
# ... use extract_instagram_profile() in custom logic
```

---

## Performance Characteristics

**Discovery Phase** (per keyword):
- 5 pages × ~30 results = ~150 requests parsed
- Total time: ~15-25 seconds (with 2-5s delays)
- Output: ~20-30 unique profiles

**Extraction Phase** (per profile):
- Page load: 5-10 seconds
- Extraction: 0.5-1 second
- Rate limited delay: 3-6 seconds
- **Total per profile: 8-17 seconds**

**Batch Example** (25 profiles):
- 25 profiles × 10s average = ~250 seconds
- With overhead: ~5-10 minutes total

---

## Next Steps

### Ready to implement:

1. **Flask API Integration**
   - GET /search?q=keyword → runs discovery + extraction
   - GET /profile?username=username → single extraction
   - POST /batch → accept list of usernames

2. **MongoDB Persistence**
   - Store extracted profiles with deduplication
   - Query by username, follower range, keyword
   - Run history logging

3. **Frontend Dashboard**
   - Search bar for keyword input
   - Profile cards with images, stats
   - Real-time progress indicators
   - Export results

4. **Advanced Filtering**
   - Filter results by follower count
   - Sort by engagement, growth
   - Save searches for monitoring

---

## Logging & Debugging

**Console Output**:
- Color-coded status messages (INFO, SUCCESS, WARNING, FAILED)
- Progress indicators with counters
- Timing information per operation
- Error messages with stack traces

**File Logging**:
- `updation.txt` - Run history from demo_playwright_extract.py
- `discovered_profiles.json` - Discovery results
- `extracted_profiles.json` - Extraction results

**Debug Mode** (future enhancement):
- Add `--debug` flag to print detailed extraction steps
- Save HTML snapshots of failed pages
- Log all extraction methods' results separately

---

## Faculty Demonstration Notes

**Best Practices**:

1. **Discovery Phase**:
   - Use specific keywords: "photographers", "designers", "content creators"
   - 5-page search typically finds 20-30 profiles
   - Total time: 15-25 seconds (impressive pagination demo)

2. **Extraction Phase**:
   - Non-headless browser shows real Instagram loading
   - Progress counter builds confidence (1/25, 2/25, etc.)
   - Profile formatting shows professional data extraction
   - Final summary demonstrates success rate

3. **Talking Points**:
   - "This demonstrates three independent, reusable modules..."
   - "Discovery uses paginated search with rate limiting..."
   - "Extraction prioritizes structured data over fragile DOM selectors..."
   - "Final JSON has full profiles for API/storage integration..."

---

## Files in This Pipeline

```
📁 instagram-discovery-dashboard/
├── duckduckgo_instagram_discovery.py    (Discovery Module)
├── demo_playwright_extract.py           (Extraction Module)
├── batch_discovery_and_extraction.py    (Orchestration Module) ← NEW
├── discovered_profiles.json             (Discovery Output)
├── extracted_profiles.json              (Final Results) ← NEW
├── updation.txt                         (Run History)
├── extractor/
│   ├── parser_utils.py
│   └── [other extraction helpers]
└── tests/
    └── test_profiles.py
```

---

## Version History

- **v1.0** - Single profile extraction (demo_playwright_extract.py)
- **v2.0** - DuckDuckGo discovery with pagination (duckduckgo_instagram_discovery.py)
- **v3.0** - Batch orchestration integration (batch_discovery_and_extraction.py) ← CURRENT

