"""Registered workload that calls an OpenAI-compatible Llama/chat API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from aegis.sandbox.workloads import register_workload

_DEFAULT_API_BASE = "https://router.huggingface.co/v1"
_DEFAULT_MODEL = "meta-llama/Llama-3.1-8B-Instruct:novita"


def api_base() -> str:
    raw = os.environ.get("ACE_LLM_API_BASE", _DEFAULT_API_BASE)
    return raw.rstrip("/")


def api_key() -> str | None:
    raw = (
        os.environ.get("ACE_LLM_API_KEY")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_HUB_TOKEN")
        or os.environ.get("OPENAI_API_KEY")
    )
    return raw.strip() if raw else None


def api_model() -> str:
    return os.environ.get("ACE_LLM_MODEL", _DEFAULT_MODEL)


def completions_url() -> str:
    explicit = os.environ.get("ACE_LLM_API_URL")
    if explicit:
        return explicit.rstrip("/")
    base = api_base()
    if not base:
        msg = "Set ACE_LLM_API_BASE (default: https://router.huggingface.co/v1)"
        raise RuntimeError(msg)
    return f"{base}/chat/completions"


def verify_api_config() -> dict[str, Any]:
    """Validate API env vars before running containment demo."""
    key = api_key()
    if not key:
        return {
            "ok": False,
            "error": (
                "No API key found. Set HF_TOKEN=hf_... "
                "(or ACE_LLM_API_KEY / OPENAI_API_KEY)."
            ),
        }
    try:
        completions_url()
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "model": api_model(), "url": completions_url()}


def _extract_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict) and message.get("content"):
            return str(message["content"]).strip()
        text = choices[0].get("text") if isinstance(choices[0], dict) else None
        if text:
            return str(text).strip()
    if data.get("output_text"):
        return str(data["output_text"]).strip()
    if data.get("generated_text"):
        return str(data["generated_text"]).strip()
    msg = f"Unexpected API response shape: {list(data.keys())}"
    raise RuntimeError(msg)


def _post_chat(payload: dict[str, Any]) -> str:
    prompt = str(payload.get("query") or payload.get("prompt") or "")
    key = api_key()
    if not key:
        msg = "ACE_LLM_API_KEY not set"
        raise RuntimeError(msg)

    url = completions_url()
    body = json.dumps(
        {
            "model": api_model(),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(os.environ.get("ACE_LLM_MAX_TOKENS", "256")),
            "temperature": float(os.environ.get("ACE_LLM_TEMPERATURE", "0.7")),
        },
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        msg = f"LLM API HTTP {exc.code} at {url}: {detail}"
        raise RuntimeError(msg) from exc
    except urllib.error.URLError as exc:
        msg = f"LLM API not reachable at {url}: {exc}"
        raise RuntimeError(msg) from exc
    return _extract_text(data)


@register_workload("api_llm")
def api_llm(payload: dict[str, Any]) -> str:
    """Call external OpenAI-compatible chat API (Together, Groq, etc.)."""
    return _post_chat(payload)
