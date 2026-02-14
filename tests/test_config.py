"""Tests for configuration loading and validation."""

import tempfile
from pathlib import Path

import pytest
import yaml

from promptlab.config import load_prompt_config, render_prompt, get_config_hash


def test_load_valid_config():
    """Test loading a valid prompt configuration."""
    config_data = {
        'name': 'test-prompt',
        'description': 'A test prompt',
        'model': 'gpt-4o',
        'match': 'contains',
        'parameters': {'temperature': 0.5},
        'system': 'You are a helpful assistant.',
        'prompt': 'Say hello to {{name}}',
        'test_cases': [
            {
                'inputs': {'name': 'Alice'},
                'expected': 'Hello Alice!',
                'match': 'exact',
                'parameters': {'max_tokens': 50}
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = Path(f.name)
    
    try:
        config = load_prompt_config(temp_path)
        
        assert config.name == 'test-prompt'
        assert config.description == 'A test prompt'
        assert config.model == 'gpt-4o'
        assert config.match == 'contains'
        assert config.parameters == {'temperature': 0.5}
        assert config.system == 'You are a helpful assistant.'
        assert config.prompt == 'Say hello to {{name}}'
        assert len(config.test_cases) == 1
        assert config.test_cases[0].inputs == {'name': 'Alice'}
        assert config.test_cases[0].expected == 'Hello Alice!'
        assert config.test_cases[0].match == 'exact'
        assert config.test_cases[0].parameters == {'max_tokens': 50}
        
    finally:
        temp_path.unlink()


def test_load_minimal_config():
    """Test loading a minimal configuration with defaults."""
    config_data = {
        'name': 'minimal-prompt',
        'prompt': 'Simple prompt',
        'test_cases': [
            {
                'inputs': {'input': 'test'},
                'expected': 'output'
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = Path(f.name)
    
    try:
        config = load_prompt_config(temp_path)
        
        assert config.name == 'minimal-prompt'
        assert config.description is None
        assert config.model == 'gpt-4o'  # Default
        assert config.match == 'exact'  # Default
        assert config.parameters == {}  # Default
        assert config.system is None
        assert config.prompt == 'Simple prompt'
        assert len(config.test_cases) == 1
        assert config.test_cases[0].match is None  # No override
        assert config.test_cases[0].parameters == {}  # Default
        
    finally:
        temp_path.unlink()


def test_load_missing_file():
    """Test loading a non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_prompt_config(Path('/nonexistent/file.yaml'))


def test_load_invalid_yaml():
    """Test loading invalid YAML."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        # Clearly invalid YAML: unclosed bracket that cannot be parsed
        f.write('[unclosed bracket')
        temp_path = Path(f.name)
    
    try:
        with pytest.raises(yaml.YAMLError):
            load_prompt_config(temp_path)
    finally:
        temp_path.unlink()


def test_load_missing_required_fields():
    """Test loading config with missing required fields."""
    config_data = {
        'name': 'incomplete-prompt',
        # Missing 'prompt' and 'test_cases'
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Missing required field"):
            load_prompt_config(temp_path)
    finally:
        temp_path.unlink()


def test_load_empty_test_cases():
    """Test loading config with empty test cases."""
    config_data = {
        'name': 'no-tests',
        'prompt': 'A prompt with no tests',
        'test_cases': []
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="At least one test case is required"):
            load_prompt_config(temp_path)
    finally:
        temp_path.unlink()


def test_render_prompt_simple():
    """Test simple prompt rendering."""
    template = "Hello {{name}}, how are you?"
    variables = {"name": "Alice"}
    
    result = render_prompt(template, variables)
    assert result == "Hello Alice, how are you?"


def test_render_prompt_multiple_variables():
    """Test prompt rendering with multiple variables."""
    template = "{{greeting}} {{name}}, the weather is {{weather}}."
    variables = {"greeting": "Hi", "name": "Bob", "weather": "sunny"}
    
    result = render_prompt(template, variables)
    assert result == "Hi Bob, the weather is sunny."


def test_render_prompt_missing_variable():
    """Test prompt rendering with missing variable."""
    template = "Hello {{name}}, you are {{age}} years old."
    variables = {"name": "Charlie"}  # Missing 'age'
    
    with pytest.raises(ValueError, match="Variable 'age' not found"):
        render_prompt(template, variables)


def test_render_prompt_no_variables():
    """Test rendering a prompt with no variables."""
    template = "This is a static prompt."
    variables = {}
    
    result = render_prompt(template, variables)
    assert result == "This is a static prompt."


def test_get_config_hash():
    """Test configuration hash generation."""
    config_data = {
        'name': 'test-prompt',
        'prompt': 'Say hello to {{name}}',
        'test_cases': [
            {
                'inputs': {'name': 'Alice'},
                'expected': 'Hello Alice!'
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = Path(f.name)
    
    try:
        config = load_prompt_config(temp_path)
        
        # Same config and models should produce same hash
        hash1 = get_config_hash(config, ['gpt-4o'])
        hash2 = get_config_hash(config, ['gpt-4o'])
        assert hash1 == hash2
        
        # Different models should produce different hash
        hash3 = get_config_hash(config, ['gpt-4o', 'claude-sonnet'])
        assert hash1 != hash3
        
        # Hash should be a short string
        assert len(hash1) == 8
        assert isinstance(hash1, str)
        
    finally:
        temp_path.unlink()