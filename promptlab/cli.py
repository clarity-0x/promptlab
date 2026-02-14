"""Main CLI interface for promptlab."""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import load_prompt_config
from .utils import get_config_hash
from .validation import validate_prompt_file
from .storage import Storage
from .display import display_results, display_run_history, display_run_details
from .compare import RunComparison


console = Console()


@click.group()
@click.version_option(version=__import__('promptlab').__version__, prog_name="promptlab")
def main() -> None:
    """PromptLab: A lightweight CLI tool for testing LLM prompts across models."""
    pass


@main.command()
@click.argument('prompt_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--models', '-m',
    default='gpt-4o',
    help='Comma-separated list of models to test (default: gpt-4o)'
)
@click.option(
    '--max-concurrent', '-c',
    default=10,
    help='Maximum concurrent API calls (default: 10)'
)
@click.option(
    '--timeout', '-t',
    default=30,
    help='Timeout per API call in seconds (default: 30)'
)
@click.option(
    '--test', 
    type=int,
    help='Run only test case N (1-indexed)'
)
def run(
    prompt_file: Path,
    models: str,
    max_concurrent: int,
    timeout: int,
    test: Optional[int]
) -> None:
    """Run all test cases in a prompt file."""
    try:
        # Load and validate prompt configuration
        with console.status("[bold green]Loading prompt configuration..."):
            config = load_prompt_config(prompt_file)
        
        console.print(f"[green]✓[/green] Loaded prompt: {config.name}")
        if config.description:
            console.print(f"  {config.description}")
        
        # Parse models
        model_list = [m.strip() for m in models.split(',')]
        console.print(f"[blue]Models:[/blue] {', '.join(model_list)}")
        # Filter test cases if --test specified
        test_cases_to_run = config.test_cases
        if test is not None:
            if test < 1 or test > len(config.test_cases):
                console.print(f"[red]Error:[/red] Test case {test} not found. Valid range: 1-{len(config.test_cases)}")
                sys.exit(1)
            test_cases_to_run = [config.test_cases[test - 1]]
            console.print(f"[blue]Running test case {test} only[/blue]")
        
        console.print(f"[blue]Test cases:[/blue] {len(test_cases_to_run)}")
        
        # Initialize storage and create run
        storage = Storage()
        config_hash = get_config_hash(config, model_list)
        run_id = storage.create_run(str(prompt_file), model_list, config_hash)
        
        console.print(f"[blue]Run ID:[/blue] {run_id}")
        
        # Run tests (lazy import to avoid loading litellm at startup)
        from .runner import PromptRunner
        runner = PromptRunner(max_concurrent=max_concurrent, timeout=timeout)
        
        # Create a temporary config with filtered test cases
        if test is not None:
            filtered_config = config.copy_with_test_cases(test_cases_to_run)
        else:
            filtered_config = config
        
        total_tasks = len(test_cases_to_run) * len(model_list)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Running {total_tasks} tests...", total=None)
            
            # Run all tests
            results = asyncio.run(runner.run_all(filtered_config, model_list))
        
        console.print(f"[green]✓[/green] Completed {len(results)} tests")
        
        # Save results to storage
        for result in results:
            storage.save_result(
                run_id=run_id,
                test_case_idx=result.test_case_idx,
                model=result.model,
                response=result.response,
                expected=result.expected,
                inputs=result.inputs,
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                cost=result.cost,
                latency_ms=result.latency_ms,
                error=result.error
            )
        
        # Display results
        display_results(results, config.name, run_id, console)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@main.command()
def history() -> None:
    """List recent test runs."""
    try:
        storage = Storage()
        runs = storage.list_runs(limit=20)
        display_run_history(runs, console)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@main.command()
@click.argument('run_id')
def show(run_id: str) -> None:
    """Show details of a specific test run."""
    try:
        storage = Storage()
        run = storage.get_run(run_id)
        
        if not run:
            console.print(f"[red]Run {run_id} not found[/red]")
            sys.exit(1)
        
        results = storage.get_results(run_id)
        display_run_details(run, results, console)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@main.command()
