"""
Phase 2 - Open Public Instagram Profile
Opens a public Instagram profile, waits for it to load, and prints the page title.
"""

from playwright.sync_api import sync_playwright


def main():
    """Open Instagram profile and verify page loads."""
    
    with sync_playwright() as p:
        try:
            # Launch Chromium browser in non-headless mode (visible window)
            print("Launching Chromium browser...")
            browser = p.chromium.launch(headless=False)
            
            # Create a new page/tab
            page = browser.new_page()
            
            # Navigate to Nike's public Instagram profile
            print("Opening Instagram profile: https://instagram.com/nike")
            page.goto("https://instagram.com/nike")
            
            # Wait until network becomes idle (page fully loaded)
            print("Waiting for page to load...")
            page.wait_for_load_state("networkidle")
            
            # Extract and print the page title
            page_title = page.title()
            print(f"Page title: {page_title}")
            
            # Print success message
            print("Profile page loaded successfully")
            
            # Close the browser
            browser.close()
            print("Browser closed")
            
        except Exception as e:
            # Handle any errors that occur
            print(f"Error occurred: {e}")
            raise


if __name__ == "__main__":
    main()
