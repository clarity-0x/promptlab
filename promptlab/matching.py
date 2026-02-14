"""Matching strategies for comparing expected vs actual responses."""

import re
from typing import Optional


class MatchResult:
    """Result of a match operation."""
    
    def __init__(self, matches: bool, mode: str, details: Optional[str] = None):
        self.matches = matches
        self.mode = mode
        self.details = details


def check_match(response: str, expected: str, mode: str, model: Optional[str] = None) -> MatchResult:
    """Check if response matches expected using the specified mode."""
    if mode == "exact":
        return _check_exact_match(response, expected)
    elif mode == "contains":
        return _check_contains_match(response, expected)
    elif mode == "starts_with":
        return _check_starts_with_match(response, expected)
    elif mode == "regex":
        return _check_regex_match(response, expected)
    elif mode == "semantic":
        return _check_semantic_match(response, expected, model)
    else:
        raise ValueError(f"Unknown match mode: {mode}")


def _check_exact_match(response: str, expected: str) -> MatchResult:
    """Case-insensitive exact match (default behavior)."""
    matches = response.strip().lower() == expected.strip().lower()
    return MatchResult(matches, "exact")


def _check_contains_match(response: str, expected: str) -> MatchResult:
    """Check if response contains expected string (case-insensitive)."""
    matches = expected.strip().lower() in response.strip().lower()
    return MatchResult(matches, "contains")


def _check_starts_with_match(response: str, expected: str) -> MatchResult:
    """Check if response starts with expected string (case-insensitive)."""
    matches = response.strip().lower().startswith(expected.strip().lower())
    return MatchResult(matches, "starts_with")


def _check_regex_match(response: str, expected: str) -> MatchResult:
    """Check if response matches expected regex pattern."""
    try:
        match = re.search(expected, response, re.IGNORECASE | re.MULTILINE)
        matches = match is not None
        details = f"Matched: '{match.group()}'" if match else "No match found"
        return MatchResult(matches, "regex", details)
    except re.error as e:
        return MatchResult(False, "regex", f"Invalid regex pattern: {str(e)}")


def _check_semantic_match(response: str, expected: str, model: Optional[str]) -> MatchResult:
    """Use LLM to judge if response matches intent semantically."""
    # Lazy import to avoid loading heavy dependencies at module level
    try:
        import litellm
    except ImportError:
        return MatchResult(False, "semantic", "litellm not available")
    
    if not model:
        model = "gpt-4o"  # Default model for semantic matching
    
    try:
        # Create a prompt to ask the LLM if the responses match semantically
        prompt = f"""Compare these two responses and determine if they convey the same meaning or intent.

Expected: {expected}
Actual: {response}

Respond with only "YES" if they match semantically, or "NO" if they don't match. Consider:
- Similar meanings expressed differently
- Equivalent information presented in different formats
- Minor variations in wording that don't change the core intent

Answer: """

        # NOTE: This is a synchronous call. When called from async context
        # (e.g., runner.py), wrap with asyncio.to_thread() to avoid blocking.
        response_obj = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.0
        )
        
        llm_response = response_obj.choices[0].message.content.strip().upper()
        matches = llm_response == "YES"
        details = f"LLM evaluation ({model}): {llm_response}"
        
        return MatchResult(matches, "semantic", details)
        
    except Exception as e:
        return MatchResult(False, "semantic", f"Error in semantic matching: {str(e)}")