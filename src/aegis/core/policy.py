"""Policy-as-code loader for containment rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from aegis.utils.config import ACEConfig, PolicyConfig, SandboxConfig


class Policy:
    """Runtime policy loaded from YAML/JSON.

    ADR: Trade-offs must be explicit and measurable — thresholds live here.
    """

    def __init__(self, config: ACEConfig | None = None) -> None:
        self.config = config or ACEConfig()

    @classmethod
    def from_file(cls, path: str | Path) -> Policy:
        path = Path(path)
        raw: dict[str, Any]
        text = path.read_text(encoding="utf-8")
        if path.suffix in {".yaml", ".yml"}:
            raw = yaml.safe_load(text) or {}
        else:
            raw = json.loads(text)
        config = ACEConfig.model_validate(raw)
        return cls(config=config)

    @property
    def policy(self) -> PolicyConfig:
        return self.config.policy

    def allows_declassification(self) -> bool:
        return self.policy.allow_declassification

    def fail_closed(self) -> bool:
        return self.policy.fail_closed

    def guardian_entropy_threshold(self) -> float:
        return self.policy.guardian.max_entropy_bits_per_char

    def rate_limit_bytes_per_minute(self) -> int:
        return self.policy.guardian.max_output_bytes_per_minute

    def sandbox_config(self) -> SandboxConfig:
        return self.policy.sandbox

    def tunnel_allowed_routes(self) -> list[str]:
        return list(self.policy.tunnel.allowed_routes)
