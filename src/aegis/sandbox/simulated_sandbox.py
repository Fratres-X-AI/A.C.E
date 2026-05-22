"""In-process simulated sandbox for laptop and CI."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aegis.ifc.labels import SecurityLabel
from aegis.sandbox.environment import SandboxInfo, SandboxState, new_sandbox_id
from aegis.sandbox.labels import bind_label_to_sandbox
from aegis.utils.config import SandboxConfig
from aegis.utils.typing import SandboxSnapshot


@dataclass
class SimulatedSandbox:
    """Simulated isolation — enforces labels and resource caps without Docker."""

    config: SandboxConfig = field(default_factory=SandboxConfig)
    runtime_name: str = "simulated"
    _state: SandboxState | None = field(default=None, repr=False)
    _memory_used_kb: int = 0

    def create(self, label: SecurityLabel) -> SandboxInfo:
        info = SandboxInfo(
            sandbox_id=new_sandbox_id(),
            runtime=self.runtime_name,
            label=label,
            memory_mb=self.config.memory_mb,
            network_enabled=self.config.network_enabled,
        )
        self._state = SandboxState(info=info)
        return info

    def run_labeled(
        self,
        workload_fn: Callable[[dict[str, Any]], str],
        payload: dict[str, Any],
        label: SecurityLabel,
    ) -> str:
        if self._state is None:
            self.create(label)
        assert self._state is not None
        bind_label_to_sandbox(label, self._state.info.label)
        payload_size = len(json.dumps(payload).encode())
        if payload_size > self.config.memory_mb * 1024:
            msg = f"Payload exceeds sandbox memory cap ({self.config.memory_mb}MB)"
            raise MemoryError(msg)
        self._memory_used_kb = payload_size // 1024
        self._state.exec_count += 1
        if not self.config.network_enabled and payload.get("requires_network"):
            msg = "Network disabled in sandbox"
            raise PermissionError(msg)
        return workload_fn(payload)

    def exec(self, command: list[str]) -> str:
        if self._state is None:
            msg = "Sandbox not created"
            raise RuntimeError(msg)
        self._state.exec_count += 1
        return f"simulated-exec:{' '.join(command)}"

    def snapshot(self) -> SandboxSnapshot:
        if self._state is None:
            msg = "Sandbox not created"
            raise RuntimeError(msg)
        snap = SandboxSnapshot(
            snapshot_id=f"snap-{self._state.exec_count}",
            sandbox_id=self._state.info.sandbox_id,
            label=self._state.info.label.sensitivity.name,
        )
        self._state.snapshots[snap.snapshot_id] = snap
        return snap

    def rollback(self, snapshot_id: str) -> None:
        if self._state is None or snapshot_id not in self._state.snapshots:
            msg = f"Snapshot {snapshot_id} not found"
            raise KeyError(msg)
        self._memory_used_kb = 0

    def inspect(self) -> dict[str, Any]:
        if self._state is None:
            return {"status": "not_created"}
        return {
            "sandbox_id": self._state.info.sandbox_id,
            "runtime": self.runtime_name,
            "label": self._state.info.label.sensitivity.name,
            "exec_count": self._state.exec_count,
            "memory_used_kb": self._memory_used_kb,
            "snapshots": len(self._state.snapshots),
        }

    def destroy(self) -> None:
        self._state = None
        self._memory_used_kb = 0
