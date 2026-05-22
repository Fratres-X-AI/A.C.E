#!/usr/bin/env python3
"""Full integrated demo: encrypt → IFC → tunnel → sandbox → guardian → audit."""

from __future__ import annotations

from pathlib import Path

from aegis.core.containment_engine import ContainmentEngine
from aegis.core.policy import Policy
from aegis.core.session import Session
from aegis.execution.mock_model import mock_llm
from aegis.ifc.labels import INTERNAL, PUBLIC
from aegis.sandbox.manager import SandboxManager
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.visualization import (
    console,
    print_layer_activation,
    print_metrics_table,
)


def main() -> None:
    console.print(
        "\n[bold cyan]A.C.E — Integrated Sandbox + Tunnel Demo[/bold cyan]\n",
    )
    repo_root = Path(__file__).resolve().parent.parent
    policy = Policy.from_file(repo_root / "policy.yaml")
    engine = ContainmentEngine(policy=policy)
    session = Session()
    session.bind_tee("integrated-demo")
    session.issue_capability("inference")

    sandbox = SandboxManager(policy.policy.sandbox).create_sandbox()
    tunnel = SimulatedTunnel(config=policy.policy.tunnel)
    runtime = sandbox.runtime_name

    print_layer_activation("Sandbox", "PASS", f"runtime={runtime}")
    print_layer_activation("Tunnel", "PASS", f"endpoint={tunnel.endpoint_id}")

    def workload(payload: dict) -> str:
        return mock_llm({"query": payload.get("query", ""), "mode": "safe"})

    result = engine.process_integrated(
        {"query": "summarize quarterly report"},
        session,
        workload,
        sandbox=sandbox,
        tunnel=tunnel,
        input_label=PUBLIC,
        output_clearance=PUBLIC,
        sensitive_keys={"query"},
    )
    tunnel.close()

    print_layer_activation(
        "Integrated pipeline",
        "PASS" if not result.blocked else "BLOCK",
        result.output[:80] if result.output else "blocked",
    )
    print_metrics_table(result.metrics_snapshot)
    console.print(f"Audit events: {result.audit_event_count}")
    console.print(f"Chain valid: {engine.audit_log.verify_chain()}\n")


if __name__ == "__main__":
    main()
