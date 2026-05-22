"""Bubblewrap (bwrap) sandbox — default lightweight Linux isolation."""

from __future__ import annotations

import sys
from typing import Any

from aegis.sandbox.backends._subprocess import combined_output, run_command, which
from aegis.sandbox.base import SandboxBackend, SandboxBackendError, SandboxCreateConfig
from aegis.sandbox.environment import SandboxInfo

_BWRAP = "bwrap"


class BubblewrapSandbox(SandboxBackend):
    """Namespace + seccomp isolation via bubblewrap."""

    name = "bubblewrap"
    recommended_for_local = True
    platforms = frozenset({"linux"})

    def is_available(self) -> bool:
        return which(_BWRAP) is not None and sys.platform.startswith("linux")

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
        state.started = True

    def stop(self, sandbox_id: str) -> None:
        state = self._require_state(sandbox_id)
        state.started = False

    def run(self, sandbox_id: str, command: list[str], **kwargs: Any) -> str:
        state = self._require_state(sandbox_id)
        if not state.started:
            msg = f"Sandbox {sandbox_id} not started"
            raise SandboxBackendError(msg)
        env = kwargs.get("env") or {}
        setenv_args: list[str] = []
        for key, value in env.items():
            setenv_args.extend(["--setenv", str(key), str(value)])
        cmd = [*self._bwrap_base(), *setenv_args, "--", *command]
        result = run_command(
            cmd,
            input_text=kwargs.get("input_text"),
            timeout=kwargs.get("timeout", 120),
        )
        state.exec_count += 1
        if result.returncode != 0:
            msg = f"bwrap run failed: {combined_output(result)}"
            raise SandboxBackendError(msg)
        return combined_output(result)

    def inspect(self, sandbox_id: str) -> dict[str, Any]:
        state = self._require_state(sandbox_id)
        return {
            "sandbox_id": sandbox_id,
            "backend": self.name,
            "started": state.started,
            "label": state.info.label.sensitivity.name,
            "exec_count": state.exec_count,
            "network_enabled": self.config.network_enabled,
            "seccomp_profile": self.config.seccomp_profile,
        }

    def destroy(self, sandbox_id: str) -> None:
        self._instances.pop(sandbox_id, None)

    def _bwrap_base(self) -> list[str]:
        cmd = [
            _BWRAP,
            "--unshare-user",
            "--unshare-ipc",
            "--unshare-pid",
            "--unshare-uts",
            "--die-with-parent",
            "--ro-bind",
            "/",
            "/",
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            "--tmpfs",
            "/tmp",
            "--rlimit-as",
            str(self.config.memory_mb * 1024 * 1024),
        ]
        if not self.config.network_enabled:
            cmd.append("--unshare-net")
        return cmd
