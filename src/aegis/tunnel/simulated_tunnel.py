"""Local loopback HTTP tunnel for demos without cloud daemons."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, ClassVar
from uuid import uuid4

from aegis.core.session import Session
from aegis.ifc.labels import SecurityLabel
from aegis.tunnel.policy_endpoint import PolicyControlledEndpoint, TunnelPolicyError
from aegis.utils.config import TunnelConfig
from aegis.utils.typing import AuditEvent, TunnelRequest


@dataclass
class SimulatedTunnel:
    """Threaded loopback HTTP gateway implementing TunnelGateway semantics."""

    config: TunnelConfig = field(default_factory=TunnelConfig)
    endpoint_id: str = field(default_factory=lambda: f"tunnel-{uuid4().hex[:8]}")
    host: str = "127.0.0.1"
    port: int = 0
    _policy: PolicyControlledEndpoint = field(init=False)
    _server: HTTPServer | None = field(default=None, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)
    _handler: Callable[[TunnelRequest], dict[str, Any]] | None = field(
        default=None,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._policy = PolicyControlledEndpoint(
            config=self.config,
            endpoint_id=self.endpoint_id,
        )

    def open_endpoint(self, session: Session) -> str:
        session.tunnel_endpoint_id = self.endpoint_id
        if self._server is None:
            _TunnelHandler.gateway = self
            self._server = HTTPServer((self.host, self.port), _TunnelHandler)
            self.port = self._server.server_address[1]
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
            )
            self._thread.start()
        return f"http://{self.host}:{self.port}"

    def close(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server = None
            self._thread = None

    def validate_ingress(
        self,
        session: Session,
        label: SecurityLabel,
        route: str = "/inference",
    ) -> bool:
        result = self._policy.validate_ingress(session, label, route)
        self.audit_event(
            AuditEvent(
                layer="tunnel",
                action="validate_ingress",
                detail=f"route={route}",
            ),
        )
        return result

    def validate_egress(self, output: str, clearance: SecurityLabel) -> bool:
        return self._policy.validate_egress(output, clearance)

    def forward_request(self, request: TunnelRequest) -> dict[str, Any]:
        if self._handler is not None:
            return self._handler(request)
        return self._policy.forward_request(request)

    def set_handler(
        self,
        handler: Callable[[TunnelRequest], dict[str, Any]],
    ) -> None:
        self._handler = handler

    def audit_event(self, event: AuditEvent) -> None:
        self._policy.audit_event(event)


class _TunnelHandler(BaseHTTPRequestHandler):
    gateway: ClassVar[SimulatedTunnel | None] = None

    def log_message(self, msg_format: str, *msg_args: object) -> None:  # noqa: ARG002
        return

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def _handle(self) -> None:
        gw = type(self).gateway
        if gw is None:
            self.send_error(503)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body.decode() or "{}")
        except json.JSONDecodeError:
            payload = {}
        session_id = self.headers.get("X-Session-ID", "anonymous")
        label = self.headers.get("X-Label", "INTERNAL")
        request = TunnelRequest(
            route=self.path,
            payload=payload,
            session_id=session_id,
            label=label,
        )
        try:
            result = gw.forward_request(request)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except TunnelPolicyError as exc:
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode())
