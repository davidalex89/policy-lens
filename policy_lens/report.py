"""Pretty-print analysis results using Rich."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


SCORE_STYLES = {
    "addressed": "[bold green]addressed[/]",
    "partial": "[bold yellow]partial[/]",
    "none": "[bold red]none[/]",
}


def print_report(evaluation: dict[str, Any], console: Console | None = None) -> None:
    """Render the Layer 3 evaluation as a rich terminal report."""
    if console is None:
        console = Console()

    summary = evaluation.get("executive_summary", "No summary available.")
    pct = evaluation.get("overall_coverage_pct", "?")
    addressed = evaluation.get("families_addressed", "?")
    partial = evaluation.get("families_partial", "?")
    none_count = evaluation.get("families_none", "?")
    total = evaluation.get("total_families", "?")

    console.print()
    console.print(
        Panel(
            f"[bold]{summary}[/bold]",
            title="Executive Summary",
            border_style="blue",
        )
    )

    console.print()
    console.print(f"  Overall coverage: [bold cyan]{pct}%[/]")
    console.print(
        f"  Families — "
        f"[green]{addressed} addressed[/], "
        f"[yellow]{partial} partial[/], "
        f"[red]{none_count} none[/] "
        f"(of {total} total)"
    )
    console.print()

    table = Table(
        title="Control Family Coverage",
        show_lines=True,
        expand=True,
    )
    table.add_column("Family", style="bold", width=8)
    table.add_column("Name", width=35)
    table.add_column("Score", width=12, justify="center")
    table.add_column("Statements", width=10, justify="center")
    table.add_column("Recommendation", ratio=1)

    for fs in evaluation.get("family_scores", []):
        score_display = SCORE_STYLES.get(fs["score"], fs["score"])
        rec = fs.get("recommendation") or "—"
        table.add_row(
            fs["family_id"],
            fs["family_name"],
            score_display,
            str(fs.get("mapped_statement_count", "?")),
            rec,
        )

    console.print(table)
    console.print()


def print_json(result_dict: dict[str, Any], console: Console | None = None) -> None:
    """Dump the full pipeline result as formatted JSON."""
    if console is None:
        console = Console()
    console.print_json(json.dumps(result_dict, indent=2))
