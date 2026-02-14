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


def get_config_hash(config: PromptConfig, models: List[str]) -> str:
    """Generate a hash of the configuration for caching/comparison."""
    import hashlib
    
    # Create a deterministic string representation
    config_str = f"{config.name}|{config.prompt}|{config.system or ''}|{config.match}|{config.parameters}|{','.join(models)}"
    for test_case in config.test_cases:
        config_str += f"|{test_case.inputs}|{test_case.expected}|{test_case.match or ''}|{test_case.parameters}"
    
    return hashlib.md5(config_str.encode()).hexdigest()[:8]