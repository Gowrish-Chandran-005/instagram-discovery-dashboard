"""
Phase 12 - Final Validation Demo
Complete Instagram public profile discovery system.
Combines keyword search, profile extraction, data storage, and Flask API.

Features:
- Search Instagram for keyword
- Extract profile data (username, bio, followers, website)
- Store in MongoDB
- Flask API integration
- Modular architecture
"""

from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import json


# ============================================================================
# DATABASE MANAGEMENT
# ============================================================================

class MongoDBManager:
    """Manager class for MongoDB operations."""
    
    def __init__(self, connection_string="mongodb://localhost:27017", db_name="instagram_db"):
        """Initialize MongoDB connection."""
        self.connection_string = connection_string
        self.db_name = db_name
        self.client = None
        self.db = None
        self.collection = None
    
    def connect(self):
        """Connect to MongoDB."""
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.collection = self.db['profiles']
            self.collection.create_index("username", unique=True)
            return True
        except ConnectionFailure:
            return False
        except Exception:
            return False
    
    def insert_profile(self, profile_data):
        """Insert profile with duplicate prevention."""
        try:
            self.collection.insert_one(profile_data)
            return True
        except DuplicateKeyError:
            return False
        except Exception:
            return False
    
    def get_all_profiles(self):
        """Get all profiles from MongoDB."""
        try:
            return list(self.collection.find({}, {'_id': 0}))
        except Exception:
            return []
    
    def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()


# ============================================================================
# DATA EXTRACTION FUNCTIONS
# ============================================================================