@click.argument('run1_id')
@click.argument('run2_id')
def compare(run1_id: str, run2_id: str) -> None:
    """Compare two test runs."""
    try:
        storage = Storage()
        comparison = RunComparison(storage)
        comparison.compare_runs(run1_id, run2_id, console)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@main.command()
@click.argument('name')
def init(name: str) -> None:
    """Create a starter YAML file with sensible defaults."""
    filename = f"{name}.yaml"
    
    if Path(filename).exists():
        console.print(f"[red]Error:[/red] File {filename} already exists")
        sys.exit(1)
    
    template = (
        "name: " + name + "\n"
        "description: Description of what this prompt does\n"
        "model: gpt-4o\n"
        "match: exact  # Match mode: exact, contains, starts_with, regex, or semantic\n"
        "parameters:   # Global model parameters\n"
        "  temperature: 0.0\n"
        "  max_tokens: 100\n"
        "system: You are a helpful assistant.\n"
        "\n"
        "prompt: |\n"
        "  Your prompt template here. Use {{variable_name}} for variables.\n"
        "  \n"
        "  Input: {{input}}\n"
        "\n"
        "test_cases:\n"
        "  - inputs:\n"
        '      input: "Example input text"\n'
        '    expected: "Expected output"\n'
        "    # match: exact           # Override global match mode for this test\n"
        "    # parameters:            # Override global parameters for this test\n"
        "    #   temperature: 0.5\n"
        "  \n"
        "  - inputs:\n"
        '      input: "Another example"\n'
        '    expected: "Another expected output"\n'
    )
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(template)
        console.print(f"[green]✓[/green] Created {filename}")
        console.print(f"[blue]Next steps:[/blue]")
        console.print(f"  1. Edit {filename} with your prompt and test cases")
        console.print(f"  2. Run: promptlab run {filename}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@main.command()
@click.argument('run_id')
@click.option('--format', 'output_format', type=click.Choice(['json', 'csv']), default='json', help='Output format (default: json)')
def export(run_id: str, output_format: str) -> None:
    """Export run results to JSON or CSV format."""
    try:
        storage = Storage()
        run = storage.get_run(run_id)
        
        if not run:
            console.print(f"[red]Run {run_id} not found[/red]")
            sys.exit(1)
        
        results = storage.get_results(run_id)
        
        if output_format == 'json':
            import json
            output = {
                'run': {
                    'id': run['id'],
                    'timestamp': run['timestamp'].isoformat(),
                    'prompt_file': run['prompt_file'],
                    'models': run['models'],
                    'config_hash': run['config_hash']
                },
                'results': results
            }
            print(json.dumps(output, indent=2, default=str))
        
        elif output_format == 'csv':
            import csv
            import sys
            
            writer = csv.DictWriter(
                sys.stdout,
                fieldnames=['test_case_idx', 'model', 'expected', 'response', 'tokens_in', 'tokens_out', 'cost', 'latency_ms', 'error', 'inputs']
            )
            writer.writeheader()
            for result in results:
                # Convert inputs dict to string for CSV
                result_copy = result.copy()
                if result_copy['inputs']:
                    result_copy['inputs'] = str(result_copy['inputs'])
                writer.writerow(result_copy)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@main.command()
@click.argument('prompt_file', type=click.Path(exists=True, path_type=Path))
def validate(prompt_file: Path) -> None:
    """Validate a prompt YAML file without running tests."""
    issues = validate_prompt_file(prompt_file)

    if issues:
        console.print(f"[red]Validation failed for {prompt_file}:[/red]")
        for issue in issues:
            console.print(f"  [red]✗[/red] {issue}")
        sys.exit(1)
    else:
        console.print(f"[green]✓[/green] {prompt_file} is valid")


if __name__ == '__main__':
    main()