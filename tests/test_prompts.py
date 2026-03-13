"""Tests for the prompt layer builders — no Ollama required."""

from policy_lens.prompts import (
    EXTRACT_SYSTEM_PROMPT,
    MAP_SYSTEM_PROMPT,
    EVALUATE_SYSTEM_PROMPT,
    build_extract_user_prompt,
    build_map_user_prompt,
    build_evaluate_user_prompt,
)


def test_extract_system_prompt_mentions_json():
    assert "JSON" in EXTRACT_SYSTEM_PROMPT


def test_map_system_prompt_mentions_control_families():
    assert "control families" in MAP_SYSTEM_PROMPT.lower()


def test_evaluate_system_prompt_mentions_coverage():
    assert "coverage" in EVALUATE_SYSTEM_PROMPT.lower()


def test_build_extract_user_prompt_wraps_text():
    prompt = build_extract_user_prompt("All users must use MFA.")
    assert "BEGIN POLICY DOCUMENT" in prompt
    assert "END POLICY DOCUMENT" in prompt
    assert "All users must use MFA." in prompt


def test_build_map_user_prompt_includes_both_inputs():
    prompt = build_map_user_prompt('{"statements": []}', '{"families": []}')
    assert "POLICY STATEMENTS" in prompt
    assert "CONTROL FAMILIES" in prompt


def test_build_evaluate_user_prompt_includes_both_inputs():
    prompt = build_evaluate_user_prompt('{"mappings": []}', '{"families": []}')
    assert "MAPPINGS" in prompt
    assert "CONTROL FAMILIES" in prompt
