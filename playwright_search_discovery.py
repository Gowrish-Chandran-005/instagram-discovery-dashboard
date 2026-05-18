"""
Playwright-based search discovery system using Bing.
Simulates real user interaction: opens Bing homepage, types query, submits search.
Uses multiple query variants for better Instagram profile coverage.
"""

import os
import time
import random
import base64
import urllib.parse
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def log_msg(msg: str, level: str = 'INFO'):
    """Print professional logs."""
    print(f"[{level.upper()}] {msg}")


def decode_bing_url(url: str) -> str:
    """
    Decode Bing's tracking/redirect URLs.
    Bing wraps the real URL in a Base64-encoded 'u' parameter with an 'a1' prefix.
    Proper padding is added to fix incorrect Base64 length errors.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)

        if "u" not in query:
            return url

        encoded = query["u"][0]

        # Remove Bing's 'a1' prefix
        if encoded.startswith("a1"):
            encoded = encoded[2:]

        # Fix base64 padding (must be a multiple of 4)
        padding = '=' * (-len(encoded) % 4)
        decoded = base64.b64decode(encoded + padding).decode("utf-8")
        return decoded

    except Exception as e:
        print(f"[ERROR] Decode failed: {e}")
        return url


def extract_username_from_url(url: str) -> str:
    """Extracts username from instagram url."""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        parts = path.split('/')
        if parts:
            return parts[0]
    except Exception:
        pass
    return ""


def _type_and_search(page, query: str) -> bool:
    """
    Open Bing homepage, locate search box, type query, press Enter.
    Returns True on success, False on failure.
    """
    try:
        log_msg("Opening Bing homepage...", "INFO")
        page.goto("https://www.bing.com", wait_until="domcontentloaded", timeout=30000)

        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            log_msg("networkidle timeout on homepage, continuing...", "WARNING")

        # Wait for Bing to fully render the search input
        page.wait_for_timeout(3000)

        search_box = page.locator("#sb_form_q").first
        search_box.wait_for(state="visible", timeout=15000)

        log_msg(f"Typing query: {query}", "INFO")
        search_box.click()
        search_box.fill("")
        search_box.type(query, delay=random.randint(60, 130))
        page.wait_for_timeout(500)
        search_box.press("Enter")
        return True
    except Exception as e:
        log_msg(f"Failed to type and search: {e}", "ERROR")
        return False


def _extract_from_results(page, page_num: int, seen: set, keyword: str) -> list:
    """
    Wait for .b_algo cards and extract main result link (h2 a) from each.
    Decodes Bing tracking URLs, filters for valid Instagram profiles.
    Returns list of new usernames discovered.
    """
    BLOCKED_PATHS = ["/p/", "/reel/", "/stories/", "/explore/", "/tv/"]
    page_usernames = []

    # Wait for results
    log_msg("Waiting for search results to load...", "INFO")
    page.wait_for_timeout(5000)

    try:
        page.wait_for_selector("#b_results", timeout=15000)
        log_msg("Result container #b_results found.", "SUCCESS")
    except PlaywrightTimeoutError:
        log_msg("Timeout waiting for #b_results.", "WARNING")

    try:
        page.wait_for_selector(".b_algo", timeout=10000)
        log_msg("Result cards .b_algo found.", "SUCCESS")
    except PlaywrightTimeoutError:
        log_msg("Timeout waiting for .b_algo result cards.", "WARNING")

    log_msg(f"Page Title: {page.title()}", "INFO")
    log_msg(f"Current URL: {page.url}", "INFO")
    log_msg(f"HTML Size: {len(page.content())} bytes", "INFO")

    # Screenshot
    os.makedirs("backend/data/debug_screenshots", exist_ok=True)
    screenshot_path = f"backend/data/debug_screenshots/bing_{keyword}_page_{page_num}.png"
    page.screenshot(path=screenshot_path, full_page=True)
    log_msg(f"Saved screenshot: {screenshot_path}", "INFO")

    # Count result cards
    result_cards = page.locator(".b_algo")
    card_count = result_cards.count()
    log_msg(f"Found {card_count} .b_algo result cards", "SUCCESS")

    raw_main_links = []
    valid_instagram_urls = []

    for i in range(card_count):
        try:
            card = result_cards.nth(i)
            main_link_el = card.locator("h2 a").first
            if main_link_el.count() == 0:
                continue

            raw_href = main_link_el.get_attribute("href")
            if not raw_href:
                continue

            raw_main_links.append(raw_href)
            decoded = decode_bing_url(raw_href)
            log_msg(f"[CARD {i+1}] decoded → {decoded[:100]}", "INFO")

            if "instagram.com/" in decoded:
                if not any(b in decoded for b in BLOCKED_PATHS):
                    valid_instagram_urls.append(decoded)
                    username = extract_username_from_url(decoded)
                    if username and username not in seen:
                        seen.add(username)
                        page_usernames.append(username)

        except Exception as e:
            log_msg(f"Error reading card {i+1}: {e}", "WARNING")
            continue

    # Save debug links on page 1
    if page_num == 1:
        os.makedirs("backend/data", exist_ok=True)
        debug_path = "backend/data/debug_links_page_1.txt"
        with open(debug_path, 'w', encoding='utf-8') as df:
            df.write(f"Total .b_algo cards: {card_count}\n")
            df.write(f"Main h2 links: {len(raw_main_links)}\n\n")
            for idx, h in enumerate(raw_main_links):
                df.write(f"{idx+1}. {h}\n")
        log_msg(f"Saved {len(raw_main_links)} main links to {debug_path}", "INFO")

    log_msg(f"Valid Instagram URLs: {valid_instagram_urls}", "INFO")
    log_msg(f"Extracted usernames: {page_usernames}", "INFO")
    log_msg(f"Found {len(page_usernames)} unique profiles on page {page_num}", "SUCCESS")

    return page_usernames


def scrape_bing(page, keyword: str, max_pages: int, seen: set) -> list:
    """
    Run multiple query variants against Bing to maximise Instagram profile discovery.
    For each variant, scrapes up to max_pages pages of results.
    """
    all_usernames = []

    query_variants = [
        f'site:instagram.com "{keyword}"',
        f'site:instagram.com "{keyword} store"',
        f'site:instagram.com "{keyword} official"',
        f'site:instagram.com "{keyword} studio"',
    ]

    for variant_idx, query in enumerate(query_variants, 1):
        log_msg(f"--- Query variant {variant_idx}/{len(query_variants)}: {query} ---", "INFO")

        # Type and search from Bing homepage for every variant (re-opens search)
        ok = _type_and_search(page, query)
        if not ok:
            log_msg(f"Skipping variant due to search error.", "WARNING")
            continue

        for page_num in range(1, max_pages + 1):
            if page_num > 1:
                # Pagination: click Next
                next_btn = page.locator('a[title="Next page"]').first
                if not next_btn.is_visible():
                    next_btn = page.locator('.sb_pagN').first

                if next_btn.count() > 0 and next_btn.is_visible():
                    log_msg(f"Navigating to page {page_num}...", "INFO")
                    next_btn.click()
                else:
                    log_msg("No next page button found. Stopping pagination for this variant.", "WARNING")
                    break

            try:
                new_usernames = _extract_from_results(page, page_num, seen, keyword)
                all_usernames.extend(new_usernames)
            except Exception as e:
                log_msg(f"Error extracting page {page_num} of variant {variant_idx}: {e}", "ERROR")
                break

            if page_num < max_pages:
                delay = random.uniform(2, 4)
                log_msg(f"Waiting {delay:.2f}s before next page...", "INFO")
                time.sleep(delay)

        # Short pause between variants
        time.sleep(random.uniform(2, 3))

    return all_usernames


def run_playwright_discovery(keyword: str, max_pages: int = 3, headless: bool = True) -> list:
    """
    Run discovery using Playwright Chromium browser on Bing.
    Simulates real user behavior to bypass bot detection.
    Uses multiple query variants for maximum Instagram profile coverage.
    """
    # Keep headless=False for debugging
    headless = False

    log_msg(f"Starting Playwright discovery for keyword: '{keyword}'", "INFO")
    all_usernames = []
    seen = set()

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()

                usernames = scrape_bing(page, keyword, max_pages, seen)
                all_usernames.extend(usernames)

            except Exception as e:
                log_msg(f"Browser launch/navigation failed: {e}", "ERROR")
            finally:
                try:
                    if 'browser' in locals():
                        browser.close()
                except Exception:
                    pass
    except Exception as e:
        log_msg(f"Playwright execution failed: {e}", "ERROR")

    log_msg(f"Total discovered unique profiles: {len(all_usernames)}", "SUCCESS")
    return all_usernames
