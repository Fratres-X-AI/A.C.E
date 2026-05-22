#!/usr/bin/env python3
"""RunPod smoke test — one script to verify sandbox backends on a Linux pod."""

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


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run_smoke(*, backend: str) -> int:
    policy = Policy.from_file(_repo_root() / "policy.yaml")
    compatible = SandboxRegistry.list_compatible()
    available = SandboxRegistry.list_available(policy.policy.sandbox)

    print("=== A.C.E RunPod Smoke Test (v0.3.0) ===\n")
    print(f"Platform backends : {', '.join(compatible) or 'none'}")
    print(f"Available now     : {', '.join(available) or 'NONE — see fix below'}\n")

    if not available and backend == "auto":
        print("FAIL: No sandbox backend available on this pod.")
        print("\nQuick fix (Ubuntu/Debian pod):")
        print("  sudo apt-get update && sudo apt-get install -y bubblewrap")
        print("  bash scripts/runpod_smoke.sh")
        return 1

    try:
        if backend == "auto":
            resolved = SandboxRegistry.resolve(policy.policy.sandbox).name
        else:
            SandboxRegistry.get(backend, policy.policy.sandbox)
            resolved = backend
    except SandboxBackendError as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"Running integrated pipeline with backend: {resolved}\n")

    engine = ContainmentEngine(policy=policy)
    tunnel = SimulatedTunnel(config=policy.policy.tunnel)
    session = Session()
    session.bind_tee("runpod-smoke")
    session.issue_capability("runpod-inference")
    session.sandbox_backend = resolved

    result = engine.process_integrated(
        {"query": "RunPod sandbox smoke test"},
        session,
        mock_llm,
        sandbox_backend=resolved,
        tunnel=tunnel,
        input_label=PUBLIC,
        output_clearance=PUBLIC,
    )

    audit_ok = engine.audit_log.verify_chain()
    tunnel.close()

    print("--- Results ---")
    print(f"  Backend     : {resolved}")
    print(f"  Sandbox ID  : {result.sandbox_id or 'n/a'}")
    print(f"  Blocked     : {result.blocked}")
    print(f"  Output      : {(result.output or '')[:120]}")
    print(f"  Audit chain : {'valid' if audit_ok else 'INVALID'}")

    if result.blocked or not audit_ok:
        print("\nFAIL: Pipeline blocked or audit chain invalid.")
        if result.reasons:
            print(f"  Reasons: {'; '.join(result.reasons)}")
        return 1

    print("\nPASS — A.C.E sandbox is working on this RunPod pod.")
    print("\nNext:")
    print("  python examples/sandbox_backend_demo.py --backend auto")
    print("  python examples/integrated_sandbox_tunnel_demo.py")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="RunPod sandbox smoke test")
    parser.add_argument(
        "--backend",
        default="auto",
        choices=["auto", "bubblewrap", "gvisor", "firecracker", "docker"],
        help="Sandbox backend (default: auto)",
    )
    args = parser.parse_args()
    sys.exit(run_smoke(backend=args.backend))


if __name__ == "__main__":
    main()
