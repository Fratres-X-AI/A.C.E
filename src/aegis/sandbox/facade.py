"""Single-session facade implementing SandboxEnvironment over SandboxBackend."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aegis.audit.tamper_proof_log import TamperProofLog
from aegis.ifc.labels import SecurityLabel
from aegis.sandbox.base import SandboxBackend, SandboxBackendError, SandboxCreateConfig
from aegis.sandbox.environment import SandboxInfo
from aegis.sandbox.workloads import resolve_workload_name
from aegis.utils.config import SandboxConfig
from aegis.utils.typing import AuditEvent, SandboxSnapshot


@dataclass
class SandboxSessionFacade:
    """High-level sandbox session — implements SandboxEnvironment protocol."""

    backend: SandboxBackend
    config: SandboxConfig = field(default_factory=SandboxConfig)
    audit_log: TamperProofLog | None = None
    runtime_name: str = field(init=False)
    _sandbox_id: str | None = field(default=None, repr=False)
    _snapshots: dict[str, SandboxSnapshot] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.runtime_name = self.backend.name

    def create(self, label: SecurityLabel) -> SandboxInfo:
        create_cfg = SandboxCreateConfig(policy=self.config, label=label)
        info = self.backend.create(create_cfg)
        self.backend.start(info.sandbox_id)
        self._sandbox_id = info.sandbox_id
        self._audit("create", info.sandbox_id, {"backend": self.backend.name})
        return info

    def run_labeled(
        self,
        workload_fn: Callable[[dict[str, Any]], str],
        payload: dict[str, Any],
        label: SecurityLabel,
    ) -> str:
        if self._sandbox_id is None:
            self.create(label)
        assert self._sandbox_id is not None
        self.backend.enforce_ifc(self._sandbox_id, label)
        workload_name = resolve_workload_name(workload_fn)
        if workload_name is None:
            msg = (
                "Callable workloads must be registered via @register_workload "
                "before running in an isolated sandbox backend."
            )
            raise SandboxBackendError(msg)
        command = [
            sys.executable,
            "-m",
            "aegis.sandbox._worker",
        ]
        payload_json = json.dumps(payload)
        output = self.backend.run(
            self._sandbox_id,
            command,
            input_text=payload_json,
            env={"ACE_WORKLOAD": workload_name},
        )
        self._audit("workload_complete", self._sandbox_id, {"workload": workload_name})
        return output

    def exec(self, command: list[str]) -> str:
        if self._sandbox_id is None:
            msg = "Sandbox not created"
            raise SandboxBackendError(msg)
        return self.backend.run(self._sandbox_id, command)

    def snapshot(self) -> SandboxSnapshot:
        if self._sandbox_id is None:
            msg = "Sandbox not created"
            raise SandboxBackendError(msg)
        state = self.backend.inspect(self._sandbox_id)
        snap = SandboxSnapshot(
            snapshot_id=f"snap-{state.get('exec_count', 0)}",
            sandbox_id=self._sandbox_id,
            label=str(state.get("label", "UNKNOWN")),
        )
        self._snapshots[snap.snapshot_id] = snap
        return snap

    def rollback(self, snapshot_id: str) -> None:
        if snapshot_id not in self._snapshots:
            msg = f"Snapshot {snapshot_id} not found"
            raise KeyError(msg)

    def inspect(self) -> dict[str, Any]:
        if self._sandbox_id is None:
            return {"status": "not_created"}
        return self.backend.inspect(self._sandbox_id)

    def destroy(self) -> None:
        if self._sandbox_id is not None:
            self.backend.stop(self._sandbox_id)
            self.backend.destroy(self._sandbox_id)
            self._audit("destroy", self._sandbox_id, {})
            self._sandbox_id = None

    def _audit(self, action: str, detail: str, metadata: dict[str, Any]) -> None:
        if self.audit_log is not None:
            self.audit_log.append(
                AuditEvent(
                    layer="sandbox",
                    action=action,
                    detail=detail,
                    metadata=metadata,
                ),
            )
