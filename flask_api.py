"""
Flask API to expose discovery and extraction endpoints.

Orchestrates:
1. SQLite Cache (cache_db)
2. Bing Search (search_engine)
3. Fallback Seeds (seed_profiles)
4. Instagram Profile Extraction (profile_extractor)

Performance: Uses ThreadPoolExecutor to scrape up to 3 Instagram profiles concurrently.
"""
from flask import Flask, request, jsonify
import traceback
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import search_engine as se
import cache_db
import seed_profiles
from profile_extractor import extract_instagram_profile, is_valid_profile
from playwright.sync_api import sync_playwright

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(name)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    if response.content_type is None:
        response.content_type = 'application/json'
    return response

def relevance_score(keyword: str, profile: dict) -> float:
    text = (
        profile.get("username", "") + " " +
        profile.get("bio", "") + " " +
        profile.get("name", "")
    ).lower()

    keywords = keyword.lower().split()
    if not keywords:
        return 1.0

    score = 0.0
    for k in keywords:
        # Heavily weight username matches
        if k in profile.get("username", "").lower():
            score += 1.5
        # Secondary weight for bio/name matches
        elif k in text:
            score += 1.0
            
    # Normalize roughly to 0.0 - 1.0
    return min(score / len(keywords), 1.5) / 1.5

def calculate_final_score(profile: dict, kw: str) -> float:
    import math
    # 1. Confidence Score (normalized from 0-160 to 0.0-1.0)
    raw_confidence = profile.get("confidence", 0)
    confidence_score = min(raw_confidence / 100.0, 1.0)

    # 2. Relevance (0.0 to 1.0)
    relevance = relevance_score(kw, profile)

    # 3. Follower Score (logarithmic scale to handle exponential spread)
    followers = profile.get("followers", 0)
    if followers > 0:
        # log10(100K) = 5. Capped at 1.0 (100K+ followers = full score)
        follower_score = min(math.log10(followers) / 5.0, 1.0)
    else:
        follower_score = 0.0

    # 4. Metadata Completeness (0.0 to 1.0)
    fields_to_check = ["bio", "website", "profile_image", "followers", "posts"]
    populated_count = sum(1 for field in fields_to_check if profile.get(field))
    metadata_completeness = populated_count / len(fields_to_check)

    # Calculate weighted score out of 100
    final_score = (
        confidence_score * 0.4 +
        relevance * 0.3 +
        follower_score * 0.2 +
        metadata_completeness * 0.1
    ) * 100.0

    return round(final_score, 1)

def extract_worker(username: str, headless: bool):
    """Worker function to extract a single profile in its own thread/Playwright context."""
    logger.info(f"Worker started for @{username}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            prof = extract_instagram_profile(page, username)
            browser.close()
            return username, prof, None
    except Exception as e:
        logger.error(f"Worker failed for @{username}: {e}")
        return username, None, str(e)


@app.route('/search')
def search_and_extract():
    kw = request.args.get('keyword') or request.args.get('q')
    if not kw:
        return jsonify({'error': 'missing keyword parameter'}), 400
    headless = request.args.get('headless', '1') != '0'

    try:
        source = "cache"
        start_time = time.time()
        
        # ── 1. Check search cache ─────────────────────────────────────────────
        cached_usernames = cache_db.get_cached_search(kw)
        
        if cached_usernames is not None:
            logger.info(f"Cache HIT for keyword '{kw}' -> {len(cached_usernames)} usernames")
            usernames = cached_usernames
            discovery_time = 0.0
        else:
            logger.info(f"Cache MISS for keyword '{kw}'. Running Bing discovery...")
            discovery_start = time.time()
            bing_result = se.run_playwright_discovery(kw, max_pages=3, headless=headless)
            discovery_time = time.time() - discovery_start
            usernames = bing_result.get('usernames', [])
            source = "bing"
            
            # Fallback to seeds if Bing failed or returned empty
            if not usernames or bing_result.get('status') == 'bot_blocked':
                logger.warning("Bing discovery failed or returned 0 profiles. Falling back to seeds.")
                usernames = seed_profiles.get_seeds(kw)
                source = "seed"
            
            cache_db.cache_search(kw, usernames)
            logger.info(f"Cached {len(usernames)} usernames for '{kw}'")

        # ── 2. Extract profiles (with per-profile cache & concurrency) ────────
        extracted = []
        failed = []
        to_extract = []
        seen = set()
        
        # Deduplicate usernames before extraction
        for u in usernames:
            if u not in seen:
                seen.add(u)
                cached_prof = cache_db.get_cached_profile(u)
                if cached_prof:
                    logger.info(f"Profile cache HIT for @{u}")
                    extracted.append(cached_prof)
                else:
                    to_extract.append(u)

        if to_extract:
            logger.info(f"Extracting {len(to_extract)} profiles concurrently...")
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(extract_worker, u, headless): u for u in to_extract}
                for future in as_completed(futures):
                    u, prof, error = future.result()
                    if error:
                        failed.append({'username': u, 'error': error})
                    elif prof:
                        extracted.append(prof)
                        cache_db.cache_profile(u, prof)

        # Soft filter out completely invalid profiles first (empty usernames or bad fallback titles)
        extracted = [p for p in extracted if is_valid_profile(p)]

        # Calculate metrics & final relevance/confidence scoring
        valid_profiles = []
        for p in extracted:
            p["relevance"] = relevance_score(kw, p)
            p["final_score"] = calculate_final_score(p, kw)
            
            # --- STRICT QUALITY FILTERING ---
            # Reject if followers are too low (bot/spam)
            if p.get("followers", 0) < 100:
                continue
            # Reject if confidence is too low (extraction failed/incomplete)
            if p.get("confidence", 0) < 30:
                continue
            # Reject if completely irrelevant
            if p.get("relevance", 0.0) < 0.1:
                continue
                
            valid_profiles.append(p)

        # Sort descending by final_score so the absolute best float to the top
        valid_profiles.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)

        # Truncate to top 20 profiles
        extracted = valid_profiles[:20]

        total_time = time.time() - start_time
        
        result = {
            'keyword': kw,
            'source': source,
            'profiles': extracted,
            'cached': source == "cache",
            'performance': {
                'time_taken_seconds': round(total_time, 2),
                'search_method': source,
                'discovery_seconds': round(discovery_time, 2),
            },
            'failed_count': len(failed),
            'failures': failed
        }
        return jsonify(result)

    except Exception as e:
        logger.error(f"Search endpoint error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/profile')
def profile_endpoint():
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'missing username parameter'}), 400
    headless = request.args.get('headless', '1') != '0'

    try:
        cached = cache_db.get_cached_profile(username)
        if cached:
            logger.info(f"Profile cache HIT for @{username}")
            return jsonify({'profile': cached, 'from_cache': True})

        _, prof, error = extract_worker(username, headless)
        
        if error:
            return jsonify({'error': error, 'success': False}), 500
            
        cache_db.cache_profile(username, prof)
        return jsonify({'profile': prof, 'from_cache': False})

    except Exception as e:
        logger.error(f"Profile endpoint error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'instagram-discovery-api'
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
