"""Shared platform TEE base — AES-GCM sealing bound to attestation measurement."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from aegis.execution.tee_abstraction import AttestationQuote


def derive_seal_key(measurement: str, salt: bytes | None = None) -> bytes:
    """Derive AES-256 seal key from TEE measurement via HKDF."""
    salt = salt or b"ace-aegis-containment-v1"
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"aegis-tee-seal",
    )
    return hkdf.derive(
        bytes.fromhex(measurement) if len(measurement) == 64 else measurement.encode()
    )


@dataclass
class PlatformTEEEnvironment(ABC):
    """Base for hardware-backed TEE environments with measurement-bound sealing."""

    tee_type: str
    _measurement: str | None = field(default=None, repr=False)
    _seal_salt: bytes = field(
        default_factory=lambda: secrets.token_bytes(16), repr=False
    )
    _memory: dict[str, bytes] = field(default_factory=dict, repr=False)
    allow_simulated_fallback: bool = True

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when underlying hardware or platform agent is present."""

    @abstractmethod
    def fetch_hardware_report(self, nonce: str) -> AttestationQuote:
        """Obtain attestation quote from platform (ioctl, sysfs, or agent)."""

    def attest(self, nonce: str | None = None) -> AttestationQuote:
        nonce = nonce or secrets.token_hex(16)
        if self.is_available():
            try:
                quote = self.fetch_hardware_report(nonce)
            except RuntimeError:
                if not self.allow_simulated_fallback:
                    raise
            else:
                self._measurement = quote.measurement
                return quote
        if self.allow_simulated_fallback:
            return self._simulated_quote(nonce)
        msg = f"{self.tee_type} hardware not available and fallback disabled"
        raise RuntimeError(msg)

    def seal(self, plaintext: bytes) -> bytes:
        if self._measurement is None:
            self.attest()
        assert self._measurement is not None
        key = derive_seal_key(self._measurement, self._seal_salt)
        aes = AESGCM(key)
        iv = secrets.token_bytes(12)
        ciphertext = aes.encrypt(iv, plaintext, associated_data=self.tee_type.encode())
        sealed = iv + ciphertext
        slot = hashlib.sha256(sealed).hexdigest()
        self._memory[slot] = sealed
        return sealed

    def unseal(self, ciphertext: bytes) -> bytes:
        if self._measurement is None:
            msg = "Must attest before unseal"
            raise RuntimeError(msg)
        key = derive_seal_key(self._measurement, self._seal_salt)
        aes = AESGCM(key)
        iv, ct = ciphertext[:12], ciphertext[12:]
        return aes.decrypt(iv, ct, associated_data=self.tee_type.encode())

    def bind_session_context(self, session_id: str, labels: dict[str, str]) -> str:
        payload = json.dumps({"session": session_id, "labels": labels}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _simulated_quote(self, nonce: str) -> AttestationQuote:
        seed = f"{self.tee_type}:simulated:{nonce}".encode()
        measurement = hashlib.sha256(seed).hexdigest()
        self._measurement = measurement
        sig_payload = f"{self.tee_type}:{measurement}:{nonce}:simulated"
        return AttestationQuote(
            tee_type=f"{self.tee_type}-simulated",
            measurement=measurement,
            nonce=nonce,
            signature=hashlib.sha256(sig_payload.encode()).hexdigest(),
            hardware_backed=False,
            platform_info={"mode": "simulated_fallback"},
        )


def read_text_file(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def read_binary_file(path: str) -> bytes | None:
    try:
        return Path(path).read_bytes()
    except OSError:
        return None


def quote_from_report_bytes(
    tee_type: str,
    report: bytes,
    nonce: str,
    measurement_offset: int,
    measurement_length: int = 48,
) -> AttestationQuote:
    """Build AttestationQuote from raw hardware report bytes."""
    measurement_bytes = report[
        measurement_offset : measurement_offset + measurement_length
    ]
    measurement = hashlib.sha256(measurement_bytes).hexdigest()
    mac = hashlib.sha256(report + nonce.encode()).hexdigest()
    return AttestationQuote(
        tee_type=tee_type,
        measurement=measurement,
        nonce=nonce,
        signature=mac,
        hardware_backed=True,
        raw_report_b64=base64.b64encode(report).decode(),
        platform_info={"report_length": len(report)},
    )


def quote_from_env_file(
    env_var: str, tee_type: str, nonce: str
) -> AttestationQuote | None:
    path = os.environ.get(env_var)
    if not path:
        return None
    report = read_binary_file(path)
    if not report:
        return None
    measurement = hashlib.sha256(report).hexdigest()
    return AttestationQuote(
        tee_type=tee_type,
        measurement=measurement,
        nonce=nonce,
        signature=hashlib.sha256(report + nonce.encode()).hexdigest(),
        hardware_backed=True,
        raw_report_b64=base64.b64encode(report).decode(),
        platform_info={"source": env_var, "path": path},
    )
