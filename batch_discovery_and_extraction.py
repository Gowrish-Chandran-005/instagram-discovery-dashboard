"""
batch_discovery_and_extraction.py

Orchestration module for Instagram profile discovery and extraction pipeline.

Architecture:
 - Discovery module: duckduckgo_instagram_discovery.py (finds usernames)
 - Extraction module: demo_playwright_extract.py (extracts metadata)
 - Orchestration module: this file (ties them together)

Flow:
 1. Load discovered_profiles.json (from discovery phase)
 2. For each discovered username:
    - Run extract_instagram_profile() from demo_playwright_extract.py
    - Handle errors gracefully
    - Apply random 3-6 second delay between profiles
    - Print progress and results
 3. Save all extracted profiles to extracted_profiles.json
 4. Print final summary (total discovered, extracted, failed)

Usage:
 python batch_discovery_and_extraction.py

Notes:
 - Reuses single browser instance for efficiency
 - Professional faculty-ready output with progress indicators
 - Modular: discovery, extraction, and orchestration are separate
"""

import json
import os
import re
import time
import random
import traceback
from typing import Dict, Any, List
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from colorama import Fore, Style, init as colorama_init

# Import extraction functions from demo_playwright_extract
from demo_playwright_extract import (
    extract_instagram_profile,
    log_stage,
)

# Initialize colorama for cross-platform colored output
colorama_init(autoreset=True)


def load_discovered_profiles(json_path: str = "backend/data/discovered_profiles.json") -> List[str]:
    """Load discovered Instagram usernames from JSON file.
    
    Returns a list of usernames, or empty list if file not found/invalid.
    """
    print(f"\n[INFO] Loading discovered profiles from {json_path}...")
    
    if not os.path.exists(json_path):
        print(f"[ERROR] File not found: {json_path}")
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        usernames = data.get('usernames', [])
        print(f"[SUCCESS] Loaded {len(usernames)} discovered usernames")
        return usernames
    
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {json_path}: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load {json_path}: {e}")
        return []


def apply_extraction_delay(min_seconds: int = 3, max_seconds: int = 6) -> None:
    """Apply random delay between profile extractions (rate limiting)."""
    delay = random.uniform(min_seconds, max_seconds)
    print(f"[INFO] Rate limiting: waiting {delay:.2f}s before next extraction...")
    time.sleep(delay)


def print_profile_separator(char: str = "=", width: int = 80) -> None:
    """Print a formatted separator line."""
    print(f"{char * width}")


def format_profile_output(profile: Dict[str, Any], username: str, index: int, total: int) -> str:
    """Format a single profile for display.
    
    Returns formatted string suitable for printing.
    """
    lines = []
    lines.append("")
    lines.append(f"[{index}/{total}] PROFILE: @{username}")
    lines.append("-" * 80)
    
    # Key fields
    lines.append(f"  Username:          {profile.get('username', 'N/A')}")
    lines.append(f"  Bio:               {profile.get('bio', 'N/A')[:70]}...")
    lines.append(f"  Followers:         {profile.get('followers', 0):,}")
    lines.append(f"  Following:         {profile.get('following', 0):,}")
    lines.append(f"  Posts:             {profile.get('posts', 0):,}")
    lines.append(f"  Website:           {profile.get('website', 'N/A')}")
    lines.append(f"  Profile Image:     {profile.get('profile_image', 'N/A')[:50]}...")
    lines.append(f"  Extraction Methods: {', '.join(profile.get('extraction_methods', []))}")
    
    # Timing
    timing = profile.get('_timing', {})
    if timing:
        lines.append(f"  Page Load Time:    {timing.get('page_load_seconds', 0):.2f}s")
        lines.append(f"  Extraction Time:   {timing.get('extraction_seconds', 0):.2f}s")
    
    return "\n".join(lines)


def extract_batch_profiles(usernames: List[str], browser, headless: bool = False) -> tuple[List[Dict], List[str], List[str]]:
    """Extract metadata for all discovered usernames.
    
    Args:
        usernames: List of Instagram usernames to extract
        browser: Playwright browser instance
        headless: Whether to run browser in headless mode
    
    Returns:
        (successful_profiles, successful_usernames, failed_usernames)
    """
    print(f"\n{'=' * 80}")
    print("BATCH EXTRACTION PHASE")
    print(f"{'=' * 80}")
    print(f"\n[INFO] Extracting metadata for {len(usernames)} discovered profiles...\n")
    
    successful_profiles: List[Dict] = []
    successful_usernames: List[str] = []
    failed_usernames: List[str] = []
    
    for idx, username in enumerate(usernames, 1):
        try:
            # Print progress indicator
            print(f"\n{Fore.CYAN}[{idx}/{len(usernames)}]{Style.RESET_ALL} Extracting @{username}...")
            
            # Create a new page for each profile (safer error handling)
            page = browser.new_page()
            
            try:
                # Extract profile with timing
                extraction_start = time.perf_counter()
                profile = extract_instagram_profile(page, username)
                extraction_end = time.perf_counter()
                extraction_duration = extraction_end - extraction_start
                
                # Suppress the pretty_print_profile() call; we'll handle formatting here
                print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Extracted @{username} in {extraction_duration:.2f}s")
                
                # Format and print profile details
                formatted = format_profile_output(profile, username, idx, len(usernames))
                print(formatted)
                
                # Add to successful list
                successful_profiles.append(profile)
                successful_usernames.append(username)
                
                print_profile_separator("-", 80)
                
            except Exception as e:
                print(f"{Fore.RED}[FAILED]{Style.RESET_ALL} Extraction error for @{username}: {e}")
                failed_usernames.append(username)
                print_profile_separator("-", 80)
            
            finally:
                try:
                    page.close()
                except Exception:
                    pass
            
            # Apply rate limiting delay (except for last profile)
            if idx < len(usernames):
                apply_extraction_delay(min_seconds=3, max_seconds=6)
        
        except Exception as e:
            print(f"{Fore.RED}[FAILED]{Style.RESET_ALL} Critical error for @{username}: {e}")
            traceback.print_exc()
            failed_usernames.append(username)
            print_profile_separator("-", 80)
    
    return successful_profiles, successful_usernames, failed_usernames


