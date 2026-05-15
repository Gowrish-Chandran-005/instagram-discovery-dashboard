"""
Phase 11 - Add Related Account Discovery
Discovers related/suggested accounts from a public Instagram profile.
Collects and extracts data from suggested accounts to expand the account network.
"""

from playwright.sync_api import sync_playwright
import json


def extract_profile_data(page, username):
    """
    Extract profile data from Instagram profile page.
    
    Args:
        page: Playwright page object
        username: Instagram username being scraped
        
    Returns:
        Dictionary containing profile data
    """
    
    profile_data = {
        "username": username,
        "bio": None
    }
    
    try:
        # Wait for profile to load
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        # Extract username
        try:
            username_element = page.locator("header h2")
            if username_element.count() > 0:
                profile_data["username"] = username_element.first.text_content().strip()
        except:
            pass
        
        # Extract bio
        try:
            bio_locators = page.locator("header span")
            for i in range(bio_locators.count()):
                text = bio_locators.nth(i).text_content()
                if text and text.strip() and len(text.strip()) > 5:
                    if not text.strip().isdigit():
                        profile_data["bio"] = text.strip()
                        break
        except:
            pass
    
    except Exception as e:
        print(f"Error during profile extraction: {e}")
    
    return profile_data


def collect_related_accounts(page, max_related=5):
    """
    Collect related/suggested accounts from current profile page.
    
    Args:
        page: Playwright page object
        max_related: Maximum related accounts to collect
        
    Returns:
        List of usernames
    """
    
    related_usernames = []
    
    try:
        # Look for suggested accounts section
        # This is typically below the bio section
        print("  Looking for related/suggested accounts...")
        page.wait_for_timeout(2000)
        
        # Try to locate suggested accounts in various places
        # Instagram suggests accounts in different formats. Use a safer selector
        # for anchors whose href starts with '/' then filter out '/'.
        suggested_links = page.locator("a[href^='/']")

        if suggested_links.count() > 0:
            for i in range(suggested_links.count()):
                try:
                    href = suggested_links.nth(i).get_attribute("href")
                    if href and href.startswith("/") and href != "/":
                        # Extract username from href
                        username = href.strip("/").split("/")[0]
                        
                        # Validate username (allow dots/underscores and alphanumerics)
                        if username and ("." in username or "_" in username or username.isalnum()):
                            if username not in related_usernames and len(related_usernames) < max_related:
                                related_usernames.append(username)
                except:
                    pass
        
        print(f"  Found {len(related_usernames)} related accounts")
        
    except Exception as e:
        print(f"  Error collecting related accounts: {e}")
    
    return related_usernames


def main():
    """Main function - discover related accounts and extract profile data."""
    
    start_username = "nike"
    max_related_per_profile = 3
    discovery_depth = 2  # Limit depth to avoid infinite crawling
    
    with sync_playwright() as p:
        try:
            # Launch Chromium browser
            print("=" * 60)
            print("Phase 11 - Add Related Account Discovery")
            print("=" * 60)
            print(f"\nStarting discovery from: @{start_username}")
            print(f"Discovery depth: {discovery_depth} levels")
            print(f"Max related per profile: {max_related_per_profile}\n")
            
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # Track discovered profiles
            discovered_profiles = []
            processed_usernames = set()
            to_process = [start_username]
            current_depth = 0
            
            # Iterative discovery with depth limit
            while to_process and current_depth < discovery_depth:
                print(f"\n{'='*60}")
                print(f"DISCOVERY LEVEL {current_depth + 1}")
                print(f"{'='*60}\n")
                
                next_level = []
                
                for username in to_process:
                    if username in processed_usernames:
                        continue
                    
                    try:
                        print(f"[PROCESSING] @{username}")
                        
                        # Navigate to profile
                        profile_url = f"https://instagram.com/{username}"
                        page.goto(profile_url)
                        
                        # Extract profile data
                        profile_data = extract_profile_data(page, username)
                        discovered_profiles.append(profile_data)
                        print(f"  ✓ Profile data extracted")
                        
                        # Collect related accounts
                        related = collect_related_accounts(page, max_related_per_profile)
                        print(f"  Related accounts: {', '.join(related)}")
                        
                        # Add to next level
                        for related_user in related:
                            if related_user not in processed_usernames:
                                next_level.append(related_user)
                        
                        processed_usernames.add(username)
                        print()
                        
                    except Exception as e:
                        print(f"  ✗ Error processing @{username}: {e}\n")
                        processed_usernames.add(username)
                
                to_process = next_level
                current_depth += 1
            
            # Display results
            print("=" * 60)
            print("DISCOVERY COMPLETE")
            print("=" * 60)
            print(f"\nTotal profiles discovered: {len(discovered_profiles)}")
            print(f"Total profiles processed: {len(processed_usernames)}\n")
            
            print("DISCOVERED PROFILES:")
            print(json.dumps(discovered_profiles, indent=2, ensure_ascii=False))
            
            # Statistics
            print("\n" + "=" * 60)
            print("DISCOVERY STATISTICS")
            print("=" * 60)
            print(f"Starting profile: @{start_username}")
            print(f"Discovery levels: {discovery_depth}")
            print(f"Profiles extracted: {len(discovered_profiles)}")
            print(f"Profiles with bio: {len([p for p in discovered_profiles if p['bio']])}")
            print("=" * 60)
            
            # Wait before closing
            print("\nWaiting 5 seconds before closing...")
            page.wait_for_timeout(5000)
            
            browser.close()
            print("Browser closed successfully\n")
            
        except Exception as e:
            print(f"\nError occurred: {e}")
            raise


if __name__ == "__main__":
    main()
