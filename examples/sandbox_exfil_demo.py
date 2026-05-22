#!/usr/bin/env python3
"""Demonstrate exfil blocked at guardian + tunnel egress with audit trail."""

from __future__ import annotations

from aegis.core.containment_engine import ContainmentEngine
from aegis.core.session import Session
from aegis.ifc.labels import INTERNAL, PUBLIC
from aegis.sandbox.simulated_sandbox import SimulatedSandbox
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.config import TunnelConfig
from aegis.utils.visualization import console, print_layer_activation


def main() -> None:
    console.print("\n[bold red]A.C.E — Sandbox Exfil Demo[/bold red]\n")
    engine = ContainmentEngine()
    session = Session()
    session.issue_capability("tunnel")
    tunnel = SimulatedTunnel(config=TunnelConfig(require_capability_token=True))
    sandbox = SimulatedSandbox()

    def malicious(payload: dict) -> str:
        return (
            "Summary: quarterly results look good. "
            "SECRET: internal-only revenue figures attached."
        )

    result = engine.process_integrated(
        {"query": "summarize with secrets"},
        session,
        malicious,
        sandbox=sandbox,
        tunnel=tunnel,
        input_label=PUBLIC,
        output_clearance=PUBLIC,
    )
    tunnel.close()

    layers = [e.event.layer for e in engine.audit_log.entries]
    print_layer_activation("Guardian + Tunnel egress", "BLOCK", str(result.reasons[:2]))
    console.print(f"Audit layer sequence: {' -> '.join(dict.fromkeys(layers))}")
    console.print(f"Blocked: {result.blocked}  Verdict: {result.verdict.name}\n")


if __name__ == "__main__":
    main()
