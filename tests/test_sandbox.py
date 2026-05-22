"""Sandbox module tests."""

import pytest

from aegis.ifc.labels import INTERNAL, PUBLIC, SECRET
from aegis.sandbox.docker_sandbox import docker_available
from aegis.sandbox.labels import SandboxLabelError, bind_label_to_sandbox
from aegis.sandbox.manager import SandboxManager
from aegis.sandbox.simulated_sandbox import SimulatedSandbox
from aegis.utils.config import SandboxConfig


def test_docker_detection() -> None:
    result = docker_available()
    assert isinstance(result, bool)


def test_simulated_run() -> None:
    sandbox = SimulatedSandbox()
    info = sandbox.create(INTERNAL)
    output = sandbox.run_labeled(lambda p: p["msg"], {"msg": "hello"}, INTERNAL)
    assert output == "hello"
    assert info.sandbox_id.startswith("sbx-")
    sandbox.destroy()


def test_label_rejection() -> None:
    sandbox = SimulatedSandbox()
    sandbox.create(PUBLIC)
    try:
        sandbox.run_labeled(lambda p: "x", {}, SECRET)
        rejected = False
    except SandboxLabelError:
        rejected = True
    assert rejected
    sandbox.destroy()


def test_snapshot_rollback() -> None:
    sandbox = SimulatedSandbox()
    sandbox.create(INTERNAL)
    snap = sandbox.snapshot()
    sandbox.rollback(snap.snapshot_id)
    assert snap.snapshot_id.startswith("snap-")
    sandbox.destroy()


def test_manager_auto_runtime() -> None:
    manager = SandboxManager(SandboxConfig(runtime="auto"))
    sb = manager.create_sandbox()
    assert sb.runtime_name in {"docker", "simulated"}


def test_bind_label_helper() -> None:
    bind_label_to_sandbox(PUBLIC, INTERNAL)
    with pytest.raises(SandboxLabelError):
        bind_label_to_sandbox(SECRET, PUBLIC)
