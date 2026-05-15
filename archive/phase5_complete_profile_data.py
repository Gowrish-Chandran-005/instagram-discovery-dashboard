"""
Phase 5 - Extract Complete Instagram Profile Data
Opens a public Instagram profile and extracts all profile information.
Stores data in a dictionary and outputs as formatted JSON.
"""

from playwright.sync_api import sync_playwright
import json


def extract_profile_data(page, username):
    """
    Extract all profile data from Instagram profile page.
    
    Args:
        page: Playwright page object
        username: Instagram username being scraped
        
    Returns:
        Dictionary containing profile data
    """
    
    profile_data = {
        "username": username,
        "bio": None,
        "followers": None,
        "following": None,
        "posts": None
    }
    
    try:
        # Wait for profile to fully load
        print("Waiting for profile content to load...")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        
        # Extract username from page
        print("Extracting username...")
        try:
            username_element = page.locator("header h2")
            if username_element.count() > 0:
                profile_data["username"] = username_element.first.text_content().strip()
        except Exception as e:
            print(f"Could not extract username: {e}")
        
        # Extract bio
        print("Extracting bio...")
        try:
            bio_locators = page.locator("header span")
            bio_text = None
            for i in range(bio_locators.count()):
                text = bio_locators.nth(i).text_content()
                if text and text.strip() and not text.strip().isdigit():
                    if len(text.strip()) > 5:
                        bio_text = text.strip()
                        break

            # Fallback to meta tags if no bio text found
            if not bio_text:
                try:
                    meta = page.locator("meta[property='og:description']").get_attribute('content')
                except Exception:
                    meta = None
                if not meta:
                    try:
                        meta = page.locator("meta[name='description']").get_attribute('content')
                    except Exception:
                        meta = None
                if meta:
                    bio_text = meta

            if bio_text:
                profile_data["bio"] = bio_text
        except Exception as e:
            print(f"Could not extract bio: {e}")
        
        # Extract followers, following, and posts count
        print("Extracting stats (followers, following, posts)...")
        try:
            # Look for stat buttons in the header
            stats = page.locator("header button")
            stat_count = 0
            
            for i in range(stats.count()):
                stat_text = stats.nth(i).text_content()
                if stat_text and stat_text.strip():
                    # Parse the stat text which is typically "count label" format
                    parts = stat_text.strip().split()
                    if parts and parts[0].replace(",", "").isdigit():
                        count = parts[0]
                        
                        # Assign to appropriate field
                        if stat_count == 0:
                            profile_data["posts"] = count
                            print(f"  Posts: {count}")
                        elif stat_count == 1:
                            profile_data["followers"] = count
                            print(f"  Followers: {count}")
                        elif stat_count == 2:
                            profile_data["following"] = count
                            print(f"  Following: {count}")
                        
                        stat_count += 1
                        
                        if stat_count >= 3:
                            break
        except Exception as e:
            print(f"Could not extract stats: {e}")
        
    except Exception as e:
        print(f"Error during data extraction: {e}")
    
    return profile_data


def main():
    """Main function - open Instagram profile and extract data."""
    
    instagram_username = "nike"
    
    with sync_playwright() as p:
        try:
            # Launch Chromium browser in non-headless mode
            print("=" * 50)
            print("Phase 5 - Extract Complete Instagram Profile Data")
            print("=" * 50)
            print(f"\nLaunching Chromium browser...")
            browser = p.chromium.launch(headless=False)
            
            # Create a new page/tab
            page = browser.new_page()
            
            # Navigate to Instagram profile
            profile_url = f"https://instagram.com/{instagram_username}"
            print(f"Opening Instagram profile: {profile_url}\n")
            page.goto(profile_url)
            
            # Extract all profile data
            profile_data = extract_profile_data(page, instagram_username)
            
            # Print results
            print("\n" + "=" * 50)
            print("EXTRACTED PROFILE DATA")
            print("=" * 50)
            print(json.dumps(profile_data, indent=2))
            print("=" * 50)
            
            # Wait before closing so user can see the page
            print("\nWaiting 5 seconds before closing browser...")
            page.wait_for_timeout(5000)
            
            # Close the browser
            browser.close()
            print("Browser closed successfully\n")
            
        except Exception as e:
            # Handle any errors that occur
            print(f"\nError occurred: {e}")
            raise


if __name__ == "__main__":
    main()
