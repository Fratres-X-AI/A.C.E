"""Pytest configuration for sandbox backend tests."""

from __future__ import annotations

import pytest

from aegis.sandbox.registry import SandboxRegistry
from tests.sandbox_helpers import MockSandboxBackend


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_bwrap: test requires bubblewrap (bwrap) on Linux",
    )
    config.addinivalue_line(
        "markers",
        "requires_docker: test requires Docker daemon",
    )


@pytest.fixture(autouse=True)
def _register_mock_sandbox_backend() -> None:
    SandboxRegistry.register("mock", MockSandboxBackend)
