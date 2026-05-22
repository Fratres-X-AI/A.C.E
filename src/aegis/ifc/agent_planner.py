"""Fides-style label tracking through agent planning and execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from aegis.ifc.flow_control import FlowControlEngine, FlowViolationError
from aegis.ifc.labels import SecurityLabel
from aegis.utils.typing import FlowOperation


@dataclass
class PlanStep:
    """Single step in an agent plan with tracked label."""

    step_id: str
    action: str
    label: SecurityLabel
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemorySlot:
    """Agent memory entry with security label."""

    key: str
    value: Any
    label: SecurityLabel


@dataclass
class AgentPlanner:
    """Track labels through tool use, memory, and planning (Fides-style).

    High-sensitivity retrieved context cannot influence low-privilege final
    output without explicit declassification.
    """

    output_clearance: SecurityLabel
    flow: FlowControlEngine = field(default_factory=FlowControlEngine)
    plan_steps: list[PlanStep] = field(default_factory=list)
    memory: dict[str, MemorySlot] = field(default_factory=dict)
    declassification_granted: bool = False

    def add_step(self, action: str, label: SecurityLabel, **payload: Any) -> PlanStep:
        step = PlanStep(
            step_id=str(uuid4()), action=action, label=label, payload=payload
        )
        self.plan_steps.append(step)
        return step

    def write_memory(self, key: str, value: Any, label: SecurityLabel) -> None:
        current = self.memory.get(key)
        source = current.label if current else label
        self.flow.enforce(source, label, FlowOperation.WRITE)
        self.memory[key] = MemorySlot(key=key, value=value, label=label)

    def read_memory(self, key: str, reader_label: SecurityLabel) -> MemorySlot:
        slot = self.memory[key]
        self.flow.enforce(slot.label, reader_label, FlowOperation.READ)
        return slot

    def grant_declassification(self) -> None:
        """Explicit declassification gate (policy-controlled)."""
        self.declassification_granted = True

    def validate_final_output(self, output_label: SecurityLabel) -> SecurityLabel:
        """Ensure final output respects clearance and plan labels."""
        input_labels = [s.label for s in self.plan_steps] + [
            m.label for m in self.memory.values()
        ]
        if not input_labels:
            return output_label
        joined = input_labels[0]
        for lbl in input_labels[1:]:
            joined = joined.join(lbl)
        if joined.sensitivity > self.output_clearance.sensitivity:
            if not self.declassification_granted:
                raise FlowViolationError(
                    "High-sensitivity context would leak into low-privilege output "
                    "without declassification",
                )
            self.flow.enforce(joined, self.output_clearance, FlowOperation.DECLASSIFY)
        self.flow.enforce(output_label, self.output_clearance, FlowOperation.WRITE)
        return output_label
