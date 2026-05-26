"""
Instagram Structured Metadata Extraction module.
Extracts profile data using JSON-LD, OpenGraph, internal state, and DOM fallback.
"""
import json
import re
import time
import logging
import traceback
from typing import Dict, Any
from playwright.sync_api import TimeoutError as PWTimeout
from extractor.parser_utils import clean_instagram_bio

# Configure structured logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(name)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def clean_number(text):
    if not text:
        return 0
    text = str(text).lower().replace(",", "").strip()
    if "k" in text:
        return int(float(text.replace("k", "")) * 1000)
    if "m" in text:
        return int(float(text.replace("m", "")) * 1000000)
    return int("".join(filter(str.isdigit, text)) or 0)

def is_valid_profile(data):
    username = data.get("username", "")
    bio = data.get("bio", "")

    if not username or len(username) < 2:
        return False

    invalid_patterns = [
        "no bio available",
        "see instagram photos and videos",
        "0 followers",
        "0 posts"
    ]
    text_blob = f"{bio}".lower()
    if any(p in text_blob for p in invalid_patterns):
        return False

    return True

def extract_jsonld(page) -> Dict[str, Any]:
    logger.debug("Running JSON-LD extraction...")
    data = {}
    try:
        scripts = page.query_selector_all("script[type='application/ld+json']")
        for s in scripts:
            try:
                text = s.text_content()
                if not text: continue
                parsed = json.loads(text)
                objs = parsed if isinstance(parsed, list) else [parsed]
                for obj in objs:
                    t = obj.get('@type') or obj.get('type')
                    if isinstance(t, list): t = t[0]
                    if t and t.lower() in ('person', 'profile', 'organization'):
                        if 'name' in obj and not data.get('username'): data['username'] = obj.get('name')
                        if 'description' in obj and not data.get('bio'): data['bio'] = obj.get('description')
                        if 'image' in obj and not data.get('profile_image'):
                            img = obj.get('image')
                            data['profile_image'] = img.get('url') if isinstance(img, dict) else img
                        if 'url' in obj and not data.get('url'): data['url'] = obj.get('url')
                        logger.debug("JSON-LD: found structured object")
                        return data
            except Exception: continue
    except Exception:
        logger.debug("JSON-LD extraction failed")
    return data

def extract_meta(page) -> Dict[str, Any]:
    logger.debug("Running OpenGraph / meta tag extraction...")
    out = {}
    try:
        def get_meta(name):
            el = page.query_selector(f"meta[property=\"{name}\"]")
            if el: return el.get_attribute('content')
            el2 = page.query_selector(f"meta[name=\"{name}\"]")
            if el2: return el2.get_attribute('content')
            return None

        og_title = get_meta('og:title')
        og_desc = get_meta('og:description') or get_meta('description')
        og_image = get_meta('og:image')
        og_url = get_meta('og:url')

        if og_title and not out.get('username'):
            m = re.search(r"@([A-Za-z0-9_.]+)", og_title)
            if m: out['username'] = m.group(1)
        if og_desc:
            cleaned = None
            try: cleaned = clean_instagram_bio(og_desc)
            except Exception: pass
            out['bio'] = cleaned if cleaned else None
            m = re.search(r"([0-9.,]+\s*[MKmk]?)\s*Followers", og_desc)
            if m: out['followers'] = clean_number(m.group(1))
            m2 = re.search(r"([0-9.,]+\s*[MKmk]?)\s*Following", og_desc)
            if m2: out['following'] = clean_number(m2.group(1))
            m3 = re.search(r"([0-9.,]+)\s*Posts", og_desc)
            if m3: out['posts'] = clean_number(m3.group(1))
            m4 = re.search(r"https?://[\w./?=#%&+-]+", og_desc)
            if m4: out['website'] = m4.group(0)
        if og_image and not out.get('profile_image'): out['profile_image'] = og_image
        if og_url and not out.get('url'): out['url'] = og_url
    except Exception:
        logger.debug("Meta extraction failed")
    return out

