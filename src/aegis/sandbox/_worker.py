"""Isolated sandbox worker invoked via python -m aegis.sandbox._worker."""

from __future__ import annotations

import json
import os
import sys

from aegis.sandbox.workloads import run_workload


def _load_builtin_workloads() -> None:
    """Import modules that register named workloads for subprocess execution."""
    import importlib

    for module_name in (
        "aegis.execution.mock_model",
        "aegis.execution.hf_workload",
        "aegis.execution.api_llm_workload",
        "aegis.execution.exfil_workload",
    ):
        importlib.import_module(module_name)


def main() -> None:
    _load_builtin_workloads()
    workload_name = os.environ.get("ACE_WORKLOAD", "echo")
    raw = sys.stdin.read()
    payload: dict[str, object] = json.loads(raw) if raw.strip() else {}
    typed_payload = {str(k): v for k, v in payload.items()}
    if workload_name == "echo":
        result = json.dumps(typed_payload)
    else:
        result = run_workload(workload_name, typed_payload)
    sys.stdout.write(result)


if __name__ == "__main__":
    main()
