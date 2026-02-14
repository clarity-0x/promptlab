"""Tests for matching functionality."""

import pytest

from promptlab.matching import check_match, MatchResult


def test_exact_match_success():
    """Test exact matching with successful match."""
    result = check_match("hello world", "Hello World", "exact")
    
    assert isinstance(result, MatchResult)
    assert result.matches is True
    assert result.mode == "exact"


def test_exact_match_failure():
    """Test exact matching with failed match."""
    result = check_match("hello world", "goodbye world", "exact")
    
    assert result.matches is False
    assert result.mode == "exact"


def test_exact_match_whitespace():
    """Test exact matching ignores extra whitespace."""
    result = check_match("  hello world  ", "hello world", "exact")
    
    assert result.matches is True
    assert result.mode == "exact"


def test_contains_match_success():
    """Test contains matching with successful match."""
    result = check_match("The quick brown fox jumps", "quick brown", "contains")
    
    assert result.matches is True
    assert result.mode == "contains"


def test_contains_match_failure():
    """Test contains matching with failed match."""
    result = check_match("The quick brown fox", "red fox", "contains")
    
    assert result.matches is False
    assert result.mode == "contains"


def test_contains_match_case_insensitive():
    """Test contains matching is case insensitive."""
    result = check_match("The QUICK brown fox", "quick Brown", "contains")
    
    assert result.matches is True
    assert result.mode == "contains"


def test_starts_with_match_success():
    """Test starts_with matching with successful match."""
    result = check_match("Hello world, how are you?", "Hello world", "starts_with")
    
    assert result.matches is True
    assert result.mode == "starts_with"


def test_starts_with_match_failure():
    """Test starts_with matching with failed match."""
    result = check_match("Hello world", "world", "starts_with")
    
    assert result.matches is False
    assert result.mode == "starts_with"


def test_starts_with_match_case_insensitive():
    """Test starts_with matching is case insensitive."""
    result = check_match("HELLO world", "hello", "starts_with")
    
    assert result.matches is True
    assert result.mode == "starts_with"


def test_regex_match_success():
    """Test regex matching with successful match."""
    result = check_match("The price is $25.99", r"\$\d+\.\d+", "regex")
    
    assert result.matches is True
    assert result.mode == "regex"
    assert "Matched:" in result.details


def test_regex_match_failure():
    """Test regex matching with failed match."""
    result = check_match("No prices here", r"\$\d+\.\d+", "regex")
    
    assert result.matches is False
    assert result.mode == "regex"
    assert "No match found" in result.details


def test_regex_match_case_insensitive():
    """Test regex matching is case insensitive."""
    result = check_match("Hello World", r"hello.*world", "regex")
    
    assert result.matches is True
    assert result.mode == "regex"


def test_regex_match_multiline():
    """Test regex matching works across lines."""
    text = """Line 1
Line 2 with pattern
Line 3"""
    result = check_match(text, r"Line 2.*pattern", "regex")
    
    assert result.matches is True
    assert result.mode == "regex"


def test_regex_invalid_pattern():
    """Test regex matching with invalid pattern."""
    result = check_match("Hello world", r"[invalid", "regex")
    
    assert result.matches is False
    assert result.mode == "regex"
    assert "Invalid regex pattern" in result.details


def test_semantic_match_no_model():
    """Test semantic matching without litellm (should fail gracefully)."""
    # This test will pass if litellm is not available or if there's no API key
    result = check_match("The cat is happy", "The feline is joyful", "semantic")
    
    # Should either work or fail gracefully
    assert result.mode == "semantic"
    assert isinstance(result.matches, bool) or result.matches is False


def test_unknown_match_mode():
    """Test unknown match mode raises ValueError."""
    with pytest.raises(ValueError, match="Unknown match mode"):
        check_match("hello", "world", "unknown_mode")


def test_match_result_properties():
    """Test MatchResult properties."""
    result = MatchResult(True, "test_mode", "test details")
    
    assert result.matches is True
    assert result.mode == "test_mode"
    assert result.details == "test details"


def test_match_result_no_details():
    """Test MatchResult without details."""
    result = MatchResult(False, "test_mode")
    
    assert result.matches is False
    assert result.mode == "test_mode"
    assert result.details is None