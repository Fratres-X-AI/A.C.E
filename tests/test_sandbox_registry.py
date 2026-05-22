"""Sandbox registry tests."""

from __future__ import annotations

import sys

import pytest

from aegis.ifc.labels import INTERNAL
from aegis.sandbox.backends.bubblewrap import BubblewrapSandbox
from aegis.sandbox.backends.docker import DockerSandbox
from aegis.sandbox.base import SandboxBackendError, SandboxCreateConfig
from aegis.sandbox.registry import SandboxRegistry, _auto_order
from aegis.utils.config import SandboxConfig
from tests.sandbox_helpers import MockSandboxBackend


def test_register_and_get() -> None:
    SandboxRegistry.register("mock", MockSandboxBackend)
    backend = SandboxRegistry.get("mock")
    assert isinstance(backend, MockSandboxBackend)


def test_get_unknown_raises() -> None:
    with pytest.raises(SandboxBackendError):
        SandboxRegistry.get("nonexistent-backend-xyz")


def test_list_available_includes_mock() -> None:
    SandboxRegistry.register("mock", MockSandboxBackend)
    assert "mock" in SandboxRegistry.list_available()


def test_mock_backend_create_run_destroy() -> None:
    backend = MockSandboxBackend()
    cfg = SandboxCreateConfig(policy=SandboxConfig(), label=INTERNAL)
    info = backend.create(cfg)
    backend.start(info.sandbox_id)
    out = backend.run(
        info.sandbox_id,
        ["python", "-c", "print('ok')"],
    )
    assert "ok" in out
    meta = backend.inspect(info.sandbox_id)
    assert meta["backend"] == "mock"
    backend.destroy(info.sandbox_id)


def test_auto_order_is_platform_specific() -> None:
    order = _auto_order()
    if sys.platform == "win32":
        assert order[0] == "windows"
    elif sys.platform.startswith("linux"):
        assert order[0] == "bubblewrap"
    else:
        assert order == ("docker",)


def test_list_compatible_excludes_linux_only_on_windows() -> None:
    if sys.platform != "win32":
        pytest.skip("Windows-only assertion")
    compatible = SandboxRegistry.list_compatible()
    assert "bubblewrap" not in compatible
    assert "docker" in compatible


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux-only backend")
def test_linux_backend_compatible_on_linux() -> None:
    assert BubblewrapSandbox.is_compatible()


def test_incompatible_backend_raises_clear_error() -> None:
    if sys.platform == "win32":
        with pytest.raises(SandboxBackendError, match="not compatible"):
            SandboxRegistry.get("bubblewrap")


def test_docker_has_cross_platform_metadata() -> None:
    assert "win32" in DockerSandbox.platforms
    assert "linux" in DockerSandbox.platforms


def test_auto_prefers_bubblewrap_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    if not sys.platform.startswith("linux"):
        pytest.skip("Linux-only auto-resolve preference")
    from aegis.sandbox.backends.firecracker import FirecrackerSandbox
    from aegis.sandbox.backends.gvisor import GVisorSandbox

    monkeypatch.setattr(BubblewrapSandbox, "is_available", lambda self: True)
    monkeypatch.setattr(GVisorSandbox, "is_available", lambda self: True)
    monkeypatch.setattr(FirecrackerSandbox, "is_available", lambda self: True)
    monkeypatch.setattr(DockerSandbox, "is_available", lambda self: True)
    backend = SandboxRegistry.resolve(SandboxConfig(backend="auto"))
    assert backend.name == "bubblewrap"
