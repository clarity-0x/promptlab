"""Validation utilities for prompt configuration files."""

import re
from pathlib import Path
from typing import List

import yaml


VALID_MATCH_MODES = {'exact', 'contains', 'starts_with', 'regex', 'semantic'}


def validate_prompt_file(file_path: Path) -> List[str]:
    """Validate a prompt file and return a list of issues found.

    Returns an empty list if the file is valid.
    """
    issues: List[str] = []

    # Load and parse YAML
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        issues.append(f"Invalid YAML: {e}")
        return issues

    if not isinstance(data, dict):
        issues.append("File must contain a YAML mapping at the top level")
        return issues

    # Check required fields
    for field in ('name', 'prompt', 'test_cases'):
        if field not in data:
            issues.append(f"Missing required field: {field}")

    if issues:
        return issues

    # Validate global match mode
    global_match = data.get('match', 'exact')
    if global_match not in VALID_MATCH_MODES:
        issues.append(f"Invalid global match mode '{global_match}'. Must be one of: {', '.join(sorted(VALID_MATCH_MODES))}")

    # Extract template variables from prompt
    template_vars = set(re.findall(r'\{\{(\w+)\}\}', data['prompt']))

    # Validate test cases
    test_cases = data.get('test_cases', [])
    if not isinstance(test_cases, list) or len(test_cases) == 0:
        issues.append("test_cases must be a non-empty list")
        return issues

    for idx, tc in enumerate(test_cases, start=1):
        if not isinstance(tc, dict):
            issues.append(f"Test case {idx}: must be a mapping")
            continue

        if 'inputs' not in tc:
            issues.append(f"Test case {idx}: missing 'inputs' field")
        if 'expected' not in tc:
            issues.append(f"Test case {idx}: missing 'expected' field")

        # Check template variables are provided in inputs
        if 'inputs' in tc and isinstance(tc['inputs'], dict):
            provided_vars = set(tc['inputs'].keys())
            missing_vars = template_vars - provided_vars
            for var in sorted(missing_vars):
                issues.append(f"Test case {idx}: missing input variable '{var}' (required by prompt template)")

        # Validate per-test match mode
        if 'match' in tc and tc['match'] not in VALID_MATCH_MODES:
            issues.append(f"Test case {idx}: invalid match mode '{tc['match']}'. Must be one of: {', '.join(sorted(VALID_MATCH_MODES))}")

    return issues
