"""Tests for the comparison module — no Ollama required."""

from __future__ import annotations

import pytest

from policy_lens.analyzer import AnalysisResult
from policy_lens.comparison import (
    SCORE_RANK,
    ComparisonResult,
    FamilyComparison,
    _build_family_comparisons,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_result(scores: dict[str, str], framework_name: str = "NIST SP 800-53 Rev. 5") -> AnalysisResult:
    """Build a minimal AnalysisResult with the given family_id → score mapping."""
    family_scores = [
        {
            "family_id": fid,
            "family_name": f"Family {fid}",
            "score": score,
            "mapped_statement_count": 1 if score != "none" else 0,
            "recommendation": f"Improve {fid}" if score != "addressed" else None,
        }
        for fid, score in scores.items()
    ]
    addressed = sum(1 for s in scores.values() if s == "addressed")
    partial = sum(1 for s in scores.values() if s == "partial")
    none_c = sum(1 for s in scores.values() if s == "none")
    total = len(scores)
    pct = round((addressed + partial) / total * 100) if total else 0

    return AnalysisResult(
        statements={"statements": []},
        mappings={"mappings": []},
        evaluation={
            "family_scores": family_scores,
            "families_addressed": addressed,
            "families_partial": partial,
            "families_none": none_c,
            "total_families": total,
            "overall_coverage_pct": pct,
            "executive_summary": "Test summary.",
        },
    )


# ── SCORE_RANK sanity ──────────────────────────────────────────────────────────

def test_score_rank_ordering():
    assert SCORE_RANK["addressed"] > SCORE_RANK["partial"] > SCORE_RANK["none"]


# ── FamilyComparison ──────────────────────────────────────────────────────────

def test_family_comparison_delta_positive_means_a_stronger():
    fc = FamilyComparison("AC", "Access Control", "addressed", "none", delta=2)
    assert fc.delta > 0
    assert fc.gap_label == "▼▼"


def test_family_comparison_delta_zero_is_parity():
    fc = FamilyComparison("AC", "Access Control", "partial", "partial", delta=0)
    assert fc.gap_label == "="


def test_family_comparison_delta_negative_means_b_stronger():
    fc = FamilyComparison("AC", "Access Control", "none", "addressed", delta=-2)
    assert fc.delta < 0
    assert fc.gap_label == "▲▲"


def test_family_comparison_to_dict():
    fc = FamilyComparison("AC", "Access Control", "addressed", "partial", delta=1)
    d = fc.to_dict()
    assert d["family_id"] == "AC"
    assert d["score_a"] == "addressed"
    assert d["score_b"] == "partial"
    assert d["delta"] == 1
    assert "gap_label" in d


# ── _build_family_comparisons ─────────────────────────────────────────────────

def test_build_comparisons_parity():
    a = _make_result({"AC": "addressed", "AT": "partial"})
    b = _make_result({"AC": "addressed", "AT": "partial"})
    comps = _build_family_comparisons(a, b)
    assert all(fc.delta == 0 for fc in comps)


def test_build_comparisons_vendor_gap():
    a = _make_result({"AC": "addressed"})
    b = _make_result({"AC": "none"})
    comps = _build_family_comparisons(a, b)
    assert comps[0].delta == 2


def test_build_comparisons_vendor_stronger():
    a = _make_result({"AC": "none"})
    b = _make_result({"AC": "addressed"})
    comps = _build_family_comparisons(a, b)
    assert comps[0].delta == -2


def test_build_comparisons_union_of_families():
    a = _make_result({"AC": "addressed", "AT": "none"})
    b = _make_result({"AC": "partial", "IR": "addressed"})
    comps = _build_family_comparisons(a, b)
    ids = {fc.family_id for fc in comps}
    assert ids == {"AC", "AT", "IR"}


def test_build_comparisons_missing_family_treated_as_none():
    a = _make_result({"AC": "addressed"})
    b = _make_result({})  # AC missing from b
    comps = _build_family_comparisons(a, b)
    ac = next(fc for fc in comps if fc.family_id == "AC")
    assert ac.score_b == "none"
    assert ac.delta == 2


# ── ComparisonResult ──────────────────────────────────────────────────────────

def _make_comparison() -> ComparisonResult:
    a = _make_result({"AC": "addressed", "AT": "addressed", "AU": "partial", "IR": "none",  "SC": "partial"})
    b = _make_result({"AC": "partial",   "AT": "none",      "AU": "none",    "IR": "addressed", "SC": "partial"})
    comps = _build_family_comparisons(a, b)
    return ComparisonResult(
        label_a="Our Policy",
        label_b="Vendor Policy",
        framework="NIST SP 800-53 Rev. 5",
        result_a=a,
        result_b=b,
        family_comparisons=comps,
    )


def test_comparison_result_coverage_properties():
    cr = _make_comparison()
    assert cr.coverage_a == 80  # 4 of 5 addressed/partial
    assert cr.coverage_b == 60  # 3 of 5


def test_comparison_result_coverage_delta():
    cr = _make_comparison()
    assert cr.coverage_delta == 20


def test_comparison_result_vendor_gaps():
    cr = _make_comparison()
    gap_ids = {fc.family_id for fc in cr.vendor_gaps}
    assert "AC" in gap_ids
    assert "AT" in gap_ids


def test_comparison_result_vendor_stronger():
    cr = _make_comparison()
    stronger_ids = {fc.family_id for fc in cr.vendor_stronger}
    assert "IR" in stronger_ids


def test_comparison_result_parity():
    cr = _make_comparison()
    parity_ids = {fc.family_id for fc in cr.parity}
    assert "SC" in parity_ids


def test_comparison_result_to_dict():
    cr = _make_comparison()
    d = cr.to_dict()
    assert d["label_a"] == "Our Policy"
    assert d["label_b"] == "Vendor Policy"
    assert d["coverage_delta"] == 20
    assert "family_comparisons" in d
    assert "result_a" in d
    assert "result_b" in d
    assert len(d["family_comparisons"]) == 5
