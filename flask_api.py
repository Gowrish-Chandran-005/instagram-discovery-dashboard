"""
Flask API to expose discovery and extraction endpoints.

Endpoints:
- GET /search?keyword=<kw>&headless=0|1
    Checks SQLite cache first.
    On cache miss: runs Playwright discovery (Bing), then extracts profiles.
    Saves results to cache for instant repeat queries.
    Returns JSON with discovered usernames and extracted profiles.

- GET /profile?username=<username>&headless=0|1
    Checks SQLite cache first.
    On cache miss: extracts a single profile and caches it.
    Returns profile metadata as JSON.

Notes: Playwright runs synchronously; use for demo/prototyping only.
"""
from flask import Flask, request, jsonify
import traceback
import time
import random

# Import discovery, extraction, and cache helpers
import playwright_search_discovery as psd
import cache_db
import seed_profiles
from demo_playwright_extract import extract_instagram_profile, log_stage
from playwright.sync_api import sync_playwright

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    """Add CORS headers so the React frontend can call the API during development."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    if response.content_type is None:
        response.content_type = 'application/json'
    return response


def run_discovery_for_keyword(keyword: str, max_pages: int = 3, headless: bool = True):
    """Run Playwright discovery. Returns a list of unique usernames."""
    return psd.run_playwright_discovery(keyword, max_pages=max_pages, headless=headless)


@app.route('/search')
def search_and_extract():
    kw = request.args.get('keyword') or request.args.get('q')
    if not kw:
        return jsonify({'error': 'missing keyword parameter'}), 400
    headless = request.args.get('headless', '1') != '0'

    try:
        # ── 1. Check search cache ─────────────────────────────────────────────
        cached_usernames = cache_db.get_cached_search(kw)
        from_cache = False

        if cached_usernames is not None:
            print(f"[INFO] Cache HIT for keyword '{kw}' → {len(cached_usernames)} usernames")
            usernames = cached_usernames
            from_cache = True
            discovery_time = 0.0
        else:
            print(f"[INFO] Cache MISS for keyword '{kw}'. Running Playwright discovery...")
            start = time.time()
            usernames = run_discovery_for_keyword(kw, max_pages=3, headless=headless)
            discovery_time = time.time() - start

            if not usernames:
                print("[WARNING] No discovered profiles found via Bing. Falling back to curated seeds.")
                usernames = seed_profiles.get_seeds(kw)
            else:
                print(f"[INFO] Discovery found {len(usernames)} profiles.")

            cache_db.cache_search(kw, usernames)
            print(f"[INFO] Cached {len(usernames)} usernames for '{kw}'")

        # ── 2. Extract profiles (with per-profile cache) ──────────────────────
        extracted = []
        failed = []

        if usernames:
            # Separate cached vs uncached profiles
            to_extract = []
            for u in usernames:
                cached_prof = cache_db.get_cached_profile(u)
                if cached_prof:
                    print(f"[INFO] Profile cache HIT for @{u}")
                    extracted.append(cached_prof)
                else:
                    to_extract.append(u)

            # Extract uncached profiles via Playwright
            if to_extract:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=headless)
                    for idx, u in enumerate(to_extract, 1):
                        try:
                            page = browser.new_page()
                            log_stage(f'Extracting @{u} ({idx}/{len(to_extract)})', 'INFO')
                            prof = extract_instagram_profile(page, u)
                            extracted.append(prof)
                            cache_db.cache_profile(u, prof)
                            page.close()
                        except Exception as e:
                            failed.append({'username': u, 'error': str(e)})
                        if idx < len(to_extract):
                            time.sleep(random.uniform(3, 6))
                    browser.close()

        result = {
            'success': True,
            'keyword': kw,
            'from_cache': from_cache,
            'total_profiles': len(extracted),
            'profiles': extracted,
            'timestamp': time.time(),
            'discovered_count': len(usernames),
            'discovery_seconds': round(discovery_time, 2),
            'failed_count': len(failed),
            'usernames': usernames,
            'failures': failed,
        }
        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/profile')
def profile_endpoint():
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'missing username parameter'}), 400
    headless = request.args.get('headless', '1') != '0'

    try:
        # Check profile cache first
        cached = cache_db.get_cached_profile(username)
        if cached:
            print(f"[INFO] Profile cache HIT for @{username}")
            return jsonify({'profile': cached, 'from_cache': True})

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            prof = extract_instagram_profile(page, username)
            page.close()
            browser.close()

        cache_db.cache_profile(username, prof)
        return jsonify({'profile': prof, 'from_cache': False})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
