"""Linux-specific TDX and SEV-SNP ioctl helpers."""

from __future__ import annotations

import struct
import sys
from pathlib import Path
from typing import Final

# TDX guest driver (Linux 6.8+): tdx_report_req = report_data[64] + tdreport[1024]
TDX_REPORT_DATA_SIZE: Final = 64
TDX_TDREPORT_SIZE: Final = 1024
TDX_REPORT_REQ_SIZE: Final = TDX_REPORT_DATA_SIZE + TDX_TDREPORT_SIZE
TDX_CMD_GET_REPORT0: Final = (
    (TDX_REPORT_REQ_SIZE << 16) | (ord("T") << 8) | 0 | 0xC0000000
)

# AMD SEV-SNP guest: simplified report buffer via SNP_GET_REPORT
SEV_SNP_REPORT_SIZE: Final = 1184
SEV_CMD_GET_REPORT: Final = (
    (SEV_SNP_REPORT_SIZE << 16) | (ord("S") << 8) | 0 | 0xC0000000
)

TDX_GUEST_DEVICES: Final = ("/dev/tdx_guest", "/dev/tdx-guest")
SEV_GUEST_DEVICES: Final = ("/dev/sev-guest", "/dev/sev")


def is_linux() -> bool:
    return sys.platform == "linux"


def first_existing_path(paths: tuple[str, ...]) -> str | None:
    for path in paths:
        if Path(path).exists():
            return path
    return None


def tdx_get_report(device_path: str, nonce: str) -> bytes | None:
    """Issue TDX_CMD_GET_REPORT0 ioctl and return TDREPORT bytes."""
    if not is_linux():
        return None
    import fcntl

    report_data = hashlib_nonce_to_report_data(nonce)
    req = report_data + bytes(TDX_TDREPORT_SIZE)
    try:
        with Path(device_path).open("rb") as dev:
            mutated = fcntl.ioctl(  # type: ignore[attr-defined]
                dev,
                TDX_CMD_GET_REPORT0,
                req,
                mutate_flag=True,
            )
        if isinstance(mutated, bytes) and len(mutated) >= TDX_REPORT_REQ_SIZE:
            end = TDX_REPORT_DATA_SIZE + TDX_TDREPORT_SIZE
            return mutated[TDX_REPORT_DATA_SIZE:end]
        if isinstance(mutated, bytes):
            return mutated[TDX_REPORT_DATA_SIZE:]
    except OSError:
        return None
    return None


def sev_snp_get_report(device_path: str, nonce: str) -> bytes | None:
    """Issue SNP_GET_REPORT ioctl and return guest attestation report."""
    if not is_linux():
        return None
    import fcntl

    report_data = hashlib_nonce_to_report_data(nonce)
    msg_version = struct.pack("Q", 1)
    req_data = struct.pack("Q", 0)
    resp_data = struct.pack("Q", 0)
    payload = (
        msg_version + req_data + resp_data + report_data + bytes(SEV_SNP_REPORT_SIZE)
    )
    try:
        with Path(device_path).open("rb") as dev:
            mutated = fcntl.ioctl(  # type: ignore[attr-defined]
                dev,
                SEV_CMD_GET_REPORT,
                payload,
                mutate_flag=True,
            )
        if isinstance(mutated, bytes) and len(mutated) >= SEV_SNP_REPORT_SIZE:
            return mutated[-SEV_SNP_REPORT_SIZE:]
    except OSError:
        return None
    return None


def hashlib_nonce_to_report_data(nonce: str) -> bytes:
    import hashlib

    digest = hashlib.sha256(nonce.encode()).digest()
    return digest[:TDX_REPORT_DATA_SIZE].ljust(TDX_REPORT_DATA_SIZE, b"\x00")
