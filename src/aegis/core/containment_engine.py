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
from aegis.sandbox.environment import SandboxEnvironment
from aegis.tunnel.gateway import TunnelGateway
from aegis.tunnel.policy_endpoint import TunnelPolicyError
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

        payload = self._encrypt_fields(session, payload, sensitive_keys)

        if input_label and output_clearance:
            ifc_block = self._enforce_ifc(input_label, output_clearance)
            if ifc_block is not None:
                return ifc_block

        for token in session.canary_tokens:
            self.guardian.register_canary(token)

        assert self.runner is not None
        raw_output = self.runner.run(model_fn, payload)

        output, final_verdict, is_blocked, reasons = self._finalize_egress(
            raw_output,
            reasons,
        )

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
            blocked=is_blocked,
            reasons=reasons,
            metrics_snapshot=self.metrics.snapshot(),
            audit_event_count=len(self.audit_log.entries),
        )

    def process_integrated(
        self,
        payload: dict[str, Any],
        session: Session,
        workload_fn: Callable[[dict[str, Any]], str],
        *,
        sandbox: SandboxEnvironment,
        tunnel: TunnelGateway,
        input_label: SecurityLabel,
        output_clearance: SecurityLabel,
        sensitive_keys: set[str] | None = None,
    ) -> ContainmentResult:
        """Integrated pipeline through tunnel ingress and sandbox runtime."""
        self.metrics.total_requests += 1
        reasons: list[str] = []
        sensitive_keys = sensitive_keys or set()

        if session.attestation is None:
            session.bind_tee()

        self.audit_log.append(
            AuditEvent(
                layer="core",
                action="integrated_start",
                detail=session.session_id,
            ),
        )

        payload = self._encrypt_fields(session, payload, sensitive_keys)

        ifc_block = self._enforce_ifc(input_label, output_clearance)
        if ifc_block is not None:
            return ifc_block

        ingress_block = self._validate_tunnel_ingress(tunnel, session, input_label)
        if ingress_block is not None:
            return ingress_block

        endpoint_url = tunnel.open_endpoint(session)
        session.tunnel_endpoint_id = tunnel.endpoint_id
        self.audit_log.append(
            AuditEvent(layer="tunnel", action="endpoint_open", detail=endpoint_url),
        )

        sandbox_info = sandbox.create(input_label)
        session.sandbox_id = sandbox_info.sandbox_id
        session.sandbox_label = input_label
        self.audit_log.append(
            AuditEvent(
                layer="sandbox",
                action="create",
                detail=sandbox_info.sandbox_id,
                metadata={"runtime": sandbox_info.runtime},
            ),
        )

        for token in session.canary_tokens:
            self.guardian.register_canary(token)

        raw_output, workload_block = self._run_sandbox_workload(
            sandbox,
            workload_fn,
            payload,
            input_label,
        )
        if workload_block is not None:
            return workload_block

        output, final_verdict, is_blocked, reasons = self._finalize_egress(
            raw_output,
            reasons,
        )

        output, final_verdict, is_blocked, reasons = self._validate_tunnel_egress(
            tunnel,
            output,
            output_clearance,
            final_verdict,
            blocked=is_blocked,
            reasons=reasons,
        )

        sandbox.destroy()
        self.audit_log.append(
            AuditEvent(
                layer="core",
                action="integrated_complete",
                detail=f"verdict={final_verdict.name}",
                metadata={"reasons": reasons},
            ),
        )

        return ContainmentResult(
            output=output,
            verdict=final_verdict,
            blocked=is_blocked,
            reasons=reasons,
            metrics_snapshot=self.metrics.snapshot(),
            audit_event_count=len(self.audit_log.entries),
            sandbox_id=session.sandbox_id,
            tunnel_endpoint_id=session.tunnel_endpoint_id,
        )

    def _encrypt_fields(
        self,
        session: Session,
        payload: dict[str, Any],
        sensitive_keys: set[str],
    ) -> dict[str, Any]:
        registry: FieldEncryptionRegistry = session.encryption_registry
        if not sensitive_keys:
            return payload
        encrypted_payload = registry.encrypt_payload_fields(payload, sensitive_keys)
        self.audit_log.append(
            AuditEvent(
                layer="crypto",
                action="field_encrypt",
                detail=str(list(sensitive_keys)),
            ),
        )
        return registry.decrypt_payload_fields(encrypted_payload)

    def _enforce_ifc(
        self,
        input_label: SecurityLabel,
        output_clearance: SecurityLabel,
    ) -> ContainmentResult | None:
        try:
            self.flow.enforce(input_label, output_clearance, FlowOperation.READ)
        except FlowViolationError as exc:
            self.metrics.label_violations += 1
            self.audit_log.append(
                AuditEvent(layer="ifc", action="flow_violation", detail=str(exc)),
            )
            if self.policy.fail_closed():
                return self._blocked_result([str(exc)])
        return None

    def _validate_tunnel_ingress(
        self,
        tunnel: TunnelGateway,
        session: Session,
        input_label: SecurityLabel,
    ) -> ContainmentResult | None:
        try:
            tunnel.validate_ingress(session, input_label)
            tunnel.audit_event(
                AuditEvent(
                    layer="tunnel",
                    action="ingress_ok",
                    detail=session.session_id,
                ),
            )
        except TunnelPolicyError as exc:
            self.audit_log.append(
                AuditEvent(layer="tunnel", action="ingress_denied", detail=str(exc)),
            )
            return self._blocked_result([str(exc)])
        return None

    def _run_sandbox_workload(
        self,
        sandbox: SandboxEnvironment,
        workload_fn: Callable[[dict[str, Any]], str],
        payload: dict[str, Any],
        input_label: SecurityLabel,
    ) -> tuple[str, ContainmentResult | None]:
        try:
            raw_output = sandbox.run_labeled(workload_fn, payload, input_label)
            self.audit_log.append(
                AuditEvent(layer="sandbox", action="workload_complete", detail="ok"),
            )
        except (PermissionError, MemoryError) as exc:
            self.audit_log.append(
                AuditEvent(layer="sandbox", action="workload_denied", detail=str(exc)),
            )
            sandbox.destroy()
            return "", self._blocked_result([str(exc)])
        return raw_output, None

    def _finalize_egress(
        self,
        raw_output: str,
        reasons: list[str],
    ) -> tuple[str | None, ContainmentVerdict, bool, list[str]]:
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

        return output, final_verdict, blocked, reasons

    def _validate_tunnel_egress(
        self,
        tunnel: TunnelGateway,
        output: str | None,
        output_clearance: SecurityLabel,
        final_verdict: ContainmentVerdict,
        *,
        blocked: bool,
        reasons: list[str],
    ) -> tuple[str | None, ContainmentVerdict, bool, list[str]]:
        if output and not tunnel.validate_egress(output, output_clearance):
            self.audit_log.append(
                AuditEvent(layer="tunnel", action="egress_denied", detail="policy"),
            )
            reasons.append("Tunnel egress policy denied output")
            self.metrics.exfil_attempts_blocked += 1
            return None, ContainmentVerdict.BLOCK, True, reasons
        if output:
            tunnel.audit_event(
                AuditEvent(layer="tunnel", action="egress_ok", detail="allowed"),
            )
        return output, final_verdict, blocked, reasons

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
