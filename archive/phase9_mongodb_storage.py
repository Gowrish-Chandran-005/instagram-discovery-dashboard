"""
Phase 9 - Add MongoDB Storage
Extends Instagram extraction to store profile data in MongoDB with duplicate prevention.
"""

from playwright.sync_api import sync_playwright
import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError


class MongoDBManager:
    """Manager class for MongoDB operations."""
    
    def __init__(self, connection_string="mongodb://localhost:27017", db_name="instagram_db"):
        """
        Initialize MongoDB connection.
        
        Args:
            connection_string: MongoDB connection URL
            db_name: Database name
        """
        self.connection_string = connection_string
        self.db_name = db_name
        self.client = None
        self.db = None
        self.collection = None
    
    def connect(self):
        """
        Connect to MongoDB.
        
        Returns:
            Boolean indicating success
        """
        try:
            print("Connecting to MongoDB...")
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            
            # Verify connection
            self.client.admin.command('ping')
            
            self.db = self.client[self.db_name]
            self.collection = self.db['profiles']
            
            # Create unique index on username to prevent duplicates
            print("Setting up unique index on 'username'...")
            self.collection.create_index("username", unique=True)
            
            print("✓ Successfully connected to MongoDB\n")
            return True
            
        except ConnectionFailure as e:
            print(f"✗ Connection failed: {e}")
            print("  Make sure MongoDB is running on localhost:27017")
            return False
        except Exception as e:
            print(f"✗ Error connecting to MongoDB: {e}")
            return False
    
    def insert_profile(self, profile_data):
        """
        Insert a profile into MongoDB.
        Prevents duplicate usernames.
        
        Args:
            profile_data: Dictionary containing profile information
            
        Returns:
            Boolean indicating success
        """
        try:
            # Try to insert the profile
            result = self.collection.insert_one(profile_data)
            print(f"  ✓ Inserted profile: @{profile_data['username']}")
            return True
            
        except DuplicateKeyError:
            print(f"  ⚠ Profile @{profile_data['username']} already exists (skipped)")
            return False
        except Exception as e:
            print(f"  ✗ Error inserting profile: {e}")
            return False
    
    def get_all_profiles(self):
        """
        Get all profiles from MongoDB.
        
        Returns:
            List of profile dictionaries
        """
        try:
            profiles = list(self.collection.find({}, {'_id': 0}))
            return profiles
        except Exception as e:
            print(f"Error retrieving profiles: {e}")
            return []
    
    def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("Disconnected from MongoDB")


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


def main():
    """Main function - search, extract, and store profile data in MongoDB."""
    
    search_keyword = "posters"
    max_profiles_to_extract = 3
    
    # Initialize MongoDB manager
    db_manager = MongoDBManager()
    
    with sync_playwright() as p:
        try:
            # Connect to MongoDB
            print("=" * 60)
            print("Phase 9 - Add MongoDB Storage")
            print("=" * 60 + "\n")
            
            if not db_manager.connect():
                print("Aborting: Cannot connect to MongoDB")
                return
            
            # Launch Chromium browser
            print(f"Searching for keyword: '{search_keyword}'")
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
            search_input.wait_for(state="visible", timeout=5000)
            search_input.click()
            search_input.type(search_keyword, delay=100)
            page.wait_for_timeout(3000)
            
            # Collect visible usernames
            print("Collecting usernames from search results...")
            usernames = []
            result_items = page.locator("[role='button'][tabindex='0']")
            
            if result_items.count() > 0:
                for i in range(min(result_items.count(), max_profiles_to_extract + 2)):
                    try:
                        item_text = result_items.nth(i).text_content()
                        if item_text and item_text.strip():
                            usernames.append(item_text.strip())
                    except:
                        pass
            
            print(f"Found {len(usernames)} usernames\n")
            
            # Open profiles and extract data
            print("=" * 60)
            print("EXTRACTING AND STORING PROFILES")
            print("=" * 60 + "\n")
            
            inserted_count = 0
            
            for idx, username in enumerate(usernames[:max_profiles_to_extract]):
                try:
                    print(f"[{idx + 1}] Processing profile: @{username}")
                    
                    # Navigate to profile
                    profile_url = f"https://instagram.com/{username}"
                    page.goto(profile_url)
                    
                    # Extract profile data
                    profile_data = extract_profile_data(page, username)
                    
                    # Insert into MongoDB
                    if db_manager.insert_profile(profile_data):
                        inserted_count += 1
                    
                    print()
                    
                except Exception as e:
                    print(f"  ✗ Error processing profile {username}: {e}\n")
            
            # Display stored profiles
            print("=" * 60)
            print("STORED PROFILES IN MONGODB")
            print("=" * 60)
            all_profiles = db_manager.get_all_profiles()
            print(json.dumps(all_profiles, indent=2, ensure_ascii=False))
            print("=" * 60)
            print(f"\nSuccessfully inserted {inserted_count} new profiles")
            print(f"Total profiles in database: {len(all_profiles)}\n")
            
            # Wait before closing
            print("Waiting 5 seconds before closing...")
            page.wait_for_timeout(5000)
            
            browser.close()
            print("Browser closed successfully")
            
        except Exception as e:
            print(f"\nError occurred: {e}")
        finally:
            # Disconnect from MongoDB
            db_manager.disconnect()


if __name__ == "__main__":
    main()
