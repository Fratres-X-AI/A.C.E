"""Supporting crypto primitives — canaries, DP noise, Caecator stubs."""

from __future__ import annotations

import hashlib
import math
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
    """Add Laplace(0, b) noise for differential privacy on exported aggregates.

    Uses inverse-CDF sampling: for u ~ Unif(-0.5, 0.5),
    noise = -b * sign(u) * ln(1 - 2|u|), with b = sensitivity / epsilon.
    """
    if epsilon <= 0:
        msg = "epsilon must be > 0 for differential privacy"
        raise ValueError(msg)
    if sensitivity < 0:
        msg = "sensitivity must be >= 0"
        raise ValueError(msg)
    scale = sensitivity / epsilon
    # Cryptographic RNG → Unif(-0.5, 0.5), excluding endpoints for log stability
    u = secrets.randbits(53) / float(1 << 53) - 0.5
    u = max(min(u, 0.499999999999), -0.499999999999)
    noise = -scale * math.copysign(1.0, u) * math.log(1.0 - 2.0 * abs(u))
    return value + noise


def caecator_blind_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Lightweight tracker blinding stub (not anonymization).

    Replaces string keys/values with truncated hashes. Non-string values pass
    through unchanged — do not treat as a privacy guarantee.
    """
    blinded: dict[str, Any] = {}
    for key, val in metadata.items():
        blind_key = hashlib.sha256(key.encode()).hexdigest()[:12]
        if isinstance(val, str):
            blinded[blind_key] = hashlib.sha256(val.encode()).hexdigest()[:16]
        else:
            blinded[blind_key] = val
    return blinded
