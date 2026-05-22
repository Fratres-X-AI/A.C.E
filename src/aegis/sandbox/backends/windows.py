"""Windows Sandbox backend — primary isolation on Windows 10/11 Pro+."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from aegis.sandbox.backends._subprocess import run_command
from aegis.sandbox.base import SandboxBackend, SandboxBackendError, SandboxCreateConfig
from aegis.sandbox.environment import SandboxInfo

_SANDBOX_EXE = "WindowsSandbox.exe"
_HOST_MOUNT = r"C:\ACEWork"
_PROJECT_MOUNT = r"C:\ACEProject"
_DEFAULT_TIMEOUT = 300


def windows_sandbox_exe() -> Path | None:
    """Return path to WindowsSandbox.exe when present on the host."""
    windir = os.environ.get("WINDIR", r"C:\Windows")
    exe = Path(windir) / "System32" / _SANDBOX_EXE
    if exe.is_file():
        return exe
    return None


def windows_sandbox_feature_enabled() -> bool:
    """Check whether the Windows Sandbox optional feature is enabled."""
    if sys.platform != "win32":
        return False
    if windows_sandbox_exe() is None:
        return False
    result = run_command(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "(Get-WindowsOptionalFeature -Online -FeatureName "
                "Containers-DisposableClientVM -ErrorAction SilentlyContinue).State"
            ),
        ],
        timeout=60,
    )
    if result.returncode == 0 and "Enabled" in (result.stdout or ""):
        return True
    return windows_sandbox_exe() is not None


def _project_root() -> Path:
    import aegis

    return Path(aegis.__file__).resolve().parent.parent.parent


class WindowsSandbox(SandboxBackend):
    """Disposable VM isolation via Windows Sandbox (.wsb configuration)."""

    name = "windows"
    recommended_for_local = True
    platforms = frozenset({"win32"})

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._workspaces: dict[str, Path] = {}
        self._wsb_paths: dict[str, Path] = {}

    def is_available(self) -> bool:
        return sys.platform == "win32" and windows_sandbox_feature_enabled()

    def create(self, create_config: SandboxCreateConfig) -> SandboxInfo:
        info = SandboxInfo(
            sandbox_id=create_config.sandbox_id,
            runtime=self.name,
            label=create_config.label,
            memory_mb=self.config.memory_mb,
            network_enabled=self.config.network_enabled,
        )
        from aegis.sandbox.base import SandboxInstanceState

        workspace = Path(
            tempfile.mkdtemp(prefix=f"ace-wsb-{info.sandbox_id}-")
        )
        self._workspaces[info.sandbox_id] = workspace
        self._instances[info.sandbox_id] = SandboxInstanceState(info=info)
        return info

    def start(self, sandbox_id: str) -> None:
        state = self._require_state(sandbox_id)
        workspace = self._workspaces[sandbox_id]
        workspace.mkdir(parents=True, exist_ok=True)
        wsb_path = workspace / f"{sandbox_id}.wsb"
        self._write_wsb_template(wsb_path, workspace)
        self._wsb_paths[sandbox_id] = wsb_path
        state.started = True

    def stop(self, sandbox_id: str) -> None:
        state = self._require_state(sandbox_id)
        state.started = False

    def run(self, sandbox_id: str, command: list[str], **kwargs: Any) -> str:
        state = self._require_state(sandbox_id)
        if not state.started:
            msg = f"Sandbox {sandbox_id} not started"
            raise SandboxBackendError(msg)

        workspace = self._workspaces[sandbox_id]
        payload_text = kwargs.get("input_text") or ""
        env = kwargs.get("env") or {}
        timeout = int(kwargs.get("timeout", _DEFAULT_TIMEOUT))

        payload_path = workspace / "payload.json"
        output_path = workspace / "output.txt"
        error_path = workspace / "error.txt"
        done_path = workspace / "done.marker"

        for path in (output_path, error_path, done_path):
            path.unlink(missing_ok=True)

        payload_path.write_text(payload_text, encoding="utf-8")
        self._write_run_script(workspace, command, env)

        wsb_path = workspace / f"{sandbox_id}-run.wsb"
        self._write_wsb_run_config(wsb_path, workspace)

        exe = windows_sandbox_exe()
        if exe is None:
            msg = (
                "Windows Sandbox is not installed. Enable the optional feature "
                "'Windows Sandbox' on Windows 10/11 Pro, Enterprise, or Education."
            )
            raise SandboxBackendError(msg)

        run_command([str(exe), str(wsb_path)], timeout=30)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if done_path.is_file():
                break
            if error_path.is_file():
                err = error_path.read_text(encoding="utf-8").strip()
                msg = f"Windows Sandbox workload failed: {err}"
                raise SandboxBackendError(msg)
            time.sleep(0.5)
        else:
            msg = f"Windows Sandbox workload timed out after {timeout}s"
            raise SandboxBackendError(msg)

        state.exec_count += 1
        if not output_path.is_file():
            msg = "Windows Sandbox completed without writing output"
            raise SandboxBackendError(msg)
        return output_path.read_text(encoding="utf-8").strip()

    def inspect(self, sandbox_id: str) -> dict[str, Any]:
        state = self._require_state(sandbox_id)
        workspace = self._workspaces.get(sandbox_id)
        return {
            "sandbox_id": sandbox_id,
            "backend": self.name,
            "platform": sys.platform,
            "started": state.started,
            "label": state.info.label.sensitivity.name,
            "exec_count": state.exec_count,
            "memory_mb": self.config.memory_mb,
            "network_enabled": self.config.network_enabled,
            "workspace": str(workspace) if workspace else "",
            "wsb_path": str(self._wsb_paths.get(sandbox_id, "")),
            "feature_enabled": windows_sandbox_feature_enabled(),
        }

    def destroy(self, sandbox_id: str) -> None:
        workspace = self._workspaces.pop(sandbox_id, None)
        self._wsb_paths.pop(sandbox_id, None)
        if workspace is not None and workspace.exists():
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)
        self._instances.pop(sandbox_id, None)

    def _write_wsb_template(self, wsb_path: Path, workspace: Path) -> None:
        root = self._wsb_root(workspace, logon_command=None)
        wsb_path.write_text(
            ET.tostring(root, encoding="unicode"),
            encoding="utf-8",
        )

    def _write_wsb_run_config(self, wsb_path: Path, workspace: Path) -> None:
        logon = (
            f"powershell.exe -ExecutionPolicy Bypass -File "
            f"{_HOST_MOUNT}\\run_worker.ps1"
        )
        root = self._wsb_root(workspace, logon_command=logon)
        wsb_path.write_text(
            ET.tostring(root, encoding="unicode"),
            encoding="utf-8",
        )

    def _wsb_root(
        self,
        workspace: Path,
        logon_command: str | None,
    ) -> ET.Element:
        root = ET.Element("Configuration")

        vgpu = "Enable" if self.config.memory_mb >= 4096 else "Disable"
        ET.SubElement(root, "VGpu").text = vgpu

        networking = "Enable" if self.config.network_enabled else "Disable"
        ET.SubElement(root, "Networking").text = networking

        ET.SubElement(root, "AudioInput").text = "Disable"
        ET.SubElement(root, "VideoInput").text = "Disable"
        ET.SubElement(root, "ClipboardRedirection").text = "Disable"
        ET.SubElement(root, "PrinterRedirection").text = "Disable"
        ET.SubElement(root, "MemoryInMB").text = str(self.config.memory_mb)

        mapped = ET.SubElement(root, "MappedFolders")

        host_folder = ET.SubElement(mapped, "MappedFolder")
        ET.SubElement(host_folder, "HostFolder").text = str(workspace.resolve())
        ET.SubElement(host_folder, "SandboxFolder").text = _HOST_MOUNT
        ET.SubElement(host_folder, "ReadOnly").text = "false"

        project_root = _project_root()
        if project_root.is_dir():
            project_map = ET.SubElement(mapped, "MappedFolder")
            ET.SubElement(project_map, "HostFolder").text = str(
                project_root.resolve()
            )
            ET.SubElement(project_map, "SandboxFolder").text = _PROJECT_MOUNT
            ET.SubElement(project_map, "ReadOnly").text = "true"

        if logon_command is not None:
            logon = ET.SubElement(root, "LogonCommand")
            ET.SubElement(logon, "Command").text = logon_command

        return root

    def _write_run_script(
        self,
        workspace: Path,
        command: list[str],
        env: dict[str, Any],
    ) -> None:
        candidates_ps = ", ".join(
            f'"{candidate}"'
            for candidate in (
                f"{_PROJECT_MOUNT}\\.venv\\Scripts\\python.exe",
                "python",
            )
        )
        env_lines = "\n".join(
            "$env:" + key + ' = "' + str(value) + '"' for key, value in env.items()
        )
        cmd_json = json.dumps(command)
        script = (
            "# ACE Windows Sandbox worker launcher\n"
            f"{env_lines}\n"
            f"$command = {cmd_json} | ConvertFrom-Json\n"
            f'$payload = Get-Content -Path "{_HOST_MOUNT}\\payload.json" '
            "-Raw -Encoding UTF8\n"
            "$python = $null\n"
            f"foreach ($candidate in @({candidates_ps})) {{\n"
            "    if (Test-Path $candidate) { $python = $candidate; break }\n"
            "    $resolved = Get-Command $candidate -ErrorAction SilentlyContinue\n"
            "    if ($resolved) { $python = $resolved.Source; break }\n"
            "}\n"
            "if (-not $python) {\n"
            '    "Python not found inside Windows Sandbox" | Set-Content "'
            f'{_HOST_MOUNT}\\error.txt"\n'
            "    shutdown /s /t 0 /f\n"
            "    exit 1\n"
            "}\n"
            "try {\n"
            "    $output = $payload | & $python @command 2>&1 | Out-String\n"
            f'    $output | Set-Content "{_HOST_MOUNT}\\output.txt" -Encoding UTF8\n'
            f'    "ok" | Set-Content "{_HOST_MOUNT}\\done.marker" -Encoding UTF8\n'
            "} catch {\n"
            f'    $_.Exception.Message | Set-Content "{_HOST_MOUNT}\\error.txt" '
            "-Encoding UTF8\n"
            "} finally {\n"
            "    shutdown /s /t 0 /f\n"
            "}\n"
        )
        (workspace / "run_worker.ps1").write_text(script, encoding="utf-8")
