# policy-lens

Evaluate security policies against NIST 800-53 using layered LLM prompts via [Ollama](https://ollama.com).

`policy-lens` takes a plain-text security policy document, passes it through a **three-layer prompt chain** running on a local LLM, and produces a coverage report showing which NIST SP 800-53 Rev. 5 control families are addressed, partially covered, or missing entirely.

## How It Works

The analysis pipeline chains three specialized system prompts, where each layer's structured output feeds the next:

```
┌─────────────────────┐     ┌─────────────────-─────┐     ┌─────────────────────┐
│  Layer 1: Extract   │────▶│   Layer 2: Map        │────▶│  Layer 3: Evaluate  │
│                     │     │                       │     │                     │
│  Parse policy into  │     │  Map each statement   │     │  Score coverage per │
│  discrete statements│     │  to NIST 800-53       │     │  control family,    │
│                     │     │  control families     │     │  identify gaps      │
└─────────────────────┘     └──────────────────-────┘     └─────────────────────┘
```

1. **Extract** — Parses the policy document into discrete, actionable policy statements.
2. **Map** — Maps each statement to one or more NIST 800-53 control families with rationale.
3. **Evaluate** — Scores coverage per control family (`addressed` / `partial` / `none`), computes an overall coverage percentage, and provides gap recommendations.

All inference runs **locally** via Ollama — no data leaves your machine.

## Web UI (No Server Required)

`policy-lens` includes a **single-file web interface** that runs entirely in your browser — no web server, no backend, no build step. It calls Ollama's local API directly via `fetch()`.

```bash
# Just open the file
open index.html
```

The web UI provides:
- Interactive three-layer pipeline with live progress
- Paste or drag-and-drop policy documents
- Full coverage report with detailed findings
- Print / Save as PDF via the browser

> Since Ollama runs on `localhost:11434` with CORS support, the browser can call it directly. All data stays local.

## Prerequisites

- **Python 3.10+**
- **[Ollama](https://ollama.com)** installed and running (`ollama serve`)
- A model pulled (e.g. `ollama pull llama3`)

## Installation

```bash
# Clone the repo
git clone https://github.com/davidalex89/policy-lens.git
cd policy-lens

# Create a virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start

```bash
# Make sure Ollama is running
ollama serve &

# Analyze the included sample policy
policy-lens examples/sample_policy.txt
```

This produces a formatted table showing coverage per NIST 800-53 control family, along with an executive summary and gap recommendations.

## Usage

```
policy-lens [-h] [-m MODEL] [-u OLLAMA_URL] [-f FRAMEWORK]
            [-o OUTPUT] [--json] [-t TEMPERATURE] [--timeout TIMEOUT]
            [-v]
            policy_file
```

| Flag | Description | Default |
|------|-------------|---------|
| `policy_file` | Path to the policy document (text/markdown) | *(required)* |
| `-m, --model` | Ollama model name | `llama3` |
| `-u, --ollama-url` | Ollama API base URL | `http://localhost:11434` |
| `-f, --framework` | Framework to evaluate against | `nist_800_53` |
| `-o, --output` | Write full JSON results to a file | — |
| `--pdf FILE` | Generate a styled PDF report | — |
| `--json` | Print raw JSON instead of the formatted report | — |
| `-t, --temperature` | LLM sampling temperature | `0.1` |
| `--timeout` | Request timeout in seconds | `300` |

### Examples

```bash
# Use a specific model
policy-lens -m mistral examples/sample_policy.txt

# Generate a PDF report
policy-lens --pdf report.pdf examples/sample_policy.txt

# Save full results (all three layers) to JSON
policy-lens -o results.json examples/sample_policy.txt

# Pipe JSON output for scripting
policy-lens --json examples/sample_policy.txt | jq '.evaluation.overall_coverage_pct'
```

## Extending

### Adding Frameworks

Drop a JSON file into `policy_lens/frameworks/` following the same schema as `nist_800_53.json`, then reference it with `-f your_framework_name`.

The schema expects:

```json
{
  "framework": "Framework Display Name",
  "description": "...",
  "control_families": [
    {
      "id": "XX",
      "name": "Family Name",
      "description": "What this family covers.",
      "example_controls": ["XX-1 Control Name", "XX-2 Another Control"]
    }
  ]
}
```

### Customizing Prompts

The system prompts live in `policy_lens/prompts/` as plain Python strings. Edit them to tune extraction quality, adjust scoring criteria, or change the output schema.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Project Structure

```
policy-lens/
├── policy_lens/
│   ├── __init__.py
│   ├── cli.py               # CLI entry point
│   ├── analyzer.py           # Three-layer pipeline orchestration
│   ├── ollama_client.py      # Async Ollama HTTP client
│   ├── report.py             # Rich terminal output
│   ├── pdf_report.py         # PDF report generation
│   ├── prompts/
│   │   ├── layer1_extract.py # System prompt: statement extraction
│   │   ├── layer2_map.py     # System prompt: control family mapping
│   │   └── layer3_evaluate.py# System prompt: coverage evaluation
│   └── frameworks/
│       └── nist_800_53.json  # NIST 800-53 Rev. 5 control families
├── examples/
│   └── sample_policy.txt     # Example policy for testing
├── tests/
├── index.html                # Self-contained web UI (no server needed)
├── pyproject.toml
├── LICENSE                   # Apache 2.0
└── README.md
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
