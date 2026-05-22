"""Abstract sandbox backend interface."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from aegis.ifc.labels import SecurityLabel
from aegis.sandbox.environment import SandboxInfo, new_sandbox_id
from aegis.sandbox.labels import bind_label_to_sandbox
from aegis.utils.config import SandboxConfig


class SandboxBackendError(RuntimeError):
    """Raised when sandbox backend operations fail."""


@dataclass
class SandboxCreateConfig:
    """Configuration bundle for creating an isolated sandbox instance."""

    policy: SandboxConfig
    label: SecurityLabel
    sandbox_id: str = field(default_factory=new_sandbox_id)


@dataclass
class SandboxInstanceState:
    """Per-sandbox mutable backend state."""

    info: SandboxInfo
    started: bool = False
    exec_count: int = 0


class SandboxBackend(ABC):
    """Pluggable isolation backend — subprocess/microVM/container only."""

    name: ClassVar[str] = "base"
    recommended_for_local: ClassVar[bool] = True
    platforms: ClassVar[frozenset[str]] = frozenset()

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()
        self._instances: dict[str, SandboxInstanceState] = {}

    @classmethod
    def is_compatible(cls) -> bool:
        if not cls.platforms:
            return True
        platform_key = "linux" if sys.platform.startswith("linux") else sys.platform
        return platform_key in cls.platforms

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when required binaries/daemons are present."""

    @abstractmethod
    def create(self, create_config: SandboxCreateConfig) -> SandboxInfo:
        """Allocate sandbox metadata and register instance state."""

    @abstractmethod
    def start(self, sandbox_id: str) -> None:
        """Start isolation environment for sandbox_id."""

    @abstractmethod
    def stop(self, sandbox_id: str) -> None:
        """Stop running sandbox without destroying state."""

    @abstractmethod
    def run(self, sandbox_id: str, command: list[str], **kwargs: Any) -> str:
        """Execute command inside sandbox."""

    @abstractmethod
    def inspect(self, sandbox_id: str) -> dict[str, Any]:
        """Return runtime metadata for sandbox_id."""

    @abstractmethod
    def destroy(self, sandbox_id: str) -> None:
        """Tear down sandbox and release resources."""

    @property
    def supports_labels(self) -> bool:
        return True

    def enforce_ifc(self, sandbox_id: str, workload_label: SecurityLabel) -> None:
        state = self._instances.get(sandbox_id)
        if state is None:
            msg = f"Sandbox {sandbox_id} not found"
            raise SandboxBackendError(msg)
        if self.supports_labels:
            bind_label_to_sandbox(workload_label, state.info.label)

    def worker_command(self) -> list[str]:
        """Command to invoke the in-sandbox worker module."""
        import sys

        return [sys.executable, "-m", "aegis.sandbox._worker"]

    def _require_state(self, sandbox_id: str) -> SandboxInstanceState:
        state = self._instances.get(sandbox_id)
        if state is None:
            msg = f"Sandbox {sandbox_id} not found"
            raise SandboxBackendError(msg)
        return state
