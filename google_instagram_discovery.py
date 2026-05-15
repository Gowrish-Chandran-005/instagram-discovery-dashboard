"""
google_instagram_discovery.py

Discover Instagram profile usernames via Google search using Playwright.

Usage: python google_instagram_discovery.py

Flow:
 - Prompt the user for a keyword
 - Open Google in Chromium (visible)
 - Search for "site:instagram.com <keyword>"
 - Collect result links and filter for profile URLs
 - Extract usernames, deduplicate, print and save to discovered_profiles.json

Notes:
 - This is a demonstration script; Google may block automated requests in some environments.
 - Keep browser visible (headless=False) for demo purposes.
"""

import json
import re
import time
import traceback
from typing import List, Set

from playwright.sync_api import sync_playwright, TimeoutError


def prompt_keyword() -> str:
    """Prompt the user for a discovery keyword."""
    kw = input("Enter discovery keyword (e.g. posters): ").strip()
    return kw


def open_google_and_search(page, query: str) -> None:
    """Navigate to Google and perform the search for the given query.

    Uses safer `textarea[name='q']` selector, handles consent popup, and includes
    proper waits and error handling.
    """
    print(f"[INFO] Opening Google and searching for: {query}")

    # Navigate to Google with safer wait condition
    try:
        print("[DEBUG] Navigating to Google (domcontentloaded)...")
        page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=60000)
        print("[INFO] Google loaded successfully")
    except TimeoutError:
        print("[WARNING] Google page load timed out, attempting to continue")
    except Exception as e:
        print(f"[ERROR] Failed to load Google: {e}")
        raise

    # Wait briefly after page load
    page.wait_for_timeout(3000)

    # Handle Google consent popup if present
    print("[DEBUG] Attempting to dismiss consent popup...")
    try:
        # Try multiple consent button selectors
        consent_buttons = [
            "button:has-text('I agree')",
            "button:has-text('Agree')",
            "button[aria-label='Accept all']",
        ]
        for selector in consent_buttons:
            try:
                btn = page.query_selector(selector)
                if btn:
                    print(f"[DEBUG] Found consent button with selector: {selector}")
                    btn.click()
                    time.sleep(1)
                    print("[INFO] Consent popup dismissed")
                    break
            except Exception:
                continue
    except Exception as e:
        print(f"[DEBUG] Could not dismiss consent popup: {e} (continuing anyway)")

    # Try to find and fill the search box using safer selector
    print("[DEBUG] Looking for search input...")
    search_box = None
    selectors = ["textarea[name='q']", "input[name='q']", "input[type='text'][name='q']"]
    for selector in selectors:
        try:
            search_box = page.query_selector(selector)
            if search_box:
                print(f"[DEBUG] Found search box with selector: {selector}")
                break
        except Exception:
            continue

    if not search_box:
        print("[ERROR] Could not find search input box")
        raise RuntimeError("Search box not found on Google homepage")

    # Fill and submit the search query
    try:
        print(f"[DEBUG] Filling search box with query: {query}")
        search_box.fill(query)
        search_box.press('Enter')
        print("[INFO] Search query submitted")
    except Exception as e:
        print(f"[ERROR] Failed to submit search: {e}")
        raise

    # Wait for results to load
    print("[DEBUG] Waiting for search results to load (networkidle)...")
    try:
        page.wait_for_load_state('networkidle', timeout=60000)
        print("[INFO] Search results loaded successfully")
    except TimeoutError:
        print("[WARNING] Results load timed out, attempting to continue with current content")
    except Exception as e:
        print(f"[ERROR] Error waiting for results: {e}")

    # Wait 5 seconds before extraction for results to stabilize
    print("[DEBUG] Waiting 5 seconds before extraction...")
    time.sleep(5)


def extract_links_from_search(page) -> List[str]:
    """Extract hrefs from search result area (best-effort selectors).

    Returns a list of href strings found on the results page.
    """
    print("[INFO] Extracting links from search results page...")

    # Print debug info
    try:
        print(f"[DEBUG] Current page title: {page.title()}")
        print(f"[DEBUG] Current URL: {page.url}")
    except Exception:
        pass

    hrefs = []
    try:
        # Limit search to anchors found inside the main results container
        print("[DEBUG] Searching for anchors in div#search...")
        anchors = page.query_selector_all('div#search a')
        print(f"[DEBUG] Found {len(anchors)} anchors in div#search")

        if not anchors or len(anchors) == 0:
            print("[DEBUG] No anchors in div#search, falling back to all anchors...")
            anchors = page.query_selector_all('a')
            print(f"[DEBUG] Found {len(anchors)} total anchors on page")

        for idx, a in enumerate(anchors):
            try:
                href = a.get_attribute('href')
                if href and href.startswith('http'):
                    hrefs.append(href)
            except Exception as e:
                print(f"[DEBUG] Error extracting href from anchor {idx}: {e}")
                continue

        print(f"[INFO] Extracted {len(hrefs)} HTTP links")

    except Exception as e:
        print(f'[ERROR] Failed to extract anchors: {e}')
        print('[WARNING] Attempting fallback extraction...')
        try:
            anchors = page.query_selector_all('a')
            print(f"[DEBUG] Fallback: found {len(anchors)} total anchors")
            for a in anchors:
                try:
                    href = a.get_attribute('href')
                    if href and href.startswith('http'):
                        hrefs.append(href)
                except Exception:
                    continue
            print(f"[INFO] Fallback extraction yielded {len(hrefs)} links")
        except Exception as e2:
            print(f'[ERROR] Fallback extraction also failed: {e2}')
            traceback.print_exc()

    print(f"[DEBUG] Total links extracted: {len(hrefs)}")
    return hrefs


