"""
Phase 8 - Save Extracted Data Locally
Extends Instagram extraction to save profile data to a local JSON file.
"""

from playwright.sync_api import sync_playwright
import json
import os


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
        except Exception as e:
            print(f"    Could not extract username: {e}")
        
        # Extract bio
        try:
            bio_locators = page.locator("header span")
            for i in range(bio_locators.count()):
                text = bio_locators.nth(i).text_content()
                if text and text.strip() and len(text.strip()) > 5:
                    if not text.strip().isdigit():
                        profile_data["bio"] = text.strip()
                        break
        except Exception as e:
            print(f"    Could not extract bio: {e}")
    
    except Exception as e:
        print(f"  Error during profile extraction: {e}")
    
    return profile_data


def save_profiles_to_json(profiles, filename="profiles.json"):
    """
    Save extracted profiles to a JSON file.
    
    Args:
        profiles: List of profile dictionaries
        filename: Name of the JSON file to save
        
    Returns:
        Boolean indicating success
    """
    
    try:
        # Get the current directory
        current_dir = os.getcwd()
        filepath = os.path.join(current_dir, filename)
        
        # Write profiles to JSON file with pretty printing
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully saved {len(profiles)} profiles to '{filename}'")
        print(f"  File location: {filepath}")
        
        return True
        
    except IOError as e:
        print(f"✗ File write error: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"✗ JSON encoding error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error while saving: {e}")
        return False


def main():
    """Main function - search, extract, and save profile data."""
    
    search_keyword = "posters"
    max_profiles_to_extract = 3
    json_filename = "profiles.json"
    
    with sync_playwright() as p:
        try:
            # Launch Chromium browser
            print("=" * 60)
            print("Phase 8 - Save Extracted Data Locally")
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

                    # Collect visible usernames
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
            
            print(f"Found {len(usernames)} usernames\n")
            
            # Open profiles and extract data
            extracted_profiles = []
            
            for idx, username in enumerate(usernames[:max_profiles_to_extract]):
                try:
                    print(f"[{idx + 1}] Opening profile: @{username}")
                    
                    # Navigate to profile
                    profile_url = f"https://instagram.com/{username}"
                    page.goto(profile_url)
                    
                    # Extract profile data
                    profile_data = extract_profile_data(page, username)
                    extracted_profiles.append(profile_data)
                    
                    print(f"  ✓ Profile data extracted\n")
                    
                except Exception as e:
                    print(f"  ✗ Error extracting profile {username}: {e}\n")
            
            # Save to JSON file
            print("=" * 60)
            print("SAVING DATA")
            print("=" * 60)
            save_success = save_profiles_to_json(extracted_profiles, json_filename)
            
            if save_success:
                # Verify saved data by reading it back
                print("\nVerifying saved data...")
                try:
                    with open(json_filename, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                    print(f"✓ Verification successful - {len(saved_data)} profiles saved\n")
                except Exception as e:
                    print(f"✗ Verification failed: {e}\n")
            
            # Wait before closing
            print("Waiting 5 seconds before closing...")
            page.wait_for_timeout(5000)
            
            browser.close()
            print("Browser closed successfully\n")
            
        except Exception as e:
            print(f"\nError occurred: {e}")
            raise
