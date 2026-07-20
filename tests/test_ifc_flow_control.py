"""Tests for information flow control."""

import pytest

from aegis.ifc.agent_planner import AgentPlanner
from aegis.ifc.flow_control import FlowControlEngine, FlowViolationError
from aegis.ifc.labels import PUBLIC, SECRET
from aegis.utils.typing import FlowOperation, SensitivityLevel


def test_no_read_up() -> None:
    flow = FlowControlEngine()
    assert flow.check_flow(SECRET, PUBLIC, FlowOperation.READ) is False
    assert flow.check_flow(PUBLIC, SECRET, FlowOperation.READ) is True


def test_no_write_down() -> None:
    flow = FlowControlEngine()
    assert flow.check_flow(SECRET, PUBLIC, FlowOperation.WRITE) is False
    assert flow.check_flow(PUBLIC, SECRET, FlowOperation.WRITE) is True


def test_enforce_raises() -> None:
    flow = FlowControlEngine()
    with pytest.raises(FlowViolationError):
        flow.enforce(SECRET, PUBLIC, FlowOperation.READ)


def test_agent_planner_blocks_declassification() -> None:
    planner = AgentPlanner(output_clearance=PUBLIC)
    planner.add_step("retrieve", SECRET, doc="classified")
    with pytest.raises(FlowViolationError):
        planner.validate_final_output(PUBLIC)


def test_agent_planner_with_declassification() -> None:
    planner = AgentPlanner(output_clearance=PUBLIC)
    planner.add_step("retrieve", SECRET, doc="classified")
    planner.grant_declassification()
    result = planner.validate_final_output(PUBLIC)
    assert result.sensitivity == SensitivityLevel.PUBLIC


def test_label_join() -> None:
    joined = PUBLIC.join(SECRET)
    assert joined.sensitivity == SECRET.sensitivity
    # Biba meet: mixing lowers integrity
    assert joined.integrity == PUBLIC.integrity


def test_read_requires_dominating_clearance() -> None:
    flow = FlowControlEngine()
    assert SECRET.dominates(PUBLIC)
    assert flow.check_flow(PUBLIC, SECRET, FlowOperation.READ) is True
    assert flow.check_flow(SECRET, PUBLIC, FlowOperation.READ) is False
