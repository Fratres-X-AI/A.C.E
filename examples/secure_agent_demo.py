#!/usr/bin/env python3
"""Demonstrate label propagation through agent planning."""

from __future__ import annotations

from aegis.ifc.agent_planner import AgentPlanner
from aegis.ifc.labels import PUBLIC, SECRET
from aegis.utils.visualization import console, print_layer_activation


def main() -> None:
    console.print("\n[bold cyan]A.C.E — Secure Agent Demo[/bold cyan]\n")

    planner = AgentPlanner(output_clearance=PUBLIC)

    print_layer_activation("Agent: Plan", "PASS", "Step 1: retrieve public FAQ")
    planner.add_step("retrieve_faq", PUBLIC, source="faq_db")

    print_layer_activation("Agent: Plan", "PASS", "Step 2: retrieve SECRET intel")
    planner.add_step("retrieve_intel", SECRET, source="classified_db")
    planner.write_memory("intel", "Project Alpha coordinates", SECRET)

    print_layer_activation(
        "Agent: Memory", "PASS", "High-sensitivity context stored with SECRET label"
    )

    console.print(
        "\n[bold yellow]Attempting final output at PUBLIC clearance "
        "without declassification...[/bold yellow]"
    )
    try:
        planner.validate_final_output(PUBLIC)
        console.print("[red]UNEXPECTED: leak allowed[/red]")
    except PermissionError as exc:
        print_layer_activation("IFC: Flow Control", "BLOCK", str(exc))

    console.print(
        "\n[bold green]Granting explicit declassification gate...[/bold green]"
    )
    planner.grant_declassification()
    label = planner.validate_final_output(PUBLIC)
    print_layer_activation(
        "IFC: Declassification", "PASS", f"Output label={label.sensitivity.name}"
    )

    console.print("\n[bold]Reading public memory only:[/bold]")
    planner.write_memory("faq", "How to reset password", PUBLIC)
    slot = planner.read_memory("faq", PUBLIC)
    console.print(f"  Retrieved: {slot.value} [{slot.label.sensitivity.name}]")


if __name__ == "__main__":
    main()
