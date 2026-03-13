"""Tests for the analyzer module — framework loading and result structure."""

import pytest

from policy_lens.analyzer import AnalysisResult, load_framework


def test_load_nist_framework():
    fw = load_framework("nist_800_53")
    assert fw["framework"] == "NIST SP 800-53 Rev. 5"
    assert len(fw["control_families"]) == 20


def test_load_framework_missing():
    with pytest.raises(FileNotFoundError):
        load_framework("nonexistent_framework")


def test_analysis_result_to_dict():
    r = AnalysisResult(
        statements={"statements": [{"id": 1, "text": "test"}]},
        mappings={"mappings": []},
        evaluation={"overall_coverage_pct": 50},
    )
    d = r.to_dict()
    assert "statements" in d
    assert "mappings" in d
    assert "evaluation" in d
    assert d["evaluation"]["overall_coverage_pct"] == 50


def test_nist_families_have_required_fields():
    fw = load_framework("nist_800_53")
    for family in fw["control_families"]:
        assert "id" in family
        assert "name" in family
        assert "description" in family
        assert len(family["id"]) == 2
