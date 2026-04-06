"""Pretty-print analysis results using Rich."""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from policy_lens.comparison import ComparisonResult


SCORE_STYLES = {
    "addressed": "[bold green]addressed[/]",
    "partial": "[bold yellow]partial[/]",
    "none": "[bold red]none[/]",
}

# Gap column: positive delta = A stronger (vendor gap), negative = B stronger
GAP_STYLES: dict[int, tuple[str, str]] = {
    2:  ("▼▼", "bold red"),
    1:  ("▼",  "red"),
    0:  ("=",  "dim"),
    -1: ("▲",  "green"),
    -2: ("▲▲", "bold green"),
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


def print_comparison_report(
    comparison: "ComparisonResult",
    console: Console | None = None,
) -> None:
    """Render a policy-to-policy comparison as a rich terminal report."""
    if console is None:
        console = Console()

    cov_a = comparison.coverage_a
    cov_b = comparison.coverage_b
    delta = comparison.coverage_delta

    eval_a = comparison.result_a.evaluation
    eval_b = comparison.result_b.evaluation

    def _stat_line(evaluation: dict[str, Any]) -> str:
        return (
            f"[green]{evaluation.get('families_addressed', '?')} addressed[/], "
            f"[yellow]{evaluation.get('families_partial', '?')} partial[/], "
            f"[red]{evaluation.get('families_none', '?')} none[/]"
        )

    # ── Header ────────────────────────────────────────────────────────────
    console.print()
    console.print(
        Panel(
            f"[bold]Framework:[/] {comparison.framework}\n\n"
            f"  [bold cyan]{comparison.label_a}:[/]  [bold]{cov_a}%[/]  —  {_stat_line(eval_a)}\n"
            f"  [bold cyan]{comparison.label_b}:[/]  [bold]{cov_b}%[/]  —  {_stat_line(eval_b)}\n\n"
            + _delta_summary(delta, comparison.label_a, comparison.label_b),
            title="Policy Comparison",
            border_style="blue",
        )
    )
    console.print()

    # ── Per-family comparison table ────────────────────────────────────────
    table = Table(
        title="Control Family Comparison",
        show_lines=True,
        expand=True,
    )
    table.add_column("Family", style="bold", width=8)
    table.add_column("Name", width=32)
    col_a = Text(comparison.label_a, style="cyan bold")
    col_b = Text(comparison.label_b, style="cyan bold")
    table.add_column(col_a, width=14, justify="center")
    table.add_column(col_b, width=14, justify="center")
    table.add_column("Gap", width=5, justify="center")

    for fc in comparison.family_comparisons:
        score_a_display = SCORE_STYLES.get(fc.score_a, fc.score_a)
        score_b_display = SCORE_STYLES.get(fc.score_b, fc.score_b)
        clamped = max(-2, min(2, fc.delta))
        gap_char, gap_style = GAP_STYLES.get(clamped, ("?", "dim"))
        table.add_row(
            fc.family_id,
            fc.family_name,
            score_a_display,
            score_b_display,
            f"[{gap_style}]{gap_char}[/]",
        )

    console.print(table)

    # ── Vendor gap detail ─────────────────────────────────────────────────
    gaps = comparison.vendor_gaps
    if gaps:
        console.print()
        console.print(
            f"  [bold red]Vendor gaps[/] — {len(gaps)} "
            f"{'family' if len(gaps) == 1 else 'families'} where "
            f"[cyan]{comparison.label_b}[/] falls short:"
        )
        for fc in gaps:
            score_b_display = SCORE_STYLES.get(fc.score_b, fc.score_b)
            score_a_display = SCORE_STYLES.get(fc.score_a, fc.score_a)
            console.print(
                f"    [bold]{fc.family_id}[/] {fc.family_name}  "
                f"{score_b_display} vs {score_a_display}"
            )
            if fc.recommendation_b:
                console.print(
                    f"      [dim]Recommendation for {comparison.label_b}:[/] "
                    f"{fc.recommendation_b}"
                )

    # ── Vendor stronger detail ─────────────────────────────────────────────
    stronger = comparison.vendor_stronger
    if stronger:
        console.print()
        console.print(
            f"  [bold green]Vendor strengths[/] — {len(stronger)} "
            f"{'family' if len(stronger) == 1 else 'families'} where "
            f"[cyan]{comparison.label_b}[/] leads:"
        )
        for fc in stronger:
            score_b_display = SCORE_STYLES.get(fc.score_b, fc.score_b)
            score_a_display = SCORE_STYLES.get(fc.score_a, fc.score_a)
            console.print(
                f"    [bold]{fc.family_id}[/] {fc.family_name}  "
                f"{score_b_display} vs {score_a_display}"
            )

    console.print()


def _delta_summary(delta: int, label_a: str, label_b: str) -> str:
    sign = f"+{delta}" if delta > 0 else str(delta)
    if delta > 0:
        return f"  Coverage delta: [bold red]{sign}pp[/]  ({label_a} is stronger overall)"
    if delta < 0:
        return f"  Coverage delta: [bold green]{sign}pp[/]  ({label_b} is stronger overall)"
    return "  Coverage delta: [dim]0pp[/]  (overall parity)"
