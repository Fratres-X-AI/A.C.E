"""Tests for tamper-proof audit log."""

from aegis.audit.tamper_proof_log import TamperProofLog
from aegis.utils.typing import AuditEvent


def test_append_and_verify() -> None:
    log = TamperProofLog()
    log.append(AuditEvent(layer="test", action="start", detail="ok"))
    log.append(AuditEvent(layer="test", action="stop", detail="ok"))
    assert log.verify_chain()
    assert len(log.entries) == 2


def test_tamper_detection() -> None:
    log = TamperProofLog()
    log.append(AuditEvent(layer="test", action="start", detail="ok"))
    log._entries[0].entry_hash = "tampered"  # noqa: SLF001
    assert not log.verify_chain()


def test_export_with_dp() -> None:
    log = TamperProofLog()
    log.append(
        AuditEvent(
            layer="metrics",
            action="count",
            detail="",
            metadata={"count": 100},
        ),
    )
    events = log.export_events(dp_epsilon=1.0)
    assert len(events) == 1
