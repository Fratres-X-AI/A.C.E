#!/usr/bin/env python3
"""Demonstrate exfil blocked at guardian + tunnel egress with audit trail."""

from __future__ import annotations

from aegis.core.containment_engine import ContainmentEngine
from aegis.core.session import Session
from aegis.ifc.labels import PUBLIC
from aegis.sandbox.manager import SandboxManager
from aegis.sandbox.workloads import register_workload
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.config import TunnelConfig
from aegis.utils.visualization import console, print_layer_activation


@register_workload("exfil_demo")
def _malicious(payload: dict) -> str:
    return (
        "Summary: quarterly results look good. "
        "SECRET: internal-only revenue figures attached."
    )


def main() -> None:
    console.print("\n[bold red]A.C.E — Sandbox Exfil Demo[/bold red]\n")
    engine = ContainmentEngine()
    session = Session()
    session.issue_capability("tunnel")
    session.sandbox_backend = "auto"
    tunnel = SimulatedTunnel(config=TunnelConfig(require_capability_token=True))
    manager = SandboxManager(audit_log=engine.audit_log)
    sandbox = manager.open_session()

    result = engine.process_integrated(
        {"query": "summarize with secrets"},
        session,
        _malicious,
        sandbox=sandbox,
        tunnel=tunnel,
        input_label=PUBLIC,
        output_clearance=PUBLIC,
    )
    tunnel.close()

    layers = [e.event.layer for e in engine.audit_log.entries]
    print_layer_activation("Guardian + Tunnel egress", "BLOCK", str(result.reasons[:2]))
    console.print(f"Audit layer sequence: {' -> '.join(dict.fromkeys(layers))}")
    console.print(f"Backend: {sandbox.runtime_name}")
    console.print(f"Blocked: {result.blocked}  Verdict: {result.verdict.name}\n")


if __name__ == "__main__":
    main()
