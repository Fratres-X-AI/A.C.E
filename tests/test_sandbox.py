"""Sandbox module tests."""

import sys

import pytest

from aegis.ifc.labels import INTERNAL, PUBLIC, SECRET
from aegis.sandbox.backends._subprocess import docker_available
from aegis.sandbox.backends.bubblewrap import BubblewrapSandbox
from aegis.sandbox.base import SandboxCreateConfig
from aegis.sandbox.labels import SandboxLabelError, bind_label_to_sandbox
from aegis.sandbox.manager import SandboxManager
from aegis.sandbox.registry import SandboxRegistry
from aegis.utils.config import SandboxConfig
from tests.sandbox_helpers import MockSandboxBackend, mock_facade


def test_docker_detection() -> None:
    assert isinstance(docker_available(), bool)


def test_mock_backend_lifecycle() -> None:
    from aegis.execution.mock_model import mock_llm

    facade = mock_facade()
    info = facade.create(INTERNAL)
    assert info.sandbox_id.startswith("sbx-")
    output = facade.run_labeled(mock_llm, {"query": "hello"}, INTERNAL)
    assert "Mock response" in output or "hello" in output
    facade.destroy()


def test_label_rejection() -> None:
    backend = MockSandboxBackend()
    create_cfg = SandboxCreateConfig(policy=SandboxConfig(), label=PUBLIC)
    info = backend.create(create_cfg)
    backend.start(info.sandbox_id)
    with pytest.raises(SandboxLabelError):
        backend.enforce_ifc(info.sandbox_id, SECRET)
    backend.destroy(info.sandbox_id)


def test_bind_label_helper() -> None:
    bind_label_to_sandbox(PUBLIC, INTERNAL)
    with pytest.raises(SandboxLabelError):
        bind_label_to_sandbox(SECRET, PUBLIC)


def test_registry_list_backends() -> None:
    names = SandboxRegistry.list_backends()
    assert "bubblewrap" in names
    assert "docker" in names
    assert "mock" in names


def test_registry_auto_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    from aegis.sandbox.backends.firecracker import FirecrackerSandbox
    from aegis.sandbox.backends.gvisor import GVisorSandbox
    from aegis.sandbox.base import SandboxBackendError
    from aegis.sandbox.registry import _load_windows_backend

    monkeypatch.setattr(BubblewrapSandbox, "is_available", lambda self: False)
    monkeypatch.setattr(GVisorSandbox, "is_available", lambda self: False)
    monkeypatch.setattr(FirecrackerSandbox, "is_available", lambda self: False)

    if sys.platform == "win32":
        windows_backend_cls = _load_windows_backend()
        monkeypatch.setattr(windows_backend_cls, "is_available", lambda self: True)
        backend = SandboxRegistry.resolve(SandboxConfig(backend="auto"))
        assert backend.name == "windows"
    elif docker_available():
        backend = SandboxRegistry.resolve(SandboxConfig(backend="auto"))
        assert backend.name == "docker"
    else:
        with pytest.raises(SandboxBackendError):
            SandboxRegistry.resolve(SandboxConfig(backend="auto"))


def test_manager_get_mock_backend() -> None:
    SandboxRegistry.register("mock", MockSandboxBackend)
    manager = SandboxManager(SandboxConfig(backend="mock"))
    backend = manager.get_backend("mock")
    assert backend.name == "mock"


@pytest.mark.requires_bwrap
def test_bubblewrap_available_on_linux() -> None:
    backend = BubblewrapSandbox()
    if not backend.is_available():
        pytest.skip("bwrap not installed")
    assert backend.name == "bubblewrap"
