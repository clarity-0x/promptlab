"""Utility functions for promptlab."""

import hashlib
import json
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import PromptConfig


def get_config_hash(config: "PromptConfig", models: List[str]) -> str:
    """Generate a hash of the configuration for caching/comparison."""
    # Create a deterministic string representation
    # Use json.dumps(sort_keys=True) for dicts to ensure deterministic ordering
    config_str = (
        f"{config.name}|{config.prompt}|{config.system or ''}|{config.match}"
        f"|{json.dumps(config.parameters, sort_keys=True)}|{','.join(models)}"
    )
    for test_case in config.test_cases:
        config_str += (
            f"|{json.dumps(test_case.inputs, sort_keys=True)}"
            f"|{test_case.expected}"
            f"|{test_case.match or ''}"
            f"|{json.dumps(test_case.parameters, sort_keys=True)}"
        )

    return hashlib.md5(config_str.encode()).hexdigest()[:8]
