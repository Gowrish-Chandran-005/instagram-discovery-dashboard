"""
Demo script: Instagram Structured Metadata Extraction

Demonstration script with stage-by-stage colored logs, timing, and
professional formatted output suitable for faculty/project demos.

Priority: JSON-LD → OpenGraph/meta → internal state → DOM fallback
Run: python demo_playwright_extract.py
"""
import os
from datetime import datetime
import json
import re
import time
import traceback
from typing import Dict, Any

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from colorama import Fore, Style, init as colorama_init

# Import the reusable bio cleaner
from extractor.parser_utils import clean_instagram_bio

# Initialize colorama for cross-platform colored output
colorama_init(autoreset=True)


def log_stage(message: str, status: str = 'INFO') -> None:
        """Print a formatted stage line with status indicator and color.

        status: one of INFO, SUCCESS, WARNING, FAILED
        """
        colors = {
                'INFO': Fore.CYAN,
                'SUCCESS': Fore.GREEN,
                'WARNING': Fore.YELLOW,
                'FAILED': Fore.RED,
        }
        color = colors.get(status, Fore.CYAN)
        label = f'[{status}]'
        print(f"{color}{label} {Style.RESET_ALL}{message}")


def parse_count(text: str) -> int | None:
    """Parse Instagram-style count strings like '1.2M', '45K', '1,234' into integers.

    Returns None when no numeric pattern is found.
    """
    if not text:
        return None
    s = str(text).strip()
    # Remove commas and surrounding words
    s = s.replace(',', '')
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([MKmk])", s)
    if m:
        num = float(m.group(1))
        mult = m.group(2).upper()
        if mult == 'M':
            return int(num * 1_000_000)
        if mult == 'K':
            return int(num * 1_000)
    # Fallback: plain integer
    m2 = re.search(r"(\d+)", s)
    if m2:
        try:
            return int(m2.group(1))
        except Exception:
            return None
    return None


def extract_jsonld(page) -> Dict[str, Any]:
    """Extract JSON-LD structured data from the page.

    Returns a dict with any of the target fields present.
    """
    log_stage("Running JSON-LD extraction...", 'INFO')
    data = {}
    try:
        scripts = page.query_selector_all("script[type='application/ld+json']")
        for s in scripts:
            try:
                text = s.text_content()
                if not text:
                    continue
                parsed = json.loads(text)
                # JSON-LD can be a list or single object
                objs = parsed if isinstance(parsed, list) else [parsed]
                for obj in objs:
                    t = obj.get('@type') or obj.get('type')
                    if isinstance(t, list):
                        t = t[0]
                    if t and t.lower() in ('person', 'profile', 'organization'):
                        # map common properties
                        if 'name' in obj and not data.get('username'):
                            data['username'] = obj.get('name')
                        if 'description' in obj and not data.get('bio'):
                            data['bio'] = obj.get('description')
                        if 'image' in obj and not data.get('profile_image'):
                            img = obj.get('image')
                            if isinstance(img, dict):
                                data['profile_image'] = img.get('url')
                            else:
                                data['profile_image'] = img
                        if 'url' in obj and not data.get('url'):
                            data['url'] = obj.get('url')
                        # JSON-LD rarely contains follower counts for Instagram
                        log_stage("JSON-LD: found structured object", 'SUCCESS')
                        return data
            except Exception:
                continue
    except Exception:
        log_stage("JSON-LD extraction failed (exception)", 'WARNING')
    return data


