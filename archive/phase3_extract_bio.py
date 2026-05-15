"""
Phase 3 - Extract Instagram Bio
Opens a public Instagram profile, waits for it to fully load, and extracts the bio text.
"""

from playwright.sync_api import sync_playwright


def main():
    """Open Instagram profile and extract bio text."""
    
    with sync_playwright() as p:
        try:
            # Launch Chromium browser in non-headless mode
            print("Launching Chromium browser...")
            browser = p.chromium.launch(headless=False)
            
            # Create a new page/tab
            page = browser.new_page()
            
            # Navigate to Nike's public Instagram profile
            print("Opening Instagram profile: https://instagram.com/nike")
            page.goto("https://instagram.com/nike")
            
            # Wait until network becomes idle (page fully loaded)
            print("Waiting for profile to load...")
            page.wait_for_load_state("networkidle")
            
            # Wait a bit for dynamic content to render
            print("Waiting for dynamic content...")
            page.wait_for_timeout(2000)
            
            # Locate and extract the bio text
            # Instagram bio is typically in a header section. If the DOM selector fails
            # (Instagram often changes), fall back to reading meta tags.
            try:
                # Primary: try locating a bio element
                bio_locator = page.locator("header [role='menuitem'] + div, header ~ section span")
                if bio_locator.count() > 0:
                    try:
                        bio_locator.first.wait_for(state="visible", timeout=3000)
                        bio_text = bio_locator.first.text_content()
                    except Exception:
                        bio_text = bio_locator.first.text_content()

                else:
                    bio_text = None

                # Fallback: read meta description
                if not bio_text or not bio_text.strip():
                    meta = None
                    try:
                        meta = page.locator("meta[property='og:description']").get_attribute('content')
                    except Exception:
                        meta = None
                    if not meta:
                        try:
                            meta = page.locator("meta[name='description']").get_attribute('content')
                        except Exception:
                            meta = None

                    if meta and isinstance(meta, str):
                        bio_text = meta

                if bio_text and bio_text.strip():
                    print(f"Bio extracted: {bio_text.strip()}")
                else:
                    print("Bio not found using available selectors/meta tags")
                    
            except Exception as e:
                print(f"Could not extract bio: {e}")
                print("Page content might have changed structure")
            
            # Print success message
            print("Bio extraction completed")
            
            # Wait before closing so user can see the page
            page.wait_for_timeout(5000)
            
            # Close the browser
            browser.close()
            print("Browser closed")
            
        except Exception as e:
            # Handle any errors that occur
            print(f"Error occurred: {e}")
            raise


if __name__ == "__main__":
    main()
