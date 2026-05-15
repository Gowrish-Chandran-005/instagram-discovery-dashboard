"""
Phase 10 - Build Mini Flask API
Flask backend API for Instagram profile discovery.
Provides a /search endpoint that runs extraction and returns JSON.
"""

from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import json


# Initialize Flask application
app = Flask(__name__)


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


def search_instagram(keyword, max_results=3):
    """
    Search Instagram for a keyword and extract profile data.
    
    Args:
        keyword: Search keyword
        max_results: Maximum number of profiles to extract
        
    Returns:
        Dictionary containing search results or error
    """
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to Instagram homepage
            page.goto("https://instagram.com")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            # Search for keyword
            search_input = page.locator("input[placeholder*='Search']")
            search_input.wait_for(state="visible", timeout=5000)
            search_input.click()
            search_input.type(keyword, delay=100)
            page.wait_for_timeout(3000)
            
            # Collect visible usernames
            usernames = []
            result_items = page.locator("[role='button'][tabindex='0']")
            
            if result_items.count() > 0:
                for i in range(min(result_items.count(), max_results + 2)):
                    try:
                        item_text = result_items.nth(i).text_content()
                        if item_text and item_text.strip():
                            usernames.append(item_text.strip())
                    except:
                        pass
            
            # Extract profiles
            extracted_profiles = []
            
            for username in usernames[:max_results]:
                try:
                    profile_url = f"https://instagram.com/{username}"
                    page.goto(profile_url)
                    
                    # Extract profile data
                    profile_data = extract_profile_data(page, username)
                    extracted_profiles.append(profile_data)
                    
                except Exception as e:
                    print(f"Error extracting profile {username}: {e}")
            
            browser.close()
            
            return {
                "status": "success",
                "keyword": keyword,
                "results_count": len(extracted_profiles),
                "profiles": extracted_profiles
            }
    
    except Exception as e:
        return {
            "status": "error",
            "keyword": keyword,
            "message": str(e)
        }


@app.route('/', methods=['GET'])
def home():
    """Home route - API information."""
    return jsonify({
        "message": "Instagram Discovery API",
        "version": "1.0",
        "endpoints": {
            "/search": "POST - Search Instagram for profiles",
            "query_param": "keyword (required)",
            "example": "/search?keyword=posters"
        }
    })


@app.route('/search', methods=['GET'])
def search():
    """
    Search endpoint for Instagram profile discovery.
    
    Query parameters:
        - keyword: Search keyword (required)
        - max_results: Maximum number of profiles to extract (optional, default=3)
    
    Returns:
        JSON response with extracted profiles
    """
    
    # Get query parameters
    keyword = request.args.get('keyword')
    max_results = request.args.get('max_results', default=3, type=int)
    
    # Validate keyword parameter
    if not keyword:
        return jsonify({
            "status": "error",
            "message": "Missing 'keyword' query parameter",
            "example": "/search?keyword=posters"
        }), 400
    
    # Validate max_results
    if max_results < 1:
        return jsonify({
            "status": "error",
            "message": "max_results must be at least 1"
        }), 400
    
    if max_results > 10:
        max_results = 10
    
    # Perform search
    print(f"Searching for keyword: '{keyword}' (max_results: {max_results})")
    result = search_instagram(keyword, max_results)
    
    # Return JSON response
    if result["status"] == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "available_endpoints": ["/", "/search"]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Phase 10 - Build Mini Flask API")
    print("=" * 60)
    print("\nStarting Instagram Discovery API...")
    print("Server running on http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  GET  /                    - API information")
    print("  GET  /search?keyword=...  - Search Instagram profiles")
    print("\nExample:")
    print("  http://localhost:5000/search?keyword=posters")
    print("\n" + "=" * 60 + "\n")
    
    # Run Flask app
    # Use debug=False in production
    app.run(debug=True, host='localhost', port=5000)
