"""Tests for Intel TDX and AMD SEV-SNP TEE adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from aegis.execution.tee_abstraction import SimulatedTEE, verify_attestation_stub
from aegis.execution.tee_amd_sev_snp import AMDSEVSNPEnvironment
from aegis.execution.tee_factory import (
    TEEPlatform,
    create_tee_environment,
    detect_platform,
)
from aegis.execution.tee_intel_tdx import IntelTDXEnvironment


def test_simulated_tee_seal_roundtrip() -> None:
    tee = SimulatedTEE()
    quote = tee.attest("nonce-1")
    assert not quote.hardware_backed
    sealed = tee.seal(b"containment-secret")
    assert tee.unseal(sealed) == b"containment-secret"


def test_intel_tdx_simulated_fallback() -> None:
    tee = IntelTDXEnvironment(allow_simulated_fallback=True)
    quote = tee.attest("test-nonce")
    assert quote.tee_type.endswith("-simulated") or quote.hardware_backed
    sealed = tee.seal(b"tdx-data")
    assert tee.unseal(sealed) == b"tdx-data"


def test_amd_sev_snp_simulated_fallback() -> None:
    tee = AMDSEVSNPEnvironment(allow_simulated_fallback=True)
    quote = tee.attest("test-nonce")
    assert quote.tee_type.endswith("-simulated") or quote.hardware_backed
    sealed = tee.seal(b"sev-data")
    assert tee.unseal(sealed) == b"sev-data"


def test_intel_tdx_env_quote_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = b"\x01" * 1024
    quote_path = tmp_path / "tdx.quote"
    quote_path.write_bytes(report)
    monkeypatch.setenv("INTEL_TDX_QUOTE_PATH", str(quote_path))
    tee = IntelTDXEnvironment(allow_simulated_fallback=False)
    assert tee.is_available()
    quote = tee.fetch_hardware_report("nonce-abc")
    assert quote.hardware_backed
    assert quote.tee_type == "intel-tdx"
    assert quote.raw_report_b64 is not None


def test_amd_sev_sysfs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sysfs = tmp_path / "sev-guest"
    sysfs.mkdir()
    (sysfs / "id").write_text("platform-chip-id-001", encoding="utf-8")
    (sysfs / "platform_status").write_text("active", encoding="utf-8")
    tee = AMDSEVSNPEnvironment(allow_simulated_fallback=False)
    tee.SEV_SYSFS_ID = str(sysfs / "id")
    tee.SEV_SYSFS_STATUS = str(sysfs / "platform_status")
    assert tee.is_available()
    quote = tee.fetch_hardware_report("nonce-xyz")
    assert quote.hardware_backed
    assert quote.platform_info.get("platform_id") == "platform-chip-id-001"


def test_create_tee_environment_simulated() -> None:
    tee = create_tee_environment("simulated")
    assert isinstance(tee, SimulatedTEE)


def test_create_tee_environment_intel() -> None:
    tee = create_tee_environment("intel-tdx")
    assert isinstance(tee, IntelTDXEnvironment)


def test_detect_platform_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACE_TEE_PLATFORM", "amd-sev-snp")
    assert detect_platform() == TEEPlatform.AMD_SEV_SNP


def test_verify_attestation_stub() -> None:
    tee = SimulatedTEE()
    quote = tee.attest()
    assert verify_attestation_stub(quote)


def test_session_uses_factory_tee() -> None:
    from aegis.core.session import Session

    session = Session()
    quote = session.bind_tee("session-nonce")
    assert quote.nonce == "session-nonce"
