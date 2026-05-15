"""
Phase 6 - Test Instagram Search
Opens Instagram homepage, searches for a keyword, and extracts visible usernames from results.
"""

from playwright.sync_api import sync_playwright


def main():
    """Open Instagram and search for keyword."""
    
    search_keyword = "posters"
    
    with sync_playwright() as p:
        try:
            # Launch Chromium browser in non-headless mode
            print("=" * 50)
            print("Phase 6 - Test Instagram Search")
            print("=" * 50)
            print("\nLaunching Chromium browser...")
            browser = p.chromium.launch(headless=False)
            
            # Create a new page/tab
            page = browser.new_page()
            
            # Navigate to Instagram homepage
            print("Opening Instagram homepage...")
            page.goto("https://instagram.com")
            
            # Wait for homepage to load
            print("Waiting for homepage to load...")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            # Locate and click the search input
            print(f"Locating search input...")
            try:
                # Search input is typically in a header or sidebar, but Instagram often
                # hides search for anonymous users. Detect and bail gracefully.
                search_input = page.locator("input[placeholder*='Search']")

                if search_input.count() == 0:
                    print("Search input not available (Instagram may require login)."
                          " Skipping search step.")
                else:
                    # Wait for search input to be visible
                    search_input.wait_for(state="visible", timeout=5000)

                    # Click on search input to focus
                    search_input.click()
                    print(f"Search input found and focused")

                    # Type the search keyword
                    print(f"Searching for keyword: '{search_keyword}'...")
                    search_input.type(search_keyword, delay=100)

                    # Wait for search suggestions/results to appear
                    print("Waiting for search results to appear...")
                    page.wait_for_timeout(3000)

                    # Extract visible usernames from search results
                    print("\nExtracting usernames from search results...")
                    usernames = []

                    # Look for username elements in search results
                    # Instagram typically shows results in a list/dropdown
                    result_items = page.locator("[role='button'][tabindex='0']")

                    if result_items.count() > 0:
                        for i in range(min(result_items.count(), 10)):  # Get up to 10 results
                            try:
                                # Get the text content of each result
                                item_text = result_items.nth(i).text_content()
                                if item_text and item_text.strip():
                                    usernames.append(item_text.strip())
                                    print(f"  {i+1}. {item_text.strip()}")
                            except Exception as e:
                                print(f"  Could not extract result {i}: {e}")

                        print(f"\nTotal usernames extracted: {len(usernames)}")
                    else:
                        print("No search results found")

                    # Wait before closing
                    print("\nWaiting 5 seconds before closing...")
                    page.wait_for_timeout(5000)

            except Exception as e:
                print(f"Error during search: {e}")
            
            # Close the browser
            browser.close()
            print("Browser closed successfully\n")
            
        except Exception as e:
            # Handle any errors
            print(f"\nError occurred: {e}")
            raise


if __name__ == "__main__":
    main()
