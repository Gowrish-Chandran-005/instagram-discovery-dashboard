"""
Phase 4 - Extract Followers Count
Opens a public Instagram profile and extracts the followers count.
"""

from playwright.sync_api import sync_playwright


def main():
    """Open Instagram profile and extract followers count."""
    
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
            
            # Wait for dynamic content to render
            print("Waiting for dynamic content...")
            page.wait_for_timeout(3000)
            
            # Locate and extract followers count
            try:
                # Primary: look for elements in header that include the word 'followers'
                followers_text = None
                buttons = page.locator("header button, header a")
                for i in range(buttons.count()):
                    try:
                        t = buttons.nth(i).text_content()
                        if t and 'follower' in t.lower():
                            followers_text = t.strip()
                            break
                    except Exception:
                        continue

                # Fallback: check header spans for numeric-looking values
                if not followers_text:
                    spans = page.locator("header span")
                    for i in range(spans.count()):
                        try:
                            span_text = spans.nth(i).text_content()
                            if span_text and span_text.strip():
                                # crude check for numbers with commas/k, e.g. "1,234" or "1.2m"
                                if any(ch.isdigit() for ch in span_text):
                                    followers_text = span_text.strip()
                                    break
                        except Exception:
                            continue

                # Fallback: try meta tags
                if not followers_text:
                    try:
                        meta = page.locator("meta[property='og:description']").get_attribute('content')
                        if meta and 'followers' in meta.lower():
                            followers_text = meta
                    except Exception:
                        pass

                if followers_text:
                    print(f"Followers information (raw): {followers_text}")
                else:
                    print("Could not find followers information using available selectors")

            except Exception as e:
                print(f"Could not extract followers count: {e}")
                print("Instagram structure may have changed")
            
            # Print success message
            print("Followers extraction completed")
            
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
