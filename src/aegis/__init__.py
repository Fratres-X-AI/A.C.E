"""A.C.E — Aegis Containment Engine.

Auditable, layered AI containment and defensive enforcement framework.
Assume breach. Contain egress. Measure everything.
"""

from aegis.core.containment_engine import ContainmentEngine
from aegis.core.session import Session
from aegis.utils.typing import ContainmentResult, ContainmentVerdict

__version__ = "0.1.0"
__all__ = [
    "ContainmentEngine",
    "ContainmentResult",
    "ContainmentVerdict",
    "Session",
    "__version__",
]
