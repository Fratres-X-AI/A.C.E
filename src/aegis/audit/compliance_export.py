"""Export auditable compliance artifact packs — no cloud required."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aegis.audit.metrics import ContainmentMetrics
from aegis.audit.tamper_proof_log import TamperProofLog
from aegis.redteam.simulator import ContainmentReport


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_compliance_pack(
    output_dir: str | Path,
    *,
    audit_log: TamperProofLog | None = None,
    metrics: ContainmentMetrics | None = None,
    benchmark: ContainmentReport | None = None,
    policy_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a self-contained compliance folder with manifest and file hashes."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    metrics = metrics or ContainmentMetrics()
    files_written: list[str] = []

    metrics_path = out / "metrics.json"
    metrics.export_compliance_artifact(str(metrics_path))
    files_written.append("metrics.json")

    if audit_log is not None:
        events_path = out / "audit_events.json"
        events_path.write_text(
            json.dumps(audit_log.export_events(), indent=2, default=str),
            encoding="utf-8",
        )
        files_written.append("audit_events.json")
        chain_path = out / "audit_chain_verification.json"
        chain_path.write_text(
            json.dumps(
                {
                    "chain_valid": audit_log.verify_chain(),
                    "events": len(audit_log.entries),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        files_written.append("audit_chain_verification.json")

    if benchmark is not None:
        bench_path = out / "containment_benchmark.json"
        bench_path.write_text(
            json.dumps(benchmark.to_dict(), indent=2), encoding="utf-8"
        )
        files_written.append("containment_benchmark.json")

    if policy_path is not None:
        src = Path(policy_path)
        if src.exists():
            dest = out / "policy.yaml"
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            files_written.append("policy.yaml")

    manifest_files = {name: _sha256_file(out / name) for name in files_written}
    manifest = {
        "framework": "A.C.E Aegis Containment Engine",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "philosophy": "assume_breach_contain_egress",
        "files": manifest_files,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest
