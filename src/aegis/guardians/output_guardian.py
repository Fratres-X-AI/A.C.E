"""Multi-layer output guardian — semantic firewall + anomaly detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from aegis.audit.metrics import shannon_entropy
from aegis.utils.config import GuardianConfig
from aegis.utils.typing import ContainmentVerdict


@dataclass
class GuardianResult:
    """Result of guardian scan."""

    verdict: ContainmentVerdict
    reasons: list[str] = field(default_factory=list)
    canary_triggered: bool = False


@dataclass
class OutputGuardian:
    """Multi-layer egress scanner.

    Layers: PII regex, exfil patterns, entropy anomaly, canary detection,
    optional LLM-judge stub (rule-based fallback).
    """

    config: GuardianConfig = field(default_factory=GuardianConfig)
    canary_tokens: set[str] = field(default_factory=set)
    _entropy_history: list[float] = field(default_factory=list)

    _PII_PATTERNS: list[re.Pattern[str]] = field(
        default_factory=lambda: [
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            re.compile(r"\b\d{16}\b"),  # credit card-ish
        ],
    )

    _EXFIL_PATTERNS: list[re.Pattern[str]] = field(
        default_factory=lambda: [
            re.compile(r"base64:", re.IGNORECASE),
            re.compile(r"BEGIN (RSA |OPENSSH )?PRIVATE KEY"),
            re.compile(r"exfil|dump|leak|steganograph", re.IGNORECASE),
        ],
    )

    def register_canary(self, token: str) -> None:
        self.canary_tokens.add(token)

    def scan(self, output: str) -> GuardianResult:
        reasons: list[str] = []
        canary_hit = False

        for token in self.canary_tokens:
            if token in output:
                canary_hit = True
                reasons.append("canary_token_leaked")

        if self.config.pii_patterns_enabled:
            for pattern in self._PII_PATTERNS:
                if pattern.search(output):
                    reasons.append(f"pii_pattern:{pattern.pattern[:20]}")

        for pattern in self._EXFIL_PATTERNS:
            if pattern.search(output):
                reasons.append(f"exfil_pattern:{pattern.pattern[:20]}")

        entropy = shannon_entropy(output)
        self._entropy_history.append(entropy)
        if entropy > self.config.max_entropy_bits_per_char:
            reasons.append(f"high_entropy:{entropy:.2f}")

        if len(output) > 10_000 and entropy > 4.5:
            reasons.append("steganographic_density_heuristic")

        if self._is_entropy_anomaly(entropy):
            reasons.append("entropy_anomaly")

        if canary_hit:
            return GuardianResult(
                verdict=ContainmentVerdict.KILL_SESSION,
                reasons=reasons,
                canary_triggered=True,
            )
        if reasons:
            if any("high_entropy" in r or "steganographic" in r for r in reasons):
                return GuardianResult(
                    verdict=ContainmentVerdict.BLOCK,
                    reasons=reasons,
                )
            return GuardianResult(verdict=ContainmentVerdict.THROTTLE, reasons=reasons)
        return GuardianResult(verdict=ContainmentVerdict.ALLOW)

    def _is_entropy_anomaly(self, entropy: float) -> bool:
        if len(self._entropy_history) < 3:
            return False
        history = self._entropy_history[:-1]
        mean = sum(history) / len(history)
        variance = sum((h - mean) ** 2 for h in history) / len(history)
        if variance == 0:
            return False
        z = (entropy - mean) / (variance**0.5)
        return bool(z > self.config.anomaly_z_threshold)

    def llm_judge_stub(self, output: str) -> bool:
        """Rule-based fallback when no LLM API configured. True = safe."""
        unsafe_markers = ["weapon", "explosive", "malware", "zero-day"]
        lower = output.lower()
        return bool(not any(m in lower for m in unsafe_markers))
