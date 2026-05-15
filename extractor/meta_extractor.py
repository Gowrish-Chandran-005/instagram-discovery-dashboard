"""
Meta tag extractor for Instagram profiles.

Extracts structured data from OpenGraph (og:*) and other meta tags.
This is the PRIMARY extraction method - most reliable and consistent.
"""

from .parser_utils import clean_string, extract_username, extract_url


def extract_meta_tags(page):
    """
    Extract all relevant meta tags from Instagram profile page.
    
    Args:
        page: Playwright page object
        
    Returns:
        Dictionary containing extracted meta data:
        {
            'title': str,           # og:title or page title
            'description': str,     # og:description or meta description
            'image': str,          # og:image (profile picture URL)
            'type': str,           # og:type
            'url': str,            # og:url (canonical URL)
            'raw_meta': dict       # All extracted meta tags
        }
    """
    
    meta_data = {
        'title': None,
        'description': None,
        'image': None,
        'type': None,
        'url': None,
        'raw_meta': {}
    }
    
    try:
        # Extract og:* meta tags (OpenGraph protocol)
        # These are the most reliable and structured
        og_tags = [
            'og:title',
            'og:description',
            'og:image',
            'og:type',
            'og:url',
        ]
        
        for tag in og_tags:
            try:
                locator = page.locator(f"meta[property='{tag}']")
                if locator.count() > 0:
                    content = locator.first.get_attribute('content')
                    if content:
                        key = tag.split(':')[1]  # Get the part after 'og:'
                        meta_data[key] = content
                        meta_data['raw_meta'][tag] = content
            except Exception as e:
                print(f"  Error extracting {tag}: {e}")
        
        # Fallback: extract regular meta tags if og: tags are missing
        if not meta_data['title']:
            try:
                title_tag = page.locator("meta[name='og:title']")
                if title_tag.count() == 0:
                    title_tag = page.locator("title")
                if title_tag.count() > 0:
                    content = title_tag.first.text_content() if title_tag.selector.startswith("title") else title_tag.first.get_attribute('content')
                    if content:
                        meta_data['title'] = content
            except Exception:
                pass
        
        if not meta_data['description']:
            try:
                desc_tag = page.locator("meta[name='description']")
                if desc_tag.count() > 0:
                    content = desc_tag.first.get_attribute('content')
                    if content:
                        meta_data['description'] = content
            except Exception:
                pass
        
        # Clean extracted values
        if meta_data['title']:
            meta_data['title'] = clean_string(meta_data['title'])
        
        if meta_data['description']:
            meta_data['description'] = clean_string(meta_data['description'])
        
        return meta_data
    
    except Exception as e:
        print(f"Error extracting meta tags: {e}")
        return meta_data


def parse_profile_from_meta(meta_data):
    """
    Parse Instagram profile fields from extracted meta data.
    
    Instagram typically provides in og:description:
    "123K Followers, 456 Following, 789 Posts - Bio text..."
    
    Args:
        meta_data: Dictionary from extract_meta_tags()
        
    Returns:
        Dictionary with parsed profile fields:
        {
            'username': str,
            'bio': str,
            'followers': int,
            'following': int,
            'posts': int,
            'profile_image': str,
            'url': str
        }
    """
    
    from .parser_utils import parse_count, is_valid_bio
    
    profile = {
        'username': None,
        'bio': None,
        'followers': None,
        'following': None,
        'posts': None,
        'profile_image': None,
        'url': None
    }
    
    try:
        # Extract username from title if available
        # Format is usually "Username (@handle)"
        if meta_data.get('title'):
            title = meta_data['title']
            username = extract_username(title)
            if username:
                profile['username'] = username
            # Title before @ is usually the display name, but handle works too
        
        # Extract profile image from og:image
        if meta_data.get('image'):
            profile['profile_image'] = meta_data['image']
        
        # Extract URL
        if meta_data.get('url'):
            profile['url'] = meta_data['url']
        
        # Parse description for stats and bio
        # Format: "123K Followers, 456 Following, 789 Posts - This is the bio"
        if meta_data.get('description'):
            desc = meta_data['description']
            
            # Try to extract counts using regex
            # Pattern: "number[MK]? Followers/Following/Posts"
            import re
            
            # Extract followers
            followers_match = re.search(r'([\d,.MK]+)\s*Followers?', desc, re.IGNORECASE)
            if followers_match:
                profile['followers'] = parse_count(followers_match.group(1))
            
            # Extract following
            following_match = re.search(r'([\d,.MK]+)\s*Following', desc, re.IGNORECASE)
            if following_match:
                profile['following'] = parse_count(following_match.group(1))
            
            # Extract posts
            posts_match = re.search(r'([\d,.MK]+)\s*Posts?', desc, re.IGNORECASE)
            if posts_match:
                profile['posts'] = parse_count(posts_match.group(1))
            
            # Extract bio (usually after the dash)
            # Format: "...Posts - This is the bio"
            bio_match = re.search(r'-\s*(.+)$', desc)
            if bio_match:
                bio_text = bio_match.group(1).strip()
                if is_valid_bio(bio_text):
                    profile['bio'] = bio_text
            
            # Fallback: if no bio extracted, use part of description
            if not profile['bio'] and is_valid_bio(desc):
                # Use description but strip out the stats part
                bio = re.sub(r'^.*?Posts?\s*-\s*', '', desc, flags=re.IGNORECASE)
                bio = re.sub(r'^[\d,.MK\s]+Followers.*?Posts?\s*', '', bio, flags=re.IGNORECASE)
                if is_valid_bio(bio):
                    profile['bio'] = bio.strip()
        
        return profile
    
    except Exception as e:
        print(f"Error parsing profile from meta: {e}")
        return profile


if __name__ == "__main__":
    print("Meta tag extractor module - use within extractor system")
