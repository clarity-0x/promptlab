"""Data models for promptlab results."""

from typing import Any, Dict, Optional

from .matching import MatchResult


class TestResult:
    """Result of running a single test case."""
    
    def __init__(
        self,
        test_case_idx: int,
        model: str,
        inputs: Dict[str, Any],
        expected: str,
        response: Optional[str] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        cost: Optional[float] = None,
        latency_ms: Optional[int] = None,
        error: Optional[str] = None,
        match_result: Optional[MatchResult] = None
    ):
        self.test_case_idx = test_case_idx
        self.model = model
        self.inputs = inputs
        self.expected = expected
        self.response = response
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost = cost
        self.latency_ms = latency_ms
        self.error = error
        self._match_result = match_result
    
    @property
    def matches(self) -> Optional[bool]:
        """Check if response matches expected output."""
        if self.response is None or self.error or self._match_result is None:
            return None
        return self._match_result.matches
    
    @property
    def match_mode(self) -> Optional[str]:
        """Get the match mode used for evaluation."""
        if self._match_result is None:
            return None
        return self._match_result.mode
    
    @property
    def match_details(self) -> Optional[str]:
        """Get details about the match evaluation."""
        if self._match_result is None:
            return None
        return self._match_result.details
