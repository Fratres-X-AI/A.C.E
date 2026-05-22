#!/usr/bin/env python3
"""RunPod demo: real Hugging Face model inside A.C.E containment."""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.request
from pathlib import Path

import aegis.execution.hf_workload  # noqa: F401 — registers hf_llm workload
from aegis.core.containment_engine import ContainmentEngine
from aegis.core.policy import Policy
from aegis.core.session import Session
from aegis.execution.hf_runtime import ensure_hf_server, hf_model_id, start_server
from aegis.execution.hf_workload import hf_llm
from aegis.ifc.labels import INTERNAL, PUBLIC
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.config import TunnelConfig
from aegis.utils.visualization import console, print_layer_activation


def _wait_for_health(url: str, timeout: float = 600.0) -> None:
    deadline = time.monotonic() + timeout
    health = url.rstrip("/") + "/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health, timeout=5) as resp:  # noqa: S310
                if resp.status == 200:
                    return
        except OSError:
            time.sleep(2.0)
    msg = f"HF server did not become ready at {health}"
    raise TimeoutError(msg)


def run_demo(*, query: str, backend: str, serve_only: bool) -> int:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    model = hf_model_id()
    if not token and "llama" in model.lower():
        console.print("[red]Gated model requires HF_TOKEN.[/red]")
        console.print("  export HF_TOKEN=hf_...")
        console.print("  Or use default Qwen: unset ACE_HF_MODEL")
        return 1
    four_bit = os.environ.get("ACE_HF_LOAD_4BIT", "0")
    console.print("\n[bold cyan]A.C.E + Hugging Face[/bold cyan]")
    console.print(f"  Model : {model}")
    console.print(f"  4-bit : {four_bit}")
    console.print(f"  Backend: {backend}\n")

    if serve_only:
        console.print(
            "[yellow]Loading model and starting server (blocking)...[/yellow]",
        )
        start_server(block=True)
        return 0

    url = ensure_hf_server()
    os.environ["ACE_HF_SERVER_URL"] = url
    console.print(f"[green]HF server:[/green] {url}")
    console.print("[dim]First run downloads weights — can take several minutes.[/dim]")
    _wait_for_health(url)

    repo_root = Path(__file__).resolve().parent.parent
    policy = Policy.from_file(repo_root / "policy.yaml")
    engine = ContainmentEngine(policy=policy)
    tunnel = SimulatedTunnel(
        config=TunnelConfig(require_capability_token=True),
    )
    session = Session()
    session.bind_tee("runpod-hf-demo")
    session.issue_capability("runpod-inference")
    session.sandbox_backend = backend

    result = engine.process_integrated(
        {"query": query},
        session,
        hf_llm,
        sandbox_backend=backend,
        tunnel=tunnel,
        input_label=INTERNAL,
        output_clearance=PUBLIC,
    )
    tunnel.close()

    print_layer_activation(
        "HF + containment",
        "PASS" if not result.blocked else "BLOCK",
        (result.output or "blocked")[:80],
    )
    console.print(f"  Sandbox ID : {result.sandbox_id}")
    console.print(f"  Audit valid: {engine.audit_log.verify_chain()}")
    if result.output:
        console.print(f"\n[bold]Model output:[/bold]\n{result.output}\n")
    return 0 if not result.blocked else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="RunPod HF + A.C.E demo")
    parser.add_argument(
        "--query",
        default="In one sentence, what is information flow control?",
    )
    parser.add_argument(
        "--backend",
        default="auto",
        help="Sandbox backend (auto picks process on RunPod)",
    )
    parser.add_argument(
        "--serve-only",
        action="store_true",
        help="Only start HF server (for debugging)",
    )
    args = parser.parse_args()
    sys.exit(
        run_demo(
            query=args.query,
            backend=args.backend,
            serve_only=args.serve_only,
        ),
    )


if __name__ == "__main__":
    main()