def is_profile_url(href: str) -> bool:
    """Return True if href looks like an Instagram profile URL (not post/reel/explore).

    Examples accepted:
      https://www.instagram.com/nike/
      https://instagram.com/nike
    Excludes URLs containing '/p/', '/reel/', '/explore', '/tags', 'accounts/login'
    """
    if 'instagram.com' not in href:
        return False

    # Normalize
    href_lower = href.lower()
    # Reject common non-profile paths
    reject_patterns = ['/p/', '/reel/', '/explore', '/tags', '/tv/', '/stories/', '/graphql/', '/accounts/login']
    for rp in reject_patterns:
        if rp in href_lower:
            return False

    # Accept if path is just /{username}/ optionally with query or trailing slash
    m = re.search(r'instagram\.com/([^/?#]+)', href)
    if not m:
        return False
    username = m.group(1)
    # Exclude short or invalid username candidates
    if len(username) < 2 or username.isdigit():
        return False
    # Reject common non-profile tokens
    if username in ('explore', 'p', 'stories', 'reel', 'accounts'):
        return False
    return True


def extract_username_from_url(href: str) -> str | None:
    """Extract username segment from an Instagram profile URL.

    Returns the username string or None if not found.
    """
    try:
        m = re.search(r'instagram\.com/([A-Za-z0-9._]+)/?', href)
        if m:
            return m.group(1).strip('/')
    except Exception:
        return None
    return None


def filter_and_deduplicate(hrefs: List[str]) -> List[str]:
    """Filter raw hrefs to valid Instagram profile usernames and remove duplicates."""
    print(f"[DEBUG] Filtering {len(hrefs)} links for Instagram profiles...")
    usernames: List[str] = []
    seen: Set[str] = set()
    profile_urls = []

    for href in hrefs:
        try:
            if not is_profile_url(href):
                continue
            u = extract_username_from_url(href)
            if not u:
                continue
            if u not in seen:
                seen.add(u)
                usernames.append(u)
                profile_urls.append(href)
        except Exception as e:
            print(f"[DEBUG] Error processing href: {e}")
            continue

    print(f"[INFO] Filtered down to {len(usernames)} unique Instagram profiles")
    if profile_urls:
        print("\n[INFO] Discovered Instagram Profile URLs:")
        for url in profile_urls:
            print(f"  → {url}")
    return usernames


def save_discovered_usernames(usernames: List[str], path: str = 'discovered_profiles.json') -> None:
    """Save discovered usernames to JSON file with timestamp."""
    payload = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'count': len(usernames),
        'usernames': usernames,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Saved {len(usernames)} usernames to {path}")


def run_discovery():
    """Main orchestration function for Google-based Instagram discovery."""
    keyword = prompt_keyword()
    if not keyword:
        print('[ERROR] No keyword provided. Exiting.')
        return

    query = f"site:instagram.com {keyword}"
    print(f"[INFO] Starting discovery with keyword: '{keyword}'")
    print(f"[INFO] Search query: {query}\n")

    try:
        with sync_playwright() as p:
            # Set default timeout on context
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            context.set_default_timeout(60000)
            page = context.new_page()

            # Perform search
            open_google_and_search(page, query)

            # Extract and process links
            hrefs = extract_links_from_search(page)
            usernames = filter_and_deduplicate(hrefs)

            # Print results
            if usernames:
                print('\n' + '=' * 60)
                print('DISCOVERED INSTAGRAM USERNAMES')
                print('=' * 60)
                for idx, u in enumerate(usernames, 1):
                    print(f'  {idx}. {u}')
                print('=' * 60 + '\n')
            else:
                print('\n[INFO] No profile usernames discovered.')

            # Save to file
            save_discovered_usernames(usernames)

            # Keep browser open temporarily for debugging/review
            keep_open = 5
            print(f"[INFO] Keeping browser open for {keep_open} seconds for debugging...")
            time.sleep(keep_open)
            print("[INFO] Closing browser...")
            context.close()
            browser.close()
            print("[INFO] Discovery complete.")

    except TimeoutError as te:
        print(f'[ERROR] Playwright operation timed out: {te}')
        traceback.print_exc()
    except Exception as e:
        print(f'[ERROR] Unexpected error during discovery: {e}')
        traceback.print_exc()


if __name__ == '__main__':
    run_discovery()
