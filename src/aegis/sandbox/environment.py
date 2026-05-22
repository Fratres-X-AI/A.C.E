"""Sandbox environment protocol and shared types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from aegis.ifc.labels import SecurityLabel
from aegis.utils.typing import SandboxSnapshot


@dataclass
class SandboxInfo:
    """Runtime metadata for an isolated sandbox."""

    sandbox_id: str
    runtime: str
    label: SecurityLabel
    memory_mb: int
    network_enabled: bool


class SandboxEnvironment(Protocol):
    """Protocol for self-hosted sandbox runtimes."""

    runtime_name: str

    def create(self, label: SecurityLabel) -> SandboxInfo: ...

    def run_labeled(
        self,
        workload_fn: Callable[[dict[str, Any]], str],
        payload: dict[str, Any],
        label: SecurityLabel,
    ) -> str: ...

    def exec(self, command: list[str]) -> str: ...

    def snapshot(self) -> SandboxSnapshot: ...

    def rollback(self, snapshot_id: str) -> None: ...

    def inspect(self) -> dict[str, Any]: ...

    def destroy(self) -> None: ...


@dataclass
class SandboxState:
    """Internal mutable sandbox state."""

    info: SandboxInfo
    snapshots: dict[str, SandboxSnapshot] = field(default_factory=dict)
    exec_count: int = 0


def new_sandbox_id() -> str:
    return f"sbx-{uuid4().hex[:12]}"