def extract_meta(page) -> Dict[str, Any]:
    """Extract OpenGraph / meta tag data and parse counts from description.
    """
    log_stage("Running OpenGraph / meta tag extraction...", 'INFO')
    out = {}
    try:
        def get_meta(name):
            el = page.query_selector(f"meta[property=\"{name}\"]")
            if el:
                return el.get_attribute('content')
            el2 = page.query_selector(f"meta[name=\"{name}\"]")
            if el2:
                return el2.get_attribute('content')
            return None

        og_title = get_meta('og:title')
        og_desc = get_meta('og:description') or get_meta('description')
        og_image = get_meta('og:image')
        og_url = get_meta('og:url')

        if og_title and not out.get('username'):
            # og:title often contains 'Name (@username) • Instagram photos and videos'
            m = re.search(r"@([A-Za-z0-9_.]+)", og_title)
            if m:
                out['username'] = m.group(1)
        if og_desc:
            # Use reusable cleaner to extract only the human-written bio part
            cleaned = None
            try:
                cleaned = clean_instagram_bio(og_desc)
            except Exception:
                cleaned = None
            out['bio'] = cleaned if cleaned else None
            # Try to parse counts like '292M Followers, 243 Following, 1,632 Posts'
            m = re.search(r"([0-9.,]+\s*[MKmk]?)\s*Followers", og_desc)
            if m:
                out['followers'] = parse_count(m.group(1))
            m2 = re.search(r"([0-9.,]+\s*[MKmk]?)\s*Following", og_desc)
            if m2:
                out['following'] = parse_count(m2.group(1))
            m3 = re.search(r"([0-9.,]+)\s*Posts", og_desc)
            if m3:
                out['posts'] = parse_count(m3.group(1))
            # Try to extract website URL inside description
            m4 = re.search(r"https?://[\w./?=#%&+-]+", og_desc)
            if m4:
                out['website'] = m4.group(0)
        if og_image and not out.get('profile_image'):
            out['profile_image'] = og_image
        if og_url and not out.get('url'):
            out['url'] = og_url
    except Exception:
        log_stage("Meta extraction failed (exception)", 'WARNING')
    return out


def extract_internal_state(page) -> Dict[str, Any]:
    """Best-effort extraction from internal JS state (window._sharedData or similar).

    This is optional and often unavailable for anonymous browsing; keep it
    as a best-effort supplemental method.
    """
    log_stage("Running internal page state extraction (best-effort)...", 'INFO')
    out = {}
    try:
        # Try common Instagram global vars
        candidates = ['window._sharedData', 'window.__additionalData', 'window.__INITIAL_STATE__']
        for c in candidates:
            try:
                val = page.evaluate(c)
                if val:
                    # crude search for counts and username
                    txt = json.dumps(val)
                    m = re.search(r"([0-9.,]+\s*[MKmk]?)\s*Followers", txt)
                    if m:
                        out['followers'] = parse_count(m.group(1))
                    # find username-like keys
                    um = re.search(r"\"username\"\s*:\s*\"([A-Za-z0-9_.]+)\"", txt)
                    if um:
                        out['username'] = um.group(1)
                    break
            except Exception:
                continue
    except Exception:
        log_stage("Internal state extraction encountered an error", 'WARNING')
    return out
    return out


def extract_dom_fallback(page) -> Dict[str, Any]:
    """DOM fallback extraction using permissive selectors and text searches.

    Fragile but useful when meta/json-ld are missing.
    """
    log_stage("Running DOM fallback extraction...", 'INFO')
    out = {}
    try:
        # Username from URL or heading
        try:
            url = page.url
            m = re.search(r"instagram.com/([A-Za-z0-9_.]+)/?", url)
            if m:
                out['username'] = m.group(1)
        except Exception:
            pass

        # Try common header selectors
        possible_bio = None
        el = page.query_selector('header')
        if el:
            text = el.inner_text()
            if text:
                # Heuristic: bio lines are typically below username
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                if len(lines) >= 2:
                    possible_bio = lines[-1]
        if not possible_bio:
            # fallback find any element that looks like a bio
            bio_el = page.query_selector("div[role='heading'] ~ div")
            if bio_el:
                possible_bio = bio_el.inner_text()
        if possible_bio:
            out['bio'] = possible_bio

        # Find counts anywhere in page text
        full = page.content()
        m = re.search(r"([0-9.,]+\s*[MKmk]?)\s*Followers", full)
        if m:
            out['followers'] = parse_count(m.group(1))
        m2 = re.search(r"([0-9.,]+\s*[MKmk]?)\s*Following", full)
        if m2:
            out['following'] = parse_count(m2.group(1))
        m3 = re.search(r"([0-9.,]+)\s*Posts", full)
        if m3:
            out['posts'] = parse_count(m3.group(1))

        # profile image fallback
        img = page.query_selector('img')
        if img and not out.get('profile_image'):
            src = img.get_attribute('src')
            if src:
                out['profile_image'] = src
    except Exception:
        log_stage("DOM fallback extraction failed", 'WARNING')
    return out


