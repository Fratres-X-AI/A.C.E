"""Tunnel module tests."""

import pytest

from aegis.core.session import Session
from aegis.ifc.labels import INTERNAL, PUBLIC
from aegis.tunnel.mcp_adapter import MCPAdapter
from aegis.tunnel.policy_endpoint import PolicyControlledEndpoint, TunnelPolicyError
from aegis.tunnel.providers import (
    generate_cloudflare_config,
    generate_tailscale_acl,
    generate_wireguard_config,
)
from aegis.tunnel.simulated_tunnel import SimulatedTunnel
from aegis.utils.config import TunnelConfig
from aegis.utils.typing import TunnelRequest


def test_policy_endpoint_allow_deny() -> None:
    cfg = TunnelConfig(allowed_routes=["/inference", "/health"])
    endpoint = PolicyControlledEndpoint(config=cfg)
    session = Session()
    session.issue_capability("tunnel")
    assert endpoint.validate_ingress(session, INTERNAL, "/inference")
    with pytest.raises(TunnelPolicyError):
        endpoint.validate_route("/evil")


def test_mcp_adapter_round_trip() -> None:
    cfg = TunnelConfig(
        allowed_routes=["/inference", "/health"],
        require_capability_token=False,
    )
    adapter = MCPAdapter(config=cfg)
    session = Session()
    adapter.open_endpoint(session)
    response = adapter.round_trip(session, "health", {"label": "INTERNAL"})
    assert "jsonrpc" in response


def test_simulated_tunnel_audit() -> None:
    cfg = TunnelConfig(require_capability_token=False)
    tunnel = SimulatedTunnel(config=cfg)
    session = Session()
    tunnel.open_endpoint(session)
    tunnel.validate_ingress(session, INTERNAL)
    assert tunnel.validate_egress("safe output", PUBLIC)
    tunnel.close()


def test_forward_request() -> None:
    endpoint = PolicyControlledEndpoint(
        config=TunnelConfig(allowed_routes=["/inference"]),
    )
    req = TunnelRequest(
        route="/inference",
        payload={"q": "test"},
        session_id="s1",
        label="INTERNAL",
    )
    result = endpoint.forward_request(req)
    assert result["status"] == "forwarded"


def test_provider_stubs() -> None:
    cf = generate_cloudflare_config("ace-tunnel", "ace.example.com")
    assert cf["tunnel"] == "ace-tunnel"
    assert "PrivateKey" in generate_wireguard_config()
    assert "tag:ace-sandbox" in generate_tailscale_acl()
