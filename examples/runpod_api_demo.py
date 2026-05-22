#!/usr/bin/env python3
"""RunPod demo: external Llama/chat API inside A.C.E containment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import aegis.execution.api_llm_workload  # noqa: F401 — registers api_llm
from aegis.core.containment_engine import ContainmentEngine
from aegis.core.policy import Policy
from aegis.core.session import Session
from aegis.execution.api_llm_workload import api_llm, api_model, verify_api_config
from aegis.ifc.labels import PUBLIC
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.config import TunnelConfig
from aegis.utils.visualization import console, print_layer_activation


def run_demo(*, query: str, backend: str) -> int:
    check = verify_api_config()
    if not check.get("ok"):
        console.print(f"[red]FAIL — {check.get('error')}[/red]")
        return 1

    console.print("\n[bold cyan]A.C.E + External LLM API[/bold cyan]")
    console.print(f"  Model   : {api_model()}")
    console.print(f"  URL     : {check.get('url')}")
    console.print(f"  Backend : {backend}\n")

    repo_root = Path(__file__).resolve().parent.parent
    policy = Policy.from_file(repo_root / "policy.yaml")
    engine = ContainmentEngine(policy=policy)
    tunnel = SimulatedTunnel(
        config=TunnelConfig(require_capability_token=True),
    )
    session = Session()
    session.bind_tee("runpod-api-demo")
    session.issue_capability("runpod-inference")
    session.sandbox_backend = backend

    result = engine.process_integrated(
        {"query": query},
        session,
        api_llm,
        sandbox_backend=backend,
        tunnel=tunnel,
        input_label=PUBLIC,
        output_clearance=PUBLIC,
    )
    tunnel.close()

    print_layer_activation(
        "API + containment",
        "PASS" if not result.blocked else "BLOCK",
        (result.output or "blocked")[:80],
    )
    console.print(f"  Sandbox ID : {result.sandbox_id}")
    console.print(f"  Audit valid: {engine.audit_log.verify_chain()}")
    if result.blocked and result.reasons:
        console.print(f"  [red]Blocked because:[/red] {'; '.join(result.reasons)}")
    if result.output:
        console.print(f"\n[bold]Model output:[/bold]\n{result.output}\n")
    return 0 if not result.blocked else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="RunPod API LLM + A.C.E demo")
    parser.add_argument(
        "--query",
        default="In one sentence, what is information flow control?",
    )
    parser.add_argument(
        "--backend",
        default="auto",
        help="Sandbox backend (auto picks process on RunPod)",
    )
    args = parser.parse_args()
    sys.exit(run_demo(query=args.query, backend=args.backend))


if __name__ == "__main__":
    main()
