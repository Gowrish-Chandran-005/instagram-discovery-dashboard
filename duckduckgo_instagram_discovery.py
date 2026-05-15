"""
duckduckgo_instagram_discovery.py

Discover Instagram profile usernames via DuckDuckGo HTML search AND extract metadata.

Usage: python duckduckgo_instagram_discovery.py

Flow:
 - Prompt the user for a keyword
 - Search DuckDuckGo with "site:instagram.com <keyword>" (paginated up to 5 pages)
 - Parse HTML with BeautifulSoup to extract links from each page
 - Filter for valid Instagram profile URLs
 - Extract usernames, deduplicate
 - FOR EACH DISCOVERED USERNAME:
   - Extract structured metadata via Playwright
   - Apply 3-6 second rate limiting delays
   - Print formatted profile output
   - Collect results
 - Save all extracted profiles to extracted_profiles.json

Features:
 - Discovery: Pagination support (5 pages), 2-5s delays, deduplication
 - Extraction: Structured metadata (bio, followers, posts, website, image)
 - Professional output: Progress indicators, colored logs, formatted profiles
 - Error handling: Gracefully skips failed extractions
 - Rate limiting: 3-6s delays between profile extractions

Notes:
 - Discovery uses requests + BeautifulSoup (fast, no browser)
 - Extraction uses Playwright (accurate, handles dynamic content)
 - Suitable for faculty demonstration with real browser visibility
"""

import json
import re
import time
import random
import traceback
import os
from typing import List, Set, Dict, Any
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from colorama import Fore, Style, init as colorama_init

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"[ERROR] Missing dependencies: {e}")
    print("[INFO] Install with: pip install requests beautifulsoup4")
    raise

# Import extraction functions from demo_playwright_extract
try:
    from demo_playwright_extract import extract_instagram_profile, log_stage
except ImportError as e:
    print(f"[ERROR] Failed to import extraction module: {e}")
    print("[INFO] Make sure demo_playwright_extract.py is in the same directory")
    raise

# Initialize colorama for cross-platform colored output
colorama_init(autoreset=True)


def get_user_agent() -> str:
    """Return a polite user agent string."""
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


def prompt_keyword() -> str:
    """Prompt the user for a discovery keyword."""
    kw = input("Enter discovery keyword (e.g. posters): ").strip()
    return kw


def search_duckduckgo(query: str, page: int = 1) -> str | None:
    """Fetch DuckDuckGo search results for the given query and page.

    Args:
        query: Search query string
        page: Page number (1-indexed)

    Returns HTML content or None on failure.
    """
    print(f"[INFO] Searching DuckDuckGo for: {query} (page {page})")
    url = "https://duckduckgo.com/html/"
    
    # DuckDuckGo pagination: s parameter represents offset
    # Page 1 = no offset, Page 2 = 30, Page 3 = 60, etc.
    offset = (page - 1) * 30
    
    params = {
        "q": query,
        "s": offset if page > 1 else None,  # s parameter for pagination
    }
    # Remove None values from params
    params = {k: v for k, v in params.items() if v is not None}
    
    headers = {
        "User-Agent": get_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        print(f"[DEBUG] Sending request to DuckDuckGo (page {page}, offset {offset})...")
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"[SUCCESS] Got response with status {response.status_code} (page {page})")
        print(f"[DEBUG] Response size: {len(response.text)} bytes")
        return response.text
    except requests.Timeout:
        print(f"[ERROR] Request timed out (30s) on page {page}")
        return None
    except requests.RequestException as e:
        print(f"[ERROR] Request failed on page {page}: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error during search on page {page}: {e}")
        traceback.print_exc()
        return None


def extract_links_from_html(html_content: str) -> List[str]:
    """Parse HTML and extract all href attributes from search results.

    Returns a list of URLs found.
    """
    print("[INFO] Parsing HTML search results...")
    links = []

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        print("[DEBUG] BeautifulSoup parsing successful")

        # Find all anchor tags
        anchors = soup.find_all("a")
        print(f"[DEBUG] Found {len(anchors)} total anchors in page")

        # Extract hrefs
        for idx, a in enumerate(anchors):
            try:
                href = a.get("href")
                if href and isinstance(href, str) and href.startswith("http"):
                    links.append(href)
            except Exception as e:
                print(f"[DEBUG] Error processing anchor {idx}: {e}")
                continue

        print(f"[INFO] Extracted {len(links)} HTTP links")

    except Exception as e:
        print(f"[ERROR] Failed to parse HTML: {e}")
        traceback.print_exc()
        return []

    return links


