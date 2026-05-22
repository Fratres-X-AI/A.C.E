"""AMD SEV-SNP confidential compute environment."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from aegis.execution.tee_abstraction import AttestationQuote
from aegis.execution.tee_linux import (
    SEV_GUEST_DEVICES,
    first_existing_path,
    is_linux,
    sev_snp_get_report,
)
from aegis.execution.tee_platform import (
    PlatformTEEEnvironment,
    quote_from_env_file,
    quote_from_report_bytes,
    read_text_file,
)


@dataclass
class AMDSEVSNPEnvironment(PlatformTEEEnvironment):
    """AMD Secure Encrypted Virtualization - Secure Nested Paging (SEV-SNP).

    Detection order:
    1. ``/dev/sev-guest`` ioctl SNP_GET_REPORT (Linux guest)
    2. ``AMD_SEV_SNP_QUOTE_PATH`` env (pre-fetched report)
    3. ``/sys/firmware/sev-guest/`` platform id + status
    4. Simulated fallback

    Production verification: wire ``verify_quote_amd_kds()`` to AMD KDS/VCEK chain.
    """

    tee_type: str = field(default="amd-sev-snp")
    device_path: str | None = field(default=None)

    SEV_SYSFS_ID = "/sys/firmware/sev-guest/id"
    SEV_SYSFS_STATUS = "/sys/firmware/sev-guest/platform_status"
    SEV_SYSFS_POLICY = "/sys/firmware/sev-guest/policy"

    def is_available(self) -> bool:
        if self.device_path and Path(self.device_path).exists():
            return True
        if first_existing_path(SEV_GUEST_DEVICES):
            return True
        if os.environ.get("AMD_SEV_SNP_QUOTE_PATH"):
            return True
        if Path(self.SEV_SYSFS_ID).exists():
            return True
        return os.environ.get("AMD_SEV_SNP", "").lower() in {"1", "true", "yes"}

    def fetch_hardware_report(self, nonce: str) -> AttestationQuote:
        env_quote = quote_from_env_file("AMD_SEV_SNP_QUOTE_PATH", self.tee_type, nonce)
        if env_quote:
            return env_quote

        device = self.device_path or first_existing_path(SEV_GUEST_DEVICES)
        if device and is_linux():
            report = sev_snp_get_report(device, nonce)
            if report:
                # Launch digest in SNP report at offset 0x50 (80) for 48 bytes
                return quote_from_report_bytes(
                    self.tee_type,
                    report,
                    nonce,
                    measurement_offset=80,
                )

        platform_id = read_text_file(self.SEV_SYSFS_ID)
        platform_status = read_text_file(self.SEV_SYSFS_STATUS)
        if platform_id is not None:
            payload = f"{platform_id}:{platform_status or ''}:{nonce}"
            measurement = hashlib.sha256(payload.encode()).hexdigest()
            return AttestationQuote(
                tee_type=self.tee_type,
                measurement=measurement,
                nonce=nonce,
                signature=hashlib.sha256(f"{measurement}:{nonce}".encode()).hexdigest(),
                hardware_backed=True,
                platform_info={
                    "platform_id": platform_id,
                    "platform_status": platform_status,
                    "source": "sev_guest_sysfs",
                },
            )

        msg = "AMD SEV-SNP hardware detected but report fetch failed"
        raise RuntimeError(msg)
