"""Tests for red-team simulator."""

from aegis.redteam.simulator import ContainmentSimulator


def test_simulator_runs_scenarios() -> None:
    sim = ContainmentSimulator()
    report = sim.run_all()
    assert report.scenarios_run >= 5
    assert report.catch_rate > 0.5


def test_report_to_dict() -> None:
    sim = ContainmentSimulator()
    report = sim.run_all()
    data = report.to_dict()
    assert "catch_rate" in data
    assert "results" in data
