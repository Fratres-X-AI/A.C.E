#!/usr/bin/env python3
"""Generate architecture Mermaid diagram."""

from pathlib import Path

from aegis.utils.visualization import generate_architecture_mermaid


def main() -> None:
    diagram = generate_architecture_mermaid()
    out = Path(__file__).resolve().parent.parent / "docs" / "architecture_diagram.mmd"
    out.write_text(diagram, encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
