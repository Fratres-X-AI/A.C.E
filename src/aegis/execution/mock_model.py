"""Lightweight deterministic mock model — no GPU, no Ollama."""

from __future__ import annotations

import hashlib
import secrets
from typing import Any


def mock_llm(payload: dict[str, Any]) -> str:
    """Deterministic fake LLM for local demos on low-spec hardware."""
    query = str(payload.get("query", "")).lower()
    if "secret" in query or "classified" in query:
        return (
            "Summary: The document discusses project timelines. "
            "No sensitive details included in this public summary."
        )
    if "exfil" in query or "dump" in query:
        token = secrets.token_hex(16)
        return f"base64:{token * 40} steganographic exfil dump"
    if "math" in query or "equation" in query:
        return '{"expression": "x**2 + 1", "verified": true, "variables": ["x"]}'
    return f"Mock response for: {payload.get('query', 'empty')[:80]}"


def mock_tool_search(query: str, sensitivity: str = "PUBLIC") -> dict[str, Any]:
    """Simulated tool returning labeled search results."""
    if "classified" in query.lower():
        return {
            "result": "Project Alpha coordinates: 38.89, -77.03",
            "label": "SECRET",
        }
    return {"result": f"Public FAQ entry for '{query[:40]}'", "label": sensitivity}


def mock_model_hash() -> str:
    """Stable identifier for audit trails."""
    return hashlib.sha256(b"ace-mock-model-v1").hexdigest()[:16]
