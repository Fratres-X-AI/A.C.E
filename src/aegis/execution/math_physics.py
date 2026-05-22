"""Narrow typed interfaces for math/physics workloads."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

try:
    import sympy
    from sympy import sympify

    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False


@dataclass(frozen=True)
class VerifiedExpression:
    """Structured verified mathematical object — never free text."""

    expression: str
    latex: str
    variables: tuple[str, ...]
    verified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "VerifiedExpression",
            "expression": self.expression,
            "latex": self.latex,
            "variables": list(self.variables),
            "verified": self.verified,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class MathPhysicsInterface:
    """Return only verified SymPy expressions or structured objects.

    ADR: Dual-use math/physics advisors must not emit unconstrained free text.
    """

    _SAFE_PATTERN = re.compile(r"^[a-zA-Z0-9_+\-*/^().,\s=]+$")

    def parse_and_verify(self, raw: str) -> VerifiedExpression:
        if not self._SAFE_PATTERN.match(raw.strip()):
            msg = "Expression contains disallowed characters (possible exfil vector)"
            raise ValueError(msg)
        if not SYMPY_AVAILABLE:
            return VerifiedExpression(
                expression=raw.strip(),
                latex=raw.strip(),
                variables=(),
                verified=False,
            )
        expr = sympify(raw.strip())
        variables = tuple(sorted(str(s) for s in expr.free_symbols))
        return VerifiedExpression(
            expression=str(expr),
            latex=str(sympy.latex(expr)),
            variables=variables,
            verified=True,
        )

    def reject_free_text(self, text: str) -> bool:
        """True if text looks like unconstrained free-text exfil."""
        if len(text) > 500:
            return True
        suspicious = [
            "password",
            "secret",
            "api_key",
            "BEGIN RSA",
            "http://",
            "https://",
        ]
        lower = text.lower()
        return any(s in lower for s in suspicious)
