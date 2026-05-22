"""Rich console output and Mermaid diagram generation."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def print_layer_activation(layer: str, status: str, detail: str = "") -> None:
    """Print a containment layer activation event."""
    color = {"PASS": "green", "BLOCK": "red", "WARN": "yellow"}.get(status, "cyan")
    body = detail or status
    console.print(Panel(body, title=f"[{color}]{layer}[/{color}]", border_style=color))


def print_metrics_table(metrics: dict[str, float | int]) -> None:
    """Render containment metrics as a Rich table."""
    table = Table(title="Containment Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    for key, value in sorted(metrics.items()):
        table.add_row(key, str(value))
    console.print(table)


def generate_architecture_mermaid() -> str:
    """Generate the layered architecture Mermaid diagram."""
    return """flowchart TB
    subgraph ingress [Ingress]
        Input[UserInput]
        EncFields[EncryptionFields]
        EE[EquivariantTransform]
        Labels[IFCLabels]
    end
    subgraph execution [Execution]
        TEE[TEEAbstraction]
        Runner[InstrumentedRunner]
        MathPhys[MathPhysicsInterface]
    end
    subgraph egress [Egress]
        Guardian[OutputGuardian]
        EgressCtrl[EgressController]
        Verify[StructuredVerification]
    end
    subgraph audit [Audit]
        Log[TamperProofLog]
        Metrics[ContainmentMetrics]
    end
    subgraph redteam [RedTeam]
        Sim[ContainmentSimulator]
        Canary[CanaryTokens]
    end
    Input --> EncFields --> EE --> Labels
    Labels --> TEE --> Runner --> MathPhys
    Runner --> Guardian --> Verify --> EgressCtrl
    Guardian --> Log
    EgressCtrl --> Log
    Log --> Metrics
    Sim -.-> ingress
    Sim -.-> egress
    Canary -.-> Guardian"""
