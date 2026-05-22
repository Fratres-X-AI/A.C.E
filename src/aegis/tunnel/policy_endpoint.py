"""Policy-controlled tunnel endpoint with allowlist and rate limits."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from aegis.core.session import Session
from aegis.ifc.flow_control import FlowControlEngine, FlowViolationError
from aegis.ifc.labels import SecurityLabel
from aegis.utils.config import TunnelConfig
from aegis.utils.typing import AuditEvent, FlowOperation, TunnelRequest


class TunnelPolicyError(PermissionError):
    """Raised when tunnel policy denies a request."""


@dataclass
class PolicyControlledEndpoint:
    """Enforces route allowlist, capability tokens, IFC, and rate limits."""

    config: TunnelConfig = field(default_factory=TunnelConfig)
    endpoint_id: str = "policy-endpoint"
    _flow: FlowControlEngine = field(default_factory=FlowControlEngine)
    _request_times: deque[float] = field(default_factory=deque)
    _audit_events: list[AuditEvent] = field(default_factory=list)

    def _check_rate_limit(self) -> None:
        now = time.monotonic()
        while self._request_times and now - self._request_times[0] > 60.0:
            self._request_times.popleft()
        if len(self._request_times) >= self.config.max_requests_per_minute:
            msg = "Tunnel rate limit exceeded"
            raise TunnelPolicyError(msg)
        self._request_times.append(now)

    def validate_route(self, route: str) -> None:
        if route not in self.config.allowed_routes:
            msg = f"Route {route!r} not in allowlist"
            raise TunnelPolicyError(msg)

    def validate_capability(self, session: Session) -> None:
        if not self.config.require_capability_token:
            return
        if session.capability is None:
            msg = "Missing capability token"
            raise TunnelPolicyError(msg)

    def validate_ingress(
        self,
        session: Session,
        label: SecurityLabel,
        route: str = "/inference",
    ) -> bool:
        self._check_rate_limit()
        self.validate_route(route)
        self.validate_capability(session)
        try:
            self._flow.enforce(label, label, FlowOperation.READ)
        except FlowViolationError as exc:
            msg = str(exc)
            raise TunnelPolicyError(msg) from exc
        self.audit_event(
            AuditEvent(
                layer="tunnel",
                action="ingress_allowed",
                detail=f"route={route} session={session.session_id}",
            ),
        )
        return True

    def validate_egress(self, output: str, clearance: SecurityLabel) -> bool:
        if "SECRET" in output.upper() and clearance.sensitivity.name == "PUBLIC":
            self.audit_event(
                AuditEvent(
                    layer="tunnel",
                    action="egress_denied",
                    detail="cross-boundary exfil blocked",
                ),
            )
            return False
        self.audit_event(
            AuditEvent(
                layer="tunnel",
                action="egress_allowed",
                detail=f"bytes={len(output)}",
            ),
        )
        return True

    def forward_request(self, request: TunnelRequest) -> dict[str, Any]:
        self.validate_route(request.route)
        return {"status": "forwarded", "route": request.route, "label": request.label}

    def audit_event(self, event: AuditEvent) -> None:
        self._audit_events.append(event)

    @property
    def audit_events(self) -> list[AuditEvent]:
        return list(self._audit_events)
