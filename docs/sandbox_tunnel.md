# Sandbox + Tunnel Architecture

## Overview

A.C.E v0.3.0 adds **self-hosted sandbox isolation** and **MCP-style tunnel gateways** as first-class containment layers. They compose with existing crypto, IFC, guardians, and audit — every boundary emits tamper-evident events and respects information-flow labels.

## Platform Support

| OS | Primary backend | Auto-resolve order |
|----|-----------------|-------------------|
| Linux | bubblewrap | `bubblewrap` → `gvisor` → `firecracker` → `docker` |
| Windows / macOS | Docker (fallback) | `docker` |

Backends declare `platforms` and `is_compatible()`; the registry filters incompatible backends before auto-selection. Linux-only backends raise a clear `SandboxBackendError` when requested on Windows.

**Docker fallback:** Cross-platform but **not recommended on Windows** — Docker Desktop is heavy. A warning is logged when Docker is auto-selected on Windows.

## Architecture Decision Records

### ADR-001: Sandbox runtime selection

| Option | Isolation | Portability | Choice |
|--------|-----------|-------------|--------|
| bubblewrap | Linux namespaces + seccomp | Linux laptops/servers | Primary on Linux |
| gVisor / Firecracker | Stronger VM isolation | Linux production | Secondary on Linux |
| Docker | Kernel namespaces, cgroups | Cross-platform fallback | Last resort (heavy on Windows) |

**Decision:** `SandboxManager` with `backend: auto` uses `_LINUX_ORDER` on Linux and Docker-only fallback on Windows/macOS. Subprocess isolation avoids heavy SDK dependencies. No simulated/in-process sandbox in production code.

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
| `sandbox/base.py` | `SandboxBackend` ABC with `platforms` / `is_compatible()` |
| `sandbox/backends/bubblewrap.py` | Linux bwrap isolation |
| `sandbox/backends/gvisor.py` | gVisor runsc OCI sandbox |
| `sandbox/backends/firecracker.py` | Firecracker microVM |
| `sandbox/backends/docker.py` | Docker CLI fallback |
| `sandbox/registry.py` | Platform-aware backend registry |
| `sandbox/manager.py` | Factory + session facade |
| `sandbox/workloads.py` | `@register_workload` callable registry |
| `sandbox/_worker.py` | Subprocess worker entrypoint |
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

Existing `process()` remains backward-compatible. IFC labels, guardians, audit, and tunnels work unchanged with any compatible backend.

Callable workloads must be registered with `@register_workload("name")` before running inside an isolated sandbox.

## Extension Guide

### bubblewrap on Linux

1. Install `bubblewrap` (`bwrap` on PATH)
2. Set `sandbox.backend: auto` or `bubblewrap` in policy
3. `python examples/sandbox_backend_demo.py --backend auto`

### gVisor on RunPod

1. Install `runsc` on the GPU node
2. Set `sandbox.backend: gvisor` or rely on Linux auto-resolve
3. Provide OCI bundle rootfs as needed

### Docker on Windows/macOS

1. Install Docker Desktop
2. Set `sandbox.backend: auto` (Docker is the fallback)
3. Expect a warning about resource usage on Windows

### Cloudflare Tunnel

```python
from aegis.tunnel.providers import generate_cloudflare_config

manifest = generate_cloudflare_config("ace-prod", "inference.example.com")
# Deploy with cloudflared using generated manifest
```

## Testing

Unit tests use `MockSandboxBackend` in `tests/sandbox_helpers.py` — a test-only backend that runs the worker subprocess without namespace isolation. Integration tests marked `@pytest.mark.requires_bwrap` or `@pytest.mark.requires_docker` run only when the host has those tools installed.
