"""Thin async client for the Ollama HTTP API."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx


MAX_RETRIES = 2


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "llama3"
    temperature: float = 0.1
    timeout: float = 300.0


class OllamaError(Exception):
    """Raised when Ollama returns an error or is unreachable."""


async def chat(
    config: OllamaConfig,
    system_prompt: str,
    user_prompt: str,
    force_json: bool = False,
) -> str:
    """Send a chat completion request and return the assistant's response text."""
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": config.temperature,
        },
    }
    if force_json:
        payload["format"] = "json"

    async with httpx.AsyncClient(
        base_url=config.base_url,
        timeout=config.timeout,
    ) as client:
        try:
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise OllamaError(
                f"Cannot connect to Ollama at {config.base_url}. "
                "Is Ollama running? (try: ollama serve)"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"Ollama returned HTTP {exc.response.status_code}: "
                f"{exc.response.text}"
            ) from exc

    data = resp.json()
    return data["message"]["content"]


async def chat_json(
    config: OllamaConfig,
    system_prompt: str,
    user_prompt: str,
) -> dict:
    """Send a chat request with JSON mode enabled and parse the response.

    Uses Ollama's native format:"json" to constrain output, with retry
    and fallback extraction if needed.
    """
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        raw = await chat(config, system_prompt, user_prompt, force_json=True)
        try:
            return _extract_json(raw)
        except OllamaError as exc:
            last_err = exc
            if attempt < MAX_RETRIES:
                continue
    raise last_err  # type: ignore[misc]


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from LLM output."""
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the outermost { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        # Try fixing trailing commas (common with small models)
        cleaned = _fix_trailing_commas(candidate)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    raise OllamaError(
        "Could not parse JSON from model response after retries. "
        "Raw response:\n" + text[:1000]
    )


def _fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] which small models sometimes emit."""
    return re.sub(r",\s*([}\]])", r"\1", text)
