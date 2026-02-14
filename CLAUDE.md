# promptlab

A lightweight CLI tool for testing, comparing, and iterating on LLM prompts across models.

## Tech Stack
- Python 3.12+ with click (CLI), rich (output formatting), litellm (multi-provider LLM calls)
- YAML for prompt definitions and test cases
- SQLite for result storage and comparison
- pytest for testing

## Architecture
- `promptlab/` — main package
  - `cli.py` — click CLI entry points
  - `config.py` — YAML prompt/test loading and validation
  - `runner.py` — test execution engine (parallel, multi-model)
  - `compare.py` — diff/compare across runs
  - `storage.py` — SQLite result persistence
  - `display.py` — rich terminal output formatting
  - `cost.py` — token usage and cost tracking
- `tests/` — pytest test suite
- `examples/` — example prompt files and test cases

## Code Style
- Type hints on all functions
- Docstrings on public functions
- No abbreviations in variable names
- Small, focused functions
- Tests for all core logic

## Commands
- `pip install -e ".[dev]"` — install for development
- `pytest` — run tests
- `pytest -x` — stop on first failure

## Key Decisions
- CLI-first, no web UI
- YAML-based config (not code-based)
- litellm for provider abstraction
- Results stored locally in SQLite
- Everything is files — git-friendly by design
