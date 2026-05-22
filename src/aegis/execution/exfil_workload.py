"""Registered malicious workload for sandbox exfil demos."""

from __future__ import annotations

from typing import Any

from aegis.sandbox.workloads import register_workload


@register_workload("exfil_demo")
def exfil_demo(payload: dict[str, Any]) -> str:
    del payload
    return (
        "Summary: quarterly results look good. "
        "SECRET: internal-only revenue figures attached."
    )
