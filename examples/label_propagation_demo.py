#!/usr/bin/env python3
"""Show IFC labels flowing session → sandbox → planner → output clearance."""

from __future__ import annotations

from aegis.core.containment_engine import ContainmentEngine
from aegis.core.session import Session
from aegis.ifc.agent_planner import AgentPlanner
from aegis.ifc.labels import INTERNAL, PUBLIC, SECRET
from aegis.sandbox.simulated_sandbox import SimulatedSandbox
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.config import TunnelConfig
from aegis.utils.visualization import console, print_layer_activation


def main() -> None:
    console.print("\n[bold green]A.C.E — Label Propagation Demo[/bold green]\n")
    engine = ContainmentEngine()
    session = Session()
    session.issue_capability("planner")
    planner = AgentPlanner(output_clearance=PUBLIC)

    planner.add_step("fetch_public", PUBLIC, source="faq")
    planner.add_step("fetch_secret", SECRET, source="vault")
    session.set_label("faq", PUBLIC)
    session.set_label("vault", SECRET)
    session.sandbox_label = INTERNAL

    tunnel = SimulatedTunnel(config=TunnelConfig(require_capability_token=True))
    sandbox = SimulatedSandbox()
    sandbox.create(INTERNAL)

    def workload(payload: dict) -> str:
        return "Public FAQ summary only — no classified content."

    result = engine.process_integrated(
        {"query": "public summary"},
        session,
        workload,
        sandbox=sandbox,
        tunnel=tunnel,
        input_label=PUBLIC,
        output_clearance=PUBLIC,
    )
    tunnel.close()

    print_layer_activation(
        "Session labels",
        "PASS",
        f"sandbox_label={session.sandbox_label}",
    )
    print_layer_activation(
        "Output clearance",
        "PASS" if not result.blocked else "BLOCK",
        result.output or "blocked",
    )
    console.print(f"Sandbox ID: {result.sandbox_id}\n")


if __name__ == "__main__":
    main()
