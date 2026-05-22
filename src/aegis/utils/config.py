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


class PolicyConfig(BaseModel):
    """Policy-as-code runtime configuration."""

    default_sensitivity: str = "INTERNAL"
    default_integrity: str = "VERIFIED"
    allow_declassification: bool = False
    fail_closed: bool = True
    guardian: GuardianConfig = Field(default_factory=GuardianConfig)


class ACEConfig(BaseModel):
    """Top-level A.C.E configuration."""

    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    audit_dp_epsilon: float | None = None
    tee_simulation: bool = True
    log_level: str = "INFO"
