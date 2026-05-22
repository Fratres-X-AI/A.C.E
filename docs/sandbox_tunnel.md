# Sandbox + Tunnel Architecture

## Overview

A.C.E v0.2.0 adds **self-hosted sandbox isolation** and **MCP-style tunnel gateways** as first-class containment layers. They compose with existing crypto, IFC, guardians, and audit — every boundary emits tamper-evident events and respects information-flow labels.

## Architecture Decision Records

### ADR-001: Sandbox runtime selection

| Option | Isolation | Portability | Choice |
|--------|-----------|-------------|--------|
| Simulated | Process-only (labels + caps) | Laptop / CI | Fallback |
| Docker | Kernel namespaces, cgroups | RunPod, servers | Primary when daemon available |
| gVisor / Firecracker / Kata | Stronger VM isolation | Production | Extension hooks (stubbed) |

**Decision:** `SandboxManager` with `runtime: auto` detects Docker via `docker info`; otherwise uses `SimulatedSandbox`. Subprocess Docker avoids `docker-py` dependency.

### ADR-002: Tunnel zero-trust model

External clients reach a **single guarded endpoint**. Each request passes:

1. Route allowlist (`/inference`, `/health`)
2. Capability token (session-bound)
3. IFC clearance check
4. Rate limit (requests/minute)

Egress is re-validated before crossing the boundary — fail-closed if output exceeds clearance.

### ADR-003: Simulated tunnel for local proof

Cloudflare, WireGuard, and Tailscale integrations are **config generators only** — they produce deployment manifests, not live daemons. `SimulatedTunnel` runs a loopback HTTP server to prove policy logic without cloud dependencies.

## Module Map

| Module | Role |
|--------|------|
| `sandbox/environment.py` | `SandboxEnvironment` protocol |
| `sandbox/simulated_sandbox.py` | In-process fallback |
| `sandbox/docker_sandbox.py` | Docker CLI sandbox |
| `sandbox/manager.py` | Factory + gVisor/Firecracker/Kata stubs |
| `sandbox/labels.py` | Label binding / clearance checks |
| `tunnel/gateway.py` | `TunnelGateway` protocol |
| `tunnel/policy_endpoint.py` | Allowlist, IFC, rate limits |
| `tunnel/simulated_tunnel.py` | Loopback HTTP gateway |
| `tunnel/mcp_adapter.py` | JSON-RPC shaped secure RPC |
| `tunnel/providers.py` | Cloudflare / WireGuard / Tailscale stubs |

## Integrated Pipeline

`ContainmentEngine.process_integrated()` orchestrates:

```
encrypt → IFC → tunnel ingress → sandbox → guardian → tunnel egress → audit
```

Existing `process()` remains backward-compatible.

## Extension Guide

### gVisor on RunPod

1. Install `runsc` on the GPU node
2. Set `sandbox.runtime: docker` with Docker configured for `--runtime=runsc`
3. Use `GVisorRuntime.is_available()` hook when runsc is present

### Cloudflare Tunnel

```python
from aegis.tunnel.providers import generate_cloudflare_config

manifest = generate_cloudflare_config("ace-prod", "inference.example.com")
# Deploy with cloudflared using generated manifest
```

### RunPod deployment

See [`integration_guide.md`](integration_guide.md#runpod-integrated) for pod setup with Docker sandbox and tunnel ingress.

## Known Limitations

- Simulated sandbox is not kernel isolation — suitable for CI and policy testing only
- MCP adapter implements secure RPC semantics, not full MCP server spec compliance
- Provider configs require manual daemon deployment (cloudflared, tailscaled, wg-quick)
