"""Docker sandbox — optional fallback (heavy on Windows; prefer native backends)."""

from __future__ import annotations

import sys
from typing import Any

from aegis.sandbox.backends._subprocess import (
    combined_output,
    docker_available,
    run_command,
)
from aegis.sandbox.base import SandboxBackend, SandboxBackendError, SandboxCreateConfig
from aegis.sandbox.environment import SandboxInfo


class DockerSandbox(SandboxBackend):
    """Docker container isolation — fallback when lightweight runtimes unavailable."""

    name = "docker"
    recommended_for_local = False
    platforms = frozenset({"linux", "win32", "darwin"})
    image: str = "python:3.12-slim"

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._container_ids: dict[str, str] = {}

    def is_available(self) -> bool:
        return docker_available()

    def create(self, create_config: SandboxCreateConfig) -> SandboxInfo:
        info = SandboxInfo(
            sandbox_id=create_config.sandbox_id,
            runtime=self.name,
            label=create_config.label,
            memory_mb=self.config.memory_mb,
            network_enabled=self.config.network_enabled,
        )
        from aegis.sandbox.base import SandboxInstanceState

        self._instances[info.sandbox_id] = SandboxInstanceState(info=info)
        return info

    def start(self, sandbox_id: str) -> None:
        state = self._require_state(sandbox_id)
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
            sandbox_id,
        ]
        if not self.config.network_enabled:
            cmd.extend(["--network", "none"])
        cmd.extend([self.image, "sleep", "3600"])
        result = run_command(cmd, timeout=120)
        if result.returncode != 0:
            msg = f"docker run failed: {combined_output(result)}"
            raise SandboxBackendError(msg)
        self._container_ids[sandbox_id] = result.stdout.strip()[:12]
        state.started = True

    def stop(self, sandbox_id: str) -> None:
        if sandbox_id in self._container_ids:
            run_command(["docker", "stop", sandbox_id], timeout=60)
        state = self._require_state(sandbox_id)
        state.started = False

    def run(self, sandbox_id: str, command: list[str], **kwargs: Any) -> str:
        state = self._require_state(sandbox_id)
        if not state.started:
            msg = f"Sandbox {sandbox_id} not started"
            raise SandboxBackendError(msg)
        container_id = self._container_ids.get(sandbox_id, sandbox_id)
        cmd = ["docker", "exec", "-i"]
        env = kwargs.get("env") or {}
        for key, value in env.items():
            cmd.extend(["-e", f"{key}={value}"])
        cmd.append(container_id)
        cmd.extend(command)
        result = run_command(
            cmd,
            input_text=kwargs.get("input_text"),
            timeout=kwargs.get("timeout", 120),
        )
        state.exec_count += 1
        if result.returncode != 0:
            msg = f"docker exec failed: {combined_output(result)}"
            raise SandboxBackendError(msg)
        return combined_output(result)

    def inspect(self, sandbox_id: str) -> dict[str, Any]:
        state = self._require_state(sandbox_id)
        metadata: dict[str, Any] = {
            "sandbox_id": sandbox_id,
            "backend": self.name,
            "started": state.started,
            "container_id": self._container_ids.get(sandbox_id),
            "label": state.info.label.sensitivity.name,
            "exec_count": state.exec_count,
            "recommended_for_local": self.recommended_for_local,
            "seccomp_profile": self.config.seccomp_profile,
        }
        if sys.platform == "win32":
            metadata["platform_warning"] = (
                "Docker Desktop on Windows is resource-heavy; on Windows/macOS "
                "Docker is the fallback when Linux-native runtimes are unavailable."
            )
        return metadata

    def destroy(self, sandbox_id: str) -> None:
        run_command(["docker", "rm", "-f", sandbox_id], timeout=60)
        self._container_ids.pop(sandbox_id, None)
        self._instances.pop(sandbox_id, None)
