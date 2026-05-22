"""Runtime configuration for A.C.E containment."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GuardianConfig(BaseModel):
    """Thresholds for egress guardian layers."""

    max_entropy_bits_per_char: float = Field(default=5.5, ge=0.0)
    max_output_bytes_per_minute: int = Field(default=50_000, ge=1)
    pii_patterns_enabled: bool = True
    canary_detection_enabled: bool = True
    anomaly_z_threshold: float = Field(default=2.5, ge=0.0)


class SandboxConfig(BaseModel):
    """Self-hosted sandbox runtime configuration."""

    backend: str = "auto"
    runtime: str | None = None  # deprecated alias for backend
    memory_mb: int = Field(default=512, ge=64)
    cpu_quota: int = Field(default=50_000, ge=1000)
    network_enabled: bool = False
    seccomp_profile: str = "default"

    def resolved_backend(self) -> str:
        """Return effective backend name, honoring deprecated runtime alias."""
        if self.runtime is not None:
            return self.runtime
        return self.backend


class TunnelConfig(BaseModel):
    """MCP-style tunnel gateway configuration."""

    allowed_routes: list[str] = Field(
        default_factory=lambda: ["/inference", "/health"],
    )
    require_capability_token: bool = True
    max_requests_per_minute: int = Field(default=60, ge=1)


class PolicyConfig(BaseModel):
    """Policy-as-code runtime configuration."""

    default_sensitivity: str = "INTERNAL"
    default_integrity: str = "VERIFIED"
    allow_declassification: bool = False
    fail_closed: bool = True
    guardian: GuardianConfig = Field(default_factory=GuardianConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    tunnel: TunnelConfig = Field(default_factory=TunnelConfig)


class ACEConfig(BaseModel):
    """Top-level A.C.E configuration."""

    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    audit_dp_epsilon: float | None = None
    tee_simulation: bool = True
    log_level: str = "INFO"
