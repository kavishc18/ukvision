"""Thin wrapper around the Groq OpenAI-compatible chat completions API.

Model names rotate — check https://console.groq.com/docs/models and
https://console.groq.com/docs/deprecations before relying on the defaults
below, and update FILTER_MODEL / CLASSIFY_MODEL / BRIEF_MODEL here (one
place) if they've been deprecated.

llama-3.1-8b-instant and llama-3.3-70b-versatile are deprecated on the
free/developer tier (shutdown 2026-08-16); using their Groq-recommended
openai/gpt-oss replacements instead.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

FILTER_MODEL = "openai/gpt-oss-20b"
CLASSIFY_MODEL = "openai/gpt-oss-120b"
BRIEF_MODEL = "openai/gpt-oss-120b"


class GroqError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise GroqError(
            "GROQ_API_KEY is not set. Get a free key at console.groq.com "
            "and export it, or set it as a GitHub Actions secret."
        )
    return key


def chat_json(
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 5,
    temperature: float = 0.0,
) -> dict:
    """Call Groq chat completions with JSON mode, return the parsed JSON body."""
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        GROQ_API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    delay = 2.0
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read())
                content = payload["choices"][0]["message"]["content"]
                return json.loads(content)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise GroqError(f"Groq API error {e.code}: {e.read().decode(errors='replace')}") from e
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise GroqError(f"Groq API connection failed: {e}") from e

    raise GroqError("Groq API retries exhausted")
