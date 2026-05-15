"""
Instagram Structured Metadata Extractor - Main Entry Point

Professional profile extraction using:
1. JSON-LD (primary)
2. Meta tags (primary)
3. DOM selectors (fallback)

This is the recommended way to extract Instagram profile data.
"""

import json
from playwright.sync_api import sync_playwright
from extractor import extract_instagram_profile, format_profile_output


def extract_profile(username):
    """
    Extract Instagram profile for a given username.
    
    Args:
        username: Instagram username (without @)
        
    Returns:
        Dictionary with extracted profile data
    """
    
    print("\n" + "=" * 60)
    print(f"INSTAGRAM STRUCTURED METADATA EXTRACTOR")
    print("=" * 60)
    print(f"\nExtracting profile: @{username}")
    print(f"URL: https://instagram.com/{username}\n")
    
    with sync_playwright() as p:
        # Launch browser
        print("Launching Chromium browser (non-headless)...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # Navigate to profile
            profile_url = f"https://instagram.com/{username}"
            print(f"Opening {profile_url}...")
            page.goto(profile_url)
            
            # Wait for page to load
            print("Waiting for page to load (networkidle)...")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            # Extract profile using structured methods
            print("\nExtracting profile data using structured methods:\n")
            profile = extract_instagram_profile(page, username)
            
            # Display formatted output
            print("\n" + format_profile_output(profile))
            
            # Display raw JSON
            print("\nRAW JSON OUTPUT:")
            print("=" * 60)
            
            # Prepare JSON-friendly output (remove raw fields)
            json_profile = {k: v for k, v in profile.items() 
                          if not k.startswith('raw_') and k != 'extraction_methods'}
            json_profile['extraction_methods'] = profile.get('extraction_methods', [])
            
            print(json.dumps(json_profile, indent=2))
            print("=" * 60)
            
            # Wait before closing
            print("\nWaiting 5 seconds before closing browser...")
            page.wait_for_timeout(5000)
            
            return profile
            
        except Exception as e:
            print(f"\n✗ Error during extraction: {e}")
            return None
        
        finally:
            browser.close()
            print("Browser closed")


def extract_multiple_profiles(usernames):
    """
    Extract multiple Instagram profiles.
    
    Args:
        usernames: List of Instagram usernames
        
    Returns:
        List of extracted profiles
    """
    
    results = []
    for username in usernames:
        try:
            profile = extract_profile(username)
            if profile:
                results.append(profile)
        except Exception as e:
            print(f"Error extracting {username}: {e}")
    
    return results


if __name__ == "__main__":
    # Example 1: Single profile extraction
    print("\n" + "🎯 EXAMPLE 1: Single Profile Extraction" + "\n")
    profile = extract_profile("nike")
    
    # Example 2: Multiple profiles (uncomment to use)
    # print("\n" + "🎯 EXAMPLE 2: Multiple Profile Extraction" + "\n")
    # usernames = ["nike", "adidas", "puma"]
    # results = extract_multiple_profiles(usernames)
    # print(f"\nExtracted {len(results)} profiles")
