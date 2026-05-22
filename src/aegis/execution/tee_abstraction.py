"""TEE / confidential compute abstraction and attestation."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class AttestationQuote:
    """Remote attestation quote from a confidential compute environment."""

    tee_type: str
    measurement: str
    nonce: str
    signature: str
    hardware_backed: bool = False
    raw_report_b64: str | None = None
    platform_info: dict[str, Any] = field(default_factory=dict)


class TEEEnvironment(Protocol):
    """Protocol for confidential compute environments.

    Implementations: Intel TDX, AMD SEV-SNP, NVIDIA CC, Azure/AWS CC VMs.
    Use ``create_tee_environment()`` from ``tee_factory`` for auto-selection.
    """

    def attest(self, nonce: str | None = None) -> AttestationQuote: ...

    def seal(self, plaintext: bytes) -> bytes: ...

    def unseal(self, ciphertext: bytes) -> bytes: ...

    def bind_session_context(self, session_id: str, labels: dict[str, str]) -> str: ...


@dataclass
class SimulatedTEE:
    """Simulated TEE for development — not hardware-backed."""

    tee_type: str = "simulated"
    _seal_key: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    _memory: dict[str, bytes] = field(default_factory=dict)

    def attest(self, nonce: str | None = None) -> AttestationQuote:
        nonce = nonce or secrets.token_hex(16)
        measurement = hashlib.sha256(self._seal_key).hexdigest()
        sig_payload = f"{self.tee_type}:{measurement}:{nonce}"
        signature = hashlib.sha256(sig_payload.encode()).hexdigest()
        return AttestationQuote(
            tee_type=self.tee_type,
            measurement=measurement,
            nonce=nonce,
            signature=signature,
            hardware_backed=False,
            platform_info={"mode": "simulated"},
        )

    def seal(self, plaintext: bytes) -> bytes:
        key = self._seal_key
        sealed = bytes(b ^ key[i % len(key)] for i, b in enumerate(plaintext))
        slot = hashlib.sha256(sealed).hexdigest()
        self._memory[slot] = sealed
        return sealed

    def unseal(self, ciphertext: bytes) -> bytes:
        key = self._seal_key
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(ciphertext))

    def bind_session_context(self, session_id: str, labels: dict[str, str]) -> str:
        """Cryptographically bind labels + session to attestation."""
        payload = json.dumps({"session": session_id, "labels": labels}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()


def verify_attestation_stub(quote: AttestationQuote) -> bool:
    """Stub for external attestation verification (DCAP / AMD KDS).

    Replace with:
    - Intel: ``sgx_dcap_quoteverify`` or Azure Attestation SDK
    - AMD: ``sev-tool verify`` or guest policy check against VCEK
    """
    if not quote.measurement or not quote.signature:
        return False
    if quote.hardware_backed and quote.raw_report_b64:
        return len(quote.raw_report_b64) > 64
    return quote.tee_type.endswith("-simulated") or quote.tee_type == "simulated"
