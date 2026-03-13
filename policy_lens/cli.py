"""Command-line interface for policy-lens."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live

from policy_lens import __version__
from policy_lens.analyzer import AnalysisResult, run_pipeline
from policy_lens.ollama_client import OllamaConfig, OllamaError
from policy_lens.report import print_json, print_report


LAYER_LABELS = {1: "Extracting policy statements", 2: "Mapping to NIST 800-53", 3: "Evaluating coverage"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="policy-lens",
        description=(
            "Evaluate a security policy against NIST 800-53 using "
            "layered LLM prompts via Ollama."
        ),
    )
    p.add_argument(
        "policy_file",
        type=Path,
        help="Path to a text/markdown security policy document.",
    )
    p.add_argument(
        "-m", "--model",
        default="llama3",
        help="Ollama model to use (default: llama3).",
    )
    p.add_argument(
        "-u", "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API base URL (default: http://localhost:11434).",
    )
    p.add_argument(
        "-f", "--framework",
        default="nist_800_53",
        help="Framework to evaluate against (default: nist_800_53).",
    )
    p.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Write the full JSON result to a file.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print raw JSON output instead of the formatted report.",
    )
    p.add_argument(
        "-t", "--temperature",
        type=float,
        default=0.1,
        help="LLM sampling temperature (default: 0.1).",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Request timeout in seconds (default: 300).",
    )
    p.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return p


async def _run(args: argparse.Namespace, console: Console) -> AnalysisResult:
    policy_text = args.policy_file.read_text()
    if not policy_text.strip():
        console.print("[red]Error:[/] Policy file is empty.")
        sys.exit(1)

    config = OllamaConfig(
        base_url=args.ollama_url,
        model=args.model,
        temperature=args.temperature,
        timeout=args.timeout,
    )

    current_label = LAYER_LABELS[1]

    async def on_layer_complete(layer_num: int, _name: str, _result: dict) -> None:
        nonlocal current_label
        next_layer = layer_num + 1
        if next_layer in LAYER_LABELS:
            current_label = LAYER_LABELS[next_layer]

    with Live(
        Spinner("dots", text=f"  {current_label}…"),
        console=console,
        refresh_per_second=8,
        transient=True,
    ) as live:

        async def on_layer_complete_with_live(
            layer_num: int, name: str, result: dict
        ) -> None:
            await on_layer_complete(layer_num, name, result)
            console.print(f"  [green]✓[/] Layer {layer_num}: {LAYER_LABELS[layer_num]}")
            live.update(Spinner("dots", text=f"  {current_label}…"))

        return await run_pipeline(
            policy_text=policy_text,
            config=config,
            framework=args.framework,
            on_layer_complete=on_layer_complete_with_live,
        )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    console = Console(stderr=True)

    if not args.policy_file.exists():
        console.print(f"[red]Error:[/] File not found: {args.policy_file}")
        sys.exit(1)

    console.print(
        f"\n[bold blue]policy-lens[/] v{__version__}  ·  "
        f"model: [cyan]{args.model}[/]  ·  "
        f"framework: [cyan]{args.framework}[/]\n"
    )

    try:
        result = asyncio.run(_run(args, console))
    except OllamaError as exc:
        console.print(f"\n[red]Error:[/] {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/]")
        sys.exit(130)

    output_console = Console()

    if args.json_output:
        print_json(result.to_dict(), console=output_console)
    else:
        print_report(result.evaluation, console=output_console)

    if args.output:
        args.output.write_text(json.dumps(result.to_dict(), indent=2))
        console.print(f"  Full results written to [bold]{args.output}[/]\n")


if __name__ == "__main__":
    main()
