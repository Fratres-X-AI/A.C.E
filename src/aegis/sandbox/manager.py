"""Sandbox factory — auto-detect runtime and manage lifecycle."""

from __future__ import annotations

from aegis.sandbox.docker_sandbox import DockerSandbox, docker_available
from aegis.sandbox.environment import SandboxEnvironment
from aegis.sandbox.simulated_sandbox import SimulatedSandbox
from aegis.utils.config import SandboxConfig


class GVisorRuntime:
    """Extension hook for gVisor runsc runtime (stub)."""

    @staticmethod
    def is_available() -> bool:
        return False

    @staticmethod
    def reason() -> str:
        return "gVisor runsc not configured — set runtime=docker with --runtime=runsc"


class FirecrackerRuntime:
    """Extension hook for Firecracker microVMs (stub)."""

    @staticmethod
    def is_available() -> bool:
        return False

    @staticmethod
    def reason() -> str:
        return "Firecracker not configured — requires firecracker binary + kernel image"


class KataRuntime:
    """Extension hook for Kata Containers (stub)."""

    @staticmethod
    def is_available() -> bool:
        return False

    @staticmethod
    def reason() -> str:
        return "Kata Containers not configured — requires containerd + kata-runtime"


class SandboxManager:
    """Create sandboxes with auto-detected or explicit runtime."""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()

    def create_sandbox(self) -> SandboxEnvironment:
        runtime = self.config.runtime.lower()
        if runtime == "simulated":
            return SimulatedSandbox(config=self.config)
        if runtime == "docker":
            return DockerSandbox(config=self.config)
        if runtime == "gvisor":
            if GVisorRuntime.is_available():
                return DockerSandbox(config=self.config)
            msg = GVisorRuntime.reason()
            raise RuntimeError(msg)
        if runtime == "auto":
            if docker_available():
                return DockerSandbox(config=self.config)
            return SimulatedSandbox(config=self.config)
        return SimulatedSandbox(config=self.config)
