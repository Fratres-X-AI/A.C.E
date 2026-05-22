#!/usr/bin/env python3
"""Demonstrate Windows Sandbox backend selection and workload execution."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aegis.ifc.labels import INTERNAL
from aegis.sandbox.base import SandboxBackendError
from aegis.sandbox.manager import SandboxManager
from aegis.sandbox.registry import SandboxRegistry
from aegis.sandbox.workloads import register_workload
from aegis.utils.config import SandboxConfig
from aegis.utils.visualization import console, print_layer_activation


@register_workload("windows_demo_echo")
def _echo(payload: dict) -> str:
    return f"windows-sandbox:{payload.get('msg', 'ok')}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Windows Sandbox backend demo")
    parser.add_argument(
        "--backend",
        default="auto",
        help="Sandbox backend (auto, windows, docker, mock)",
    )
    args = parser.parse_args()

    console.print("\n[bold cyan]A.C.E — Windows Sandbox Demo[/bold cyan]\n")

    if args.backend == "mock":
        tests_dir = Path(__file__).resolve().parent.parent / "tests"
        sys.path.insert(0, str(tests_dir))
        from sandbox_helpers import MockWindowsSandboxBackend

        SandboxRegistry.register("windows", MockWindowsSandboxBackend)
        backend_name = "windows"
    else:
        backend_name = args.backend

    config = SandboxConfig(backend=backend_name)
    manager = SandboxManager(config)
    session = manager.open_session()

    print_layer_activation(
        "Platform",
        "PASS",
        f"compatible={SandboxRegistry.list_compatible()}",
    )
    print_layer_activation(
        "Available",
        "PASS",
        f"backends={SandboxRegistry.list_available(config)}",
    )

    try:
        resolved = backend_name if backend_name != "auto" else None
        backend = manager.get_backend(resolved)
    except SandboxBackendError as exc:
        console.print(f"[red]Backend unavailable:[/red] {exc}")
        console.print(
            "\n[yellow]Windows note:[/yellow] Enable Windows Sandbox via "
            "'Turn Windows features on or off' → Windows Sandbox "
            "(Pro/Enterprise/Education). Docker Desktop works as fallback but "
            "is resource-heavy on Windows.\n",
        )
        sys.exit(1)

    session.backend = backend
    session.create(INTERNAL)
    output = session.run_labeled(_echo, {"msg": "hello-from-host"}, INTERNAL)
    meta = session.inspect()

    print_layer_activation("Sandbox", "PASS", f"runtime={backend.name}")
    print_layer_activation("Workload", "PASS", output.strip())
    console.print(f"Inspect: {meta}\n")
    session.destroy()


if __name__ == "__main__":
    main()
