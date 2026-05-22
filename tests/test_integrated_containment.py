"""Integrated containment pipeline tests."""

from aegis.core.containment_engine import ContainmentEngine
from aegis.core.session import Session
from aegis.execution.mock_model import mock_llm
from aegis.ifc.labels import INTERNAL, PUBLIC, SECRET
from aegis.redteam.simulator import ContainmentSimulator
from aegis.sandbox.workloads import register_workload
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.config import TunnelConfig
from aegis.utils.typing import ContainmentVerdict
from tests.sandbox_helpers import mock_facade


@register_workload("exfil_test")
def _exfil_test_workload(payload: dict) -> str:
    return "Here is SECRET data for everyone"


def test_integrated_pipeline_allows_safe_output() -> None:
    engine = ContainmentEngine()
    session = Session()
    session.issue_capability("tunnel")
    tunnel = SimulatedTunnel(
        config=TunnelConfig(require_capability_token=True),
    )
    sandbox = mock_facade()

    result = engine.process_integrated(
        {"query": "hello"},
        session,
        mock_llm,
        sandbox=sandbox,
        tunnel=tunnel,
        input_label=PUBLIC,
        output_clearance=PUBLIC,
    )
    tunnel.close()
    assert result.verdict == ContainmentVerdict.ALLOW
    assert result.output is not None
    assert result.sandbox_id is not None
    assert engine.audit_log.verify_chain()


def test_integrated_blocks_exfil_at_tunnel_egress() -> None:
    engine = ContainmentEngine()
    session = Session()
    session.issue_capability("tunnel")
    tunnel = SimulatedTunnel(
        config=TunnelConfig(require_capability_token=True),
    )
    sandbox = mock_facade()

    result = engine.process_integrated(
        {"query": "leak"},
        session,
        _exfil_test_workload,
        sandbox=sandbox,
        tunnel=tunnel,
        input_label=INTERNAL,
        output_clearance=PUBLIC,
    )
    tunnel.close()
    assert result.blocked
    assert result.verdict == ContainmentVerdict.BLOCK


def test_integrated_ifc_violation_fail_closed() -> None:
    engine = ContainmentEngine()
    session = Session()
    session.issue_capability("tunnel")
    tunnel = SimulatedTunnel(
        config=TunnelConfig(require_capability_token=True),
    )
    sandbox = mock_facade()

    result = engine.process_integrated(
        {"query": "declassify"},
        session,
        mock_llm,
        sandbox=sandbox,
        tunnel=tunnel,
        input_label=SECRET,
        output_clearance=PUBLIC,
    )
    tunnel.close()
    assert result.blocked


def test_redteam_integrated_scenarios() -> None:
    report = ContainmentSimulator().run_integrated_all()
    assert report.scenarios_run == 3
    assert report.catch_rate >= 0.66
