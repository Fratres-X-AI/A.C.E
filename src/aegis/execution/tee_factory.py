"""TEE environment factory — auto-detect Intel TDX, AMD SEV-SNP, or simulation."""

from __future__ import annotations

import os
from enum import StrEnum
from typing import Literal

from aegis.execution.tee_abstraction import SimulatedTEE, TEEEnvironment
from aegis.execution.tee_amd_sev_snp import AMDSEVSNPEnvironment
from aegis.execution.tee_intel_tdx import IntelTDXEnvironment


class TEEPlatform(StrEnum):
    """Supported confidential compute platforms."""

    AUTO = "auto"
    INTEL_TDX = "intel-tdx"
    AMD_SEV_SNP = "amd-sev-snp"
    SIMULATED = "simulated"


def detect_platform() -> TEEPlatform:
    """Detect the best available TEE platform on this host."""
    override = os.environ.get("ACE_TEE_PLATFORM", "").lower()
    if override == "intel-tdx":
        return TEEPlatform.INTEL_TDX
    if override == "amd-sev-snp":
        return TEEPlatform.AMD_SEV_SNP
    if override == "simulated":
        return TEEPlatform.SIMULATED

    tdx = IntelTDXEnvironment(allow_simulated_fallback=False)
    if tdx.is_available():
        return TEEPlatform.INTEL_TDX

    sev = AMDSEVSNPEnvironment(allow_simulated_fallback=False)
    if sev.is_available():
        return TEEPlatform.AMD_SEV_SNP

    return TEEPlatform.SIMULATED


def create_tee_environment(
    platform: TEEPlatform
    | Literal["auto", "intel-tdx", "amd-sev-snp", "simulated"] = "auto",
    *,
    allow_simulated_fallback: bool = True,
) -> TEEEnvironment:
    """Create a TEE environment for the requested or detected platform.

    Args:
        platform: Target platform or ``auto`` for detection.
        allow_simulated_fallback: When True, platform adapters fall back to
            simulated quotes if hardware report fetch fails. When False,
            raises ``RuntimeError`` on unavailable hardware.

    Returns:
        A ``TEEEnvironment`` implementation (Intel TDX, AMD SEV-SNP, or simulated).

    """
    if isinstance(platform, str):
        platform = TEEPlatform(platform)

    if platform == TEEPlatform.AUTO:
        platform = detect_platform()

    if platform == TEEPlatform.INTEL_TDX:
        return IntelTDXEnvironment(allow_simulated_fallback=allow_simulated_fallback)
    if platform == TEEPlatform.AMD_SEV_SNP:
        return AMDSEVSNPEnvironment(allow_simulated_fallback=allow_simulated_fallback)
    return SimulatedTEE()
