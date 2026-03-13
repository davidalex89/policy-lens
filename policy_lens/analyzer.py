"""Three-layer analysis pipeline.

Orchestrates the prompt chain:
  Layer 1 (Extract)  →  Layer 2 (Map)  →  Layer 3 (Evaluate)

Each layer feeds its structured output into the next layer's user prompt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from policy_lens.ollama_client import OllamaConfig, chat_json
from policy_lens.prompts import (
    EXTRACT_SYSTEM_PROMPT,
    EVALUATE_SYSTEM_PROMPT,
    MAP_SYSTEM_PROMPT,
    build_extract_user_prompt,
    build_evaluate_user_prompt,
    build_map_user_prompt,
)

FRAMEWORKS_DIR = Path(__file__).parent / "frameworks"


@dataclass
class AnalysisResult:
    """Container for the full pipeline output."""

    statements: dict[str, Any] = field(default_factory=dict)
    mappings: dict[str, Any] = field(default_factory=dict)
    evaluation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "statements": self.statements,
            "mappings": self.mappings,
            "evaluation": self.evaluation,
        }


def load_framework(name: str = "nist_800_53") -> dict[str, Any]:
    path = FRAMEWORKS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Framework file not found: {path}")
    return json.loads(path.read_text())


async def run_pipeline(
    policy_text: str,
    config: OllamaConfig | None = None,
    framework: str = "nist_800_53",
    on_layer_complete: Any | None = None,
) -> AnalysisResult:
    """Execute the full three-layer analysis pipeline.

    Args:
        policy_text: Raw text of the security policy document.
        config: Ollama connection/model configuration.
        framework: Name of the framework JSON file (without extension).
        on_layer_complete: Optional async callback(layer_num, layer_name, result)
            invoked after each layer finishes.

    Returns:
        AnalysisResult with the output from all three layers.
    """
    if config is None:
        config = OllamaConfig()

    fw = load_framework(framework)
    families_json = json.dumps(fw["control_families"], indent=2)
    result = AnalysisResult()

    # --- Layer 1: Extract ---
    statements = await chat_json(
        config,
        EXTRACT_SYSTEM_PROMPT,
        build_extract_user_prompt(policy_text),
    )
    result.statements = statements
    if on_layer_complete:
        await on_layer_complete(1, "extract", statements)

    # --- Layer 2: Map ---
    mappings = await chat_json(
        config,
        MAP_SYSTEM_PROMPT,
        build_map_user_prompt(json.dumps(statements, indent=2), families_json),
    )
    result.mappings = mappings
    if on_layer_complete:
        await on_layer_complete(2, "map", mappings)

    # --- Layer 3: Evaluate ---
    evaluation = await chat_json(
        config,
        EVALUATE_SYSTEM_PROMPT,
        build_evaluate_user_prompt(json.dumps(mappings, indent=2), families_json),
    )
    result.evaluation = evaluation
    if on_layer_complete:
        await on_layer_complete(3, "evaluate", evaluation)

    return result
