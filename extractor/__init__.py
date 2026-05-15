"""
Instagram Structured Metadata Extractor

Professional, modular extraction system using:
1. JSON-LD extraction (most reliable)
2. Meta tag extraction (very reliable)
3. DOM selector fallback (fragile but works)

This is an INDUSTRY-STANDARD extraction approach.
"""

from .meta_extractor import extract_meta_tags, parse_profile_from_meta
from .jsonld_extractor import extract_profile_jsonld
from .dom_fallback import extract_profile_dom_fallback


def merge_profiles(*profiles):
    """
    Merge multiple profile dictionaries, preferring non-None values.
    Earlier profiles take precedence.
    
    Args:
        *profiles: Variable number of profile dictionaries
        
    Returns:
        Merged profile dictionary
    """
    
    merged = {
        'username': None,
        'bio': None,
        'followers': None,
        'following': None,
        'posts': None,
        'profile_image': None,
        'url': None,
        'website': None,
        'extraction_methods': []
    }
    
    for profile in profiles:
        if not profile or not isinstance(profile, dict):
            continue
        
        # Prefer first non-None value for each field
        for key in merged.keys():
            if key == 'extraction_methods':
                continue
            if merged[key] is None and profile.get(key) is not None:
                merged[key] = profile[key]
        
        # Track which methods provided data
        if 'extraction_method' in profile:
            merged['extraction_methods'].append(profile['extraction_method'])
        elif 'raw_meta' in profile and profile['raw_meta']:
            merged['extraction_methods'].append('meta_tags')
        elif 'raw_jsonld' in profile and profile['raw_jsonld']:
            merged['extraction_methods'].append('jsonld')
    
    return merged


def extract_instagram_profile(page, username=None):
    """
    Extract Instagram profile using multi-method extraction pipeline.
    
    EXTRACTION PRIORITY:
    1. JSON-LD (if available)
    2. Meta tags (usually available)
    3. DOM selectors (fragile fallback)
    
    Args:
        page: Playwright page object
        username: Expected username (for validation)
        
    Returns:
        Dictionary with extracted profile data and metadata
    """
    
    profiles = []
    
    # Method 1: JSON-LD extraction
    print("  [1/3] Attempting JSON-LD extraction...")
    jsonld_profile = extract_profile_jsonld(page)
    if jsonld_profile and any(v is not None for v in jsonld_profile.values() if v not in ['raw_jsonld', 'extraction_method']):
        jsonld_profile['extraction_method'] = 'jsonld'
        profiles.append(jsonld_profile)
        print("    ✓ JSON-LD data found")
    else:
        print("    ✗ No JSON-LD data found")
    
    # Method 2: Meta tag extraction (usually most complete)
    print("  [2/3] Attempting meta tag extraction...")
    meta_data = extract_meta_tags(page)
    meta_profile = parse_profile_from_meta(meta_data)
    if meta_profile and any(v is not None for v in meta_profile.values()):
        meta_profile['extraction_method'] = 'meta_tags'
        profiles.append(meta_profile)
        print("    ✓ Meta tag data found")
    else:
        print("    ✗ No meta tag data found")
    
    # Method 3: DOM selector fallback (only if above didn't provide enough)
    print("  [3/3] Attempting DOM selector fallback...")
    dom_profile = extract_profile_dom_fallback(page)
    if dom_profile and any(v is not None for v in dom_profile.values() if v not in ['extraction_method']):
        profiles.append(dom_profile)
        print("    ✓ DOM selector data found")
    else:
        print("    ✗ No DOM selector data found")
    
    # Merge results with priority
    merged = merge_profiles(*profiles)
    
    # Validate result
    if not merged['username'] and username:
        merged['username'] = username
    
    return merged


def format_profile_output(profile):
    """
    Format extracted profile for clean output.
    
    Args:
        profile: Extracted profile dictionary
        
    Returns:
        Formatted string representation
    """
    
    output = []
    output.append("=" * 60)
    output.append("EXTRACTED INSTAGRAM PROFILE DATA")
    output.append("=" * 60)
    
    # Display each field with label
    fields = [
        ('Username', 'username'),
        ('Bio', 'bio'),
        ('Followers', 'followers'),
        ('Following', 'following'),
        ('Posts', 'posts'),
        ('Profile Image', 'profile_image'),
        ('URL', 'url'),
        ('Website', 'website'),
    ]
    
    for label, key in fields:
        value = profile.get(key)
        if value:
            if key == 'profile_image' or key == 'url':
                # Truncate long URLs
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
            output.append(f"{label:20} : {value}")
        else:
            output.append(f"{label:20} : (not found)")
    
    output.append("=" * 60)
    if profile.get('extraction_methods'):
        output.append(f"Extraction methods: {', '.join(profile['extraction_methods'])}")
    output.append("=" * 60)
    
    return "\n".join(output)


if __name__ == "__main__":
    print("Instagram Structured Metadata Extractor")
    print("Use this module with Playwright to extract Instagram profile data")
