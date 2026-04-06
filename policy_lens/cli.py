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
from policy_lens.comparison import ComparisonResult, run_comparison
from policy_lens.ollama_client import OllamaConfig, OllamaError
from policy_lens.pdf_report import generate_pdf, generate_comparison_pdf
from policy_lens.report import print_json, print_report, print_comparison_report


LAYER_LABELS = {1: "Extracting policy statements", 2: "Mapping to control families", 3: "Evaluating coverage"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="policy-lens",
        description=(
            "Evaluate a security policy against a compliance framework using "
            "layered LLM prompts via Ollama. Use --compare to diff two policies."
        ),
    )
    p.add_argument(
        "policy_file",
        type=Path,
        help="Path to a security policy document (.txt, .md, or .pdf).",
    )
    p.add_argument(
        "--compare",
        type=Path,
        default=None,
        metavar="POLICY_FILE",
        help=(
            "Compare policy_file against a second policy document. "
            "Runs both through the same framework and produces a gap analysis."
        ),
    )
    p.add_argument(
        "--label-a",
        default=None,
        metavar="LABEL",
        help="Display label for policy_file in comparison mode (default: filename).",
    )
    p.add_argument(
        "--label-b",
        default=None,
        metavar="LABEL",
        help="Display label for the --compare file in comparison mode (default: filename).",
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
        help=(
            "Framework to evaluate against (default: nist_800_53). "
            "Available: nist_800_53, iso27001_2022, soc2_type2, cis_controls_v8, adobe_ccf_v5."
        ),
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
        "--pdf",
        type=Path,
        default=None,
        metavar="FILE",
        help="Generate a PDF report at the given path.",
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


def _read_policy(path: Path) -> str:
    """Read policy text from .txt, .md, or .pdf files."""
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise SystemExit(
                "PDF support requires pypdf. Install it with: pip install pypdf"
            )
        reader = PdfReader(path)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text()


# ── Single-policy analysis ────────────────────────────────────────────────────

async def _run(args: argparse.Namespace, console: Console) -> AnalysisResult:
    policy_text = _read_policy(args.policy_file)
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


# ── Comparison mode ───────────────────────────────────────────────────────────

async def _run_comparison(args: argparse.Namespace, console: Console) -> ComparisonResult:
    policy_text_a = _read_policy(args.policy_file)
    policy_text_b = _read_policy(args.compare)

    if not policy_text_a.strip():
        console.print(f"[red]Error:[/] {args.policy_file} is empty.")
        sys.exit(1)
    if not policy_text_b.strip():
        console.print(f"[red]Error:[/] {args.compare} is empty.")
        sys.exit(1)

    label_a = args.label_a or args.policy_file.name
    label_b = args.label_b or args.compare.name

    config = OllamaConfig(
        base_url=args.ollama_url,
        model=args.model,
        temperature=args.temperature,
        timeout=args.timeout,
    )

    current_spinner = f"[{label_a}] {LAYER_LABELS[1]}…"

    with Live(
        Spinner("dots", text=f"  {current_spinner}"),
        console=console,
        refresh_per_second=8,
        transient=True,
    ) as live:

        async def on_progress(
            policy_label: str, layer_num: int, _name: str, _result: dict
        ) -> None:
            nonlocal current_spinner
            console.print(
                f"  [green]✓[/] [{policy_label}] Layer {layer_num}: {LAYER_LABELS[layer_num]}"
            )
            next_layer = layer_num + 1
            if next_layer in LAYER_LABELS:
                current_spinner = f"[{policy_label}] {LAYER_LABELS[next_layer]}…"
                live.update(Spinner("dots", text=f"  {current_spinner}"))

        return await run_comparison(
            policy_text_a=policy_text_a,
            policy_text_b=policy_text_b,
            label_a=label_a,
            label_b=label_b,
            config=config,
            framework=args.framework,
            on_progress=on_progress,
        )


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    console = Console(stderr=True)

    if not args.policy_file.exists():
        console.print(f"[red]Error:[/] File not found: {args.policy_file}")
        sys.exit(1)

    if args.compare and not args.compare.exists():
        console.print(f"[red]Error:[/] File not found: {args.compare}")
        sys.exit(1)

    mode = "compare" if args.compare else "analyze"

    console.print(
        f"\n[bold blue]policy-lens[/] v{__version__}  ·  "
        f"mode: [cyan]{mode}[/]  ·  "
        f"model: [cyan]{args.model}[/]  ·  "
        f"framework: [cyan]{args.framework}[/]\n"
    )

    output_console = Console()

    try:
        if mode == "compare":
            comparison = asyncio.run(_run_comparison(args, console))

            if args.json_output:
                print_json(comparison.to_dict(), console=output_console)
            else:
                print_comparison_report(comparison, console=output_console)

            if args.pdf:
                generate_comparison_pdf(
                    comparison.to_dict(),
                    output_path=args.pdf,
                    model=args.model,
                )
                console.print(f"  PDF report written to [bold]{args.pdf}[/]")

            if args.output:
                args.output.write_text(json.dumps(comparison.to_dict(), indent=2))
                console.print(f"  Full results written to [bold]{args.output}[/]\n")

        else:
            result = asyncio.run(_run(args, console))

            if args.json_output:
                print_json(result.to_dict(), console=output_console)
            else:
                print_report(result.evaluation, console=output_console)

            if args.pdf:
                from policy_lens.analyzer import load_framework
                fw = load_framework(args.framework)
                generate_pdf(
                    result.to_dict(),
                    output_path=args.pdf,
                    framework=fw.get("framework", args.framework),
                    model=args.model,
                )
                console.print(f"  PDF report written to [bold]{args.pdf}[/]")

            if args.output:
                args.output.write_text(json.dumps(result.to_dict(), indent=2))
                console.print(f"  Full results written to [bold]{args.output}[/]\n")

    except OllamaError as exc:
        console.print(f"\n[red]Error:[/] {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/]")
        sys.exit(130)


if __name__ == "__main__":
    main()
