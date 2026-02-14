"""Tests for CLI commands."""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from promptlab.cli import main


class TestValidateCommand:
    """Tests for the 'validate' command."""

    def setup_method(self) -> None:
        self.runner = CliRunner()

    def _write_yaml(self, content: str) -> Path:
        """Write YAML content to a temp file and return its path."""
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False, encoding='utf-8'
        )
        tmp.write(content)
        tmp.close()
        return Path(tmp.name)

    def test_valid_file(self) -> None:
        path = self._write_yaml("""
name: test-prompt
prompt: "Hello {{name}}, welcome to {{place}}"
test_cases:
  - inputs:
      name: Alice
      place: Wonderland
    expected: "Hello Alice"
""")
        try:
            result = self.runner.invoke(main, ['validate', str(path)])
            assert result.exit_code == 0
            assert "is valid" in result.output
        finally:
            path.unlink()

    def test_valid_file_with_match_modes(self) -> None:
        path = self._write_yaml("""
name: test-prompt
match: contains
prompt: "Summarize: {{text}}"
test_cases:
  - inputs:
      text: "Some long text"
    expected: "summary"
  - inputs:
      text: "Another text"
    expected: "pattern.*"
    match: regex
""")
        try:
            result = self.runner.invoke(main, ['validate', str(path)])
            assert result.exit_code == 0
            assert "is valid" in result.output
        finally:
            path.unlink()

    def test_missing_required_field(self) -> None:
        path = self._write_yaml("""
name: test-prompt
test_cases:
  - inputs:
      text: hello
    expected: world
""")
        try:
            result = self.runner.invoke(main, ['validate', str(path)])
            assert result.exit_code == 1
            assert "Missing required field: prompt" in result.output
        finally:
            path.unlink()

    def test_invalid_yaml(self) -> None:
        path = self._write_yaml("{ invalid yaml: [")
        try:
            result = self.runner.invoke(main, ['validate', str(path)])
            assert result.exit_code == 1
            assert "Invalid YAML" in result.output
        finally:
            path.unlink()

    def test_missing_input_variable(self) -> None:
        path = self._write_yaml("""
name: test-prompt
prompt: "Hello {{name}}, welcome to {{place}}"
test_cases:
  - inputs:
      name: Alice
    expected: "Hello Alice"
""")
        try:
            result = self.runner.invoke(main, ['validate', str(path)])
            assert result.exit_code == 1
            assert "missing input variable 'place'" in result.output
        finally:
            path.unlink()

    def test_invalid_global_match_mode(self) -> None:
        path = self._write_yaml("""
name: test-prompt
match: fuzzy
prompt: "Hello {{name}}"
test_cases:
  - inputs:
      name: Alice
    expected: "Hello Alice"
""")
        try:
            result = self.runner.invoke(main, ['validate', str(path)])
            assert result.exit_code == 1
            assert "Invalid global match mode 'fuzzy'" in result.output
        finally:
            path.unlink()

    def test_invalid_per_test_match_mode(self) -> None:
        path = self._write_yaml("""
name: test-prompt
prompt: "Hello {{name}}"
test_cases:
  - inputs:
      name: Alice
    expected: "Hello Alice"
    match: approximate
""")
        try:
            result = self.runner.invoke(main, ['validate', str(path)])
            assert result.exit_code == 1
            assert "invalid match mode 'approximate'" in result.output
        finally:
            path.unlink()

    def test_empty_test_cases(self) -> None:
        path = self._write_yaml("""
name: test-prompt
prompt: "Hello {{name}}"
test_cases: []
""")
        try:
            result = self.runner.invoke(main, ['validate', str(path)])
            assert result.exit_code == 1
            assert "non-empty list" in result.output
        finally:
            path.unlink()

    def test_multiple_issues_reported(self) -> None:
        path = self._write_yaml("""
name: test-prompt
match: invalid_mode
prompt: "Hello {{name}} from {{city}}"
test_cases:
  - inputs:
      name: Alice
    expected: "Hello Alice"
    match: wrong
""")
        try:
            result = self.runner.invoke(main, ['validate', str(path)])
            assert result.exit_code == 1
            assert "Invalid global match mode" in result.output
            assert "missing input variable 'city'" in result.output
            assert "invalid match mode 'wrong'" in result.output
        finally:
            path.unlink()

    def test_nonexistent_file(self) -> None:
        result = self.runner.invoke(main, ['validate', '/tmp/nonexistent_file.yaml'])
        assert result.exit_code != 0

    def test_no_template_variables(self) -> None:
        path = self._write_yaml("""
name: static-prompt
prompt: "Just a static prompt with no variables"
test_cases:
  - inputs: {}
    expected: "Some response"
""")
        try:
            result = self.runner.invoke(main, ['validate', str(path)])
            assert result.exit_code == 0
            assert "is valid" in result.output
        finally:
            path.unlink()
