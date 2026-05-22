"""Sandbox backend implementations."""

from aegis.sandbox.backends._subprocess import docker_available
from aegis.sandbox.backends.bubblewrap import BubblewrapSandbox
from aegis.sandbox.backends.docker import DockerSandbox
from aegis.sandbox.backends.firecracker import FirecrackerSandbox
from aegis.sandbox.backends.gvisor import GVisorSandbox

__all__ = [
    "BubblewrapSandbox",
    "DockerSandbox",
    "FirecrackerSandbox",
    "GVisorSandbox",
    "docker_available",
]
