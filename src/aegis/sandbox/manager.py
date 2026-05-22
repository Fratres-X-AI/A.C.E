"""Sandbox factory — registry-driven backend selection."""

from __future__ import annotations

import os

from aegis.audit.tamper_proof_log import TamperProofLog
from aegis.ifc.labels import SecurityLabel
from aegis.sandbox.base import SandboxBackend
from aegis.sandbox.facade import SandboxSessionFacade
from aegis.sandbox.registry import SandboxRegistry
from aegis.utils.config import SandboxConfig


class SandboxManager:
    """Create sandbox sessions using pluggable isolation backends."""

    def __init__(
        self,
        config: SandboxConfig | None = None,
        audit_log: TamperProofLog | None = None,
    ) -> None:
        self.config = config or SandboxConfig()
        self.audit_log = audit_log

    def get_backend(self, name: str | None = None) -> SandboxBackend:
        if name is not None:
            return SandboxRegistry.get(name, self.config)
        env_name = os.environ.get("ACE_SANDBOX_BACKEND")
        if env_name:
            return SandboxRegistry.get(env_name, self.config)
        return SandboxRegistry.resolve(self.config)

    def open_session(self, _label: SecurityLabel | None = None) -> SandboxSessionFacade:
        backend = self.get_backend()
        return SandboxSessionFacade(
            backend=backend,
            config=self.config,
            audit_log=self.audit_log,
        )

    def create_sandbox(self) -> SandboxSessionFacade:
        """Backward-compatible alias — returns facade without starting workload."""
        return self.open_session()
