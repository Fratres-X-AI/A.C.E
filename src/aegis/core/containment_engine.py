"""Central containment engine — orchestrates all layers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aegis.audit.metrics import ContainmentMetrics
from aegis.audit.tamper_proof_log import TamperProofLog
from aegis.core.policy import Policy
from aegis.core.session import Session
from aegis.crypto.encryption_fields import FieldEncryptionRegistry
from aegis.execution.instrumented_runner import InstrumentedRunner
from aegis.guardians.egress_controller import EgressController
from aegis.guardians.output_guardian import OutputGuardian
from aegis.guardians.verification import VerificationEngine
from aegis.ifc.flow_control import FlowControlEngine, FlowViolationError
from aegis.ifc.labels import SecurityLabel
from aegis.utils.typing import (
    AuditEvent,
    ContainmentResult,
    ContainmentVerdict,
    FlowOperation,
)


@dataclass
class ContainmentEngine:
    """Main orchestrator — assume breach, contain egress, measure everything."""

    policy: Policy = field(default_factory=Policy)
    audit_log: TamperProofLog = field(default_factory=TamperProofLog)
    metrics: ContainmentMetrics = field(default_factory=ContainmentMetrics)
    flow: FlowControlEngine = field(default_factory=FlowControlEngine)
    guardian: OutputGuardian = field(default_factory=OutputGuardian)
    egress: EgressController = field(default_factory=EgressController)
    verification: VerificationEngine = field(default_factory=VerificationEngine)
    runner: InstrumentedRunner | None = None

    def __post_init__(self) -> None:
        self.guardian.config = self.policy.policy.guardian
        self.egress.max_bytes_per_minute = self.policy.rate_limit_bytes_per_minute()
        self.runner = InstrumentedRunner(audit_log=self.audit_log)

    def process(
        self,
        payload: dict[str, Any],
        session: Session,
        model_fn: Callable[[dict[str, Any]], str],
        *,
        input_label: SecurityLabel | None = None,
        output_clearance: SecurityLabel | None = None,
        sensitive_keys: set[str] | None = None,
    ) -> ContainmentResult:
        """Process input through full containment pipeline."""
        self.metrics.total_requests += 1
        reasons: list[str] = []
        sensitive_keys = sensitive_keys or set()

        if session.attestation is None:
            session.bind_tee()

        self.audit_log.append(
            AuditEvent(layer="core", action="process_start", detail=session.session_id),
        )

        # Ingress: field encryption
        registry: FieldEncryptionRegistry = session.encryption_registry
        if sensitive_keys:
            encrypted_payload = registry.encrypt_payload_fields(payload, sensitive_keys)
            self.audit_log.append(
                AuditEvent(
                    layer="crypto",
                    action="field_encrypt",
                    detail=str(list(sensitive_keys)),
                ),
            )
            payload = registry.decrypt_payload_fields(encrypted_payload)

        # IFC check
        if input_label and output_clearance:
            try:
                self.flow.enforce(input_label, output_clearance, FlowOperation.READ)
            except FlowViolationError as exc:
                self.metrics.label_violations += 1
                self.audit_log.append(
                    AuditEvent(layer="ifc", action="flow_violation", detail=str(exc)),
                )
                if self.policy.fail_closed():
                    return self._blocked_result([str(exc)])

        # Register canaries with guardian
        for token in session.canary_tokens:
            self.guardian.register_canary(token)

        # Execution in instrumented runner
        assert self.runner is not None
        raw_output = self.runner.run(model_fn, payload)

        # Egress: guardian scan
        guard_result = self.guardian.scan(raw_output)
        if guard_result.canary_triggered:
            self.metrics.canary_triggers += 1
        if guard_result.verdict != ContainmentVerdict.ALLOW:
            self.metrics.guardian_blocks += 1
            if any(
                "exfil" in r or "entropy" in r or "steganographic" in r
                for r in guard_result.reasons
            ):
                self.metrics.exfil_attempts_blocked += 1
        reasons.extend(guard_result.reasons)

        # Egress controller
        final_verdict = self.egress.check_egress(raw_output, guard_result.verdict)
        if final_verdict == ContainmentVerdict.KILL_SESSION:
            self.metrics.killed_sessions += 1
            self.egress.kill_session()
        elif final_verdict == ContainmentVerdict.THROTTLE:
            self.metrics.throttled_sessions += 1

        output: str | None = raw_output
        blocked = False
        if final_verdict == ContainmentVerdict.KILL_SESSION:
            output = None
            blocked = True
        elif final_verdict in {ContainmentVerdict.BLOCK, ContainmentVerdict.THROTTLE}:
            output = (
                self.egress.throttle_output(raw_output)
                if final_verdict == ContainmentVerdict.THROTTLE
                else None
            )
            blocked = final_verdict == ContainmentVerdict.BLOCK

        if output:
            self.metrics.record_output_entropy(output)

        self.audit_log.append(
            AuditEvent(
                layer="core",
                action="process_complete",
                detail=f"verdict={final_verdict.name}",
                metadata={"reasons": reasons},
            ),
        )

        return ContainmentResult(
            output=output,
            verdict=final_verdict,
            blocked=blocked,
            reasons=reasons,
            metrics_snapshot=self.metrics.snapshot(),
            audit_event_count=len(self.audit_log.entries),
        )

    def _blocked_result(self, reasons: list[str]) -> ContainmentResult:
        self.metrics.label_violations += 1
        return ContainmentResult(
            output=None,
            verdict=ContainmentVerdict.BLOCK,
            blocked=True,
            reasons=reasons,
            metrics_snapshot=self.metrics.snapshot(),
            audit_event_count=len(self.audit_log.entries),
        )
