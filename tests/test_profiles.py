"""
Test suite for Instagram Structured Metadata Extractor

Tests core extraction functions and validates output structure.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor.parser_utils import parse_count, extract_username, extract_url, is_valid_bio, clean_instagram_bio


def test_parse_count():
    """Test follower count parsing."""
    print("Testing parse_count()...")
    
    test_cases = [
        ("1.2M followers", 1_200_000),
        ("42.5K", 42_500),
        ("1,234", 1_234),
        ("292M Followers, 243 Following", 292_000_000),  # Will extract 292M
        ("123K posts", 123_000),
    ]
    
    for input_str, expected in test_cases:
        result = parse_count(input_str)
        status = "✓" if result == expected else "✗"
        print(f"  {status} parse_count('{input_str}') = {result} (expected {expected})")
        assert result == expected, f"Failed: {input_str}"
    
    print("  All tests passed!\n")


def test_extract_username():
    """Test username extraction."""
    print("Testing extract_username()...")
    
    test_cases = [
        ("@nike", "nike"),
        ("Nike (@nike)", "nike"),
        ("Check out @adidas_official", "adidas_official"),
        ("Follow @my.account now", "my.account"),
    ]
    
    for input_str, expected in test_cases:
        result = extract_username(input_str)
        status = "✓" if result == expected else "✗"
        print(f"  {status} extract_username('{input_str}') = {result} (expected {expected})")
        assert result == expected, f"Failed: {input_str}"
    
    print("  All tests passed!\n")


def test_extract_url():
    """Test URL extraction."""
    print("Testing extract_url()...")
    
    test_cases = [
        ("Visit https://nike.com", "https://nike.com"),
        ("Check http://example.org/page", "http://example.org/page"),
        ("No URL here", None),
    ]
    
    for input_str, expected in test_cases:
        result = extract_url(input_str)
        status = "✓" if result == expected else "✗"
        print(f"  {status} extract_url('{input_str}') = {result} (expected {expected})")
        assert result == expected, f"Failed: {input_str}"
    
    print("  All tests passed!\n")


def test_is_valid_bio():
    """Test bio validation."""
    print("Testing is_valid_bio()...")
    
    test_cases = [
        ("Just Shoes", True),
        ("⚽ Sports brand | Innovation since 1972", True),
        ("123456", False),  # Just numbers
        ("ab", False),  # Too short
        ("", False),  # Empty
    ]
    
    for input_str, expected in test_cases:
        result = is_valid_bio(input_str)
        status = "✓" if result == expected else "✗"
        print(f"  {status} is_valid_bio('{input_str}') = {result} (expected {expected})")
        assert result == expected, f"Failed: {input_str}"
    
    print("  All tests passed!\n")


def test_clean_instagram_bio():
    """Test cleaning of Instagram meta descriptions into pure bios."""
    print("Testing clean_instagram_bio()...")

    test_cases = [
        ("292M Followers, 243 Following, 1,632 Posts - Just Do It.", "Just Do It."),
        ("292M Followers, 243 Following, 1,632 Posts", None),
        ("Some malformed description -", None),
        ("No counts here, just a bio about the brand", "No counts here, just a bio about the brand"),
    ]

    for input_str, expected in test_cases:
        result = clean_instagram_bio(input_str)
        status = "✓" if result == expected else "✗"
        print(f"  {status} clean_instagram_bio('{input_str}') = {result} (expected {expected})")
        assert result == expected, f"Failed: {input_str} -> {result} != {expected}"

    print("  All tests passed!\n")


def test_extraction_structure():
    """Test that extraction functions return proper structure."""
    print("Testing extraction output structure...")
    
    from extractor import extract_instagram_profile, format_profile_output
    
    # Create dummy profile
    dummy_profile = {
        'username': 'testuser',
        'bio': 'Test bio',
        'followers': 1000,
        'following': 500,
        'posts': 100,
        'profile_image': 'https://example.com/img.jpg',
        'url': 'https://instagram.com/testuser',
        'website': 'https://example.com',
        'extraction_methods': ['meta_tags']
    }
    
    # Test formatting
    output = format_profile_output(dummy_profile)
    
    # Verify output contains expected fields
    assert 'testuser' in output, "Username not in output"
    assert 'Test bio' in output, "Bio not in output"
    assert '1000' in output or '1,000' in output, "Followers not in output"
    
    print("  ✓ Output structure is valid")
    print("  ✓ All required fields present\n")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("INSTAGRAM EXTRACTOR TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_parse_count()
        test_extract_username()
        test_extract_url()
        test_is_valid_bio()
        test_extraction_structure()
        
        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
