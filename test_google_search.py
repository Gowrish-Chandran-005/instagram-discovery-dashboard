import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read API credentials
API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID = os.getenv("GOOGLE_CSE_ID")

# Google Custom Search API endpoint
URL = "https://www.googleapis.com/customsearch/v1"

# Search query
QUERY = "site:instagram.com posters"

# Parameters
params = {
    "key": API_KEY,
    "cx": CSE_ID,
    "q": QUERY,
    "num": 10
}

print("=" * 60)
print("[INFO] GOOGLE CUSTOM SEARCH TEST")
print("=" * 60)

try:
    print("[INFO] Sending request to Google Custom Search API...")

    response = requests.get(URL, params=params, timeout=15)

    print(f"[STATUS CODE] {response.status_code}")
    print("=" * 60)

    # Print raw response for debugging
    print("[RAW RESPONSE]")
    print(response.text)
    print("=" * 60)

    # Convert response to JSON
    data = response.json()

    # Extract search results
    items = data.get("items", [])

    print(f"[INFO] Results found: {len(items)}")

    # Filter valid Instagram profile URLs
    valid_profiles = []

    blocked_paths = [
        "/p/",
        "/reel/",
        "/explore/",
        "/stories/",
        "/tv/"
    ]

    for item in items:
        link = item.get("link", "")

        if "instagram.com/" not in link:
            continue

        # Skip unwanted Instagram paths
        if any(path in link for path in blocked_paths):
            continue

        valid_profiles.append(link)

    print("=" * 60)
    print("[VALID INSTAGRAM PROFILE LINKS]")
    print("=" * 60)

    if not valid_profiles:
        print("[WARNING] No valid Instagram profiles found.")

    for index, profile in enumerate(valid_profiles, start=1):
        print(f"{index}. {profile}")

except Exception as error:
    print("[ERROR] Request failed.")
    print(str(error))