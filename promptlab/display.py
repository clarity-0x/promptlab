"""Rich terminal output formatting for promptlab results."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box

from .models import TestResult


def display_results(
    results: List[TestResult],
    prompt_name: str,
    run_id: str,
    console: Optional[Console] = None
) -> None:
    """Display test results in a rich table."""
    if console is None:
        console = Console()
    
    # Group results by test case for better display
    test_cases: Dict[int, List[TestResult]] = {}
    for result in results:
        if result.test_case_idx not in test_cases:
            test_cases[result.test_case_idx] = []
        test_cases[result.test_case_idx].append(result)
    
    # Create main results table
    table = Table(title=f"Results for {prompt_name} (Run: {run_id})", box=box.ROUNDED)
    table.add_column("Test", style="cyan", min_width=4)
    table.add_column("Model", style="magenta", min_width=15)
    table.add_column("Input", style="white", max_width=30)
    table.add_column("Expected", style="green", max_width=20)
    table.add_column("Actual", style="yellow", max_width=20)
    table.add_column("Match", justify="center", min_width=5)
    table.add_column("Tokens", justify="right", min_width=8)
    table.add_column("Cost", justify="right", min_width=8)
    table.add_column("Time", justify="right", min_width=6)
    
    total_cost = 0.0
    total_tokens_in = 0
    total_tokens_out = 0
    total_matches = 0
    total_tests = 0
    
    for test_idx in sorted(test_cases.keys()):
        test_results = test_cases[test_idx]
        
        for i, result in enumerate(test_results):
            # Format input display (show first variable for brevity)
            input_display = ""
            if result.inputs:
                first_key = list(result.inputs.keys())[0]
                first_value = str(result.inputs[first_key])
                if len(first_value) > 25:
                    first_value = first_value[:22] + "..."
                input_display = f"{first_key}: {first_value}"
            
            # Format expected output
            expected_display = result.expected
            if len(expected_display) > 17:
                expected_display = expected_display[:14] + "..."
            
            # Format actual output
            actual_display = result.response or ""
            if result.error:
                actual_display = f"[red]ERROR: {result.error}[/red]"
            elif len(actual_display) > 17:
                actual_display = actual_display[:14] + "..."
            
            # Format match indicator
            if result.error:
                match_display = "[red]✗[/red]"
            elif result.matches is True:
                match_display = "[green]✓[/green]"
                total_matches += 1
            elif result.matches is False:
                match_display = "[red]✗[/red]"
            else:
                match_display = "[dim]?[/dim]"
            
            # Format tokens
            tokens_display = ""
            if result.tokens_in and result.tokens_out:
                tokens_display = f"{result.tokens_in + result.tokens_out}"
                total_tokens_in += result.tokens_in
                total_tokens_out += result.tokens_out
            
            # Format cost
            cost_display = ""
            if result.cost:
                cost_display = f"${result.cost:.4f}"
                total_cost += result.cost
            
            # Format latency
            time_display = ""
            if result.latency_ms:
                time_display = f"{result.latency_ms}ms"
            
            # Show test case number only on first row for this test
            test_display = str(test_idx + 1) if i == 0 else ""
            
            table.add_row(
                test_display,
                result.model,
                input_display,
                expected_display,
                actual_display,
                match_display,
                tokens_display,
                cost_display,
                time_display
            )
            
            total_tests += 1
    
    # Add summary row
    if total_tests > 0:
        accuracy = (total_matches / total_tests) * 100
        table.add_section()
        table.add_row(
            "[bold]Total[/bold]",
            "",
            "",
            "",
            "",
            f"[bold]{total_matches}/{total_tests} ({accuracy:.1f}%)[/bold]",
            f"[bold]{total_tokens_in + total_tokens_out}[/bold]",
            f"[bold]${total_cost:.4f}[/bold]" if total_cost > 0 else "",
            ""
        )
    
    console.print(table)


def display_run_history(runs: List[Dict[str, Any]], console: Optional[Console] = None) -> None:
    """Display run history table."""
    if console is None:
        console = Console()
    
    if not runs:
        console.print("[yellow]No runs found.[/yellow]")
        return
    
    table = Table(title="Recent Runs", box=box.ROUNDED)
    table.add_column("Run ID", style="cyan", min_width=15)
    table.add_column("Timestamp", style="white", min_width=16)
    table.add_column("Prompt File", style="green", min_width=20)
    table.add_column("Models", style="magenta", max_width=30)
    
    for run in runs:
        timestamp = run["timestamp"].strftime("%Y-%m-%d %H:%M")
        models_str = ", ".join(run["models"])
        if len(models_str) > 25:
            models_str = models_str[:22] + "..."
        
        table.add_row(
            run["id"],
            timestamp,
            run["prompt_file"],
            models_str
        )
    
    console.print(table)


def display_run_details(
    run: Dict[str, Any],
    results: List[Dict[str, Any]],
    console: Optional[Console] = None
) -> None:
    """Display detailed information about a specific run."""
    if console is None:
        console = Console()
    
    # Run metadata panel
    timestamp = run["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    models_str = ", ".join(run["models"])
    
    info_text = f"""
[bold]Run ID:[/bold] {run['id']}
[bold]Timestamp:[/bold] {timestamp}
[bold]Prompt File:[/bold] {run['prompt_file']}
[bold]Models:[/bold] {models_str}
[bold]Config Hash:[/bold] {run['config_hash']}
    """.strip()
    
    console.print(Panel(info_text, title="Run Details", box=box.ROUNDED))
    
    # Convert storage results to TestResult objects for display
    test_results = []
    for result in results:
        test_result = TestResult(
            test_case_idx=result["test_case_idx"],
            model=result["model"],
            inputs=result.get("inputs") or {"input": "..."},
            expected=result["expected"],
            response=result["response"],
            tokens_in=result["tokens_in"],
            tokens_out=result["tokens_out"],
            cost=result["cost"],
            latency_ms=result["latency_ms"],
            error=result["error"]
        )
        test_results.append(test_result)
    
    display_results(test_results, run["prompt_file"], run["id"], console)