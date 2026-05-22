"""Supporting crypto primitives — canaries, DP noise, Caecator stubs."""

from __future__ import annotations

import hashlib
import secrets
import string
from typing import Any


def generate_canary_token(prefix: str = "ACE-CANARY", length: int = 32) -> str:
    """Generate a unique canary token for honeypot injection."""
    alphabet = string.ascii_letters + string.digits
    body = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}-{body}"


def hash_canary(token: str) -> str:
    """Hash canary for audit without storing plaintext in logs."""
    return hashlib.sha256(token.encode()).hexdigest()[:16]


def add_laplace_noise(value: float, epsilon: float, sensitivity: float = 1.0) -> float:
    """Add Laplace noise for differential privacy on exported aggregates."""
    import random

    if epsilon <= 0:
        return value
    scale = sensitivity / epsilon
    u = random.random() - 0.5
    noise = -scale * (1 if u < 0 else -1) * (1 - 2 * abs(u))
    return value + noise


def caecator_blind_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Caecator-style lightweight tracker blinding stub.

    Replaces identifiable keys with hashed surrogates for fusion resistance.
    """
    blinded: dict[str, Any] = {}
    for key, val in metadata.items():
        blind_key = hashlib.sha256(key.encode()).hexdigest()[:12]
        if isinstance(val, str):
            blinded[blind_key] = hashlib.sha256(val.encode()).hexdigest()[:16]
        else:
            blinded[blind_key] = val
    return blinded
