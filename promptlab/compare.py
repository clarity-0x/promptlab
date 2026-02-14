"""Compare and diff functionality for promptlab runs."""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box

from .storage import Storage


class RunComparison:
    """Compare two promptlab runs."""
    
    def __init__(self, storage: Storage):
        self.storage = storage
    
    def compare_runs(
        self,
        run1_id: str,
        run2_id: str,
        console: Optional[Console] = None
    ) -> None:
        """Compare two runs and display differences."""
        if console is None:
            console = Console()
        
        # Get run metadata
        run1 = self.storage.get_run(run1_id)
        run2 = self.storage.get_run(run2_id)
        
        if not run1:
            console.print(f"[red]Run {run1_id} not found[/red]")
            return
        
        if not run2:
            console.print(f"[red]Run {run2_id} not found[/red]")
            return
        
        # Get results
        results1 = self.storage.get_results(run1_id)
        results2 = self.storage.get_results(run2_id)
        
        # Display comparison
        self._display_run_comparison_header(run1, run2, console)
        self._display_detailed_comparison(results1, results2, console)
        self._display_summary_comparison(results1, results2, console)
    
    def _display_run_comparison_header(
        self,
        run1: Dict[str, Any],
        run2: Dict[str, Any],
        console: Console
    ) -> None:
        """Display header information about the two runs."""
        info_text = f"""
[bold blue]Run 1:[/bold blue] {run1['id']} ({run1['timestamp'].strftime('%Y-%m-%d %H:%M')})
[bold green]Run 2:[/bold green] {run2['id']} ({run2['timestamp'].strftime('%Y-%m-%d %H:%M')})

[bold]Prompt File:[/bold] {run1['prompt_file']} vs {run2['prompt_file']}
[bold]Models 1:[/bold] {', '.join(run1['models'])}
[bold]Models 2:[/bold] {', '.join(run2['models'])}
        """.strip()
        
        console.print(Panel(info_text, title="Run Comparison", box=box.ROUNDED))
    
    def _display_detailed_comparison(
        self,
        results1: List[Dict[str, Any]],
        results2: List[Dict[str, Any]],
        console: Console
    ) -> None:
        """Display detailed side-by-side comparison of results."""
        # Create a mapping of (test_case_idx, model) -> result for easy lookup
        results1_map = {(r["test_case_idx"], r["model"]): r for r in results1}
        results2_map = {(r["test_case_idx"], r["model"]): r for r in results2}
        
        # Get all unique (test_case, model) combinations
        all_keys = set(results1_map.keys()) | set(results2_map.keys())
        
        table = Table(title="Detailed Comparison", box=box.ROUNDED)
        table.add_column("Test", style="cyan", min_width=4)
        table.add_column("Model", style="magenta", min_width=15)
        table.add_column("Run 1 Response", style="blue", max_width=25)
        table.add_column("Run 2 Response", style="green", max_width=25)
        table.add_column("Change", justify="center", min_width=6)
        table.add_column("Cost Δ", justify="right", min_width=8)
        table.add_column("Time Δ", justify="right", min_width=8)
        
        for test_idx, model in sorted(all_keys):
            result1 = results1_map.get((test_idx, model))
            result2 = results2_map.get((test_idx, model))
            
            # Format responses
            response1 = self._format_response(result1)
            response2 = self._format_response(result2)
            
            # Determine change type
            change_indicator = self._get_change_indicator(result1, result2)
            
            # Calculate cost delta
            cost_delta = self._calculate_cost_delta(result1, result2)
            
            # Calculate time delta
            time_delta = self._calculate_time_delta(result1, result2)
            
            table.add_row(
                str(test_idx + 1),
                model,
                response1,
                response2,
                change_indicator,
                cost_delta,
                time_delta
            )
        
        console.print(table)
    
    def _display_summary_comparison(
        self,
        results1: List[Dict[str, Any]],
        results2: List[Dict[str, Any]],
        console: Console
    ) -> None:
        """Display summary statistics comparison."""
        stats1 = self._calculate_stats(results1)
        stats2 = self._calculate_stats(results2)
        
        # Create side-by-side summary
        summary_table = Table(box=box.ROUNDED, title="Summary Comparison")
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Run 1", style="blue", justify="right")
        summary_table.add_column("Run 2", style="green", justify="right")
        summary_table.add_column("Change", style="yellow", justify="right")
        
        # Total tests
        summary_table.add_row(
            "Total Tests",
            str(stats1["total_tests"]),
            str(stats2["total_tests"]),
            self._format_delta(stats2["total_tests"] - stats1["total_tests"])
        )
        
        # Accuracy
        summary_table.add_row(
            "Accuracy",
            f"{stats1['accuracy']:.1f}%",
            f"{stats2['accuracy']:.1f}%",
            f"{stats2['accuracy'] - stats1['accuracy']:+.1f}%"
        )
        
        # Total cost
        summary_table.add_row(
            "Total Cost",
            f"${stats1['total_cost']:.4f}",
            f"${stats2['total_cost']:.4f}",
            f"${stats2['total_cost'] - stats1['total_cost']:+.4f}"
        )
        
        # Average latency
        summary_table.add_row(
            "Avg Latency",
            f"{stats1['avg_latency']:.0f}ms",
            f"{stats2['avg_latency']:.0f}ms",
            f"{stats2['avg_latency'] - stats1['avg_latency']:+.0f}ms"
        )
        
        # Total tokens
        summary_table.add_row(
            "Total Tokens",
            str(stats1['total_tokens']),
            str(stats2['total_tokens']),
            self._format_delta(stats2['total_tokens'] - stats1['total_tokens'])
        )
        
        console.print(summary_table)
    
    def _format_response(self, result: Optional[Dict[str, Any]]) -> str:
        """Format a response for display."""
        if not result:
            return "[dim]N/A[/dim]"
        
        if result["error"]:
            return f"[red]ERROR: {result['error'][:20]}...[/red]"
        
        if not result["response"]:
            return "[dim]No response[/dim]"
        
        response = result["response"]
        if len(response) > 22:
            response = response[:19] + "..."
        
        return response
    
    def _get_change_indicator(
        self,
        result1: Optional[Dict[str, Any]],
        result2: Optional[Dict[str, Any]]
    ) -> str:
        """Get a visual indicator for the type of change."""
        if not result1 and not result2:
            return "[dim]─[/dim]"
        
        if not result1:
            return "[green]+[/green]"
        
        if not result2:
            return "[red]−[/red]"
        
        # Both exist, check if responses match their expected values
        match1 = self._response_matches_expected(result1)
        match2 = self._response_matches_expected(result2)
        
        if match1 and match2:
            return "[green]✓✓[/green]"
        elif not match1 and not match2:
            return "[red]✗✗[/red]"
        elif match1 and not match2:
            return "[red]✓→✗[/red]"  # Regression
        elif not match1 and match2:
            return "[green]✗→✓[/green]"  # Improvement
        else:
            return "[yellow]≠[/yellow]"  # Different
    
    def _calculate_cost_delta(
        self,
        result1: Optional[Dict[str, Any]],
        result2: Optional[Dict[str, Any]]
    ) -> str:
        """Calculate cost difference."""
        cost1 = result1["cost"] if result1 and result1["cost"] else 0
        cost2 = result2["cost"] if result2 and result2["cost"] else 0
        
        if cost1 == 0 and cost2 == 0:
            return ""
        
        delta = cost2 - cost1
        if abs(delta) < 0.0001:
            return "─"
        
        return f"${delta:+.4f}"
    
    def _calculate_time_delta(
        self,
        result1: Optional[Dict[str, Any]],
        result2: Optional[Dict[str, Any]]
    ) -> str:
        """Calculate time difference."""
        time1 = result1["latency_ms"] if result1 and result1["latency_ms"] else 0
        time2 = result2["latency_ms"] if result2 and result2["latency_ms"] else 0
        
        if time1 == 0 and time2 == 0:
            return ""
        
        delta = time2 - time1
        if delta == 0:
            return "─"
        
        return f"{delta:+d}ms"
    
    def _calculate_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics for a set of results."""
        if not results:
            return {
                "total_tests": 0,
                "accuracy": 0.0,
                "total_cost": 0.0,
                "avg_latency": 0.0,
                "total_tokens": 0
            }
        
        total_tests = len(results)
        matches = sum(1 for r in results if self._response_matches_expected(r))
        accuracy = (matches / total_tests * 100) if total_tests > 0 else 0
        
        total_cost = sum(r["cost"] or 0 for r in results)
        
        latencies = [r["latency_ms"] for r in results if r["latency_ms"]]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        total_tokens = sum(
            (r["tokens_in"] or 0) + (r["tokens_out"] or 0)
            for r in results
        )
        
        return {
            "total_tests": total_tests,
            "accuracy": accuracy,
            "total_cost": total_cost,
            "avg_latency": avg_latency,
            "total_tokens": total_tokens
        }
    
    def _response_matches_expected(self, result: Dict[str, Any]) -> bool:
        """Check if a response matches the expected output using the appropriate match mode."""
        if not result["response"] or result.get("error"):
            return False
        
        # Use the matching module for consistent evaluation
        from .matching import check_match
        
        # Results from storage may include match_mode; default to exact
        mode = result.get("match_mode", "exact")
        # Don't use semantic matching in comparisons (requires API call)
        if mode == "semantic":
            mode = "exact"
        
        match_result = check_match(result["response"], result["expected"], mode)
        return match_result.matches
    
    def _format_delta(self, value: int) -> str:
        """Format an integer delta with +/- sign."""
        if value == 0:
            return "─"
        return f"{value:+d}"