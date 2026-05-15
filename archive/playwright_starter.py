"""
Playwright Starter Script - Instagram Discovery Dashboard
Opens Instagram in a visible Chromium browser and waits for user interaction.
"""

from playwright.sync_api import sync_playwright
import time


def main():
    """Main function to launch browser and open Instagram."""
    
    # Initialize Playwright and launch browser
    with sync_playwright() as p:
        try:
            # Launch Chromium browser in non-headless mode (visible window)
            browser = p.chromium.launch(headless=False)
            
            # Create a new page/tab in the browser
            page = browser.new_page()
            
            # Navigate to Instagram
            print("Navigating to Instagram...")
            page.goto("https://instagram.com")
            
            # Wait for 10 seconds
            print("Waiting for 10 seconds...")
            time.sleep(10)
            
            # Print success message
            print("Instagram opened successfully")
            
            # Close the browser properly
            browser.close()
            print("Browser closed successfully")
            
        except Exception as e:
            # Handle any errors that occur during execution
            print(f"An error occurred: {e}")
            raise


if __name__ == "__main__":
    main()