def merge_profiles(*sources: Dict[str, Any], source_names: list[str] | None = None) -> Dict[str, Any]:
    """Merge multiple partial profile dicts, preferring earlier sources.

    Also tracks which source provided each field.
    """
    fields = ['username', 'bio', 'followers', 'following', 'posts', 'website', 'profile_image', 'url']
    result: Dict[str, Any] = {f: None for f in fields}
    field_sources: Dict[str, str] = {}
    methods_used = []

    for idx, src in enumerate(sources):
        name = source_names[idx] if source_names and idx < len(source_names) else f'method_{idx}'
        if src:
            for f in fields:
                if result.get(f) in (None, '') and src.get(f) not in (None, ''):
                    result[f] = src.get(f)
                    field_sources[f] = name
            if any(k in src for k in fields):
                methods_used.append(name)

    # Normalize numeric fields
    for k in ('followers', 'following', 'posts'):
        if isinstance(result.get(k), str):
            parsed = parse_count(result.get(k))
            result[k] = parsed if parsed is not None else result.get(k)

    # Final structured output
    output = {
        'username': result.get('username') or '',
        'bio': result.get('bio') or '',
        'followers': int(result.get('followers')) if isinstance(result.get('followers'), int) else (result.get('followers') or 0),
        'following': int(result.get('following')) if isinstance(result.get('following'), int) else (result.get('following') or 0),
        'posts': int(result.get('posts')) if isinstance(result.get('posts'), int) else (result.get('posts') or 0),
        'website': result.get('website') or '',
        'profile_image': result.get('profile_image') or '',
        'extraction_methods': list(dict.fromkeys(methods_used)),
        'field_sources': field_sources,
    }
    return output


def extract_instagram_profile(page, username_or_url: str) -> Dict[str, Any]:
    """High-level orchestration: runs the 4 extraction methods and merges results.
    """
    log_stage("Opening Instagram profile...", 'INFO')
    page_load_start = time.perf_counter()
    url = username_or_url if username_or_url.startswith('http') else f'https://instagram.com/{username_or_url}'
    try:
        page.goto(url, timeout=60000)
        page.wait_for_load_state('networkidle', timeout=60000)
        page_load_end = time.perf_counter()
        page_load_duration = page_load_end - page_load_start
        log_stage(f"Page load completed in {page_load_duration:.2f}s", 'SUCCESS')
    except PWTimeout:
        page_load_end = time.perf_counter()
        page_load_duration = page_load_end - page_load_start
        log_stage(f"Navigation timed out after {page_load_duration:.2f}s (continuing)", 'WARNING')
    except Exception as e:
        page_load_end = time.perf_counter()
        page_load_duration = page_load_end - page_load_start
        log_stage(f"Error opening profile: {e}", 'FAILED')
        traceback.print_exc()

    # Run extractors in priority order and measure extraction time
    extraction_start = time.perf_counter()
    jsonld = extract_jsonld(page)
    meta = extract_meta(page)
    internal = extract_internal_state(page)
    dom = extract_dom_fallback(page)
    merged = merge_profiles(jsonld, meta, internal, dom, source_names=['jsonld', 'meta_tags', 'internal_state', 'dom_fallback'])
    extraction_end = time.perf_counter()
    extraction_duration = extraction_end - extraction_start
    log_stage(f"Merging extracted data... (took {extraction_duration:.2f}s)", 'INFO')
    merged['_timing'] = {
        'page_load_seconds': round(page_load_duration, 3),
        'extraction_seconds': round(extraction_duration, 3),
    }
    return merged


