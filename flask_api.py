"""
Flask API to expose discovery and extraction endpoints.

Endpoints:
- GET /search?keyword=<kw>&headless=0|1
    Runs DuckDuckGo discovery (up to 5 pages) and extracts metadata for discovered profiles.
    Returns JSON with discovered usernames and extracted profiles.

- GET /profile?username=<username>&headless=0|1
    Extracts a single profile and returns metadata

Notes: This runs Playwright synchronously and can be slow; use for demo/prototyping only.
"""
from flask import Flask, request, jsonify
import traceback
import time
import random

# Import discovery and extraction helpers
import duckduckgo_instagram_discovery as duck
from demo_playwright_extract import extract_instagram_profile, log_stage
from playwright.sync_api import sync_playwright

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    """Add CORS headers so the React frontend can call the API during development."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    # Ensure JSON responses have the correct content type
    if response.content_type is None:
        response.content_type = 'application/json'
    return response


def run_discovery_for_keyword(keyword: str, max_pages: int = 5):
    """Run discovery using functions from duckduckgo_instagram_discovery module.

    Returns a list of unique usernames.
    """
    query = f"site:instagram.com {keyword}"
    all_usernames = []
    seen = set()

    for page in range(1, max_pages + 1):
        html = duck.search_duckduckgo(query, page=page)
        if not html:
            break
        links = duck.extract_links_from_html(html)
        page_usernames, _ = duck.filter_and_deduplicate(links)
        new = False
        for u in page_usernames:
            if u not in seen:
                seen.add(u)
                all_usernames.append(u)
                new = True
        if not new:
            break
        if page < max_pages:
            duck.apply_random_delay(2, 5)
    return all_usernames


@app.route('/search')
def search_and_extract():
    kw = request.args.get('keyword') or request.args.get('q')
    if not kw:
        return jsonify({'error': 'missing keyword parameter'}), 400
    headless = request.args.get('headless', '1') != '0'

    try:
        # Discovery
        start = time.time()
        usernames = run_discovery_for_keyword(kw, max_pages=5)
        discovery_time = time.time() - start

        # If discovery returned no profiles, use fallback test usernames (do not modify discovery logic)
        if not usernames:
            print("[WARNING] No discovered profiles found.")
            print("Using fallback test profiles.")
            usernames = [
                "nike",
                "cristiano",
                "posterlounge",
            ]

        # Extraction
        extracted = []
        failed = []
        if usernames:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                for idx, u in enumerate(usernames, 1):
                    try:
                        page = browser.new_page()
                        log_stage(f'Extracting @{u} ({idx}/{len(usernames)})', 'INFO')
                        prof = extract_instagram_profile(page, u)
                        extracted.append(prof)
                        page.close()
                    except Exception as e:
                        failed.append({'username': u, 'error': str(e)})
                    # rate limit between extractions
                    if idx < len(usernames):
                        time.sleep(random.uniform(3, 6))
                browser.close()

        result = {
            'timestamp': time.time(),
            'keyword': kw,
            'discovered_count': len(usernames),
            'discovery_seconds': round(discovery_time, 2),
            'extracted_count': len(extracted),
            'failed_count': len(failed),
            'usernames': usernames,
            'profiles': extracted,
            'failures': failed,
        }
        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/profile')
def profile_endpoint():
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'missing username parameter'}), 400
    headless = request.args.get('headless', '1') != '0'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            prof = extract_instagram_profile(page, username)
            page.close()
            browser.close()
        return jsonify({'profile': prof})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
