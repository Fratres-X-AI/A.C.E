"""Sandbox backend registry and resolution."""

from __future__ import annotations

import logging
import os
import sys
from typing import ClassVar

from aegis.sandbox.backends.bubblewrap import BubblewrapSandbox, running_in_container
from aegis.sandbox.backends.docker import DockerSandbox
from aegis.sandbox.backends.firecracker import FirecrackerSandbox
from aegis.sandbox.backends.gvisor import GVisorSandbox
from aegis.sandbox.backends.process import ProcessSandbox
from aegis.sandbox.base import SandboxBackend, SandboxBackendError
from aegis.utils.config import SandboxConfig

logger = logging.getLogger(__name__)

# gVisor / Firecracker stay registered but is_available() is False until functional.
_linux_order = ("bubblewrap", "docker", "process")
_win_order = ("windows", "docker")


def _load_windows_backend() -> type[SandboxBackend]:
    from aegis.sandbox.backends.windows import WindowsSandbox

    return WindowsSandbox


def _auto_order() -> tuple[str, ...]:
    if sys.platform.startswith("linux"):
        if running_in_container():
            return (*_linux_order, "process")
        return _linux_order
    if sys.platform == "win32":
        return _win_order
    return ("docker",)


def _platform_label() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


class SandboxRegistry:
    """Register and resolve pluggable sandbox backends."""

    _windows_registered: ClassVar[bool] = False
    _backends: ClassVar[dict[str, type[SandboxBackend]]] = {
        BubblewrapSandbox.name: BubblewrapSandbox,
        GVisorSandbox.name: GVisorSandbox,
        FirecrackerSandbox.name: FirecrackerSandbox,
        DockerSandbox.name: DockerSandbox,
        ProcessSandbox.name: ProcessSandbox,
    }

    @classmethod
    def _ensure_platform_backends(cls) -> None:
        if sys.platform == "win32" and not cls._windows_registered:
            windows_cls = _load_windows_backend()
            cls._backends[windows_cls.name] = windows_cls
            cls._windows_registered = True

    @classmethod
    def register(cls, name: str, backend_cls: type[SandboxBackend]) -> None:
        cls._ensure_platform_backends()
        cls._backends[name] = backend_cls

    @classmethod
    def get(cls, name: str, config: SandboxConfig | None = None) -> SandboxBackend:
        cls._ensure_platform_backends()
        if name not in cls._backends:
            msg = f"Unknown sandbox backend: {name!r}"
            raise SandboxBackendError(msg)
        backend_cls = cls._backends[name]
        if not backend_cls.is_compatible():
            msg = (
                f"Sandbox backend {name!r} is not compatible with {_platform_label()}. "
                f"Supported platforms: {sorted(backend_cls.platforms)}"
            )
            raise SandboxBackendError(msg)
        backend = backend_cls(config)
        if not backend.is_available():
            msg = (
                f"Sandbox backend {name!r} is not available on this host. "
                "Install required binaries or choose another backend."
            )
            raise SandboxBackendError(msg)
        cls._warn_if_docker_on_windows(backend)
        return backend

    @classmethod
    def list_backends(cls) -> list[str]:
        cls._ensure_platform_backends()
        return sorted(cls._backends.keys())

    @classmethod
    def list_compatible(cls) -> list[str]:
        cls._ensure_platform_backends()
        return sorted(
            name for name in cls._backends if cls._backends[name].is_compatible()
        )

    @classmethod
    def list_available(cls, config: SandboxConfig | None = None) -> list[str]:
        cls._ensure_platform_backends()
        cfg = config or SandboxConfig()
        return [
            name
            for name in cls.list_compatible()
            if cls._backends[name](cfg).is_available()
        ]

    @classmethod
    def resolve(cls, config: SandboxConfig | None = None) -> SandboxBackend:
        cls._ensure_platform_backends()
        cfg = config or SandboxConfig()
        env_backend = os.environ.get("ACE_SANDBOX_BACKEND", cfg.resolved_backend())
        backend_name = env_backend.lower()

        if backend_name == "auto":
            for name in _auto_order():
                if name not in cls._backends:
                    continue
                backend_cls = cls._backends[name]
                if not backend_cls.is_compatible():
                    continue
                candidate = backend_cls(cfg)
                if candidate.is_available():
                    cls._warn_if_docker_on_windows(candidate)
                    return candidate
            compatible = ", ".join(cls.list_compatible()) or "none"
            if sys.platform == "win32":
                hint = (
                    "On Windows enable Windows Sandbox (Pro/Enterprise) or install "
                    "Docker Desktop as fallback."
                )
            elif sys.platform.startswith("linux"):
                hint = (
                    "On Linux install bubblewrap or Docker. "
                    "(gVisor/Firecracker are registered but not functional yet.)"
                )
            else:
                hint = "Install Docker Desktop as fallback."
            msg = (
                "No sandbox backend available on this platform. "
                f"Compatible backends: {compatible}. {hint}"
            )
            raise SandboxBackendError(msg)

        return cls.get(backend_name, cfg)

    @classmethod
    def _warn_if_docker_on_windows(cls, backend: SandboxBackend) -> None:
        if sys.platform == "win32" and backend.name == "docker":
            logger.warning(
                "Docker Desktop on Windows is resource-heavy. Prefer Windows Sandbox "
                "when available; Docker is the fallback."
            )
