"""Host subprocess worker sandbox — RunPod nested-container fallback.

Runs ``python -m aegis.sandbox._worker`` in a separate OS process (not in-process).
No namespace/microVM isolation. Use bubblewrap or Docker when the host allows it.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from aegis.sandbox.backends._subprocess import combined_output, run_command
from aegis.sandbox.backends.bubblewrap import running_in_container
from aegis.sandbox.base import SandboxBackend, SandboxBackendError, SandboxCreateConfig
from aegis.sandbox.environment import SandboxInfo

logger = logging.getLogger(__name__)


class ProcessSandbox(SandboxBackend):
    """Separate-process worker execution when namespaces are unavailable."""

    name = "process"
    recommended_for_local = False
    platforms = frozenset({"linux"})

    def is_available(self) -> bool:
        if not sys.platform.startswith("linux"):
            return False
        if running_in_container():
            return True
        return os.environ.get("ACE_ALLOW_PROCESS_SANDBOX") == "1"

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
        if running_in_container():
            logger.warning(
                "Process sandbox active: worker runs in a separate OS process only "
                "(no namespace isolation). Typical on RunPod pods. For full isolation "
                "deploy on a VM with bubblewrap or Docker."
            )
        return info

    def start(self, sandbox_id: str) -> None:
        self._require_state(sandbox_id).started = True

    def stop(self, sandbox_id: str) -> None:
        self._require_state(sandbox_id).started = False

    def run(self, sandbox_id: str, command: list[str], **kwargs: Any) -> str:
        state = self._require_state(sandbox_id)
        if not state.started:
            msg = f"Sandbox {sandbox_id} not started"
            raise SandboxBackendError(msg)
        result = run_command(
            command,
            input_text=kwargs.get("input_text"),
            timeout=kwargs.get("timeout", 120),
            env=kwargs.get("env"),
        )
        state.exec_count += 1
        if result.returncode != 0:
            msg = f"process worker failed: {combined_output(result)}"
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
            "isolation": "process-only",
            "nested_container": running_in_container(),
        }

    def destroy(self, sandbox_id: str) -> None:
        self._instances.pop(sandbox_id, None)
