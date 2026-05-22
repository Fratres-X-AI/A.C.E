"""Structured output enforcement, consensus, ZK proof hooks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError


class ZKProofHook(Protocol):
    """Hook for external zero-knowledge proof generation."""

    def generate_proof(self, statement: dict[str, Any]) -> str: ...


@dataclass
class NoOpZKHook:
    """Stub ZK proof hook — returns attestation placeholder."""

    def generate_proof(self, statement: dict[str, Any]) -> str:
        return f"zk-stub:{hash(json.dumps(statement, sort_keys=True)) % 10**8:08d}"


class StructuredMathOutput(BaseModel):
    """JSON schema for verified math outputs."""

    expression: str
    verified: bool
    variables: list[str] = []


@dataclass
class VerificationEngine:
    """Structured output enforcement and ensemble consensus."""

    zk_hook: ZKProofHook = field(default_factory=NoOpZKHook)
    consensus_threshold: float = 0.66

    def enforce_schema(self, data: dict[str, Any]) -> StructuredMathOutput:
        return StructuredMathOutput.model_validate(data)

    def validate_json_output(self, raw: str) -> StructuredMathOutput | None:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return self.enforce_schema(parsed)
        except (json.JSONDecodeError, ValidationError):
            return None
        return None

    def ensemble_consensus(self, outputs: list[str]) -> tuple[bool, str]:
        """N-of-M agreement — diverse models must agree for high-stakes outputs."""
        if not outputs:
            return False, ""
        from collections import Counter

        counts = Counter(outputs)
        winner, count = counts.most_common(1)[0]
        agreement = count / len(outputs)
        return agreement >= self.consensus_threshold, winner

    def attach_zk_proof(self, statement: dict[str, Any]) -> dict[str, Any]:
        proof = self.zk_hook.generate_proof(statement)
        return {**statement, "zk_proof": proof}
