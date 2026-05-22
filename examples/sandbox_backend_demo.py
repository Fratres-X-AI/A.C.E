#!/usr/bin/env python3
"""Demonstrate pluggable sandbox backends with full A.C.E integration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aegis.core.containment_engine import ContainmentEngine
from aegis.core.policy import Policy
from aegis.core.session import Session
from aegis.execution.mock_model import mock_llm
from aegis.ifc.labels import PUBLIC
from aegis.sandbox.base import SandboxBackendError
from aegis.sandbox.registry import SandboxRegistry
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.visualization import console, print_layer_activation


def run_backend_demo(*, backend_name: str, loop_all: bool) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    policy = Policy.from_file(repo_root / "policy.yaml")
    engine = ContainmentEngine(policy=policy)
    tunnel = SimulatedTunnel(config=policy.policy.tunnel)

    if loop_all:
        targets = SandboxRegistry.list_available(policy.policy.sandbox)
    elif backend_name == "auto":
        try:
            targets = [SandboxRegistry.resolve(policy.policy.sandbox).name]
        except SandboxBackendError as exc:
            console.print(f"[red]No sandbox backend available:[/red] {exc}")
            return 1
    else:
        targets = [backend_name]

    exit_code = 0
    for name in targets:
        console.print(f"\n[bold cyan]Backend: {name}[/bold cyan]")
        session = Session()
        session.bind_tee("sandbox-backend-demo")
        session.issue_capability("inference")
        session.sandbox_backend = name
        try:
            result = engine.process_integrated(
                {"query": "sandbox backend smoke test"},
                session,
                mock_llm,
                sandbox_backend=name,
                tunnel=tunnel,
                input_label=PUBLIC,
                output_clearance=PUBLIC,
            )
            print_layer_activation(
                name,
                "PASS" if not result.blocked else "BLOCK",
                (result.output or "blocked")[:60],
            )
            console.print(f"  Sandbox ID: {result.sandbox_id}")
            console.print(f"  Audit chain valid: {engine.audit_log.verify_chain()}")
        except SandboxBackendError as exc:
            console.print(f"  [yellow]Skipped — {exc}[/yellow]")
            exit_code = 1
    tunnel.close()
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="A.C.E sandbox backend demo")
    parser.add_argument(
        "--backend",
        default="auto",
        choices=[
            "auto",
            "bubblewrap",
            "gvisor",
            "firecracker",
            "docker",
        ],
    )
    parser.add_argument(
        "--loop-available",
        action="store_true",
        help="Run demo for every available backend",
    )
    args = parser.parse_args()
    sys.exit(run_backend_demo(backend_name=args.backend, loop_all=args.loop_available))


if __name__ == "__main__":
    main()
