"""Configuration and prompt file loading."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class TestCase:
    """A single test case with inputs and expected output."""
    
    def __init__(
        self, 
        inputs: Dict[str, Any], 
        expected: str, 
        match: Optional[str] = None, 
        parameters: Optional[Dict[str, Any]] = None
    ):
        self.inputs = inputs
        self.expected = expected
        self.match = match
        self.parameters = parameters or {}


class PromptConfig:
    """Configuration for a prompt test file."""
    
    def __init__(
        self,
        name: str,
        prompt: str,
        test_cases: List[Dict[str, Any]],
        description: Optional[str] = None,
        model: str = "gpt-4o",
        system: Optional[str] = None,
        match: str = "exact",
        parameters: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.description = description
        self.model = model
        self.system = system
        self.prompt = prompt
        self.match = match
        self.parameters = parameters or {}
        
        # Convert test case dicts to TestCase objects
        self.test_cases = []
        for tc in test_cases:
            if not isinstance(tc, dict) or 'inputs' not in tc or 'expected' not in tc:
                raise ValueError("Each test case must have 'inputs' and 'expected' fields")
            self.test_cases.append(
                TestCase(
                    tc['inputs'], 
                    tc['expected'],
                    tc.get('match'),
                    tc.get('parameters')
                )
            )
        
        if not self.test_cases:
            raise ValueError("At least one test case is required")


def load_prompt_config(file_path: Path) -> PromptConfig:
    """Load and validate a prompt configuration file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML structure in {file_path}")
    
    # Validate required fields
    required_fields = ['name', 'prompt', 'test_cases']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in {file_path}")
    
    return PromptConfig(
        name=data['name'],
        prompt=data['prompt'],
        test_cases=data['test_cases'],
        description=data.get('description'),
        model=data.get('model', 'gpt-4o'),
        system=data.get('system'),
        match=data.get('match', 'exact'),
        parameters=data.get('parameters')
    )


def render_prompt(template: str, variables: Dict[str, Any]) -> str:
    """Render a prompt template with variables using {{var}} syntax."""
    result = template
    
    # Find all variables in {{var}} format
    pattern = r'\{\{(\w+)\}\}'
    matches = re.findall(pattern, template)
    
    for var_name in matches:
        if var_name not in variables:
            raise ValueError(f"Variable '{var_name}' not found in inputs")
        
        placeholder = f"{{{{{var_name}}}}}"
        result = result.replace(placeholder, str(variables[var_name]))
    
    return result


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


def get_config_hash(config: PromptConfig, models: List[str]) -> str:
    """Generate a hash of the configuration for caching/comparison."""
    import hashlib
    
    # Create a deterministic string representation
    config_str = f"{config.name}|{config.prompt}|{config.system or ''}|{config.match}|{config.parameters}|{','.join(models)}"
    for test_case in config.test_cases:
        config_str += f"|{test_case.inputs}|{test_case.expected}|{test_case.match or ''}|{test_case.parameters}"
    
    return hashlib.md5(config_str.encode()).hexdigest()[:8]