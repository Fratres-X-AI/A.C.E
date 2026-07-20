"""Narrow typed interfaces for math expression parsing (not physics proofs)."""

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
class ParsedExpression:
    """Structured parsed mathematical object — not a formal proof."""

    expression: str
    latex: str
    variables: tuple[str, ...]
    sympy_parsed: bool

    @property
    def verified(self) -> bool:
        """Deprecated alias for :attr:`sympy_parsed` (parse success only)."""
        return self.sympy_parsed

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "ParsedExpression",
            "expression": self.expression,
            "latex": self.latex,
            "variables": list(self.variables),
            "sympy_parsed": self.sympy_parsed,
            # Legacy key for schema callers still expecting "verified"
            "verified": self.sympy_parsed,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# Backward-compatible name
VerifiedExpression = ParsedExpression


class MathPhysicsInterface:
    """Parse expressions via SymPy charset gate — not physics verification.

    ADR: Dual-use math/physics advisors must not emit unconstrained free text.
    ``sympy_parsed=True`` means the expression parsed, not that it is proven,
    dimensionally consistent, or physically meaningful.
    """

    _SAFE_PATTERN = re.compile(r"^[a-zA-Z0-9_+\-*/^().,\s=]+$")

    def parse_and_verify(self, raw: str) -> ParsedExpression:
        """Parse a safe-charset expression. Name kept for API stability."""
        if not self._SAFE_PATTERN.match(raw.strip()):
            msg = "Expression contains disallowed characters (possible exfil vector)"
            raise ValueError(msg)
        if not SYMPY_AVAILABLE:
            return ParsedExpression(
                expression=raw.strip(),
                latex=raw.strip(),
                variables=(),
                sympy_parsed=False,
            )
        expr = sympify(raw.strip())
        variables = tuple(sorted(str(s) for s in expr.free_symbols))
        return ParsedExpression(
            expression=str(expr),
            latex=str(sympy.latex(expr)),
            variables=variables,
            sympy_parsed=True,
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
