"""
JSON-LD extractor for Instagram profiles.

Extracts structured data from JSON-LD script tags.
This is a PRIMARY extraction method when available.

JSON-LD is a W3C standard for embedding structured data in HTML.
Instagram may include profile data in schema.org format.
"""

import json


def extract_jsonld_scripts(page):
    """
    Extract all JSON-LD script tags from page.
    
    Args:
        page: Playwright page object
        
    Returns:
        List of parsed JSON-LD objects
    """
    
    jsonld_objects = []
    
    try:
        # Find all script tags with type="application/ld+json"
        script_locator = page.locator("script[type='application/ld+json']")
        
        if script_locator.count() > 0:
            for i in range(script_locator.count()):
                try:
                    # Get the script content
                    script_text = script_locator.nth(i).text_content()
                    
                    if script_text:
                        # Parse JSON safely
                        try:
                            jsonld_obj = json.loads(script_text)
                            jsonld_objects.append(jsonld_obj)
                        except json.JSONDecodeError as e:
                            print(f"  Failed to parse JSON-LD at index {i}: {e}")
                except Exception as e:
                    print(f"  Error extracting JSON-LD script {i}: {e}")
        
        return jsonld_objects
    
    except Exception as e:
        print(f"Error extracting JSON-LD scripts: {e}")
        return []


def find_person_schema(jsonld_objects):
    """
    Find Person schema object from JSON-LD objects.
    
    JSON-LD uses schema.org types. Person schema typically contains profile info.
    
    Args:
        jsonld_objects: List of JSON-LD objects from extract_jsonld_scripts()
        
    Returns:
        Person schema object or None
    """
    
    for obj in jsonld_objects:
        if isinstance(obj, dict):
            # Check if this object is a Person schema
            obj_type = obj.get('@type')
            if obj_type == 'Person' or (isinstance(obj_type, list) and 'Person' in obj_type):
                return obj
            
            # Check nested structures (Graph pattern)
            if obj_type == 'ItemList' or '@graph' in obj:
                graph = obj.get('@graph', [])
                for item in graph:
                    if isinstance(item, dict):
                        item_type = item.get('@type')
                        if item_type == 'Person' or (isinstance(item_type, list) and 'Person' in item_type):
                            return item
    
    return None


def parse_profile_from_jsonld(jsonld_obj):
    """
    Extract profile fields from Person schema JSON-LD object.
    
    Args:
        jsonld_obj: Person schema object from find_person_schema()
        
    Returns:
        Dictionary with extracted profile fields
    """
    
    from .parser_utils import parse_count, clean_string, extract_url
    
    profile = {
        'username': None,
        'name': None,
        'bio': None,
        'followers': None,
        'following': None,
        'posts': None,
        'profile_image': None,
        'url': None,
        'website': None,
        'raw_jsonld': jsonld_obj
    }
    
    if not jsonld_obj or not isinstance(jsonld_obj, dict):
        return profile
    
    try:
        # Extract basic fields
        profile['name'] = clean_string(jsonld_obj.get('name'))
        profile['bio'] = clean_string(jsonld_obj.get('description'))
        profile['url'] = jsonld_obj.get('url')
        profile['website'] = extract_url(profile['bio']) if profile['bio'] else None
        
        # Extract image
        image = jsonld_obj.get('image')
        if image:
            if isinstance(image, str):
                profile['profile_image'] = image
            elif isinstance(image, dict):
                profile['profile_image'] = image.get('url')
            elif isinstance(image, list) and len(image) > 0:
                profile['profile_image'] = image[0] if isinstance(image[0], str) else image[0].get('url')
        
        # Extract social media interaction stats (not always present)
        interaction_stats = jsonld_obj.get('interactionStatistic', [])
        for stat in interaction_stats:
            if isinstance(stat, dict):
                interaction_type = stat.get('interactionType', '').lower()
                count = stat.get('userInteractionCount', 0)
                
                if 'follow' in interaction_type.lower():
                    profile['followers'] = count
                elif 'follow' in interaction_type.lower() and 'user' in interaction_type.lower():
                    profile['followers'] = count
        
        # Try to extract username from URL
        if profile['url']:
            import re
            url_match = re.search(r'/([a-zA-Z0-9_.]+)/?$', profile['url'])
            if url_match:
                profile['username'] = url_match.group(1)
        
        return profile
    
    except Exception as e:
        print(f"Error parsing profile from JSON-LD: {e}")
        return profile


def extract_profile_jsonld(page):
    """
    Complete JSON-LD extraction pipeline.
    
    Args:
        page: Playwright page object
        
    Returns:
        Dictionary with extracted profile, or None if no valid data found
    """
    
    try:
        # Extract all JSON-LD scripts
        jsonld_objects = extract_jsonld_scripts(page)
        
        if not jsonld_objects:
            return None
        
        # Find Person schema
        person_schema = find_person_schema(jsonld_objects)
        
        if not person_schema:
            return None
        
        # Parse profile from schema
        profile = parse_profile_from_jsonld(person_schema)
        
        return profile
    
    except Exception as e:
        print(f"Error in JSON-LD extraction pipeline: {e}")
        return None


if __name__ == "__main__":
    print("JSON-LD extractor module - use within extractor system")
