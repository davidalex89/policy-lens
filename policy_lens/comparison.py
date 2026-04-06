"""Policy-to-policy comparison using a shared compliance framework as the anchor.

Both policies are evaluated independently through the existing three-layer
pipeline, then their per-family scores are diffed programmatically to produce
a ComparisonResult — no extra LLM call required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from policy_lens.analyzer import AnalysisResult, load_framework, run_pipeline
from policy_lens.ollama_client import OllamaConfig


# Numeric rank for score comparison; higher = better coverage
SCORE_RANK: dict[str, int] = {"addressed": 2, "partial": 1, "none": 0}

DELTA_LABEL: dict[int, str] = {
    2:  "▼▼",   # a=addressed, b=none  — major vendor gap
    1:  "▼",    # a stronger by one level
    0:  "=",    # parity
    -1: "▲",    # b stronger by one level
    -2: "▲▲",   # b=addressed, a=none  — vendor clearly stronger
}


@dataclass
class FamilyComparison:
    """Per-family comparison between two policies."""

    family_id: str
    family_name: str
    score_a: str                    # "addressed" | "partial" | "none"
    score_b: str
    delta: int                      # rank(a) - rank(b); positive = A stronger
    recommendation_a: str | None = None
    recommendation_b: str | None = None

    @property
    def gap_label(self) -> str:
        clamped = max(-2, min(2, self.delta))
        return DELTA_LABEL.get(clamped, str(self.delta))

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "family_name": self.family_name,
            "score_a": self.score_a,
            "score_b": self.score_b,
            "delta": self.delta,
            "gap_label": self.gap_label,
            "recommendation_a": self.recommendation_a,
            "recommendation_b": self.recommendation_b,
        }


@dataclass
class ComparisonResult:
    """Full comparison of two policies evaluated against a shared framework."""

    label_a: str
    label_b: str
    framework: str
    result_a: AnalysisResult
    result_b: AnalysisResult
    family_comparisons: list[FamilyComparison] = field(default_factory=list)

    # ── Derived stats ────────────────────────────────────────────────────────

    @property
    def coverage_a(self) -> int:
        return int(self.result_a.evaluation.get("overall_coverage_pct", 0))

    @property
    def coverage_b(self) -> int:
        return int(self.result_b.evaluation.get("overall_coverage_pct", 0))

    @property
    def coverage_delta(self) -> int:
        return self.coverage_a - self.coverage_b

    @property
    def vendor_gaps(self) -> list[FamilyComparison]:
        """Families where Policy A is stronger than Policy B."""
        return [f for f in self.family_comparisons if f.delta > 0]

    @property
    def vendor_stronger(self) -> list[FamilyComparison]:
        """Families where Policy B is stronger than Policy A."""
        return [f for f in self.family_comparisons if f.delta < 0]

    @property
    def parity(self) -> list[FamilyComparison]:
        """Families where both policies score the same."""
        return [f for f in self.family_comparisons if f.delta == 0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label_a": self.label_a,
            "label_b": self.label_b,
            "framework": self.framework,
            "coverage_a": self.coverage_a,
            "coverage_b": self.coverage_b,
            "coverage_delta": self.coverage_delta,
            "vendor_gaps": len(self.vendor_gaps),
            "vendor_stronger": len(self.vendor_stronger),
            "parity": len(self.parity),
            "family_comparisons": [f.to_dict() for f in self.family_comparisons],
            "result_a": self.result_a.to_dict(),
            "result_b": self.result_b.to_dict(),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_family_comparisons(
    result_a: AnalysisResult,
    result_b: AnalysisResult,
) -> list[FamilyComparison]:
    scores_a = {s["family_id"]: s for s in result_a.evaluation.get("family_scores", [])}
    scores_b = {s["family_id"]: s for s in result_b.evaluation.get("family_scores", [])}

    all_ids = sorted(set(scores_a) | set(scores_b))
    comparisons: list[FamilyComparison] = []

    for fid in all_ids:
        sa = scores_a.get(fid, {})
        sb = scores_b.get(fid, {})
        score_a = sa.get("score", "none")
        score_b = sb.get("score", "none")
        delta = SCORE_RANK.get(score_a, 0) - SCORE_RANK.get(score_b, 0)
        comparisons.append(
            FamilyComparison(
                family_id=fid,
                family_name=sa.get("family_name") or sb.get("family_name", fid),
                score_a=score_a,
                score_b=score_b,
                delta=delta,
                recommendation_a=sa.get("recommendation"),
                recommendation_b=sb.get("recommendation"),
            )
        )

    return comparisons


def _make_progress_cb(
    policy_label: str,
    on_progress: Callable | None,
) -> Callable | None:
    """Wrap the user-supplied progress callback with a policy label."""
    if on_progress is None:
        return None

    async def cb(layer_num: int, name: str, result: dict) -> None:
        await on_progress(policy_label, layer_num, name, result)

    return cb


# ── Public API ────────────────────────────────────────────────────────────────

async def run_comparison(
    policy_text_a: str,
    policy_text_b: str,
    label_a: str = "Policy A",
    label_b: str = "Policy B",
    config: OllamaConfig | None = None,
    framework: str = "nist_800_53",
    on_progress: Callable | None = None,
) -> ComparisonResult:
    """Evaluate two policies against the same framework and diff the results.

    Args:
        policy_text_a: Raw text of the reference (your) policy.
        policy_text_b: Raw text of the policy to compare against (e.g. vendor).
        label_a: Display label for policy A.
        label_b: Display label for policy B.
        config: Ollama connection/model configuration.
        framework: Framework JSON name (without extension).
        on_progress: Optional async callback(policy_label, layer_num, name, result)
            called after each of the six pipeline layers completes.

    Returns:
        ComparisonResult with per-family scores, deltas, and full sub-results.
    """
    if config is None:
        config = OllamaConfig()

    result_a = await run_pipeline(
        policy_text=policy_text_a,
        config=config,
        framework=framework,
        on_layer_complete=_make_progress_cb(label_a, on_progress),
    )
    result_b = await run_pipeline(
        policy_text=policy_text_b,
        config=config,
        framework=framework,
        on_layer_complete=_make_progress_cb(label_b, on_progress),
    )

    fw = load_framework(framework)
    return ComparisonResult(
        label_a=label_a,
        label_b=label_b,
        framework=fw.get("framework", framework),
        result_a=result_a,
        result_b=result_b,
        family_comparisons=_build_family_comparisons(result_a, result_b),
    )