def is_profile_url(href: str) -> bool:
    """Return True if href looks like an Instagram profile URL (not post/reel/explore/hashtag).

    Examples accepted:
      https://www.instagram.com/nike/
      https://instagram.com/nike
    Excludes URLs containing '/p/', '/reel/', '/explore', '/tags', 'accounts/login', '/stories/'
    """
    if "instagram.com" not in href:
        return False

    # Normalize
    href_lower = href.lower()

    # Reject common non-profile paths
    reject_patterns = [
        "/p/",
        "/reel/",
        "/explore",
        "/tags",
        "/tv/",
        "/stories/",
        "/graphql/",
        "/accounts/login",
        "/api/",
    ]
    for rp in reject_patterns:
        if rp in href_lower:
            return False

    # Accept if path is just /{username}/ optionally with query or trailing slash
    m = re.search(r"instagram\.com/([^/?#]+)", href)
    if not m:
        return False

    username = m.group(1)

    # Exclude short or invalid username candidates
    if len(username) < 2 or username.isdigit():
        return False

    # Reject common non-profile tokens
    if username in ("explore", "p", "stories", "reel", "accounts", "api"):
        return False

    return True


def extract_username_from_url(href: str) -> str | None:
    """Extract username segment from an Instagram profile URL.

    Returns the username string or None if not found.
    """
    try:
        m = re.search(r"instagram\.com/([A-Za-z0-9._]+)/?", href)
        if m:
            return m.group(1).strip("/")
    except Exception:
        return None
    return None


def apply_random_delay(min_seconds: int = 2, max_seconds: int = 5) -> None:
    """Apply a random delay between requests for rate limiting.
    
    Args:
        min_seconds: Minimum delay in seconds (default 2)
        max_seconds: Maximum delay in seconds (default 5)
    """
    delay = random.uniform(min_seconds, max_seconds)
    print(f"[INFO] Rate limiting: waiting {delay:.2f} seconds...")
    time.sleep(delay)


def apply_extraction_delay(min_seconds: int = 3, max_seconds: int = 6) -> None:
    """Apply random delay between profile extractions.
    
    Args:
        min_seconds: Minimum delay in seconds (default 3)
        max_seconds: Maximum delay in seconds (default 6)
    """
    delay = random.uniform(min_seconds, max_seconds)
    print(f"{Fore.CYAN}[DELAY]{Style.RESET_ALL} Waiting {delay:.2f}s before next extraction...")
    time.sleep(delay)


def print_profile_separator(width: int = 80) -> None:
    """Print a formatted separator line."""
    print("=" * width)


def format_profile_output(profile: Dict[str, Any], index: int, total: int) -> str:
    """Format a single extracted profile for display.
    
    Returns formatted string suitable for printing.
    """
    lines = []
    lines.append("")
    lines.append(f"PROFILE #{index}/{total}: @{profile.get('username', 'UNKNOWN')}")
    lines.append("=" * 80)
    
    # Extract fields
    username = profile.get('username', 'N/A')
    bio = profile.get('bio', 'N/A')[:70]
    followers = profile.get('followers', 0)
    following = profile.get('following', 0)
    posts = profile.get('posts', 0)
    website = profile.get('website', 'N/A')[:70]
    methods = ', '.join(profile.get('extraction_methods', []))
    
    lines.append(f"\nUsername:          {username}")
    lines.append(f"Bio:               {bio}")
    lines.append(f"Followers:         {followers:,}")
    lines.append(f"Following:         {following:,}")
    lines.append(f"Posts:             {posts:,}")
    lines.append(f"Website:           {website}")
    lines.append(f"Methods Used:      {methods}")
    
    # Timing
    timing = profile.get('_timing', {})
    if timing:
        lines.append(f"\nPage Load Time:    {timing.get('page_load_seconds', 0):.2f}s")
        lines.append(f"Extraction Time:   {timing.get('extraction_seconds', 0):.2f}s")
    
    lines.append("\n" + "=" * 80)
    
    return "\n".join(lines)


