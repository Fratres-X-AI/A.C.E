"""Information flow enforcement — BLP confidentiality + Biba integrity."""

from __future__ import annotations

from aegis.ifc.labels import SecurityLabel
from aegis.utils.typing import FlowOperation, SensitivityLevel


class FlowViolationError(PermissionError):
    """Raised when an illegal information flow is attempted."""


class FlowControlEngine:
    """MLS-style IFC: Bell-LaPadula sensitivity + Biba integrity.

    ADR: Perfect blocking is impossible due to neural compression side channels;
    IFC limits *explicit* label violations and forces declassification gates.

    Role convention: ``source`` is the data/object label; ``sink`` is the
    subject clearance (READ) or destination label (WRITE).
    """

    def check_flow(
        self,
        source: SecurityLabel,
        sink: SecurityLabel,
        operation: FlowOperation,
    ) -> bool:
        """Return True if flow is permitted."""
        if operation == FlowOperation.READ:
            # Clearance must dominate data (no read-up on sensitivity,
            # no read of higher-integrity-than-clearance... via dominates:
            # sink.sens >= source.sens AND sink.integ >= source.integ).
            return sink.dominates(source)
        if operation == FlowOperation.WRITE:
            # BLP no write-down on sensitivity. Integrity elevation is blocked
            # via join (min integrity) and DECLASSIFY checks.
            return sink.sensitivity >= source.sensitivity
        if operation == FlowOperation.DECLASSIFY:
            # May only lower/keep sensitivity and integrity
            return (
                sink.sensitivity <= source.sensitivity
                and sink.integrity <= source.integrity
            )
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
                f"{source.sensitivity.name}/{source.integrity.name} -> "
                f"{sink.sensitivity.name}/{sink.integrity.name}",
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
        if not output_clearance.dominates(joined):
            raise FlowViolationError(
                f"Output label {joined.sensitivity.name}/{joined.integrity.name} "
                f"exceeds clearance "
                f"{output_clearance.sensitivity.name}/"
                f"{output_clearance.integrity.name}",
            )
        return joined

    @staticmethod
    def sensitivity_order(level: SensitivityLevel) -> int:
        return int(level)
