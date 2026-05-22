"""Containment session with crypto + label binding."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from uuid import uuid4

from aegis.crypto.encryption_fields import FieldEncryptionRegistry
from aegis.execution.tee_abstraction import AttestationQuote, TEEEnvironment
from aegis.execution.tee_factory import create_tee_environment
from aegis.ifc.labels import SecurityLabel


@dataclass
class CapabilityToken:
    """Signed execution context stub (capability-style token)."""

    token_id: str
    scope: str
    signature: str

    @classmethod
    def issue(cls, scope: str, secret: bytes | None = None) -> CapabilityToken:
        secret = secret or secrets.token_bytes(32)
        token_id = str(uuid4())
        payload = f"{token_id}:{scope}".encode()
        signature = hashlib.sha256(secret + payload).hexdigest()
        return cls(token_id=token_id, scope=scope, signature=signature)


@dataclass
class Session:
    """Session with encryption context, labels, TEE binding."""

    session_id: str = field(default_factory=lambda: str(uuid4()))
    clearance: SecurityLabel | None = None
    encryption_registry: FieldEncryptionRegistry = field(
        default_factory=FieldEncryptionRegistry,
    )
    tee: TEEEnvironment = field(default_factory=create_tee_environment)
    attestation: AttestationQuote | None = None
    capability: CapabilityToken | None = None
    label_map: dict[str, SecurityLabel] = field(default_factory=dict)
    canary_tokens: list[str] = field(default_factory=list)
    sandbox_id: str | None = None
    tunnel_endpoint_id: str | None = None
    sandbox_label: SecurityLabel | None = None
    sandbox_backend: str | None = None

    def bind_tee(self, nonce: str | None = None) -> AttestationQuote:
        self.attestation = self.tee.attest(nonce)
        return self.attestation

    def issue_capability(self, scope: str) -> CapabilityToken:
        self.capability = CapabilityToken.issue(scope)
        return self.capability

    def set_label(self, key: str, label: SecurityLabel) -> None:
        self.label_map[key] = label

    def inject_canary(self, token: str) -> None:
        self.canary_tokens.append(token)
