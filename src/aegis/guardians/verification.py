"""Structured output enforcement, consensus, proof placeholders."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    computed_field,
    model_validator,
)


class ProofHook(Protocol):
    """Hook for external proof generation (ZK or otherwise)."""

    def generate_proof(self, statement: dict[str, Any]) -> str: ...


# Backward-compatible alias
ZKProofHook = ProofHook


@dataclass
class ProofPlaceholderHook:
    """Non-cryptographic placeholder — not a ZK proof."""

    def generate_proof(self, statement: dict[str, Any]) -> str:
        digest = hashlib.sha256(
            json.dumps(statement, sort_keys=True).encode(),
        ).hexdigest()[:16]
        return f"proof-placeholder:{digest}"


# Deprecated name kept for imports
NoOpZKHook = ProofPlaceholderHook


class StructuredMathOutput(BaseModel):
    """JSON schema for parsed math outputs (not proven correct)."""

    expression: str
    sympy_parsed: bool = Field(
        default=False,
        description="True if SymPy parsed the expression — not a proof",
    )
    variables: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_verified(cls, data: Any) -> Any:
        if isinstance(data, dict) and "sympy_parsed" not in data and "verified" in data:
            return {**data, "sympy_parsed": bool(data["verified"])}
        return data

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verified(self) -> bool:
        """Deprecated alias for sympy_parsed (parse success, not a proof)."""
        return self.sympy_parsed


@dataclass
class VerificationEngine:
    """Structured output enforcement and ensemble consensus."""

    proof_hook: ProofHook = field(default_factory=ProofPlaceholderHook)
    consensus_threshold: float = 0.66

    @property
    def zk_hook(self) -> ProofHook:
        return self.proof_hook

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
        """N-of-M agreement — exact string match only (prototype)."""
        if not outputs:
            return False, ""
        counts = Counter(outputs)
        winner, count = counts.most_common(1)[0]
        agreement = count / len(outputs)
        return agreement >= self.consensus_threshold, winner

    def attach_proof_placeholder(self, statement: dict[str, Any]) -> dict[str, Any]:
        """Attach a non-cryptographic placeholder string (not a ZK proof)."""
        proof = self.proof_hook.generate_proof(statement)
        return {**statement, "proof_placeholder": proof}

    def attach_zk_proof(self, statement: dict[str, Any]) -> dict[str, Any]:
        """Deprecated alias for :meth:`attach_proof_placeholder`."""
        result = self.attach_proof_placeholder(statement)
        result["zk_proof"] = result["proof_placeholder"]
        return result
