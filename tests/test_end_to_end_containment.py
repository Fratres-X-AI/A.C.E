"""End-to-end containment pipeline tests."""

from aegis.core.containment_engine import ContainmentEngine
from aegis.core.session import Session
from aegis.ifc.labels import PUBLIC, SECRET
from aegis.utils.typing import ContainmentVerdict


def test_full_pipeline_blocks_exfil() -> None:
    engine = ContainmentEngine()
    session = Session()
    session.bind_tee()

    def malicious_model(payload: dict) -> str:
        return "base64:" + "X" * 5000 + " exfil dump steganographic"

    result = engine.process(
        {"query": "summarize", "secret": "TOP_SECRET"},
        session,
        malicious_model,
        input_label=SECRET,
        output_clearance=PUBLIC,
        sensitive_keys={"secret"},
    )
    assert result.blocked or result.verdict != ContainmentVerdict.ALLOW
    assert engine.audit_log.verify_chain()
    assert result.metrics_snapshot["total_requests"] >= 1


def test_legal_flow_allowed() -> None:
    engine = ContainmentEngine()
    session = Session()

    def safe_model(payload: dict) -> str:
        return "Summary complete. No sensitive data included."

    result = engine.process(
        {"query": "summarize public data"},
        session,
        safe_model,
        input_label=PUBLIC,
        output_clearance=PUBLIC,
    )
    assert result.verdict == ContainmentVerdict.ALLOW
    assert result.output is not None
