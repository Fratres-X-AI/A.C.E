"""Secure tunnel gateway layer."""

from aegis.tunnel.gateway import TunnelGateway
from aegis.tunnel.mcp_adapter import MCPAdapter, MCPEndpointRegistry
from aegis.tunnel.policy_endpoint import PolicyControlledEndpoint, TunnelPolicyError
from aegis.tunnel.providers import (
    CloudflareTunnelManifest,
    TailscaleACLSnippet,
    WireGuardPeerConfig,
    generate_cloudflare_config,
    generate_tailscale_acl,
    generate_wireguard_config,
)
from aegis.tunnel.simulated_tunnel import SimulatedTunnel

__all__ = [
    "CloudflareTunnelManifest",
    "MCPAdapter",
    "MCPEndpointRegistry",
    "PolicyControlledEndpoint",
    "SimulatedTunnel",
    "TailscaleACLSnippet",
    "TunnelGateway",
    "TunnelPolicyError",
    "WireGuardPeerConfig",
    "generate_cloudflare_config",
    "generate_tailscale_acl",
    "generate_wireguard_config",
]
