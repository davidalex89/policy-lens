"""Tests for JSON extraction logic (no network calls)."""

import pytest

from policy_lens.ollama_client import _extract_json, OllamaError


def test_extract_plain_json():
    raw = '{"statements": [{"id": 1, "text": "Use MFA."}]}'
    result = _extract_json(raw)
    assert result["statements"][0]["text"] == "Use MFA."


def test_extract_json_with_code_fences():
    raw = '```json\n{"key": "value"}\n```'
    result = _extract_json(raw)
    assert result["key"] == "value"


def test_extract_json_with_preamble():
    raw = 'Here is the result:\n\n{"key": "value"}\n\nDone.'
    result = _extract_json(raw)
    assert result["key"] == "value"


def test_extract_json_invalid_raises():
    with pytest.raises(OllamaError, match="Could not parse JSON"):
        _extract_json("This is not JSON at all.")


def test_extract_json_with_whitespace():
    raw = "  \n  {\"a\": 1}  \n  "
    result = _extract_json(raw)
    assert result["a"] == 1


def test_extract_json_with_trailing_commas():
    raw = '{"items": [1, 2, 3,], "key": "value",}'
    result = _extract_json(raw)
    assert result["items"] == [1, 2, 3]
    assert result["key"] == "value"


def test_extract_json_nested_with_trailing_comma():
    raw = '{"scores": [{"id": "AC", "score": "addressed",},]}'
    result = _extract_json(raw)
    assert result["scores"][0]["id"] == "AC"
