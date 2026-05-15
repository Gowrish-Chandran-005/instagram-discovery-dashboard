"""
Phase 7 - Open Search Results & Extract Profiles
Searches Instagram for a keyword, collects usernames, and extracts profile data from first 3 results.
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
        
        # Extract username from page header
        try:
            username_element = page.locator("header h2")
            if username_element.count() > 0:
                profile_data["username"] = username_element.first.text_content().strip()
        except Exception as e:
            print(f"    Could not extract username: {e}")
        
        # Extract bio
        try:
            bio_locators = page.locator("header span")
            for i in range(bio_locators.count()):
                text = bio_locators.nth(i).text_content()
                if text and text.strip() and len(text.strip()) > 5:
                    # Look for bio text (longer strings that aren't just numbers)
                    if not text.strip().isdigit():
                        profile_data["bio"] = text.strip()
                        break
        except Exception as e:
            print(f"    Could not extract bio: {e}")
    
    except Exception as e:
        print(f"  Error during profile extraction: {e}")
    
    return profile_data


def main():
    """Main function - search Instagram and extract profile data."""
    
    search_keyword = "posters"
    max_profiles_to_extract = 3
    
    with sync_playwright() as p:
        try:
            # Launch Chromium browser in non-headless mode
            print("=" * 60)
            print("Phase 7 - Open Search Results & Extract Profiles")
            print("=" * 60)
            print(f"\nSearching for keyword: '{search_keyword}'")
            print(f"Will extract data from first {max_profiles_to_extract} profiles\n")
            
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # Navigate to Instagram homepage
            print("Opening Instagram homepage...")
            page.goto("https://instagram.com")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            # Search for keyword
            print(f"Searching for '{search_keyword}'...")
            search_input = page.locator("input[placeholder*='Search']")

            usernames = []
            if search_input.count() == 0:
                print("Search input not available (Instagram may require login)."
                      " Falling back to direct profile URLs is recommended.")
            else:
                try:
                    search_input.wait_for(state="visible", timeout=5000)
                    search_input.click()
                    search_input.type(search_keyword, delay=100)
                    page.wait_for_timeout(3000)

                    # Collect visible usernames from search results
                    print("Collecting usernames from search results...")
                    result_items = page.locator("[role='button'][tabindex='0']")
                    
                    if result_items.count() > 0:
                        for i in range(min(result_items.count(), max_profiles_to_extract + 2)):
                            try:
                                item_text = result_items.nth(i).text_content()
                                if item_text and item_text.strip():
                                    usernames.append(item_text.strip())
                            except:
                                pass
                except Exception as e:
                    print(f"Search interaction failed: {e}")
            
            print(f"Found {len(usernames)} usernames")
            
            # Open profiles and extract data
            extracted_profiles = []
            
            for idx, username in enumerate(usernames[:max_profiles_to_extract]):
                try:
                    print(f"\n[{idx + 1}] Opening profile: @{username}")
                    
                    # Navigate to profile
                    profile_url = f"https://instagram.com/{username}"
                    page.goto(profile_url)
                    
                    # Extract profile data
                    profile_data = extract_profile_data(page, username)
                    extracted_profiles.append(profile_data)
                    
                    print(f"    ✓ Profile data extracted")
                    print(f"    Username: {profile_data['username']}")
                    print(f"    Bio: {profile_data['bio'][:50] if profile_data['bio'] else 'None'}...")
                    
                except Exception as e:
                    print(f"    Error extracting profile {username}: {e}")
            
            # Print results as formatted JSON
            print("\n" + "=" * 60)
            print("EXTRACTED PROFILE DATA")
            print("=" * 60)
            print(json.dumps(extracted_profiles, indent=2))
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
