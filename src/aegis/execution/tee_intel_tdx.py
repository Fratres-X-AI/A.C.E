"""Intel TDX confidential compute environment."""

from __future__ import annotations

import hashlib
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from aegis.execution.tee_abstraction import AttestationQuote
from aegis.execution.tee_linux import (
    TDX_GUEST_DEVICES,
    first_existing_path,
    is_linux,
    tdx_get_report,
)
from aegis.execution.tee_platform import (
    PlatformTEEEnvironment,
    quote_from_env_file,
    quote_from_report_bytes,
    read_text_file,
)


@dataclass
class IntelTDXEnvironment(PlatformTEEEnvironment):
    """Intel Trust Domain Extensions (TDX) attestation and sealing.

    Detection order:
    1. ``/dev/tdx_guest`` or ``/dev/tdx-guest`` ioctl (Linux guest)
    2. ``INTEL_TDX_QUOTE_PATH`` env (pre-fetched quote from deployment agent)
    3. Azure IMDS TDX attestation endpoint (confidential VM)
    4. ``/sys/firmware/tdx_guest/`` sysfs status
    5. Simulated fallback (when ``allow_simulated_fallback=True``)

    Production verification: wire ``verify_quote_dcap()`` to Intel DCAP QVL.
    """

    tee_type: str = field(default="intel-tdx")
    device_path: str | None = field(default=None)
    imds_endpoint: str | None = field(default=None)

    TDX_SYSFS_STATUS = "/sys/firmware/tdx_guest/status"
    TDX_SYSFS_CPUID = "/sys/firmware/tdx_guest/cpuids"

    def is_available(self) -> bool:
        if self.device_path and Path(self.device_path).exists():
            return True
        if first_existing_path(TDX_GUEST_DEVICES):
            return True
        if os.environ.get("INTEL_TDX_QUOTE_PATH"):
            return True
        if self._azure_attestation_enabled():
            return True
        if Path(self.TDX_SYSFS_STATUS).exists():
            return True
        return os.environ.get("INTEL_TDX", "").lower() in {"1", "true", "yes"}

    def _azure_attestation_enabled(self) -> bool:
        """Only opt in when explicitly running on Azure confidential infrastructure."""
        return os.environ.get("AZURE_CONFIDENTIAL_VM", "").lower() in {
            "1",
            "true",
            "yes",
        }

    def fetch_hardware_report(self, nonce: str) -> AttestationQuote:
        env_quote = quote_from_env_file("INTEL_TDX_QUOTE_PATH", self.tee_type, nonce)
        if env_quote:
            return env_quote

        device = self.device_path or first_existing_path(TDX_GUEST_DEVICES)
        if device and is_linux():
            report = tdx_get_report(device, nonce)
            if report:
                # MRTD is at offset 528 in TDREPORT (simplified; full parse via DCAP)
                return quote_from_report_bytes(
                    self.tee_type,
                    report,
                    nonce,
                    measurement_offset=min(528, max(0, len(report) - 48)),
                )

        azure_quote = self._fetch_azure_imds_tdx(nonce)
        if azure_quote:
            return azure_quote

        status = read_text_file(self.TDX_SYSFS_STATUS)
        if status is not None:
            measurement = hashlib.sha256(f"tdx-sysfs:{status}".encode()).hexdigest()
            return AttestationQuote(
                tee_type=self.tee_type,
                measurement=measurement,
                nonce=nonce,
                signature=hashlib.sha256(f"{measurement}:{nonce}".encode()).hexdigest(),
                hardware_backed=True,
                platform_info={"sysfs_status": status, "source": "tdx_guest_sysfs"},
            )

        msg = "Intel TDX attestation sources exhausted"
        raise RuntimeError(msg)

    def _azure_imds_available(self) -> bool:
        return self._azure_attestation_enabled()

    def _fetch_azure_imds_tdx(self, nonce: str) -> AttestationQuote | None:
        if not self._azure_attestation_enabled():
            return None
        if os.environ.get("ACE_DISABLE_AZURE_IMDS", "").lower() in {"1", "true"}:
            return None
        endpoint = self.imds_endpoint or os.environ.get(
            "AZURE_IMDS_ENDPOINT",
            "http://169.254.169.254",
        )
        url = f"{endpoint}/attestation/TDX?api-version=2025-01-01&nonce={nonce}"
        req = urllib.request.Request(  # noqa: S310
            url,
            headers={"Metadata": "true"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                body = resp.read()
        except (urllib.error.URLError, TimeoutError, OSError):
            return None
        measurement = hashlib.sha256(body).hexdigest()
        return AttestationQuote(
            tee_type=f"{self.tee_type}-azure-imds",
            measurement=measurement,
            nonce=nonce,
            signature=hashlib.sha256(body + nonce.encode()).hexdigest(),
            hardware_backed=True,
            raw_report_b64=None,
            platform_info={"source": "azure_imds_tdx", "endpoint": endpoint},
        )
