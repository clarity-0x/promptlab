# PromptLab

A lightweight CLI tool for testing, comparing, and iterating on LLM prompts across multiple models.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is PromptLab?

PromptLab solves the common AI engineering workflow pain point: **testing and comparing prompts across multiple LLM models**. Instead of copy-pasting prompts between different UIs or writing custom scripts, PromptLab lets you:

- Define prompts and test cases in simple YAML files
- Run tests across multiple models in parallel  
- Compare results between different runs
- Track costs and performance metrics
- Version control your prompts naturally (it's all just files!)

Perfect for AI engineers who want reproducible, git-friendly prompt testing without the overhead of enterprise evaluation platforms.

## Quick Start

### Installation

```bash
pip install promptlab
```

Or for development:

```bash
git clone https://github.com/yourusername/promptlab.git
cd promptlab
pip install -e ".[dev]"
```

### Your First Prompt Test

1. Create a prompt file `sentiment.yaml`:

```yaml
name: classify-sentiment
description: Classify text sentiment
model: gpt-4o
system: You are a sentiment classifier. Respond with exactly one word: positive, negative, or neutral.
prompt: |
  Classify the sentiment of this text: {{text}}
test_cases:
  - inputs:
      text: "I love this product, it's amazing!"
    expected: positive
  - inputs:
      text: "This is the worst experience ever."
    expected: negative
  - inputs:
      text: "The weather is okay today."  
    expected: neutral
```

2. Run the test:

```bash
promptlab run sentiment.yaml
```

3. Compare across multiple models:

```bash
promptlab run sentiment.yaml --models gpt-4o,claude-sonnet-4,gemini-2
```

## Features

### 🎯 **Simple YAML Configuration**
Define prompts, test cases, and expected outputs in clean, version-controllable YAML files.

### 🚀 **Multi-Model Testing**  
Test the same prompt across GPT-4, Claude, Gemini, and other models in parallel.

### 📊 **Rich Output**
Beautiful terminal tables showing results, match rates, token usage, and costs.

### 🔍 **Run Comparison**
Compare different runs to see how prompt changes affect results across models.

### 💾 **Local Storage**
All results stored locally in SQLite - no external dependencies or data sharing.

### ⚡ **Fast & Parallel**
Async execution with configurable concurrency limits.

## CLI Commands

### Run Tests

```bash
# Run with default model (gpt-4o)
promptlab run prompt.yaml

# Run across multiple models
promptlab run prompt.yaml --models gpt-4o,claude-sonnet-4

# Customize concurrency and timeout
promptlab run prompt.yaml --max-concurrent 5 --timeout 45
```

### View History

```bash
# List recent runs
promptlab history

# Show details of a specific run
promptlab show 20240315-143022-abcd
```

### Compare Runs

```bash
# Compare two runs side-by-side
promptlab compare 20240315-143022-abcd 20240315-144531-efgh
```

## YAML Format Reference

```yaml
name: your-prompt-name              # Required: Unique identifier
description: What this prompt does  # Optional: Human description  
model: gpt-4o                      # Optional: Default model (default: gpt-4o)
system: You are a helpful assistant # Optional: System message

prompt: |                          # Required: The prompt template
  Your prompt here with {{variables}}
  
test_cases:                        # Required: List of test cases
  - inputs:                        # Input variables for the prompt
      variable1: value1
      variable2: value2
    expected: expected output      # What you expect the model to return
    
  - inputs:
      variable1: different value
    expected: different expected output
```

### Variable Substitution

Use `{{variable_name}}` in your prompt template. Variables are replaced with values from each test case's `inputs`.

```yaml
prompt: |
  Translate this {{source_language}} text to {{target_language}}: {{text}}
  
test_cases:
  - inputs:
      source_language: English
      target_language: Spanish  
      text: Hello, world!
    expected: ¡Hola, mundo!
```

## Supported Models

PromptLab uses [LiteLLM](https://github.com/BerriAI/litellm) under the hood, supporting 100+ models:

- **OpenAI**: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`
- **Anthropic**: `claude-3-sonnet-20240229`, `claude-3-opus-20240229`
- **Google**: `gemini-pro`, `gemini-pro-vision`
- **Cohere**: `command-r`, `command-r-plus`
- **And many more...**

Set your API keys as environment variables (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).

## Examples

Check out the `examples/` directory for ready-to-run prompt files:

- [`classify-sentiment.yaml`](examples/classify-sentiment.yaml) - Sentiment classification
- [`extract-entities.yaml`](examples/extract-entities.yaml) - Named entity extraction

Run them:

```bash
promptlab run examples/classify-sentiment.yaml --models gpt-4o,claude-sonnet-4
```

## Output Format

PromptLab shows results in a clean table format:

```
┌─────┬──────────────┬────────────────────┬──────────┬───────────┬───────┬────────┬──────────┬──────┐
│Test │ Model        │ Input             │ Expected │ Actual    │ Match │ Tokens │ Cost     │ Time │
├─────┼──────────────┼────────────────────┼──────────┼───────────┼───────┼────────┼──────────┼──────┤
│ 1   │ gpt-4o       │ text: I love...   │ positive │ positive  │   ✓   │ 45     │ $0.0023  │ 234ms│
│     │ claude-sonnet│ text: I love...   │ positive │ positive  │   ✓   │ 41     │ $0.0019  │ 187ms│
│ 2   │ gpt-4o       │ text: This is...  │ negative │ negative  │   ✓   │ 48     │ $0.0025  │ 198ms│
│     │ claude-sonnet│ text: This is...  │ negative │ negative  │   ✓   │ 43     │ $0.0021  │ 165ms│
├─────┼──────────────┼────────────────────┼──────────┼───────────┼───────┼────────┼──────────┼──────┤
│Total│              │                   │          │           │4/4 80%│ 177    │ $0.0088  │      │
└─────┴──────────────┴────────────────────┴──────────┴───────────┴───────┴────────┴──────────┴──────┘
```

## Configuration

PromptLab stores results in `~/.promptlab/results.db` by default. No additional configuration required!

## Development

```bash
# Clone and install for development
git clone https://github.com/yourusername/promptlab.git
cd promptlab
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=promptlab

# Format code
black promptlab/ tests/

# Type checking
mypy promptlab/
```

## Why PromptLab?

**vs. Jupyter Notebooks**: Reproducible, version-controllable, no messy cell state

**vs. Custom Scripts**: Standard format, built-in comparison tools, rich output

**vs. Enterprise Platforms**: Runs locally, no vendor lock-in, git-friendly, free

**vs. Manual Testing**: Automated, parallel execution, historical comparison

## Roadmap

- [ ] Watch mode (`promptlab watch prompt.yaml`)
- [ ] JSON output format for CI/CD integration  
- [ ] Prompt template inheritance and composition
- [ ] Custom evaluation metrics beyond exact match
- [ ] Integration with popular evaluation frameworks

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**PromptLab**: Because prompt engineering should be engineering, not guesswork. ⚡