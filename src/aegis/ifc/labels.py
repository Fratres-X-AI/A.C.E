"""Information flow control labels."""

from __future__ import annotations

from dataclasses import dataclass

from aegis.utils.typing import IntegrityLevel, SensitivityLevel


@dataclass(frozen=True)
class SecurityLabel:
    """Combined confidentiality + integrity label."""

    sensitivity: SensitivityLevel
    integrity: IntegrityLevel

    def dominates(self, other: SecurityLabel) -> bool:
        """True if this label is at least as restrictive as other."""
        return (
            self.sensitivity >= other.sensitivity and self.integrity >= other.integrity
        )

    def join(self, other: SecurityLabel) -> SecurityLabel:
        """Lattice join — highest sensitivity, lowest integrity (Biba meet)."""
        return SecurityLabel(
            sensitivity=max(self.sensitivity, other.sensitivity),
            integrity=min(self.integrity, other.integrity),
        )

    @classmethod
    def from_names(cls, sensitivity: str, integrity: str) -> SecurityLabel:
        return SecurityLabel(
            sensitivity=SensitivityLevel[sensitivity.upper()],
            integrity=IntegrityLevel[integrity.upper()],
        )


PUBLIC = SecurityLabel(SensitivityLevel.PUBLIC, IntegrityLevel.UNTRUSTED)
INTERNAL = SecurityLabel(SensitivityLevel.INTERNAL, IntegrityLevel.VERIFIED)
SECRET = SecurityLabel(SensitivityLevel.SECRET, IntegrityLevel.ATTESTED)
TOP_SECRET = SecurityLabel(SensitivityLevel.TOP_SECRET, IntegrityLevel.FORMAL)
