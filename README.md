# Instagram Structured Metadata Extractor

A **professional-grade**, **modular**, and **robust** Instagram profile data extraction system using industry-standard structured data methods.

## 🎯 Architecture Philosophy

This system extracts Instagram profile data using a **priority-based extraction pipeline**:

1. **JSON-LD** (if available) — W3C standard structured data
2. **Meta Tags** (usually available) — OpenGraph protocol data
3. **DOM Selectors** (fallback) — Fragile but works when others don't

## ✨ Key Features

✅ **Professional** — Uses structured data standards (JSON-LD, OpenGraph)  
✅ **Robust** — Multiple extraction methods with intelligent fallbacks  
✅ **Modular** — Clean separation of concerns across modules  
✅ **Tested** — Full test suite for all extraction functions  
✅ **Well-documented** — Clear comments and structured code  
✅ **Scalable** — Easy to extend with new extraction methods  

## 📁 Project Structure

```
instagram-discovery-dashboard/
│
├── extractor/                    # Core extraction modules
│   ├── __init__.py              # Main orchestrator
│   ├── meta_extractor.py        # OpenGraph meta tag extraction
│   ├── jsonld_extractor.py      # JSON-LD structured data extraction
│   ├── dom_fallback.py          # DOM selector fallback extraction
│   └── parser_utils.py          # Utility functions for parsing
│
├── tests/                        # Test suite
│   └── test_profiles.py         # Unit tests for all extractors
│
├── main.py                       # Main entry point / example usage
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🧭 Project Cleanup & Organization

- `archive/`: Contains experimental and phase-based scripts (archived). These files are preserved for historical context, testing notes, and reproducibility but are not active parts of the main pipeline.
- `backend/`: Backend helpers and runtime data. Runtime JSON data files are stored under `backend/data/` to keep the project root clean.
- `frontend/`: React demo app (unchanged) — calls the Flask API for demo purposes.

Core production files (kept in project root):
- `flask_api.py` - Production Flask API entrypoint (reuses the extraction pipeline).
- `batch_discovery_and_extraction.py` - Batch orchestration, reuses single Playwright browser.
- `duckduckgo_instagram_discovery.py` - DuckDuckGo discovery + extraction orchestration.
- `main.py` - Example extractor entry point.
- `README.md`, `QUICKSTART.md`, `requirements.txt` - Documentation and deps.

Notes:
- Experimental files were moved into `archive/` to declutter the root. They retain original names and full source for reference.
- Data files (`discovered_profiles.json`, `extracted_profiles.json`, `profiles.json`) were migrated to `backend/data/`. Code paths were updated so file I/O points to `backend/data/` by default.
- Frontend and `extractor/` remain untouched.


## 🚀 Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Example Extraction

```bash
python main.py
```

This will extract the @nike Instagram profile and display:
- Username
- Bio
- Followers count
- Following count
- Posts count
- Profile image URL
- Instagram URL
- Extraction methods used

### Run Tests

```bash
python tests/test_profiles.py
```

Verifies all parsing functions work correctly.

## 💻 Usage Example

```python
from playwright.sync_api import sync_playwright
from extractor import extract_instagram_profile, format_profile_output

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # Open Instagram profile
    page.goto("https://instagram.com/nike")
    page.wait_for_load_state("networkidle")
    
    # Extract profile using all methods
    profile = extract_instagram_profile(page, "nike")
    
    # Display results
    print(format_profile_output(profile))
    
    browser.close()
