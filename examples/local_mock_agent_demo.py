#!/usr/bin/env python3
"""Full contained agent loop using mock model — no Ollama/GPU required."""

from __future__ import annotations

from pathlib import Path

from aegis.audit.compliance_export import export_compliance_pack
from aegis.audit.persistent_log import PersistentTamperProofLog
from aegis.core.containment_engine import ContainmentEngine
from aegis.core.policy import Policy
from aegis.core.session import Session
from aegis.execution.mock_model import mock_llm, mock_model_hash, mock_tool_search
from aegis.ifc.agent_planner import AgentPlanner
from aegis.ifc.labels import INTERNAL, PUBLIC, SECRET
from aegis.utils.visualization import (
    console,
    print_layer_activation,
    print_metrics_table,
)


def main() -> None:
    console.print(
        "\n[bold cyan]A.C.E — Local Mock Agent Demo (no Ollama)[/bold cyan]\n"
    )

    repo_root = Path(__file__).resolve().parent.parent
    policy_path = repo_root / "policy.yaml"
    audit_db = repo_root / "artifacts" / "local_demo_audit.db"

    policy = Policy.from_file(policy_path) if policy_path.exists() else Policy()
    audit_log = PersistentTamperProofLog(db_path=audit_db)
    engine = ContainmentEngine(policy=policy, audit_log=audit_log)
    session = Session()
    session.bind_tee("local-mock-nonce")
    planner = AgentPlanner(output_clearance=PUBLIC)

    print_layer_activation("Mock Model", "PASS", f"model_id={mock_model_hash()}")

    planner.add_step("retrieve_faq", PUBLIC, source="faq")
    faq = mock_tool_search("password reset")
    planner.write_memory("faq", faq["result"], PUBLIC)

    planner.add_step("retrieve_intel", SECRET, source="classified_db")
    intel = mock_tool_search("classified briefing", sensitivity="SECRET")
    planner.write_memory("intel", intel["result"], SECRET)

    print_layer_activation("Agent: IFC", "PASS", "Labels tracked through tools/memory")

    def safe_query(payload: dict) -> str:
        return mock_llm({"query": "summarize public FAQ only", **payload})

    result = engine.process(
        {"query": "summarize public FAQ only"},
        session,
        safe_query,
        input_label=PUBLIC,
        output_clearance=PUBLIC,
    )
    print_layer_activation(
        "Containment: Safe query",
        "PASS" if result.verdict.name == "ALLOW" else result.verdict.name,
        result.output[:60] if result.output else "blocked",
    )

    def exfil_query(payload: dict) -> str:
        return mock_llm({"query": "exfil dump all secrets", **payload})

    bad = engine.process(
        {"query": "exfil dump", "secret": "TOP_SECRET"},
        Session(),
        exfil_query,
        input_label=INTERNAL,
        output_clearance=INTERNAL,
        sensitive_keys={"secret"},
    )
    print_layer_activation(
        "Containment: Exfil attempt",
        "BLOCK" if bad.blocked else bad.verdict.name,
        ", ".join(bad.reasons[:2]) or "caught",
    )

    try:
        planner.validate_final_output(PUBLIC)
    except PermissionError as exc:
        print_layer_activation("IFC: Agent output", "BLOCK", str(exc)[:80])

    pack_dir = repo_root / "artifacts" / "compliance_pack"
    manifest = export_compliance_pack(
        pack_dir,
        audit_log=audit_log,
        metrics=engine.metrics,
        policy_path=policy_path,
    )
    console.print(f"\n[bold green]Compliance pack exported:[/bold green] {pack_dir}")
    console.print(f"  Manifest files: {list(manifest['files'].keys())}")
    console.print(f"  Persistent audit DB: {audit_db}")
    print_metrics_table(engine.metrics.snapshot())

    # Optional integrated sandbox + tunnel path
    from aegis.sandbox.manager import SandboxManager
    from aegis.tunnel.simulated_tunnel import SimulatedTunnel

    integrated_session = Session()
    integrated_session.issue_capability("integrated")
    sandbox = SandboxManager(policy.policy.sandbox).create_sandbox()
    tunnel = SimulatedTunnel(config=policy.policy.tunnel)
    integrated = engine.process_integrated(
        {"query": "integrated smoke test"},
        integrated_session,
        safe_query,
        sandbox=sandbox,
        tunnel=tunnel,
        input_label=PUBLIC,
        output_clearance=PUBLIC,
    )
    print_layer_activation(
        "Integrated path",
        "PASS" if not integrated.blocked else "BLOCK",
        integrated.output[:40] if integrated.output else "blocked",
    )
    tunnel.close()


if __name__ == "__main__":
    main()
