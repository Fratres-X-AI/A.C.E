"""Tests for persistent audit log and compliance export."""

from pathlib import Path

from aegis.audit.compliance_export import export_compliance_pack
from aegis.audit.metrics import ContainmentMetrics
from aegis.audit.persistent_log import PersistentTamperProofLog
from aegis.utils.typing import AuditEvent


def test_persistent_log_survives_reload(tmp_path: Path) -> None:
    db = tmp_path / "audit.db"
    log1 = PersistentTamperProofLog(db_path=db)
    log1.append(AuditEvent(layer="test", action="start", detail="a"))
    log1.append(AuditEvent(layer="test", action="stop", detail="b"))
    assert log1.verify_chain()

    log2 = PersistentTamperProofLog(db_path=db)
    assert len(log2.entries) == 2
    assert log2.verify_chain()


def test_compliance_pack_export(tmp_path: Path) -> None:
    log = PersistentTamperProofLog(db_path=tmp_path / "a.db")
    log.append(AuditEvent(layer="core", action="test", detail="ok"))
    metrics = ContainmentMetrics()
    metrics.total_requests = 1

    manifest = export_compliance_pack(
        tmp_path / "pack",
        audit_log=log,
        metrics=metrics,
    )
    assert "metrics.json" in manifest["files"]
    assert (tmp_path / "pack" / "manifest.json").exists()
