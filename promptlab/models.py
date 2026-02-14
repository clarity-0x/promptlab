"""Data models for promptlab results."""

from typing import Any, Dict, Optional


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
        error: Optional[str] = None
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
    
    @property
    def matches(self) -> Optional[bool]:
        """Check if response matches expected output."""
        if self.response is None or self.error:
            return None
        return self.response.strip().lower() == self.expected.strip().lower()
