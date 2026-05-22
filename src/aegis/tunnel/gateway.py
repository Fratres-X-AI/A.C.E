"""Tunnel gateway protocol."""

from __future__ import annotations

from typing import Any, Protocol

from aegis.core.session import Session
from aegis.ifc.labels import SecurityLabel
from aegis.utils.typing import AuditEvent, TunnelRequest


class TunnelGateway(Protocol):
    """Protocol for MCP-style secure tunnel gateways."""

    endpoint_id: str

    def open_endpoint(self, session: Session) -> str: ...

    def close(self) -> None: ...

    def validate_ingress(
        self,
        session: Session,
        label: SecurityLabel,
        route: str = "/inference",
    ) -> bool: ...

    def validate_egress(
        self,
        output: str,
        clearance: SecurityLabel,
    ) -> bool: ...

    def forward_request(self, request: TunnelRequest) -> dict[str, Any]: ...

    def audit_event(self, event: AuditEvent) -> None: ...
