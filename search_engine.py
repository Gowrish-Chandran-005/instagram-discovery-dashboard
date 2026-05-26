"""
Bing search engine discovery module.
Uses Playwright to simulate human search and extract Instagram profiles from .b_algo cards.
"""

import os
import time
import random
import base64
import urllib.parse
from urllib.parse import urlparse, parse_qs
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configure structured logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(name)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def decode_bing_url(url: str) -> str:
    """Decode Bing's tracking/redirect URLs (Base64 u parameter)."""
    try:
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        if "u" not in query:
            return url
        encoded = query["u"][0]
        if encoded.startswith("a1"):
            encoded = encoded[2:]
        padding = '=' * (-len(encoded) % 4)
        return base64.b64decode(encoded + padding).decode("utf-8")
    except Exception as e:
        logger.debug(f"Decode failed for {url}: {e}")
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
    """Type query into Bing homepage and submit."""
    try:
        logger.info("Opening Bing homepage...")
        page.goto("https://www.bing.com", wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            logger.warning("networkidle timeout on homepage, continuing...")
        
        page.wait_for_timeout(3000)
        
        # Check for CAPTCHA/bot protection on homepage
        if "captcha" in page.title().lower() or "sorry" in page.title().lower():
            logger.error("Bot protection detected on Bing homepage.")
            return False

        search_box = page.locator("#sb_form_q").first
        search_box.wait_for(state="visible", timeout=15000)

        logger.info(f"Typing query: {query}")
        search_box.click()
        search_box.fill("")
        search_box.type(query, delay=random.randint(60, 130))
        page.wait_for_timeout(500)
        search_box.press("Enter")
        return True
    except Exception as e:
        logger.error(f"Failed to type and search: {e}")
        return False

def _extract_from_results(page, page_num: int, seen: set, keyword: str) -> list:
    """Extract main result links from Bing search results."""
    BLOCKED_PATHS = ["/p/", "/reel/", "/stories/", "/explore/", "/tv/"]
    page_usernames = []
    profile_dicts = []  # List of dicts with enriched data


    logger.info("Waiting for search results to load...")
    page.wait_for_timeout(5000)

    # Detect CAPTCHA/Bot protection
    if "captcha" in page.title().lower() or "sorry" in page.title().lower() or "verify" in page.title().lower():
        logger.error("Bot protection detected on search results page.")
        raise RuntimeError("BOT_PROTECTION")

    try:
        page.wait_for_selector("#b_results", timeout=15000)
        logger.debug("Result container #b_results found.")
    except PlaywrightTimeoutError:
        logger.warning("Timeout waiting for #b_results.")

    # Try different selectors for result cards
    result_cards = None
    for selector in [".b_algo", "li.b_algo", "article"]:
        try:
            page.wait_for_selector(selector, timeout=5000)
            result_cards = page.locator(selector)
            if result_cards.count() > 0:
                logger.info(f"Result cards found using selector: {selector}")
                break
        except PlaywrightTimeoutError:
            continue

    if not result_cards or result_cards.count() == 0:
        logger.warning(f"No result cards found on page {page_num}.")
        return []

    card_count = result_cards.count()
    logger.info(f"Found {card_count} result cards.")

    for i in range(card_count):
        try:
            card = result_cards.nth(i)
            # Try to get main link (h2 a is standard for bing, but fallback to any a inside if h2 is missing)
            main_link_el = card.locator("h2 a").first
            if main_link_el.count() == 0:
                main_link_el = card.locator("a").first

            if main_link_el.count() == 0:
                continue

            raw_href = main_link_el.get_attribute("href")
            if not raw_href:
                continue

            decoded = decode_bing_url(raw_href)
            logger.debug(f"[CARD {i+1}] decoded -> {decoded[:80]}")

            if "instagram.com/" in decoded:
                if not any(b in decoded for b in BLOCKED_PATHS):
                    username = extract_username_from_url(decoded)
                    if username and username not in seen:
                        seen.add(username)
                        # Extract snippet paragraph if available
                        snippet_text = ""
                        try:
                            snippet_el = card.locator("p").first
                            if snippet_el.count() > 0:
                                snippet_text = snippet_el.inner_text().strip()
                        except Exception:
                            pass

                        # Parse follower/following/post counts from snippet using regex
                        followers = None
                        following = None
                        posts = None
                        import re
                        # Example patterns: "145K followers", "145k Followers", "1.2M followers"
                        follower_match = re.search(r"([\d.,]+\s*[kKmMbB]?)[\s-]*followers", snippet_text, re.IGNORECASE)
                        following_match = re.search(r"([\d.,]+\s*[kKmMbB]?)[\s-]*following", snippet_text, re.IGNORECASE)
                        posts_match = re.search(r"([\d.,]+\s*[kKmMbB]?)[\s-]*posts", snippet_text, re.IGNORECASE)
                        if follower_match:
                            followers = follower_match.group(1).replace(",", "").strip()
                        if following_match:
                            following = following_match.group(1).replace(",", "").strip()
                        if posts_match:
                            posts = posts_match.group(1).replace(",", "").strip()

                        profile = {
                            "username": username,
                            "profile_url": decoded,
                            "bio": snippet_text,
                            "followers": followers,
                            "following": following,
                            "posts": posts,
                        }
                        profile_dicts.append(profile)
                        page_usernames.append(username)
        except Exception as e:
            logger.warning(f"Error reading card {i+1}: {e}")
            continue

    logger.info(f"Extracted {len(page_usernames)} unique profiles on page {page_num}.")
    return profile_dicts

    page.wait_for_timeout(5000)

    # Detect CAPTCHA/Bot protection
    if "captcha" in page.title().lower() or "sorry" in page.title().lower() or "verify" in page.title().lower():
        logger.error("Bot protection detected on search results page.")
        raise RuntimeError("BOT_PROTECTION")

    try:
        page.wait_for_selector("#b_results", timeout=15000)
        logger.debug("Result container #b_results found.")
    except PlaywrightTimeoutError:
        logger.warning("Timeout waiting for #b_results.")

    # Try different selectors for result cards
    result_cards = None
    for selector in [".b_algo", "li.b_algo", "article"]:
        try:
            page.wait_for_selector(selector, timeout=5000)
            result_cards = page.locator(selector)
            if result_cards.count() > 0:
                logger.info(f"Result cards found using selector: {selector}")
                break
        except PlaywrightTimeoutError:
            continue
    
    if not result_cards or result_cards.count() == 0:
        logger.warning(f"No result cards found on page {page_num}.")
        return []

    card_count = result_cards.count()
    logger.info(f"Found {card_count} result cards.")

    for i in range(card_count):
        try:
            card = result_cards.nth(i)
            # Try to get main link (h2 a is standard for bing, but fallback to any a inside if h2 is missing)
            main_link_el = card.locator("h2 a").first
            if main_link_el.count() == 0:
                main_link_el = card.locator("a").first
            
            if main_link_el.count() == 0:
                continue

            raw_href = main_link_el.get_attribute("href")
            if not raw_href:
                continue

            decoded = decode_bing_url(raw_href)
            logger.debug(f"[CARD {i+1}] decoded -> {decoded[:80]}")

            if "instagram.com/" in decoded:
                if not any(b in decoded for b in BLOCKED_PATHS):
                    username = extract_username_from_url(decoded)
                    if username and username not in seen:
                        seen.add(username)
                        page_usernames.append(username)
        except Exception as e:
            logger.warning(f"Error reading card {i+1}: {e}")
            continue

    logger.info(f"Extracted {len(page_usernames)} unique profiles on page {page_num}.")
    return page_usernames

def run_playwright_discovery(keyword: str, max_pages: int = 3, headless: bool = True) -> dict:
    """
    Run multi-variant discovery on Bing. 
    Returns dict: {'profiles': [...], 'source': 'bing', 'status': 'success|bot_blocked'}
    Each profile dict contains keys: username, profile_url, bio, followers, following, posts.
    """
    logger.info(f"Starting Bing discovery for keyword: '{keyword}'")
    all_profiles = []
    seen = set()
    
    query_variants = [
        f'intitle:"{keyword}" site:instagram.com',
        f'site:instagram.com "{keyword}"',
        f'site:instagram.com "{keyword} store"',
    ]

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
    ]
    
    VIEWPORTS = [
        {"width": 1280, "height": 800},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
        {"width": 1920, "height": 1080}
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport=random.choice(VIEWPORTS),
                locale="en-US",
                timezone_id="America/New_York"
            )
            page = context.new_page()

            for variant_idx, query in enumerate(query_variants, 1):
                logger.info(f"--- Query variant {variant_idx}/{len(query_variants)}: {query} ---")
                
                # Retry mechanism for each query variant
                retries = 2
                success = False
                while retries > 0 and not success:
                    ok = _type_and_search(page, query)
                    if not ok:
                        logger.warning("Search failed, retrying...")
                        retries -= 1
                        time.sleep(3)
                        continue
                    
                    try:
                        for page_num in range(1, max_pages + 1):
                            if page_num > 1:
                                next_btn = page.locator('a[title="Next page"]').first
                                if not next_btn.is_visible():
                                    next_btn = page.locator('.sb_pagN').first
                                if next_btn.count() > 0 and next_btn.is_visible():
                                    logger.info(f"Navigating to page {page_num}...")
                                    next_btn.click()
                                else:
                                    logger.info("No next page button found.")
                                    break
                            
                            new_profiles = _extract_from_results(page, page_num, seen, keyword)
                            if not new_profiles:
                                logger.info(f"No valid profiles found on page {page_num}, stopping pagination for this variant.")
                                break
                            
                            all_profiles.extend(new_profiles)
                            success = True
                            
                            if page_num < max_pages:
                                time.sleep(random.uniform(2, 4))
                    except RuntimeError as re:
                        if str(re) == "BOT_PROTECTION":
                            logger.error("Bot protection hit, aborting Bing discovery.")
                            browser.close()
                            return {'profiles': all_profiles, 'source': 'bing', 'status': 'bot_blocked'}
                    except Exception as e:
                        logger.error(f"Error during variant {variant_idx} extraction: {e}")
                    
                    if not success:
                        retries -= 1
                        time.sleep(2)
                
                time.sleep(random.uniform(2, 3))

            browser.close()
    except Exception as e:
        logger.error(f"Playwright execution failed: {e}")

    return {
        'profiles': all_profiles, 
        'source': 'bing', 
        'status': 'success' if all_profiles else 'no_results'
    }

    """
    Run multi-variant discovery on Bing. 
    Returns dict: {'usernames': [...], 'source': 'bing', 'status': 'success|bot_blocked'}
    """
    logger.info(f"Starting Bing discovery for keyword: '{keyword}'")
    all_usernames = []
    seen = set()
    
    query_variants = [
        f'intitle:"{keyword}" site:instagram.com',
        f'site:instagram.com "{keyword}"',
        f'site:instagram.com "{keyword} store"',
    ]

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
    ]
    
    VIEWPORTS = [
        {"width": 1280, "height": 800},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
        {"width": 1920, "height": 1080}
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport=random.choice(VIEWPORTS),
                locale="en-US",
                timezone_id="America/New_York"
            )
            page = context.new_page()

            for variant_idx, query in enumerate(query_variants, 1):
                logger.info(f"--- Query variant {variant_idx}/{len(query_variants)}: {query} ---")
                
                # Retry mechanism for each query variant
                retries = 2
                success = False
                while retries > 0 and not success:
                    ok = _type_and_search(page, query)
                    if not ok:
                        logger.warning("Search failed, retrying...")
                        retries -= 1
                        time.sleep(3)
                        continue
                    
                    try:
                        for page_num in range(1, max_pages + 1):
                            if page_num > 1:
                                next_btn = page.locator('a[title="Next page"]').first
                                if not next_btn.is_visible():
                                    next_btn = page.locator('.sb_pagN').first
                                if next_btn.count() > 0 and next_btn.is_visible():
                                    logger.info(f"Navigating to page {page_num}...")
                                    next_btn.click()
                                else:
                                    logger.info("No next page button found.")
                                    break
                            
                            new_usernames = _extract_from_results(page, page_num, seen, keyword)
                            if not new_usernames:
                                logger.info(f"No valid profiles found on page {page_num}, stopping pagination for this variant.")
                                break
                            
                            all_usernames.extend(new_usernames)
                            success = True
                            
                            if page_num < max_pages:
                                time.sleep(random.uniform(2, 4))
                                
                    except RuntimeError as re:
                        if str(re) == "BOT_PROTECTION":
                            logger.error("Bot protection hit, aborting Bing discovery.")
                            browser.close()
                            return {'usernames': all_usernames, 'source': 'bing', 'status': 'bot_blocked'}
                    except Exception as e:
                        logger.error(f"Error during variant {variant_idx} extraction: {e}")
                    
                    if not success:
                        retries -= 1
                        time.sleep(2)
                
                time.sleep(random.uniform(2, 3))

            browser.close()
    except Exception as e:
        logger.error(f"Playwright execution failed: {e}")

    return {
        'usernames': all_usernames, 
        'source': 'bing', 
        'status': 'success' if all_usernames else 'no_results'
    }