def extract_profile_data(page, username):
    """
    Extract complete profile data from Instagram profile page.
    
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
        "website": None
    }
    
    try:
        # Wait for profile to load
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        # Extract username from header
        try:
            username_element = page.locator("header h2")
            if username_element.count() > 0:
                profile_data["username"] = username_element.first.text_content().strip()
        except:
            pass
        
        # Extract bio (with fallback to meta tags)
        try:
            bio_locators = page.locator("header span")
            bio_text = None
            for i in range(bio_locators.count()):
                text = bio_locators.nth(i).text_content()
                if text and text.strip() and len(text.strip()) > 5:
                    if not text.strip().isdigit() and "@" not in text:
                        bio_text = text.strip()
                        break

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
        except:
            pass
        
        # Extract followers count
        try:
            stats = page.locator("header button")
            for i in range(stats.count()):
                stat_text = stats.nth(i).text_content()
                if stat_text and "follower" in stat_text.lower():
                    # Extract just the number
                    parts = stat_text.strip().split()
                    if parts:
                        profile_data["followers"] = parts[0]
                    break
        except:
            pass
        
        # Extract website link
        try:
            links = page.locator("a[href*='http']")
            for i in range(links.count()):
                try:
                    href = links.nth(i).get_attribute("href")
                    if href and href.startswith("http") and "instagram" not in href:
                        profile_data["website"] = href
                        break
                except:
                    pass
        except:
            pass
    
    except Exception as e:
        print(f"Error during profile extraction: {e}")
    
    return profile_data


def search_instagram_profiles(keyword, max_results=3):
    """
    Search Instagram for keyword and extract profiles.
    
    Args:
        keyword: Search keyword
        max_results: Maximum profiles to extract
        
    Returns:
        List of profile dictionaries
    """
    
    extracted_profiles = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to Instagram
            page.goto("https://instagram.com")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            # Search for keyword
            search_input = page.locator("input[placeholder*='Search']")
            search_input.wait_for(state="visible", timeout=5000)
            search_input.click()
            search_input.type(keyword, delay=100)
            page.wait_for_timeout(3000)
            
            # Collect usernames from search results
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
            
            # Extract profile data from each username
            for username in usernames[:max_results]:
                try:
                    profile_url = f"https://instagram.com/{username}"
                    page.goto(profile_url)
                    
                    # Extract all profile data
                    profile_data = extract_profile_data(page, username)
                    extracted_profiles.append(profile_data)
                    
                except Exception as e:
                    print(f"Error extracting profile {username}: {e}")
            
            browser.close()
    
    except Exception as e:
        print(f"Error during search: {e}")
    
    return extracted_profiles


# ============================================================================
# FLASK API
# ============================================================================

app = Flask(__name__)


@app.route('/', methods=['GET'])
def home():
    """Home endpoint - API information."""
    return jsonify({
        "service": "Instagram Discovery Dashboard",
        "version": "12.0",
        "status": "running",
        "endpoints": {
            "GET /": "API information",
            "GET /search": "Search and extract Instagram profiles",
            "GET /profiles": "Get all stored profiles",
            "POST /search": "Advanced search with keyword and MongoDB storage"
        },
        "query_parameters": {
            "keyword": "Search keyword (required)",
            "max_results": "Maximum profiles to extract (optional, default=3, max=10)"
        },
        "example": "/search?keyword=posters&max_results=5"
    })


@app.route('/search', methods=['GET'])
def search_profiles():
    """
    Search endpoint for Instagram profile discovery.
    
    Query parameters:
        - keyword: Search keyword (required)
        - max_results: Maximum profiles to extract (optional, default=3)
        - store: Store results in MongoDB (optional, default=false)
    
    Returns:
        JSON response with extracted profiles
    """
    
    # Get query parameters
    keyword = request.args.get('keyword')
    max_results = request.args.get('max_results', default=3, type=int)
    store = request.args.get('store', default='false').lower() == 'true'
    
    # Validate keyword
    if not keyword:
        return jsonify({
            "status": "error",
            "message": "Missing 'keyword' query parameter",
            "example": "/search?keyword=posters&max_results=5"
        }), 400
    
    # Validate and limit max_results
    if max_results < 1:
        return jsonify({"status": "error", "message": "max_results must be at least 1"}), 400
    if max_results > 10:
        max_results = 10
    
    print(f"[API] Searching for keyword: '{keyword}' (max_results: {max_results}, store: {store})")
    
    # Extract profiles
    profiles = search_instagram_profiles(keyword, max_results)
    
    # Store in MongoDB if requested
    if store:
        db_manager = MongoDBManager()
        if db_manager.connect():
            for profile in profiles:
                db_manager.insert_profile(profile)
            db_manager.disconnect()
    
    # Return results
    return jsonify({
        "status": "success",
        "keyword": keyword,
        "results_count": len(profiles),
        "stored": store,
        "profiles": profiles
    }), 200


@app.route('/profiles', methods=['GET'])
def get_all_profiles():
    """Get all stored profiles from MongoDB."""
    
    db_manager = MongoDBManager()
    
    if not db_manager.connect():
        return jsonify({
            "status": "error",
            "message": "Cannot connect to MongoDB"
        }), 500
    
    profiles = db_manager.get_all_profiles()
    db_manager.disconnect()
    
    return jsonify({
        "status": "success",
        "total_profiles": len(profiles),
        "profiles": profiles
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "status": "error",
        "message": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("PHASE 12 - FINAL VALIDATION DEMO")
    print("Instagram Public Profile Discovery System")
    print("=" * 70)
    print("\nFeatures:")
    print("  ✓ Instagram keyword search")
    print("  ✓ Profile data extraction (username, bio, followers, website)")
    print("  ✓ MongoDB integration (optional storage)")
    print("  ✓ Flask REST API")
    print("  ✓ Dynamic content handling with Playwright")
    print("\nAPI Endpoints:")
    print("  GET  /                    - API information")
    print("  GET  /search?keyword=...  - Search and extract profiles")
    print("  GET  /profiles            - Get all stored profiles")
    print("\nExample Requests:")
    print("  http://localhost:5000/search?keyword=posters&max_results=3")
    print("  http://localhost:5000/search?keyword=design&max_results=5&store=true")
    print("  http://localhost:5000/profiles")
    print("\n" + "=" * 70 + "\n")
    print("Starting server on http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    # Run Flask server
    app.run(debug=True, host='localhost', port=5000, use_reloader=False)
