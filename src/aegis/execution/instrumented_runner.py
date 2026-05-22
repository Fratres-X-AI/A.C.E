"""Instrumented inference runner with containment hooks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aegis.audit.tamper_proof_log import TamperProofLog
from aegis.utils.typing import AuditEvent


@dataclass
class InstrumentedRunner:
    """Wrap model inference with pre/post containment hooks.

    ADR: All inference paths must pass through auditable hooks — no bypass.
    """

    audit_log: TamperProofLog
    pre_hooks: list[Callable[[dict[str, Any]], dict[str, Any]]] = field(
        default_factory=list,
    )
    post_hooks: list[Callable[[str], str]] = field(default_factory=list)

    def register_pre_hook(
        self,
        hook: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.pre_hooks.append(hook)

    def register_post_hook(self, hook: Callable[[str], str]) -> None:
        self.post_hooks.append(hook)

    def run(
        self,
        model_fn: Callable[[dict[str, Any]], str],
        payload: dict[str, Any],
    ) -> str:
        self.audit_log.append(
            AuditEvent(layer="execution", action="inference_start", detail="runner"),
        )
        processed = payload
        for hook in self.pre_hooks:
            processed = hook(processed)
        raw_output: str = model_fn(processed)
        output: str = raw_output
        for post_hook in self.post_hooks:
            output = post_hook(output)
        self.audit_log.append(
            AuditEvent(
                layer="execution",
                action="inference_complete",
                detail=f"output_len={len(output)}",
            ),
        )
        return output
