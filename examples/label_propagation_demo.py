#!/usr/bin/env python3
"""Show IFC labels flowing session -> sandbox -> planner -> output clearance."""

from __future__ import annotations

from aegis.core.containment_engine import ContainmentEngine
from aegis.core.session import Session
from aegis.ifc.agent_planner import AgentPlanner
from aegis.ifc.labels import INTERNAL, PUBLIC, SECRET
from aegis.sandbox.manager import SandboxManager
from aegis.sandbox.workloads import register_workload
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.config import TunnelConfig
from aegis.utils.visualization import console, print_layer_activation


@register_workload("label_demo")
def _label_workload(payload: dict) -> str:
    return "Public FAQ summary only — no classified content."


def main() -> None:
    console.print("\n[bold green]A.C.E — Label Propagation Demo[/bold green]\n")
    engine = ContainmentEngine()
    session = Session()
    session.issue_capability("planner")
    session.sandbox_backend = "auto"
    planner = AgentPlanner(output_clearance=PUBLIC)

    planner.add_step("fetch_public", PUBLIC, source="faq")
    planner.add_step("fetch_secret", SECRET, source="vault")
    session.set_label("faq", PUBLIC)
    session.set_label("vault", SECRET)
    session.sandbox_label = INTERNAL

    tunnel = SimulatedTunnel(config=TunnelConfig(require_capability_token=True))
    manager = SandboxManager(audit_log=engine.audit_log)
    sandbox = manager.open_session()

    result = engine.process_integrated(
        {"query": "public summary"},
        session,
        _label_workload,
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
    console.print(f"Backend: {sandbox.runtime_name}")
    console.print(f"Sandbox ID: {result.sandbox_id}\n")


if __name__ == "__main__":
    main()
