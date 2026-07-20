"""Firecracker microVM sandbox backend."""

from __future__ import annotations

import json
import os
import socket
import tempfile
import time
from pathlib import Path
from typing import Any

from aegis.sandbox.base import SandboxBackend, SandboxBackendError, SandboxCreateConfig
from aegis.sandbox.environment import SandboxInfo

_FC = "firecracker"


class FirecrackerSandbox(SandboxBackend):
    """Firecracker microVM isolation for server/RunPod deployments."""

    name = "firecracker"
    recommended_for_local = False
    platforms = frozenset({"linux"})

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._api_sockets: dict[str, Path] = {}
        self._processes: dict[str, Any] = {}

    def is_available(self) -> bool:
        """Unavailable until guest workload exec is implemented.

        Firecracker has no ``Exec`` action; ACE workloads cannot run without a
        guest agent. Backend remains registered for future work only.
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

        socket_path = Path(tempfile.gettempdir()) / f"ace-fc-{info.sandbox_id}.sock"
        self._api_sockets[info.sandbox_id] = socket_path
        self._instances[info.sandbox_id] = SandboxInstanceState(info=info)
        return info

    def start(self, sandbox_id: str) -> None:
        state = self._require_state(sandbox_id)
        socket_path = self._api_sockets[sandbox_id]
        if socket_path.exists():
            socket_path.unlink()
        kernel = os.environ["ACE_FC_KERNEL"]
        rootfs = os.environ["ACE_FC_ROOTFS"]
        import subprocess

        proc = subprocess.Popen(
            [
                _FC,
                "--api-sock",
                str(socket_path),
                "--config-file",
                self._write_fc_config(sandbox_id, kernel, rootfs),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._processes[sandbox_id] = proc
        for _ in range(50):
            if socket_path.exists():
                break
            time.sleep(0.1)
        else:
            msg = "Firecracker API socket did not become ready"
            raise SandboxBackendError(msg)
        state.started = True

    def stop(self, sandbox_id: str) -> None:
        proc = self._processes.pop(sandbox_id, None)
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=10)
        socket_path = self._api_sockets.get(sandbox_id)
        if socket_path and socket_path.exists():
            socket_path.unlink()
        state = self._require_state(sandbox_id)
        state.started = False

    def run(self, sandbox_id: str, command: list[str], **_kwargs: Any) -> str:
        state = self._require_state(sandbox_id)
        if not state.started:
            msg = f"Sandbox {sandbox_id} not started"
            raise SandboxBackendError(msg)
        payload = {
            "action_type": "Exec",
            "command": command,
        }
        response = self._api_call(sandbox_id, payload)
        state.exec_count += 1
        return json.dumps(response)

    def inspect(self, sandbox_id: str) -> dict[str, Any]:
        state = self._require_state(sandbox_id)
        return {
            "sandbox_id": sandbox_id,
            "backend": self.name,
            "started": state.started,
            "label": state.info.label.sensitivity.name,
            "exec_count": state.exec_count,
            "api_socket": str(self._api_sockets.get(sandbox_id, "")),
        }

    def destroy(self, sandbox_id: str) -> None:
        self.stop(sandbox_id)
        self._api_sockets.pop(sandbox_id, None)
        self._instances.pop(sandbox_id, None)

    def _write_fc_config(self, sandbox_id: str, kernel: str, rootfs: str) -> str:
        cfg_path = Path(tempfile.gettempdir()) / f"ace-fc-{sandbox_id}.json"
        cfg = {
            "boot-source": {
                "kernel_image_path": kernel,
                "boot_args": "console=ttyS0 reboot=k panic=1 pci=off",
            },
            "drives": [
                {
                    "drive_id": "rootfs",
                    "path_on_host": rootfs,
                    "is_root_device": True,
                    "is_read_only": False,
                },
            ],
            "machine-config": {
                "vcpu_count": 1,
                "mem_size_mib": self.config.memory_mb,
            },
        }
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        return str(cfg_path)

    def _api_call(self, sandbox_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        socket_path = self._api_sockets[sandbox_id]
        body = json.dumps(payload).encode()
        request = (
            b"PUT /actions HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n\r\n".encode()
            + body
        )
        af_unix = getattr(socket, "AF_UNIX", None)
        if af_unix is None:
            msg = "Firecracker requires Unix domain sockets (Linux only)"
            raise SandboxBackendError(msg)
        with socket.socket(af_unix, socket.SOCK_STREAM) as sock:
            sock.connect(str(socket_path))
            sock.sendall(request)
            data = sock.recv(4096)
        text = data.decode(errors="replace")
        if "200" in text.split("\r\n", maxsplit=1)[0]:
            return {"status": "ok", "raw": text}
        msg = f"Firecracker API error: {text[:200]}"
        raise SandboxBackendError(msg)
