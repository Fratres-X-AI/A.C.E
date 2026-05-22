"""Tunnel provider config generators (stubs — no live daemons)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CloudflareTunnelManifest:
    """Generate cloudflared tunnel manifest snippet."""

    tunnel_name: str
    hostname: str
    service_url: str = "http://localhost:8080"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tunnel": self.tunnel_name,
            "ingress": [
                {
                    "hostname": self.hostname,
                    "service": self.service_url,
                },
                {"service": "http_status:404"},
            ],
        }


@dataclass
class WireGuardPeerConfig:
    """Generate WireGuard peer configuration stub."""

    private_key: str = "<YOUR_PRIVATE_KEY>"
    public_key: str = "<PEER_PUBLIC_KEY>"
    endpoint: str = "vpn.example.com:51820"
    allowed_ips: str = "10.0.0.0/24"

    def render(self) -> str:
        return f"""[Interface]
PrivateKey = {self.private_key}
Address = 10.0.0.2/32

[Peer]
PublicKey = {self.public_key}
Endpoint = {self.endpoint}
AllowedIPs = {self.allowed_ips}
PersistentKeepalive = 25
"""


@dataclass
class TailscaleACLSnippet:
    """Generate Tailscale/Headscale ACL snippet."""

    tag: str = "tag:ace-sandbox"

    def render(self) -> str:
        return f"""// Tailscale ACL snippet for A.C.E sandbox tunnel
{{
  "acls": [
    {{
      "action": "accept",
      "src": ["autogroup:member"],
      "dst": ["{self.tag}:*"]
    }}
  ],
  "tagOwners": {{
    "{self.tag}": ["autogroup:admin"]
  }}
}}
"""


def generate_cloudflare_config(
    tunnel_name: str,
    hostname: str,
    service_url: str = "http://localhost:8080",
) -> dict[str, Any]:
    return CloudflareTunnelManifest(tunnel_name, hostname, service_url).to_dict()


def generate_wireguard_config(**kwargs: str) -> str:
    return WireGuardPeerConfig(**kwargs).render()


def generate_tailscale_acl(tag: str = "tag:ace-sandbox") -> str:
    return TailscaleACLSnippet(tag=tag).render()
