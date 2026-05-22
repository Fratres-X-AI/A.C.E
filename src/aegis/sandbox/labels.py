"""Sandbox label binding and clearance checks."""

from __future__ import annotations

from aegis.ifc.labels import SecurityLabel
from aegis.utils.typing import SensitivityLevel


class SandboxLabelError(PermissionError):
    """Raised when workload label exceeds sandbox clearance."""


def bind_label_to_sandbox(
    workload_label: SecurityLabel,
    sandbox_clearance: SecurityLabel,
) -> SecurityLabel:
    """Verify workload may run inside sandbox at given clearance."""
    if workload_label.sensitivity > sandbox_clearance.sensitivity:
        raise SandboxLabelError(
            f"Workload {workload_label.sensitivity.name} exceeds sandbox "
            f"clearance {sandbox_clearance.sensitivity.name}",
        )
    return workload_label


def default_sandbox_clearance(level: str = "INTERNAL") -> SecurityLabel:
    from aegis.utils.typing import IntegrityLevel

    return SecurityLabel(
        sensitivity=SensitivityLevel[level.upper()],
        integrity=IntegrityLevel.VERIFIED,
    )
