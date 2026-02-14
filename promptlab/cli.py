"""Main CLI interface for promptlab."""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import load_prompt_config, get_config_hash
from .storage import Storage
from .display import display_results, display_run_history, display_run_details
from .compare import RunComparison


console = Console()


@click.group()
@click.version_option()
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
def run(
    prompt_file: Path,
    models: str,
    max_concurrent: int,
    timeout: int
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
        console.print(f"[blue]Test cases:[/blue] {len(config.test_cases)}")
        
        # Initialize storage and create run
        storage = Storage()
        config_hash = get_config_hash(config, model_list)
        run_id = storage.create_run(str(prompt_file), model_list, config_hash)
        
        console.print(f"[blue]Run ID:[/blue] {run_id}")
        
        # Run tests (lazy import to avoid loading litellm at startup)
        from .runner import PromptRunner
        runner = PromptRunner(max_concurrent=max_concurrent, timeout=timeout)
        
        total_tasks = len(config.test_cases) * len(model_list)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Running {total_tasks} tests...", total=None)
            
            # Run all tests
            results = asyncio.run(runner.run_all(config, model_list))
        
        console.print(f"[green]✓[/green] Completed {len(results)} tests")
        
        # Save results to storage
        for result in results:
            storage.save_result(
                run_id=run_id,
                test_case_idx=result.test_case_idx,
                model=result.model,
                response=result.response,
                expected=result.expected,
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


if __name__ == '__main__':
    main()