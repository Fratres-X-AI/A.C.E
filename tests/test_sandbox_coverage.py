"""Additional sandbox and worker coverage tests."""

from __future__ import annotations

import sys
from typing import Any

import pytest

from aegis.audit.tamper_proof_log import TamperProofLog
from aegis.ifc.labels import INTERNAL
from aegis.sandbox.base import SandboxBackendError, SandboxCreateConfig
from aegis.sandbox.facade import SandboxSessionFacade
from aegis.sandbox.registry import SandboxRegistry
from aegis.sandbox.workloads import (
    get_workload,
    list_workloads,
    register_workload,
    run_workload,
)
from aegis.utils.config import SandboxConfig
from tests.sandbox_helpers import MockSandboxBackend


def test_workloads_get_and_list() -> None:
    assert "echo" in list_workloads()
    assert get_workload("echo")({"x": 1}) == '{"x": 1}'
    assert run_workload("echo", {"y": 2}) == '{"y": 2}'
    with pytest.raises(KeyError):
        get_workload("nonexistent-workload-xyz")


@register_workload("coverage_temp")
def _coverage_temp(payload: dict[str, object]) -> str:
    return str(payload.get("k", ""))


def test_facade_unregistered_workload_raises() -> None:
    def unregistered(payload: dict[str, object]) -> str:
        return str(payload)

    facade = SandboxSessionFacade(backend=MockSandboxBackend())
    facade.create(INTERNAL)
    with pytest.raises(SandboxBackendError, match="register_workload"):
        facade.run_labeled(unregistered, {"q": "x"}, INTERNAL)
    facade.destroy()


def test_facade_exec_snapshot_rollback() -> None:
    audit = TamperProofLog()
    facade = SandboxSessionFacade(
        backend=MockSandboxBackend(),
        audit_log=audit,
    )
    assert facade.inspect() == {"status": "not_created"}
    with pytest.raises(SandboxBackendError):
        facade.exec(["echo", "x"])
    facade.create(INTERNAL)
    out = facade.exec([sys.executable, "-c", "print('exec')"])
    assert "exec" in out
    snap = facade.snapshot()
    assert snap.sandbox_id
    with pytest.raises(KeyError):
        facade.rollback("missing-snap")
    facade.destroy()
    assert len(audit.entries) >= 2


def test_registry_get_unavailable_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    if sys.platform != "linux":
        with pytest.raises(SandboxBackendError, match="not compatible"):
            SandboxRegistry.get("bubblewrap")
        return
    from aegis.sandbox.backends.bubblewrap import BubblewrapSandbox

    monkeypatch.setattr(BubblewrapSandbox, "is_available", lambda self: False)
    with pytest.raises(SandboxBackendError, match="not available"):
        SandboxRegistry.get("bubblewrap")


def test_registry_resolve_no_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    from aegis.sandbox.backends.bubblewrap import BubblewrapSandbox
    from aegis.sandbox.backends.docker import DockerSandbox
    from aegis.sandbox.backends.firecracker import FirecrackerSandbox
    from aegis.sandbox.backends.gvisor import GVisorSandbox
    from aegis.sandbox.backends.process import ProcessSandbox

    for backend_cls in (
        BubblewrapSandbox,
        GVisorSandbox,
        FirecrackerSandbox,
        DockerSandbox,
        ProcessSandbox,
    ):
        monkeypatch.setattr(backend_cls, "is_available", lambda self: False)

    with pytest.raises(SandboxBackendError, match="No sandbox backend"):
        SandboxRegistry.resolve(SandboxConfig(backend="auto"))


def test_registry_docker_warning_on_windows(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    if sys.platform != "win32":
        pytest.skip("Windows-only docker warning")
    from aegis.sandbox.backends.docker import DockerSandbox

    monkeypatch.setattr(DockerSandbox, "is_available", lambda self: True)
    with caplog.at_level("WARNING"):
        backend = SandboxRegistry.resolve(SandboxConfig(backend="docker"))
    assert backend.name == "docker"
    assert any("Docker Desktop" in r.message for r in caplog.records)


def test_docker_backend_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    from aegis.sandbox.backends import docker as docker_mod
    from aegis.sandbox.backends.docker import DockerSandbox

    def fake_run(
        command: list[str],
        **_kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="container-id\n",
            stderr="",
        )

    monkeypatch.setattr(docker_mod, "run_command", fake_run)
    backend = DockerSandbox(SandboxConfig())
    cfg = SandboxCreateConfig(policy=SandboxConfig(), label=INTERNAL)
    info = backend.create(cfg)
    backend.start(info.sandbox_id)
    backend.run(info.sandbox_id, ["echo", "hi"])
    meta = backend.inspect(info.sandbox_id)
    assert meta["backend"] == "docker"
    backend.destroy(info.sandbox_id)


def test_worker_main_echo(monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    from aegis.sandbox import _worker

    monkeypatch.setenv("ACE_WORKLOAD", "echo")
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"k":"v"}'))
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)
    _worker.main()
    assert stdout.getvalue() == '{"k": "v"}'


def test_bubblewrap_backend_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    from aegis.sandbox.backends import bubblewrap as bwrap_mod
    from aegis.sandbox.backends.bubblewrap import BubblewrapSandbox

    monkeypatch.setattr(bwrap_mod, "which", lambda _name: "/usr/bin/bwrap")
    monkeypatch.setattr(bwrap_mod, "_bwrap_namespace_works", lambda: True)

    def fake_run(
        command: list[str],
        **_kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    monkeypatch.setattr(bwrap_mod, "run_command", fake_run)
    backend = BubblewrapSandbox(SandboxConfig())
    cfg = SandboxCreateConfig(policy=SandboxConfig(), label=INTERNAL)
    info = backend.create(cfg)
    backend.start(info.sandbox_id)
    out = backend.run(info.sandbox_id, ["echo", "hi"], env={"ACE": "1"})
    assert "ok" in out
    meta = backend.inspect(info.sandbox_id)
    assert meta["backend"] == "bubblewrap"
    backend.destroy(info.sandbox_id)