def extract_discovered_profiles(usernames: List[str], browser) -> tuple[List[Dict], List[str], List[str]]:
    """Extract metadata for all discovered usernames.
    
    Args:
        usernames: List of Instagram usernames to extract
        browser: Playwright browser instance
    
    Returns:
        (successful_profiles, successful_usernames, failed_usernames)
    """
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}PHASE 2: EXTRACTING METADATA FOR {len(usernames)} PROFILES{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    successful_profiles: List[Dict] = []
    successful_usernames: List[str] = []
    failed_usernames: List[str] = []
    
    for idx, username in enumerate(usernames, 1):
        try:
            # Progress indicator
            print(f"{Fore.CYAN}[{idx}/{len(usernames)}]{Style.RESET_ALL} Extracting @{username}...")
            
            # Create a new page for each profile
            page = browser.new_page()
            
            try:
                # Extract profile with timing
                extraction_start = time.perf_counter()
                profile = extract_instagram_profile(page, username)
                extraction_end = time.perf_counter()
                extraction_duration = extraction_end - extraction_start
                
                # Log success
                print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Extracted @{username} in {extraction_duration:.2f}s")
                
                # Format and print profile details
                formatted = format_profile_output(profile, idx, len(usernames))
                print(formatted)
                
                # Add to successful list
                successful_profiles.append(profile)
                successful_usernames.append(username)
                
            except PWTimeout as e:
                print(f"{Fore.YELLOW}[TIMEOUT]{Style.RESET_ALL} Page load timed out for @{username}")
                failed_usernames.append(username)
            except Exception as e:
                print(f"{Fore.RED}[FAILED]{Style.RESET_ALL} Extraction error for @{username}: {str(e)[:50]}")
                failed_usernames.append(username)
            
            finally:
                try:
                    page.close()
                except Exception:
                    pass
            
            # Apply rate limiting delay (except for last profile)
            if idx < len(usernames):
                apply_extraction_delay(min_seconds=3, max_seconds=6)
        
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Critical error for @{username}: {str(e)[:50]}")
            failed_usernames.append(username)
    
    return successful_profiles, successful_usernames, failed_usernames


def save_extracted_profiles(profiles: List[Dict], usernames: List[str],
                           output_path: str = "backend/data/extracted_profiles.json") -> None:
    """Save extracted profiles to JSON file with metadata.
    
    Args:
        profiles: List of extracted profile dictionaries
        usernames: List of successfully extracted usernames
        output_path: Path to save JSON file
    """
    print(f"\n{Fore.CYAN}[INFO]{Style.RESET_ALL} Saving {len(profiles)} extracted profiles to {output_path}...")
    
    output = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "discovery_method": "duckduckgo",
        "extraction_count": len(profiles),
        "usernames_extracted": usernames,
        "profiles": profiles,
    }
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Saved to {output_path}")
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to save {output_path}: {e}")
        traceback.print_exc()


def print_extraction_summary(total_discovered: int, successful_usernames: List[str],
                            failed_usernames: List[str]) -> None:
    """Print final extraction summary."""
    total_extracted = len(successful_usernames)
    total_failed = len(failed_usernames)
    success_rate = (total_extracted / total_discovered * 100) if total_discovered > 0 else 0
    
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}EXTRACTION SUMMARY{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"Discovery Results:")
    print(f"  Total profiles discovered:  {total_discovered}")
    
    print(f"\nExtraction Results:")
    print(f"  Successfully extracted:     {Fore.GREEN}{total_extracted}{Style.RESET_ALL}")
    print(f"  Failed extractions:         {Fore.RED if total_failed > 0 else Fore.GREEN}{total_failed}{Style.RESET_ALL}")
    print(f"  Success rate:               {Fore.GREEN if success_rate >= 80 else Fore.YELLOW}{success_rate:.1f}%{Style.RESET_ALL}")
    
    if successful_usernames:
        print(f"\n{Fore.GREEN}Successfully Extracted ({len(successful_usernames)}):{Style.RESET_ALL}")
        for idx, u in enumerate(successful_usernames, 1):
            print(f"  {idx:2d}. @{u}")
    
    if failed_usernames:
        print(f"\n{Fore.RED}Failed Extractions ({len(failed_usernames)}):{Style.RESET_ALL}")
        for idx, u in enumerate(failed_usernames, 1):
            print(f"  {idx:2d}. @{u}")
    
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")


def filter_and_deduplicate(links: List[str]) -> tuple[List[str], List[str]]:
    """Filter raw links to valid Instagram profile usernames and remove duplicates.

    Returns (usernames, profile_urls) tuple.
    """
    print(f"[DEBUG] Filtering {len(links)} links for Instagram profiles...")
    usernames: List[str] = []
    profile_urls: List[str] = []
    seen: Set[str] = set()

    for href in links:
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
            print(f"[DEBUG] Error processing link: {e}")
            continue

    print(f"[INFO] Filtered to {len(usernames)} unique Instagram profiles")
    return usernames, profile_urls


def save_discovered_usernames(
    usernames: List[str], path: str = "backend/data/discovered_profiles.json"
) -> None:
    """Save discovered usernames to JSON file with timestamp."""
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "method": "duckduckgo",
        "count": len(usernames),
        "usernames": usernames,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[SUCCESS] Saved {len(usernames)} usernames to {path}")
    except Exception as e:
        print(f"[ERROR] Failed to save to {path}: {e}")


