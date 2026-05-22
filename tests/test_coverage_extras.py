"""Additional tests for coverage on core paths."""

import pytest

from aegis.core.policy import Policy
from aegis.core.session import CapabilityToken, Session
from aegis.crypto.primitives import (
    add_laplace_noise,
    caecator_blind_metadata,
    generate_canary_token,
    hash_canary,
)
from aegis.execution.math_physics import MathPhysicsInterface
from aegis.execution.tee_abstraction import SimulatedTEE
from aegis.guardians.egress_controller import EgressController
from aegis.guardians.output_guardian import OutputGuardian
from aegis.guardians.verification import VerificationEngine
from aegis.ifc.flow_control import FlowControlEngine
from aegis.ifc.labels import INTERNAL, PUBLIC, SECRET
from aegis.redteam.canary import CanaryManager
from aegis.sandbox.manager import SandboxManager
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.config import SandboxConfig, TunnelConfig
from aegis.utils.typing import ContainmentVerdict


def test_policy_from_defaults() -> None:
    policy = Policy()
    assert policy.fail_closed()
    assert policy.guardian_entropy_threshold() == 5.5


def test_policy_yaml(tmp_path: object) -> None:
    from pathlib import Path

    path = Path(str(tmp_path)) / "policy.yaml"
    path.write_text("policy:\n  fail_closed: false\n", encoding="utf-8")
    policy = Policy.from_file(path)
    assert not policy.fail_closed()


def test_crypto_primitives() -> None:
    token = generate_canary_token()
    assert "ACE-CANARY" in token
    assert len(hash_canary(token)) == 16
    noisy = add_laplace_noise(100.0, 1.0)
    assert isinstance(noisy, float)
    blinded = caecator_blind_metadata({"user_id": "alice"})
    assert blinded != {"user_id": "alice"}


def test_session_capability_and_tee() -> None:
    session = Session()
    cap = session.issue_capability("inference")
    assert cap.scope == "inference"
    quote = session.bind_tee("nonce123")
    assert quote.nonce == "nonce123"
    tee = SimulatedTEE()
    sealed = tee.seal(b"secret")
    assert tee.unseal(sealed) == b"secret"


def test_canary_manager() -> None:
    mgr = CanaryManager()
    ctx, token = mgr.inject("context")
    assert token in ctx
    assert mgr.detect_leak(f"leaked {token}") == [token]


def test_egress_kill_and_throttle() -> None:
    ctrl = EgressController(max_violations_before_kill=1)
    v = ctrl.check_egress("bad", ContainmentVerdict.BLOCK)
    assert v == ContainmentVerdict.KILL_SESSION
    assert ctrl.is_killed
    throttled = ctrl.throttle_output("x" * 200)
    assert "THROTTLED" in throttled


def test_verification_json_and_zk() -> None:
    engine = VerificationEngine()
    assert engine.validate_json_output('{"expression":"x","verified":true}') is not None
    assert engine.validate_json_output("not json") is None
    proof = engine.attach_zk_proof({"expression": "x"})
    assert "zk_proof" in proof


def test_math_physics_reject() -> None:
    iface = MathPhysicsInterface()
    assert iface.reject_free_text("password secret key " + "x" * 600)


def test_guardian_llm_judge() -> None:
    g = OutputGuardian()
    assert g.llm_judge_stub("safe output")
    assert not g.llm_judge_stub("weapon design instructions")


def test_flow_effective_output_label() -> None:
    flow = FlowControlEngine()
    with pytest.raises(PermissionError):
        flow.effective_output_label([SECRET, INTERNAL], PUBLIC)


def test_policy_sandbox_tunnel_accessors() -> None:
    policy = Policy()
    assert policy.sandbox_config().resolved_backend() == "auto"
    assert "/inference" in policy.tunnel_allowed_routes()


def test_mock_backend_inspect() -> None:
    from aegis.sandbox.base import SandboxBackendError
    from tests.sandbox_helpers import MockSandboxBackend

    backend = MockSandboxBackend()
    with pytest.raises(SandboxBackendError):
        backend.inspect("nonexistent")


def test_sandbox_manager_mock_backend() -> None:
    manager = SandboxManager(SandboxConfig(backend="mock"))
    facade = manager.create_sandbox()
    assert facade.runtime_name == "mock"


def test_mock_facade_echo_workload() -> None:
    from aegis.execution.mock_model import mock_llm
    from tests.sandbox_helpers import mock_facade

    facade = mock_facade()
    facade.create(INTERNAL)
    output = facade.run_labeled(mock_llm, {"query": "test"}, INTERNAL)
    assert output
    facade.destroy()


def test_compliance_export_pack(tmp_path: object) -> None:
    from pathlib import Path

    from aegis.audit.compliance_export import export_compliance_pack
    from aegis.audit.tamper_proof_log import TamperProofLog
    from aegis.redteam.simulator import ContainmentReport

    out = Path(str(tmp_path)) / "pack"
    audit = TamperProofLog()
    audit.append(
        __import__("aegis.utils.typing", fromlist=["AuditEvent"]).AuditEvent(
            layer="test",
            action="x",
            detail="y",
        ),
    )
    manifest = export_compliance_pack(
        out,
        audit_log=audit,
        benchmark=ContainmentReport(
            scenarios_run=0,
            scenarios_caught=0,
            catch_rate=1.0,
            results=[],
        ),
        policy_path=Path(__file__).resolve().parent.parent / "policy.yaml",
    )
    assert "files" in manifest
    assert (out / "manifest.json").exists()


def test_simulated_tunnel_http_handler() -> None:
    import time
    import urllib.error
    import urllib.request

    cfg = TunnelConfig(require_capability_token=False, allowed_routes=["/health"])
    tunnel = SimulatedTunnel(config=cfg)
    session = Session()
    url = tunnel.open_endpoint(session)
    time.sleep(0.3)
    req = urllib.request.Request(f"{url}/health", method="GET")
    req.add_header("X-Session-ID", session.session_id)
    req.add_header("X-Label", "INTERNAL")
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read().decode()
    assert "status" in body

    bad_req = urllib.request.Request(f"{url}/denied", method="POST", data=b"{}")
    bad_req.add_header("Content-Type", "application/json")
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(bad_req, timeout=5)
    tunnel.close()


def test_capability_token() -> None:
    cap = CapabilityToken.issue("test")
    assert cap.token_id
    assert cap.signature
