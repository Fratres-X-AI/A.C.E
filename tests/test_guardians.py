"""Tests for egress guardians."""

from aegis.guardians.egress_controller import EgressController
from aegis.guardians.output_guardian import OutputGuardian
from aegis.guardians.verification import VerificationEngine
from aegis.utils.typing import ContainmentVerdict


def test_pii_detection() -> None:
    guardian = OutputGuardian()
    result = guardian.scan("Contact: user@example.com or SSN 123-45-6789")
    assert result.verdict != ContainmentVerdict.ALLOW


def test_high_entropy_block() -> None:
    import secrets
    import string

    guardian = OutputGuardian()
    # Random alphanumeric string has high per-char entropy
    high_entropy = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(3000)
    )
    result = guardian.scan(high_entropy)
    assert result.verdict in {ContainmentVerdict.BLOCK, ContainmentVerdict.KILL_SESSION}


def test_canary_triggers_kill() -> None:
    guardian = OutputGuardian()
    token = "ACE-CANARY-test-token-12345"
    guardian.register_canary(token)
    result = guardian.scan(f"Leaked: {token}")
    assert result.canary_triggered
    assert result.verdict == ContainmentVerdict.KILL_SESSION


def test_rate_limit_throttle() -> None:
    controller = EgressController(max_bytes_per_minute=100)
    verdict = controller.check_egress("x" * 200, ContainmentVerdict.ALLOW)
    assert verdict == ContainmentVerdict.THROTTLE


def test_ensemble_consensus() -> None:
    engine = VerificationEngine()
    ok, winner = engine.ensemble_consensus(["a", "a", "b"])
    assert ok
    assert winner == "a"


def test_structured_schema() -> None:
    engine = VerificationEngine()
    out = engine.enforce_schema(
        {"expression": "x+1", "verified": True, "variables": ["x"]}
    )
    assert out.verified