def extract_internal_state(page) -> Dict[str, Any]:
    logger.debug("Running internal page state extraction...")
    out = {}
    try:
        candidates = ['window._sharedData', 'window.__additionalData', 'window.__INITIAL_STATE__']
        for c in candidates:
            try:
                val = page.evaluate(c)
                if val:
                    txt = json.dumps(val)
                    m = re.search(r"([0-9.,]+\s*[MKmk]?)\s*Followers", txt)
                    if m: out['followers'] = clean_number(m.group(1))
                    um = re.search(r"\"username\"\s*:\s*\"([A-Za-z0-9_.]+)\"", txt)
                    if um: out['username'] = um.group(1)
                    break
            except Exception: continue
    except Exception:
        logger.debug("Internal state extraction failed")
    return out

def extract_dom_fallback(page) -> Dict[str, Any]:
    logger.debug("Running DOM fallback extraction...")
    out = {}
    try:
        try:
            m = re.search(r"instagram.com/([A-Za-z0-9_.]+)/?", page.url)
            if m: out['username'] = m.group(1)
        except Exception: pass

        img = page.query_selector('img')
        if img and not out.get('profile_image'):
            src = img.get_attribute('src')
            if src: out['profile_image'] = src
    except Exception:
        logger.debug("DOM fallback extraction failed")
    return out

def merge_profiles(*sources: Dict[str, Any], source_names: list[str] | None = None) -> Dict[str, Any]:
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

    for k in ('followers', 'following', 'posts'):
        if isinstance(result.get(k), str) or isinstance(result.get(k), float):
            result[k] = clean_number(str(result.get(k)))

    confidence = 0
    if "jsonld" in methods_used: confidence += 50
    if "meta_tags" in methods_used: confidence += 50
    if "og_tags" in methods_used: confidence += 30
    if "internal_state" in methods_used: confidence += 20
    if "dom_fallback" in methods_used: confidence += 10

    return {
        'username': result.get('username') or '',
        'bio': result.get('bio') or '',
        'followers': int(result.get('followers')) if isinstance(result.get('followers'), int) else (result.get('followers') or 0),
        'following': int(result.get('following')) if isinstance(result.get('following'), int) else (result.get('following') or 0),
        'posts': int(result.get('posts')) if isinstance(result.get('posts'), int) else (result.get('posts') or 0),
        'website': result.get('website') or '',
        'profile_image': result.get('profile_image') or '',
        'extraction_methods': list(dict.fromkeys(methods_used)),
        'field_sources': field_sources,
        'confidence': confidence
    }

def extract_instagram_profile(page, username_or_url: str) -> Dict[str, Any]:
    logger.info(f"Opening Instagram profile: {username_or_url}")
    page_load_start = time.perf_counter()
    url = username_or_url if username_or_url.startswith('http') else f'https://instagram.com/{username_or_url}'
    try:
        page.goto(url, timeout=45000)
        page.wait_for_load_state('networkidle', timeout=45000)
    except PWTimeout:
        logger.warning(f"Navigation timed out for {url}, attempting extraction anyway")
    except Exception as e:
        logger.error(f"Error opening profile {url}: {e}")

    extraction_start = time.perf_counter()
    jsonld = extract_jsonld(page)
    meta = extract_meta(page)
    internal = extract_internal_state(page)
    dom = extract_dom_fallback(page)
    merged = merge_profiles(jsonld, meta, internal, dom, source_names=['jsonld', 'meta_tags', 'internal_state', 'dom_fallback'])
    
    if merged.get('followers', 0) == 0:
        logger.info(f"0 followers found for {url}, retrying once...")
        try:
            page.reload(timeout=45000)
            page.wait_for_load_state('networkidle', timeout=45000)
            jsonld = extract_jsonld(page)
            meta = extract_meta(page)
            internal = extract_internal_state(page)
            dom = extract_dom_fallback(page)
            merged = merge_profiles(jsonld, meta, internal, dom, source_names=['jsonld', 'meta_tags', 'internal_state', 'dom_fallback'])
        except Exception as e:
            logger.warning(f"Retry failed for {url}: {e}")
    
    extraction_duration = time.perf_counter() - extraction_start
    merged['_timing'] = {
        'page_load_seconds': round(time.perf_counter() - page_load_start - extraction_duration, 3),
        'extraction_seconds': round(extraction_duration, 3),
    }
    
    logger.info(f"Finished extracting profile: {merged.get('username')} in {extraction_duration:.2f}s")
    return merged