def save_extracted_profiles(profiles: List[Dict], usernames: List[str], 
                           discovery_method: str = "duckduckgo",
                           output_path: str = "backend/data/extracted_profiles.json") -> None:
    """Save extracted profiles to JSON file with metadata.
    
    Args:
        profiles: List of extracted profile dictionaries
        usernames: List of extracted usernames (for reference)
        discovery_method: Method used for discovery
        output_path: Path to save JSON file
    """
    print(f"\n[INFO] Saving {len(profiles)} extracted profiles to {output_path}...")
    
    output = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "discovery_method": discovery_method,
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


def print_final_summary(total_discovered: int, successful_usernames: List[str], 
                       failed_usernames: List[str]) -> None:
    """Print final batch processing summary."""
    total_extracted = len(successful_usernames)
    total_failed = len(failed_usernames)
    success_rate = (total_extracted / total_discovered * 100) if total_discovered > 0 else 0
    
    print(f"\n{'=' * 80}")
    print("BATCH PROCESSING SUMMARY")
    print(f"{'=' * 80}\n")
    
    print(f"{Fore.CYAN}Discovery Phase:{Style.RESET_ALL}")
    print(f"  Total profiles discovered:  {total_discovered}")
    
    print(f"\n{Fore.CYAN}Extraction Phase:{Style.RESET_ALL}")
    print(f"  Total extracted successfully: {Fore.GREEN}{total_extracted}{Style.RESET_ALL}")
    print(f"  Total extraction failures:    {Fore.RED if total_failed > 0 else Fore.GREEN}{total_failed}{Style.RESET_ALL}")
    print(f"  Success rate:                 {Fore.GREEN if success_rate >= 80 else Fore.YELLOW}{success_rate:.1f}%{Style.RESET_ALL}")
    
    if successful_usernames:
        print(f"\n{Fore.GREEN}Successfully Extracted ({len(successful_usernames)}):{Style.RESET_ALL}")
        for idx, u in enumerate(successful_usernames, 1):
            print(f"  {idx:2d}. @{u}")
    
    if failed_usernames:
        print(f"\n{Fore.RED}Failed Extractions ({len(failed_usernames)}):{Style.RESET_ALL}")
        for idx, u in enumerate(failed_usernames, 1):
            print(f"  {idx:2d}. @{u}")
    
    print(f"\n{'=' * 80}\n")


def run_batch_pipeline(discovered_json: str = "backend/data/discovered_profiles.json",
                       extracted_json: str = "backend/data/extracted_profiles.json",
                       headless: bool = False) -> None:
    """Main orchestration function: run complete discovery → extraction pipeline.
    
    Args:
        discovered_json: Path to discovered profiles JSON (from discovery phase)
        extracted_json: Path to save extracted profiles JSON
        headless: Whether to run browser headless
    """
    print("\n" + "=" * 80)
    print("INSTAGRAM PROFILE DISCOVERY & EXTRACTION PIPELINE")
    print("=" * 80)
    print(f"\n[INFO] Phase 1: Loading discovered profiles...")
    
    # Phase 1: Load discovered profiles
    usernames = load_discovered_profiles(discovered_json)
    if not usernames:
        # Keep discovery logic unchanged; provide fallback test usernames for extraction
        print("[WARNING] No discovered profiles found.")
        print("Using fallback test profiles.")
        usernames = [
            "nike",
            "cristiano",
            "posterlounge",
        ]
    
    print(f"\n[INFO] Phase 2: Launching browser and extracting metadata...")
    
    # Phase 2: Launch browser and extract
    try:
        with sync_playwright() as p:
            log_stage('Launching Chromium (non-headless for demo)...', 'INFO')
            browser = p.chromium.launch(headless=headless)
            
            # Run batch extraction
            successful_profiles, successful_usernames, failed_usernames = extract_batch_profiles(
                usernames, 
                browser,
                headless=headless
            )
            
            # Close browser
            browser.close()
            log_stage('Browser closed', 'SUCCESS')
            
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Fatal error during extraction: {e}")
        traceback.print_exc()
        return
    
    # Phase 3: Save results
    print(f"\n[INFO] Phase 3: Saving extracted profiles...")
    save_extracted_profiles(successful_profiles, successful_usernames, output_path=extracted_json)
    
    # Phase 4: Print summary
    print_final_summary(len(usernames), successful_usernames, failed_usernames)


if __name__ == '__main__':
    try:
        run_batch_pipeline(
            discovered_json="backend/data/discovered_profiles.json",
            extracted_json="backend/data/extracted_profiles.json",
            headless=False  # Non-headless for faculty demo visibility
        )
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[INFO]{Style.RESET_ALL} Pipeline interrupted by user.")
    except Exception as e:
        print(f"\n{Fore.RED}[ERROR]{Style.RESET_ALL} Fatal error: {e}")
        traceback.print_exc()
