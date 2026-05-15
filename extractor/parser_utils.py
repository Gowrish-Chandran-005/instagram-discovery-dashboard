"""
Parser utility functions for Instagram profile data extraction.

Provides helper functions to:
- Parse follower/following counts (e.g., "1.2M" → 1200000)
- Extract numbers from strings
- Validate data types
- Clean extracted strings
"""

import re


def parse_count(count_str):
    """
    Parse Instagram count strings like "1.2M", "42K", "1,234" into integers.
    
    Args:
        count_str: String representation of a count (e.g., "1.2M followers")
        
    Returns:
        Integer count or None if unable to parse
        
    Examples:
        >>> parse_count("1.2M followers")
        1200000
        >>> parse_count("42.5K")
        42500
        >>> parse_count("1,234")
        1234
    """
    if not count_str or not isinstance(count_str, str):
        return None
    
    try:
        # Extract only the numeric part
        count_str = str(count_str).strip()
        
        # Extract just the first number + multiplier
        # Matches patterns like "1.2M", "42K", "1,234"
        match = re.search(r'([\d,.]+)\s*([MK])?', count_str)
        if not match:
            return None
        
        num_part = match.group(1)
        multiplier = match.group(2)
        
        if not num_part:
            return None
        
        # Convert to float
        num = float(num_part.replace(',', ''))
        
        # Apply multiplier
        if multiplier and multiplier.upper() == 'M':
            return int(num * 1_000_000)
        elif multiplier and multiplier.upper() == 'K':
            return int(num * 1_000)
        else:
            return int(num)
    
    except (ValueError, AttributeError):
        return None


def extract_username(text):
    """
    Extract Instagram username from text.
    
    Args:
        text: Text that may contain an Instagram handle
        
    Returns:
        Username (without @) or None
        
    Examples:
        >>> extract_username("@nike")
        "nike"
        >>> extract_username("Nike (@nike)")
        "nike"
    """
    if not text or not isinstance(text, str):
        return None
    
    # Look for @username pattern
    match = re.search(r'@(\w+(?:[._]\w+)*)', text)
    if match:
        return match.group(1)
    
    return None


def extract_url(text):
    """
    Extract first HTTP URL from text.
    
    Args:
        text: Text that may contain URLs
        
    Returns:
        URL string or None
        
    Examples:
        >>> extract_url("Visit https://nike.com for more")
        "https://nike.com"
    """
    if not text or not isinstance(text, str):
        return None
    
    # Look for http(s) URLs
    match = re.search(r'https?://[^\s]+', text)
    if match:
        return match.group(0)
    
    return None


def clean_string(text):
    """
    Clean extracted string: strip whitespace, remove extra spaces.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned string or None
    """
    if not text or not isinstance(text, str):
        return None
    
    # Strip whitespace and normalize spaces
    cleaned = ' '.join(text.split())
    
    return cleaned if cleaned else None


def is_valid_bio(text):
    """
    Check if text looks like a valid bio (not just metadata).
    
    Args:
        text: Text to validate
        
    Returns:
        Boolean indicating if text is likely a real bio
    """
    if not text or not isinstance(text, str):
        return False
    
    # Bio should have some minimum length and not be purely numeric
    if len(text.strip()) < 5:
        return False
    
    if text.strip().isdigit():
        return False
    
    return True


def clean_instagram_bio(description: str) -> str | None:
    """Extract the human-written bio from an Instagram meta description.

    Instagram meta descriptions often combine counts and bio like:
    "292M Followers, 243 Following, 1,632 Posts - Just Do It."

    This function returns the portion after the dash ("-") where present,
    otherwise attempts to strip the leading counts and return any remaining
    text. Returns None when no usable bio is found.
    """
    if not description or not isinstance(description, str):
        return None

    desc = description.strip()

    # Split on common dash separators (hyphen, en-dash, em-dash)
    parts = re.split(r"\s[-–—]\s", desc, maxsplit=1)
    if len(parts) == 2:
        bio_candidate = parts[1].strip()
        # Clean whitespace
        bio_candidate = ' '.join(bio_candidate.split())
        return bio_candidate if bio_candidate else None

    # No dash: try removing leading counts like "292M Followers, 243 Following, 1,632 Posts"
    # Remove common counts patterns
    cleaned = re.sub(r'^(?:[0-9.,]+\s*[MKmk]?\s*Followers,?\s*)?(?:[0-9.,]+\s*[MKmk]?\s*Following,?\s*)?(?:[0-9.,]+\s*Posts,?\s*)?-?\s*', '', desc, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    cleaned = ' '.join(cleaned.split())
    if cleaned and len(cleaned) >= 3:
        return cleaned

    return None


if __name__ == "__main__":
    # Quick tests
    print("Testing parse_count:")
    print(f"  '1.2M followers' → {parse_count('1.2M followers')}")
    print(f"  '42.5K' → {parse_count('42.5K')}")
    print(f"  '1,234' → {parse_count('1,234')}")
    
    print("\nTesting extract_username:")
    print(f"  '@nike' → {extract_username('@nike')}")
    print(f"  'Nike (@nike)' → {extract_username('Nike (@nike)')}")
    
    print("\nTesting extract_url:")
    print(f"  'Visit https://nike.com' → {extract_url('Visit https://nike.com')}")
    
    print("\nTesting clean_string:")
    print(f"  '  hello   world  ' → '{clean_string('  hello   world  ')}'")
