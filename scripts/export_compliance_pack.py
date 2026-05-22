#!/usr/bin/env python3
"""Generate a full compliance artifact pack from local red-team benchmark."""

from __future__ import annotations

from pathlib import Path

from aegis.audit.compliance_export import export_compliance_pack
from aegis.audit.metrics import ContainmentMetrics
from aegis.audit.persistent_log import PersistentTamperProofLog
from aegis.core.containment_engine import ContainmentEngine
from aegis.core.policy import Policy
from aegis.redteam.simulator import ContainmentSimulator
from aegis.utils.visualization import console


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    policy_path = root / "policy.yaml"
    out_dir = root / "artifacts" / "compliance_pack"
    audit_db = root / "artifacts" / "benchmark_audit.db"

    policy = Policy.from_file(policy_path) if policy_path.exists() else Policy()
    audit_log = PersistentTamperProofLog(db_path=audit_db)
    engine = ContainmentEngine(policy=policy, audit_log=audit_log)
    sim = ContainmentSimulator(engine=engine)
    report = sim.run_all()

    metrics = ContainmentMetrics()
    metrics.total_requests = report.scenarios_run
    metrics.exfil_attempts_blocked = report.scenarios_caught

    manifest = export_compliance_pack(
        out_dir,
        audit_log=audit_log,
        metrics=metrics,
        benchmark=report,
        policy_path=policy_path,
    )

    console.print(f"[green]Compliance pack written to[/green] {out_dir}")
    console.print(f"Catch rate: {report.catch_rate:.1%}")
    console.print(f"Chain valid: {audit_log.verify_chain()}")
    console.print(f"Manifest: {list(manifest['files'].keys())}")


if __name__ == "__main__":
    main()
