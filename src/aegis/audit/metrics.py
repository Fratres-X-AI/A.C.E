"""Containment effectiveness metrics and compliance export."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def shannon_entropy(text: str) -> float:
    """Compute Shannon entropy (bits per character) of text."""
    if not text:
        return 0.0
    counts = Counter(text)
    length = len(text)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


@dataclass
class ContainmentMetrics:
    """Real-time containment effectiveness metrics."""

    exfil_attempts_blocked: int = 0
    label_violations: int = 0
    canary_triggers: int = 0
    guardian_blocks: int = 0
    throttled_sessions: int = 0
    killed_sessions: int = 0
    total_requests: int = 0
    output_entropy_samples: list[float] = field(default_factory=list)

    def record_output_entropy(self, text: str) -> None:
        self.output_entropy_samples.append(shannon_entropy(text))

    @property
    def containment_effectiveness_score(self) -> float:
        """Score in [0, 1]: fraction of adversarial/violation events caught."""
        if self.total_requests == 0:
            return 1.0
        caught = (
            self.exfil_attempts_blocked
            + self.label_violations
            + self.canary_triggers
            + self.guardian_blocks
        )
        return min(1.0, caught / max(1, self.total_requests))

    @property
    def avg_output_entropy(self) -> float:
        if not self.output_entropy_samples:
            return 0.0
        return sum(self.output_entropy_samples) / len(self.output_entropy_samples)

    def snapshot(self) -> dict[str, float | int]:
        return {
            "exfil_attempts_blocked": self.exfil_attempts_blocked,
            "label_violations": self.label_violations,
            "canary_triggers": self.canary_triggers,
            "guardian_blocks": self.guardian_blocks,
            "throttled_sessions": self.throttled_sessions,
            "killed_sessions": self.killed_sessions,
            "total_requests": self.total_requests,
            "containment_effectiveness_score": round(
                self.containment_effectiveness_score,
                4,
            ),
            "avg_output_entropy": round(self.avg_output_entropy, 4),
        }

    def export_compliance_artifact(self, path: str | None = None) -> dict[str, Any]:
        """Export auditable compliance artifact for DIU/gov submissions."""
        artifact = {
            "framework": "A.C.E Aegis Containment Engine",
            "version": "0.1.0",
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "metrics": self.snapshot(),
            "philosophy": "assume_breach_contain_egress",
        }
        if path:
            from pathlib import Path

            Path(path).write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        return artifact
