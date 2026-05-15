"""
DOM selector fallback extractor for Instagram profiles.

This is the TERTIARY extraction method - only used if JSON-LD and meta tags fail.
DOM selectors are fragile but provide additional extraction options.
"""

from .parser_utils import clean_string, parse_count


def extract_username_from_dom(page):
    """
    Extract username from DOM selectors.
    Try multiple selector patterns as Instagram changes structure frequently.
    
    Args:
        page: Playwright page object
        
    Returns:
        Username string or None
    """
    
    selectors = [
        "header h2",                    # Common location in header
        "header [role='heading']",      # Alternative heading role
        "[data-testid='profile-username']",  # Test ID attribute
        "header [data-testid]",         # Any element with test ID in header
    ]
    
    for selector in selectors:
        try:
            locator = page.locator(selector)
            if locator.count() > 0:
                text = locator.first.text_content()
                if text:
                    cleaned = clean_string(text)
                    # Username should be relatively short and alphanumeric
                    if cleaned and len(cleaned) < 50 and any(c.isalnum() for c in cleaned):
                        return cleaned
        except Exception:
            continue
    
    return None


def extract_bio_from_dom(page):
    """
    Extract bio from DOM selectors.
    
    Args:
        page: Playwright page object
        
    Returns:
        Bio string or None
    """
    
    selectors = [
        "header span",                  # Common location for bio spans
        "header article span",          # Alternative: within article element
        "header [data-testid='bio']",   # Test ID for bio
        "header section span",          # Within section
    ]
    
    for selector in selectors:
        try:
            locator = page.locator(selector)
            for i in range(locator.count()):
                text = locator.nth(i).text_content()
                if text:
                    cleaned = clean_string(text)
                    # Bio should be longer than just counts
                    if cleaned and len(cleaned) > 10 and not cleaned.replace(',', '').replace('K', '').replace('M', '').isdigit():
                        return cleaned
        except Exception:
            continue
    
    return None


def extract_stats_from_dom(page):
    """
    Extract followers, following, posts from DOM.
    Instagram typically shows these in header buttons.
    
    Args:
        page: Playwright page object
        
    Returns:
        Dictionary with counts: {'followers': int, 'following': int, 'posts': int}
    """
    
    stats = {'followers': None, 'following': None, 'posts': None}
    stat_keywords = ['followers', 'following', 'posts']
    found_stats = []
    
    try:
        # Look for buttons/divs in header containing stats
        selectors = [
            "header button",
            "header a",
            "header [role='button']",
            "header [data-testid]"
        ]
        
        for selector in selectors:
            try:
                locator = page.locator(selector)
                for i in range(locator.count()):
                    text = locator.nth(i).text_content()
                    if text:
                        text_lower = text.lower()
                        # Check if this element contains a stat keyword
                        for keyword in stat_keywords:
                            if keyword in text_lower:
                                found_stats.append(text)
                                break
            except Exception:
                continue
            
            if found_stats:
                break
        
        # Parse found stats
        if found_stats:
            for i, stat_text in enumerate(found_stats[:3]):  # Max 3 stats
                count = parse_count(stat_text)
                if count is not None:
                    if i == 0:
                        stats['posts'] = count
                    elif i == 1:
                        stats['followers'] = count
                    elif i == 2:
                        stats['following'] = count
        
        return stats
    
    except Exception as e:
        print(f"Error extracting stats from DOM: {e}")
        return stats


def extract_profile_image_from_dom(page):
    """
    Extract profile image URL from DOM.
    
    Args:
        page: Playwright page object
        
    Returns:
        Image URL string or None
    """
    
    selectors = [
        "header img[alt*='profile']",
        "header img[role='img']",
        "header img",
        "header [role='img'] img"
    ]
    
    for selector in selectors:
        try:
            locator = page.locator(selector)
            if locator.count() > 0:
                src = locator.first.get_attribute('src')
                if src:
                    return src
        except Exception:
            continue
    
    return None


def extract_profile_dom_fallback(page):
    """
    Complete DOM fallback extraction pipeline.
    Call this only if JSON-LD and meta tags fail.
    
    Args:
        page: Playwright page object
        
    Returns:
        Dictionary with extracted profile data
    """
    
    profile = {
        'username': None,
        'bio': None,
        'followers': None,
        'following': None,
        'posts': None,
        'profile_image': None,
        'url': None,
        'extraction_method': 'dom_fallback'
    }
    
    try:
        print("  Falling back to DOM selector extraction...")
        
        # Extract each field
        profile['username'] = extract_username_from_dom(page)
        profile['bio'] = extract_bio_from_dom(page)
        profile['profile_image'] = extract_profile_image_from_dom(page)
        
        # Extract stats
        stats = extract_stats_from_dom(page)
        profile.update(stats)
        
        return profile
    
    except Exception as e:
        print(f"Error in DOM fallback extraction: {e}")
        return profile


if __name__ == "__main__":
    print("DOM fallback extractor module - use within extractor system")
