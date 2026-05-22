"""Execution layer — TEE, instrumented runner, math/physics."""

from aegis.execution.tee_abstraction import (
    AttestationQuote,
    SimulatedTEE,
    TEEEnvironment,
    verify_attestation_stub,
)
from aegis.execution.tee_amd_sev_snp import AMDSEVSNPEnvironment
from aegis.execution.tee_factory import (
    TEEPlatform,
    create_tee_environment,
    detect_platform,
)
from aegis.execution.tee_intel_tdx import IntelTDXEnvironment

__all__ = [
    "AMDSEVSNPEnvironment",
    "AttestationQuote",
    "IntelTDXEnvironment",
    "SimulatedTEE",
    "TEEEnvironment",
    "TEEPlatform",
    "create_tee_environment",
    "detect_platform",
    "verify_attestation_stub",
]
