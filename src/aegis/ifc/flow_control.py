"""Information flow enforcement — no read-up, no write-down."""

from __future__ import annotations

from aegis.ifc.labels import SecurityLabel
from aegis.utils.typing import FlowOperation, SensitivityLevel


class FlowViolationError(PermissionError):
    """Raised when an illegal information flow is attempted."""


class FlowControlEngine:
    """Bell-LaPadula-style IFC enforcement engine.

    ADR: Perfect blocking is impossible due to neural compression side channels;
    IFC limits *explicit* label violations and forces declassification gates.
    """

    def check_flow(
        self,
        source: SecurityLabel,
        sink: SecurityLabel,
        operation: FlowOperation,
    ) -> bool:
        """Return True if flow is permitted."""
        if operation == FlowOperation.READ:
            # No read-up: reader sensitivity must be >= source sensitivity
            return sink.sensitivity >= source.sensitivity
        if operation == FlowOperation.WRITE:
            # No write-down: cannot write high-sensitivity data to lower label
            return sink.sensitivity >= source.sensitivity
        if operation == FlowOperation.DECLASSIFY:
            # Declassification always requires explicit gate (checked by policy)
            return sink.sensitivity <= source.sensitivity
        return False

    def enforce(
        self,
        source: SecurityLabel,
        sink: SecurityLabel,
        operation: FlowOperation,
    ) -> None:
        """Raise FlowViolationError if flow is illegal."""
        if not self.check_flow(source, sink, operation):
            raise FlowViolationError(
                f"Illegal {operation.name} flow: "
                f"{source.sensitivity.name} -> {sink.sensitivity.name}",
            )

    def effective_output_label(
        self,
        inputs: list[SecurityLabel],
        output_clearance: SecurityLabel,
    ) -> SecurityLabel:
        """Compute effective label for aggregated inputs."""
        if not inputs:
            return output_clearance
        joined = inputs[0]
        for label in inputs[1:]:
            joined = joined.join(label)
        # Output cannot exceed reader clearance (no read-up on output channel)
        if joined.sensitivity > output_clearance.sensitivity:
            raise FlowViolationError(
                f"Output label {joined.sensitivity.name} exceeds clearance "
                f"{output_clearance.sensitivity.name}",
            )
        return joined

    @staticmethod
    def sensitivity_order(level: SensitivityLevel) -> int:
        return int(level)