def pretty_print_profile(profile: Dict[str, Any]):
    print('\n' + '=' * 80)
    log_stage('Final profile generated', 'SUCCESS')
    print('=' * 80)
    # Pretty JSON output for demonstration
    print(json.dumps(profile, indent=4, ensure_ascii=False))
    print('=' * 80 + '\n')
    # Print human-readable selected fields
    print(f"Username: {profile.get('username')}")
    print(f"Bio: {profile.get('bio')}")
    print(f"Followers: {profile.get('followers')}")
    print(f"Following: {profile.get('following')}")
    print(f"Posts: {profile.get('posts')}")
    print(f"Website: {profile.get('website')}")
    print(f"Profile image: {profile.get('profile_image')}")
    print(f"Extraction methods used: {', '.join(profile.get('extraction_methods', []))}")


if __name__ == '__main__':
    print('Demo: Instagram Structured Metadata Extraction')

    # Prompt user for username input
    try:
        username = input('Enter Instagram username: ').strip()
    except Exception:
        log_stage('Failed to read input from terminal', 'FAILED')
        raise

    if not username:
        log_stage('No username provided. Exiting.', 'FAILED')
        raise SystemExit(1)

    # Normalize username or accept full URL
    if username.startswith('http'):
        profile_url = username
        # sanitize display name
        display_name = re.sub(r'https?://(www\.)?instagram\.com/', '', username).strip('/')
    else:
        # basic validation: allow letters, numbers, dot and underscore
        if not re.match(r'^[A-Za-z0-9._]+$', username):
            log_stage('Invalid username format. Use only letters, numbers, dot and underscore.', 'FAILED')
            raise SystemExit(1)
        profile_url = f'https://instagram.com/{username}'
        display_name = username

    log_stage(f'Opening profile: {display_name}', 'INFO')

    # Prepare run log entry
    log_path = os.path.join(os.getcwd(), 'updation.txt')
    run_entry = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'username': display_name,
        'profile_url': profile_url,
        'status': 'STARTED',
        'notes': None,
    }

    try:
        with sync_playwright() as p:
            log_stage('Launching Chromium (non-headless)...', 'INFO')
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            start = time.perf_counter()
            profile = extract_instagram_profile(page, profile_url)
            end = time.perf_counter()
            total = end - start
            log_stage(f'Total demo duration: {total:.2f}s', 'INFO')
            pretty_print_profile(profile)

            # Update run_entry with timing and status
            run_entry['status'] = 'SUCCESS'
            run_entry['notes'] = f"total_seconds={total:.3f}, page_load={profile.get('_timing', {}).get('page_load_seconds')}, extraction={profile.get('_timing', {}).get('extraction_seconds')}"

            # Keep browser open a few seconds for demonstration visibility
            keep_open = 4
            log_stage(f'Keeping browser open for {keep_open}s for demo visibility...', 'INFO')
            time.sleep(keep_open)
            browser.close()
            log_stage('Browser closed', 'SUCCESS')

    except Exception as e:
        run_entry['status'] = 'FAILED'
        run_entry['notes'] = str(e)
        log_stage(f'Fatal error running demo: {e}', 'FAILED')
        traceback.print_exc()

    # Append run entry to updation.txt
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(run_entry, ensure_ascii=False) + '\n')
        log_stage(f'Appended run log to {log_path}', 'INFO')
    except Exception:
        log_stage('Failed to write updation.txt', 'WARNING')
