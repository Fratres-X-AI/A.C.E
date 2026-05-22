"""Windows Sandbox backend unit tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from aegis.ifc.labels import INTERNAL
from aegis.sandbox.backends.windows import (
    WindowsSandbox,
    windows_sandbox_exe,
    windows_sandbox_feature_enabled,
)
from aegis.sandbox.base import SandboxBackendError, SandboxCreateConfig
from aegis.utils.config import SandboxConfig


def test_windows_sandbox_exe_returns_none_off_windows() -> None:
    if sys.platform == "win32":
        pytest.skip("Windows host always has WindowsSandbox.exe path")
    assert windows_sandbox_exe() is None


def test_windows_sandbox_feature_disabled_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert windows_sandbox_feature_enabled() is False


def test_windows_backend_platform_metadata() -> None:
    assert WindowsSandbox.name == "windows"
    assert WindowsSandbox.platforms == frozenset({"win32"})


def test_windows_backend_is_compatible_on_windows() -> None:
    if sys.platform != "win32":
        pytest.skip("Windows-only backend")
    assert WindowsSandbox.is_compatible()


def test_windows_backend_not_compatible_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert not WindowsSandbox.is_compatible()


def test_windows_backend_create_start_inspect_destroy() -> None:
    backend = WindowsSandbox(SandboxConfig())
    cfg = SandboxCreateConfig(policy=SandboxConfig(), label=INTERNAL)
    info = backend.create(cfg)
    backend.start(info.sandbox_id)
    meta = backend.inspect(info.sandbox_id)
    assert meta["backend"] == "windows"
    assert meta["memory_mb"] == backend.config.memory_mb
    assert meta["network_enabled"] == backend.config.network_enabled
    assert meta["workspace"]
    backend.destroy(info.sandbox_id)


def test_windows_backend_wsb_template_written_on_start() -> None:
    backend = WindowsSandbox(SandboxConfig(memory_mb=512))
    cfg = SandboxCreateConfig(policy=SandboxConfig(memory_mb=512), label=INTERNAL)
    info = backend.create(cfg)
    backend.start(info.sandbox_id)
    meta = backend.inspect(info.sandbox_id)
    wsb_path = Path(meta["wsb_path"])
    assert wsb_path.is_file()
    content = wsb_path.read_text(encoding="utf-8")
    assert "Configuration" in content
    assert "MemoryInMB" in content
    backend.destroy(info.sandbox_id)


def test_windows_backend_run_polls_mapped_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aegis.sandbox.backends.windows as windows_mod

    backend = WindowsSandbox(SandboxConfig())
    cfg = SandboxCreateConfig(policy=SandboxConfig(), label=INTERNAL)
    info = backend.create(cfg)
    backend.start(info.sandbox_id)
    meta = backend.inspect(info.sandbox_id)
    workspace = Path(meta["workspace"])

    def fake_run_command(
        command: list[str],
        **_kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        (workspace / "output.txt").write_text("sandbox-output", encoding="utf-8")
        (workspace / "done.marker").write_text("ok", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(windows_mod, "run_command", fake_run_command)
    monkeypatch.setattr(
        windows_mod,
        "windows_sandbox_exe",
        lambda: Path("WindowsSandbox.exe"),
    )

    out = backend.run(
        info.sandbox_id,
        ["-m", "aegis.sandbox._worker"],
        input_text='{"msg":"hi"}',
        env={"ACE_WORKLOAD": "echo"},
    )
    assert out == "sandbox-output"
    backend.destroy(info.sandbox_id)


def test_windows_backend_run_not_started_raises() -> None:
    backend = WindowsSandbox(SandboxConfig())
    cfg = SandboxCreateConfig(policy=SandboxConfig(), label=INTERNAL)
    info = backend.create(cfg)
    with pytest.raises(SandboxBackendError, match="not started"):
        backend.run(info.sandbox_id, ["echo", "x"])
    backend.destroy(info.sandbox_id)
