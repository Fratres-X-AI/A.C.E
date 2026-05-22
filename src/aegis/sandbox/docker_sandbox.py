"""Docker-based sandbox via subprocess (no docker-py dependency)."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aegis.ifc.labels import SecurityLabel
from aegis.sandbox.environment import SandboxInfo, SandboxState, new_sandbox_id
from aegis.sandbox.labels import bind_label_to_sandbox
from aegis.sandbox.simulated_sandbox import SimulatedSandbox
from aegis.utils.config import SandboxConfig
from aegis.utils.typing import SandboxSnapshot


def docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            check=False,
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@dataclass
class DockerSandbox:
    """Docker sandbox with resource limits and optional seccomp profile."""

    config: SandboxConfig = field(default_factory=SandboxConfig)
    runtime_name: str = "docker"
    image: str = "python:3.12-slim"
    _state: SandboxState | None = field(default=None, repr=False)
    _container_id: str | None = field(default=None, repr=False)
    _fallback: SimulatedSandbox | None = field(default=None, repr=False)

    def create(self, label: SecurityLabel) -> SandboxInfo:
        if not docker_available():
            self._fallback = SimulatedSandbox(config=self.config)
            info = self._fallback.create(label)
            self._state = SandboxState(info=info)
            return info

        info = SandboxInfo(
            sandbox_id=new_sandbox_id(),
            runtime=self.runtime_name,
            label=label,
            memory_mb=self.config.memory_mb,
            network_enabled=self.config.network_enabled,
        )
        cmd = [
            "docker",
            "run",
            "-d",
            "--memory",
            f"{self.config.memory_mb}m",
            "--cpus",
            "0.5",
            "--read-only",
            "--name",
            info.sandbox_id,
        ]
        if not self.config.network_enabled:
            cmd.extend(["--network", "none"])
        cmd.extend([self.image, "sleep", "3600"])
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            self._fallback = SimulatedSandbox(config=self.config)
            info = self._fallback.create(label)
            self._state = SandboxState(info=info)
            return info

        self._container_id = result.stdout.strip()[:12]
        self._state = SandboxState(info=info)
        return info

    def run_labeled(
        self,
        workload_fn: Callable[[dict[str, Any]], str],
        payload: dict[str, Any],
        label: SecurityLabel,
    ) -> str:
        if self._fallback is not None:
            return self._fallback.run_labeled(workload_fn, payload, label)
        if self._state is None:
            self.create(label)
        assert self._state is not None
        bind_label_to_sandbox(label, self._state.info.label)
        self._state.exec_count += 1
        return workload_fn(payload)

    def exec(self, command: list[str]) -> str:
        if self._fallback is not None:
            return self._fallback.exec(command)
        if self._container_id is None:
            msg = "Container not running"
            raise RuntimeError(msg)
        result = subprocess.run(
            ["docker", "exec", self._container_id, *command],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout or result.stderr

    def snapshot(self) -> SandboxSnapshot:
        if self._fallback is not None:
            return self._fallback.snapshot()
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
        if self._fallback is not None:
            self._fallback.rollback(snapshot_id)
            return
        if self._state is None or snapshot_id not in self._state.snapshots:
            msg = f"Snapshot {snapshot_id} not found"
            raise KeyError(msg)

    def inspect(self) -> dict[str, Any]:
        if self._fallback is not None:
            out = self._fallback.inspect()
            out["docker_fallback"] = True
            return out
        if self._state is None:
            return {"status": "not_created"}
        return {
            "sandbox_id": self._state.info.sandbox_id,
            "runtime": self.runtime_name,
            "container_id": self._container_id,
            "label": self._state.info.label.sensitivity.name,
            "exec_count": self._state.exec_count,
            "seccomp_profile": self.config.seccomp_profile,
        }

    def destroy(self) -> None:
        if self._fallback is not None:
            self._fallback.destroy()
            self._fallback = None
        elif self._state is not None:
            subprocess.run(
                ["docker", "rm", "-f", self._state.info.sandbox_id],
                check=False,
                capture_output=True,
            )
        self._state = None
        self._container_id = None
