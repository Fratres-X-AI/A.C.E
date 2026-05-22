"""Canary token injection and detection."""

from __future__ import annotations

from dataclasses import dataclass, field

from aegis.crypto.primitives import generate_canary_token, hash_canary


@dataclass
class CanaryManager:
    """Inject honeypot tokens and track detections."""

    active_canaries: dict[str, str] = field(default_factory=dict)

    def inject(self, context: str, prefix: str = "ACE-CANARY") -> tuple[str, str]:
        """Inject canary into context; return (modified_context, token)."""
        token = generate_canary_token(prefix=prefix)
        self.active_canaries[token] = hash_canary(token)
        marker = f"[CANARY:{token}]"
        return f"{context}\n{marker}", token

    def detect_leak(self, output: str) -> list[str]:
        """Return list of leaked canary tokens."""
        leaked = [t for t in self.active_canaries if t in output]
        return leaked

    def count_active(self) -> int:
        return len(self.active_canaries)
