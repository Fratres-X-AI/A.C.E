#!/usr/bin/env python3
"""Run internal red-team simulator and print containment effectiveness report."""

from __future__ import annotations

import json

from rich.panel import Panel
from rich.table import Table

from aegis.audit.metrics import ContainmentMetrics
from aegis.redteam.simulator import ContainmentSimulator
from aegis.utils.visualization import console, print_metrics_table


def main() -> None:
    console.print("\n[bold cyan]A.C.E — Containment Benchmark[/bold cyan]\n")

    sim = ContainmentSimulator()
    report = sim.run_all()

    table = Table(title="Red-Team Scenario Results")
    table.add_column("Scenario", style="cyan")
    table.add_column("Caught", style="green")
    table.add_column("Verdict")
    table.add_column("Reasons")
    for r in report.results:
        table.add_row(
            r.name,
            "YES" if r.caught else "NO",
            r.verdict.name,
            ", ".join(r.reasons[:2]) or "-",
        )
    console.print(table)

    console.print(
        Panel(
            f"Scenarios: {report.scenarios_run}\n"
            f"Caught: {report.scenarios_caught}\n"
            f"Catch Rate: {report.catch_rate:.1%}",
            title="Containment Effectiveness",
            border_style="green" if report.catch_rate >= 0.8 else "yellow",
        ),
    )

    metrics = ContainmentMetrics()
    metrics.total_requests = report.scenarios_run
    metrics.exfil_attempts_blocked = report.scenarios_caught
    print_metrics_table(metrics.snapshot())

    artifact = metrics.export_compliance_artifact()
    console.print("\n[bold]Compliance Artifact (JSON):[/bold]")
    console.print(json.dumps({**artifact, "benchmark": report.to_dict()}, indent=2))


if __name__ == "__main__":
    main()
