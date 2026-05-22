"""Registered workload that calls the local HF inference server."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from aegis.execution.hf_runtime import hf_server_url
from aegis.sandbox.workloads import register_workload


def _post_generate(payload: dict[str, Any]) -> str:
    url = os.environ.get("ACE_HF_SERVER_URL", hf_server_url()) + "/generate"
    prompt = str(payload.get("query") or payload.get("prompt") or "")
    body = json.dumps({"prompt": prompt, "query": prompt}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        msg = (
            f"HF server not reachable at {url}. "
            "Start it first: python examples/runpod_hf_demo.py --serve-only"
        )
        raise RuntimeError(msg) from exc
    return str(data.get("text", ""))


@register_workload("hf_llm")
def hf_llm(payload: dict[str, Any]) -> str:
    """Call loopback HF server (model loaded once on GPU in parent process)."""
    return _post_generate(payload)