```

## 📊 Extracted Data Structure

```json
{
  "username": "nike",
  "bio": "See Instagram photos and videos from Nike (@nike)",
  "followers": 292000000,
  "following": 243,
  "posts": 1632,
  "profile_image": "https://...",
  "url": "https://www.instagram.com/nike",
  "website": null,
  "extraction_methods": ["meta_tags", "dom_fallback"]
}
```

## 🔧 Module Reference

### `extractor/__init__.py`
**Main orchestrator** combining all extraction methods.

Key functions:
- `extract_instagram_profile(page, username)` — Main extraction function
- `merge_profiles(*profiles)` — Intelligently merge multiple extraction results
- `format_profile_output(profile)` — Pretty-print profile data

### `extractor/meta_extractor.py`
**Extracts OpenGraph and meta tags** — MOST RELIABLE method.

Key functions:
- `extract_meta_tags(page)` — Extract all og:* and meta tags
- `parse_profile_from_meta(meta_data)` — Parse profile from meta data

### `extractor/jsonld_extractor.py`
**Extracts JSON-LD structured data** — WHEN AVAILABLE.

Key functions:
- `extract_jsonld_scripts(page)` — Find all JSON-LD scripts
- `find_person_schema(jsonld_objects)` — Locate Person schema
- `parse_profile_from_jsonld(jsonld_obj)` — Extract from schema

### `extractor/dom_fallback.py`
**DOM selector extraction** — FRAGILE but functional fallback.

Key functions:
- `extract_profile_dom_fallback(page)` — Complete DOM extraction
- `extract_username_from_dom(page)` — Username from DOM
- `extract_bio_from_dom(page)` — Bio from DOM
- `extract_stats_from_dom(page)` — Stats from DOM

### `extractor/parser_utils.py`
**Utility functions** for parsing and validation.

Key functions:
- `parse_count(count_str)` — Parse "1.2M" → 1200000
- `extract_username(text)` — Extract @username from text
- `extract_url(text)` — Extract URLs from text
- `is_valid_bio(text)` — Validate if text looks like a bio
- `clean_string(text)` — Normalize whitespace

## ⚡ Parsing Examples

```python
from extractor.parser_utils import parse_count

parse_count("1.2M followers")      # → 1200000
parse_count("42.5K")               # → 42500
parse_count("1,234")               # → 1234
parse_count("292M Followers, 243") # → 292000000
```

## 🧪 Running Tests

All utility functions are tested:

```bash
python tests/test_profiles.py
```

Output:
```
✓ parse_count() - All 5 tests passed
✓ extract_username() - All 4 tests passed
✓ extract_url() - All 3 tests passed
✓ is_valid_bio() - All 5 tests passed
✓ Output structure - Valid

✓ ALL TESTS PASSED!
```

## 📈 Why This Architecture?

### Before (Old Approach)
❌ Fragile DOM selectors break constantly  
❌ No fallback mechanisms  
❌ Hard to maintain and extend  
❌ Unreliable for production use  

### After (New Approach)
✅ Uses **W3C standard** structured data (JSON-LD)  
✅ Falls back to **OpenGraph** (widely supported)  
✅ Final fallback to **DOM selectors** (works in worst case)  
✅ Professional, maintainable, scalable  
✅ Industry best-practice approach  

## 🔒 Instagram Rate Limiting & Authentication

- **Anonymous Extraction**: Works for public profiles
- **Rate Limiting**: Instagram may limit requests
- **Login Required**: Some data hidden from anonymous users
- **Recommendation**: Add delays between requests in production

## 🚨 Known Limitations

- **Hidden Fields**: Instagram hides some data from non-authenticated users
- **Page Changes**: Instagram structure changes frequently (handled by multi-method approach)
- **Dynamic Content**: Some data loaded via JavaScript (handled via `wait_for_load_state("networkidle")`)
- **JSON-LD Availability**: Not always present in all profiles

## 📚 Academic / Professional Value

This extraction system demonstrates:
- **Structured data extraction** from web pages
- **Multi-method fallback** architecture (robust engineering)
- **Python web automation** with Playwright
- **Professional software architecture** (modular design)
- **Quality assurance** (test-driven approach)

## 🔄 Future Extensions

Easy to add:
- MongoDB storage integration
- Flask API wrapper
- Batch extraction
- Related account discovery
- Search functionality
- Data caching

## 📝 License & Notes

This is an educational tool for public profile analysis. Respect Instagram's Terms of Service.

---

**Built with:** Python, Playwright, Structured Data Standards

**Status:** ✅ Production-Ready
