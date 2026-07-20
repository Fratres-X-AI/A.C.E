"""gVisor (runsc) sandbox backend."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from aegis.sandbox.backends._subprocess import combined_output, run_command
from aegis.sandbox.base import SandboxBackend, SandboxBackendError, SandboxCreateConfig
from aegis.sandbox.environment import SandboxInfo

_RUNSC = "runsc"


class GVisorSandbox(SandboxBackend):
    """OCI sandbox via gVisor runsc."""

    name = "gvisor"
    recommended_for_local = True
    platforms = frozenset({"linux"})

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._bundle_dirs: dict[str, Path] = {}
        self._container_ids: dict[str, str] = {}

    def is_available(self) -> bool:
        """Unavailable until a real OCI rootfs + workload path ships.

        Current bundle writes an empty rootfs (no ``sleep``/``python``). Kept
        registered for future work but never auto-selected.
        """
        return False

    def create(self, create_config: SandboxCreateConfig) -> SandboxInfo:
        info = SandboxInfo(
            sandbox_id=create_config.sandbox_id,
            runtime=self.name,
            label=create_config.label,
            memory_mb=self.config.memory_mb,
            network_enabled=self.config.network_enabled,
        )
        from aegis.sandbox.base import SandboxInstanceState

        bundle = Path(tempfile.mkdtemp(prefix=f"ace-gvisor-{info.sandbox_id}-"))
        self._bundle_dirs[info.sandbox_id] = bundle
        self._write_minimal_bundle(bundle)
        self._instances[info.sandbox_id] = SandboxInstanceState(info=info)
        return info

    def start(self, sandbox_id: str) -> None:
        state = self._require_state(sandbox_id)
        bundle = self._bundle_dirs[sandbox_id]
        cmd = [
            _RUNSC,
            "run",
            "--bundle",
            str(bundle),
            sandbox_id,
        ]
        result = run_command(cmd, timeout=60)
        if result.returncode != 0:
            msg = f"runsc start failed: {combined_output(result)}"
            raise SandboxBackendError(msg)
        self._container_ids[sandbox_id] = sandbox_id
        state.started = True

    def stop(self, sandbox_id: str) -> None:
        if sandbox_id in self._container_ids:
            run_command([_RUNSC, "kill", sandbox_id, "KILL"], timeout=30)
            self._container_ids.pop(sandbox_id, None)
        state = self._require_state(sandbox_id)
        state.started = False

    def run(self, sandbox_id: str, command: list[str], **kwargs: Any) -> str:
        state = self._require_state(sandbox_id)
        if not state.started:
            msg = f"Sandbox {sandbox_id} not started"
            raise SandboxBackendError(msg)
        cmd = [_RUNSC, "exec", sandbox_id, *command]
        result = run_command(
            cmd,
            input_text=kwargs.get("input_text"),
            timeout=kwargs.get("timeout", 120),
            env=kwargs.get("env"),
        )
        state.exec_count += 1
        if result.returncode != 0:
            msg = f"runsc exec failed: {combined_output(result)}"
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
            "bundle": str(self._bundle_dirs.get(sandbox_id, "")),
        }

    def destroy(self, sandbox_id: str) -> None:
        self.stop(sandbox_id)
        bundle = self._bundle_dirs.pop(sandbox_id, None)
        if bundle and bundle.exists():
            import shutil

            shutil.rmtree(bundle, ignore_errors=True)
        self._instances.pop(sandbox_id, None)

    def _write_minimal_bundle(self, bundle: Path) -> None:
        rootfs = bundle / "rootfs"
        rootfs.mkdir(parents=True, exist_ok=True)
        config = {
            "ociVersion": "1.0.2",
            "process": {
                "terminal": False,
                "user": {"uid": 0, "gid": 0},
                "args": ["sleep", "3600"],
                "env": ["PATH=/usr/local/bin:/usr/bin:/bin"],
                "cwd": "/",
            },
            "root": {"path": "rootfs", "readonly": False},
            "linux": {
                "namespaces": [
                    {"type": "pid"},
                    {"type": "network"},
                    {"type": "ipc"},
                    {"type": "mount"},
                    {"type": "uts"},
                ],
            },
        }
        (bundle / "config.json").write_text(json.dumps(config), encoding="utf-8")
