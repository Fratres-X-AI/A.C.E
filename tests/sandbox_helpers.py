"""Test-only sandbox backend for subprocess worker tests."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from aegis.sandbox.backends._subprocess import combined_output, run_command
from aegis.sandbox.base import SandboxBackend, SandboxBackendError, SandboxCreateConfig
from aegis.sandbox.environment import SandboxInfo

if TYPE_CHECKING:
    from aegis.sandbox.facade import SandboxSessionFacade


class MockSandboxBackend(SandboxBackend):
    """Test double: real subprocess worker execution, no isolation wrapper."""

    name = "mock"
    recommended_for_local = False

    def is_available(self) -> bool:
        return True

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
        self._require_state(sandbox_id).started = True

    def stop(self, sandbox_id: str) -> None:
        self._require_state(sandbox_id).started = False

    def run(self, sandbox_id: str, command: list[str], **kwargs: Any) -> str:
        state = self._require_state(sandbox_id)
        if not state.started:
            msg = f"Sandbox {sandbox_id} not started"
            raise SandboxBackendError(msg)
        is_worker = command[-2:] == ["-m", "aegis.sandbox._worker"]
        if is_worker:
            import io
            import os

            from aegis.sandbox import _worker

            prior_workload = os.environ.get("ACE_WORKLOAD")
            try:
                for key, value in (kwargs.get("env") or {}).items():
                    os.environ[str(key)] = str(value)
                sys.stdin = io.StringIO(kwargs.get("input_text") or "")
                captured = io.StringIO()
                sys.stdout = captured
                _worker.main()
                state.exec_count += 1
                return captured.getvalue()
            finally:
                sys.stdin = sys.__stdin__
                sys.stdout = sys.__stdout__
                if prior_workload is None:
                    os.environ.pop("ACE_WORKLOAD", None)
                else:
                    os.environ["ACE_WORKLOAD"] = prior_workload
        result = run_command(
            command,
            input_text=kwargs.get("input_text"),
            timeout=kwargs.get("timeout", 120),
            env=kwargs.get("env"),
        )
        state.exec_count += 1
        if result.returncode != 0:
            msg = f"mock run failed: {combined_output(result)}"
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
        }

    def destroy(self, sandbox_id: str) -> None:
        self._instances.pop(sandbox_id, None)


def mock_facade() -> SandboxSessionFacade:
    """Return a facade backed by MockSandboxBackend for unit tests."""
    from aegis.sandbox.facade import SandboxSessionFacade

    return SandboxSessionFacade(backend=MockSandboxBackend())

