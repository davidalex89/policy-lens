"""Thin async client for the Ollama HTTP API."""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx


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
    """Send a chat request and parse the response as JSON.

    Attempts to extract JSON from the response even if the model wraps it
    in markdown fences or preamble text.
    """
    raw = await chat(config, system_prompt, user_prompt)
    return _extract_json(raw)


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from LLM output."""
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the first { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise OllamaError(
        "Could not parse JSON from model response. "
        "Try a more capable model or re-run. Raw response:\n" + text[:500]
    )
