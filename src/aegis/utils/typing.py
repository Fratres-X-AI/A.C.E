"""Shared type definitions for A.C.E containment layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any


class SensitivityLevel(IntEnum):
    """Confidentiality lattice — higher values are more sensitive."""

    PUBLIC = 0
    INTERNAL = 1
    SECRET = 2
    TOP_SECRET = 3


class IntegrityLevel(IntEnum):
    """Integrity lattice — higher values require stronger provenance."""

    UNTRUSTED = 0
    VERIFIED = 1
    ATTESTED = 2
    FORMAL = 3


class ContainmentVerdict(IntEnum):
    """Outcome of a containment check."""

    ALLOW = 0
    THROTTLE = 1
    BLOCK = 2
    KILL_SESSION = 3


class FlowOperation(IntEnum):
    """Information flow operation types for IFC enforcement."""

    READ = 0
    WRITE = 1
    DECLASSIFY = 2


@dataclass(frozen=True)
class AuditEvent:
    """Structured audit event emitted by containment layers."""

    layer: str
    action: str
    detail: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContainmentResult:
    """Final result of processing through the containment engine."""

    output: str | None
    verdict: ContainmentVerdict
    blocked: bool
    reasons: list[str] = field(default_factory=list)
    metrics_snapshot: dict[str, float | int] = field(default_factory=dict)
    audit_event_count: int = 0
