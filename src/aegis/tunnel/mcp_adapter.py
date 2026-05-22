"""MCP-style secure RPC adapter for guarded sandbox access."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from aegis.core.session import Session
from aegis.ifc.labels import SecurityLabel
from aegis.tunnel.policy_endpoint import PolicyControlledEndpoint, TunnelPolicyError
from aegis.utils.config import TunnelConfig
from aegis.utils.typing import AuditEvent, TunnelRequest


@dataclass
class MCPEndpointRegistry:
    """Authenticated endpoint registry for MCP-style clients."""

    endpoints: dict[str, str] = field(default_factory=dict)

    def register(self, name: str, url: str, capability_token: str) -> None:
        self.endpoints[name] = url
        self._tokens: dict[str, str] = getattr(self, "_tokens", {})
        self._tokens[name] = capability_token

    def authenticate(self, name: str, token: str) -> bool:
        tokens: dict[str, str] = getattr(self, "_tokens", {})
        return tokens.get(name) == token


@dataclass
class MCPAdapter:
    """JSON-RPC shaped adapter mapping external requests to sandbox RPC."""

    config: TunnelConfig = field(default_factory=TunnelConfig)
    endpoint_id: str = field(default_factory=lambda: f"mcp-{uuid4().hex[:8]}")
    registry: MCPEndpointRegistry = field(default_factory=MCPEndpointRegistry)
    _policy: PolicyControlledEndpoint = field(init=False)
    _rpc_handlers: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._policy = PolicyControlledEndpoint(
            config=self.config,
            endpoint_id=self.endpoint_id,
        )

    def open_endpoint(self, session: Session) -> str:
        session.tunnel_endpoint_id = self.endpoint_id
        url = f"mcp://localhost/{self.endpoint_id}"
        if session.capability is None:
            session.issue_capability("tunnel")
        token = session.capability.signature if session.capability else uuid4().hex
        self.registry.register(self.endpoint_id, url, token)
        return url

    def close(self) -> None:
        pass

    def validate_ingress(
        self,
        session: Session,
        label: SecurityLabel,
        route: str = "/inference",
    ) -> bool:
        return self._policy.validate_ingress(session, label, route)

    def validate_egress(self, output: str, clearance: SecurityLabel) -> bool:
        return self._policy.validate_egress(output, clearance)

    def register_rpc(self, method: str, handler: Any) -> None:
        self._rpc_handlers[method] = handler

    def handle_jsonrpc(
        self,
        message: dict[str, Any],
        session: Session,
    ) -> dict[str, Any]:
        method = message.get("method", "")
        params = message.get("params", {})
        req_id = message.get("id")
        route = f"/{method}" if not method.startswith("/") else method
        label_name = params.get("label", "INTERNAL")
        request = TunnelRequest(
            route=route,
            payload=params,
            session_id=session.session_id,
            label=label_name,
        )
        try:
            allowed = self.config.allowed_routes
            if route not in allowed and f"/{method}" not in allowed:
                self._policy.validate_route(route)
            handler = self._rpc_handlers.get(method)
            if handler is None:
                result = self._policy.forward_request(request)
            else:
                result = handler(params)
        except TunnelPolicyError as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(exc)},
            }
        else:
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def forward_request(self, request: TunnelRequest) -> dict[str, Any]:
        return self._policy.forward_request(request)

    def audit_event(self, event: AuditEvent) -> None:
        self._policy.audit_event(event)

    def round_trip(self, session: Session, method: str, params: dict[str, Any]) -> str:
        response = self.handle_jsonrpc(
            {"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
            session,
        )
        return json.dumps(response)