def run_discovery():
    """Main orchestration: DuckDuckGo discovery → Playwright extraction pipeline."""
    print("\n" + "=" * 80)
    print("INSTAGRAM DISCOVERY & EXTRACTION PIPELINE")
    print("=" * 80)
    print(f"\n{Fore.CYAN}PHASE 1: DISCOVERING PROFILES VIA DUCKDUCKGO{Style.RESET_ALL}\n")

    keyword = prompt_keyword()
    if not keyword:
        print("[ERROR] No keyword provided. Exiting.")
        return

    query = f"site:instagram.com {keyword}"
    print(f"[INFO] Discovery keyword: '{keyword}'")
    print(f"[INFO] Search query: {query}")
    print(f"[INFO] Scraping up to 5 pages with random 2-5 second delays...\n")

    # Global tracking across all pages
    all_usernames: List[str] = []
    all_urls: List[str] = []
    seen_usernames: Set[str] = set()
    
    # Per-page tracking
    page_stats: List[dict] = []
    
    max_pages = 5
    
    # Pagination loop
    for page_num in range(1, max_pages + 1):
        print(f"\n{'=' * 70}")
        print(f"PAGE {page_num}")
        print(f"{'=' * 70}")
        
        # Fetch search results for this page
        html_content = search_duckduckgo(query, page=page_num)
        if not html_content:
            print(f"[ERROR] Failed to fetch page {page_num}. Stopping pagination.")
            break
        
        # Extract links from this page
        links = extract_links_from_html(html_content)
        print(f"[DEBUG] Found {len(links)} total links on page {page_num}")
        
        if not links:
            print(f"[WARNING] No links extracted from page {page_num}. Stopping pagination.")
            break
        
        # Filter and deduplicate for this page
        page_usernames, page_urls = filter_and_deduplicate(links)
        
        # Track which usernames are NEW on this page
        new_usernames = []
        for u in page_usernames:
            if u not in seen_usernames:
                seen_usernames.add(u)
                new_usernames.append(u)
                all_usernames.append(u)
                all_urls.append(page_urls[page_usernames.index(u)])
        
        # Record per-page statistics
        page_stat = {
            "page": page_num,
            "profiles_found": len(page_usernames),
            "new_profiles": len(new_usernames),
            "cumulative_total": len(all_usernames),
        }
        page_stats.append(page_stat)
        
        print(f"\n[STATS] Page {page_num} Results:")
        print(f"  → Profiles found on page: {len(page_usernames)}")
        print(f"  → New profiles (not seen before): {len(new_usernames)}")
        print(f"  → Cumulative total: {len(all_usernames)}")
        
        # Stop if no new profiles found on this page
        if len(new_usernames) == 0:
            print(f"[INFO] No new profiles found on page {page_num}. Stopping pagination.")
            break
        
        # Display profiles from this page
        if new_usernames:
            print(f"\n[INFO] New profiles discovered on page {page_num}:")
            for idx, u in enumerate(new_usernames, 1):
                print(f"  {idx}. @{u}")
        
        # Apply random delay before next page request (except on last page)
        if page_num < max_pages:
            apply_random_delay(min_seconds=2, max_seconds=5)
    
    # Final discovery summary
    print(f"\n{'=' * 70}")
    print("DISCOVERY PHASE COMPLETE")
    print(f"{'=' * 70}")
    
    print(f"\nPages Scraped: {len(page_stats)}")
    for stat in page_stats:
        print(f"  Page {stat['page']}: {stat['profiles_found']} profiles, {stat['new_profiles']} new → {stat['cumulative_total']} total")
    
    print(f"\nTotal Unique Profiles Discovered: {len(all_usernames)}")
    
    if not all_usernames:
        print("[INFO] No Instagram profiles discovered from search results.")
        return
    
    # Save discovered profiles
    save_discovered_usernames(all_usernames)
    
    # ========== EXTRACTION PHASE ==========
    # Launch browser and extract metadata for each profile
    print(f"\n{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting extraction phase with Playwright...")
    
    try:
        with sync_playwright() as p:
            log_stage('Launching Chromium (non-headless for visibility)...', 'INFO')
            browser = p.chromium.launch(headless=False)
            
            # Extract all discovered profiles
            successful_profiles, successful_usernames, failed_usernames = extract_discovered_profiles(
                all_usernames,
                browser
            )
            
            # Close browser
            browser.close()
            log_stage('Browser closed', 'SUCCESS')
    
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Fatal error during extraction: {e}")
        traceback.print_exc()
        return
    
    # Save extracted results
    save_extracted_profiles(successful_profiles, successful_usernames, output_path="backend/data/extracted_profiles.json")
    
    # Print final summary
    print_extraction_summary(len(all_usernames), successful_usernames, failed_usernames)
    print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Pipeline complete.")


if __name__ == "__main__":
    try:
        run_discovery()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[INFO]{Style.RESET_ALL} Pipeline interrupted by user.")
    except Exception as e:
        print(f"\n{Fore.RED}[ERROR]{Style.RESET_ALL} Fatal error: {e}")
        traceback.print_exc()
