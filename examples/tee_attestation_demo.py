#!/usr/bin/env python3
"""Demonstrate TEE platform detection, attestation, and measurement-bound sealing."""

from __future__ import annotations

from aegis.execution.tee_abstraction import SimulatedTEE, verify_attestation_stub
from aegis.execution.tee_factory import create_tee_environment, detect_platform
from aegis.utils.visualization import console, print_layer_activation


def main() -> None:
    console.print("\n[bold cyan]A.C.E — TEE Attestation Demo[/bold cyan]\n")

    platform = detect_platform()
    print_layer_activation(
        "TEE: Detection", "PASS", f"Detected platform={platform.value}"
    )

    tee = create_tee_environment(platform)
    quote = tee.attest("ace-demo-nonce-001")

    hw = "hardware" if quote.hardware_backed else "simulated"
    print_layer_activation(
        "TEE: Attestation",
        "PASS",
        f"type={quote.tee_type}, backing={hw}",
    )
    console.print(f"  Measurement: {quote.measurement[:32]}...")
    console.print(f"  Nonce:       {quote.nonce}")
    if quote.platform_info:
        console.print(f"  Platform:    {quote.platform_info}")

    verified = verify_attestation_stub(quote)
    print_layer_activation(
        "TEE: Verification (stub)",
        "PASS" if verified else "BLOCK",
        "DCAP/KDS stub check",
    )

    plaintext = b"Classified model weights fragment"
    sealed = tee.seal(plaintext)
    recovered = tee.unseal(sealed)
    assert recovered == plaintext
    seal_mode = "XOR (dev simulated)" if isinstance(tee, SimulatedTEE) else "AES-GCM"
    print_layer_activation(
        "TEE: Seal/Unseal",
        "PASS",
        f"{seal_mode} bound to measurement ({len(sealed)} bytes sealed)",
    )

    binding = tee.bind_session_context(
        "demo-session",
        {"input": "SECRET", "output": "INTERNAL"},
    )
    console.print(f"\n[bold]Session binding hash:[/bold] {binding[:24]}...")


if __name__ == "__main__":
    main()
