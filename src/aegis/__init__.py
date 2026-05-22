"""A.C.E — Aegis Containment Engine.

Auditable, layered AI containment and defensive enforcement framework.
Assume breach. Contain egress. Measure everything.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.3.0"

if TYPE_CHECKING:
    from aegis.core.containment_engine import ContainmentEngine
    from aegis.core.session import Session
    from aegis.utils.typing import ContainmentResult, ContainmentVerdict

__all__ = [
    "ContainmentEngine",
    "ContainmentResult",
    "ContainmentVerdict",
    "Session",
    "__version__",
]


def __getattr__(name: str) -> Any:
    if name == "ContainmentEngine":
        from aegis.core.containment_engine import ContainmentEngine

        return ContainmentEngine
    if name == "Session":
        from aegis.core.session import Session

        return Session
    if name == "ContainmentResult":
        from aegis.utils.typing import ContainmentResult

        return ContainmentResult
    if name == "ContainmentVerdict":
        from aegis.utils.typing import ContainmentVerdict

        return ContainmentVerdict
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
