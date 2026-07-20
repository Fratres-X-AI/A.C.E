# A.C.E Architecture

## Design Philosophy

A.C.E assumes breach. Neural networks compress information lossily — emergent side channels and adaptive attacks mean perfect blocking is impossible. The architecture therefore focuses on **containment**: auditable layers that limit what exits in usable form.

## Layer ADRs

### ADR-001: Assume Breach, Contain Egress

**Decision:** Prioritize egress control over input blocking.

**Rationale:** Red-team exercises demonstrate that determined adversaries find compression side channels. Measuring and limiting outbound information density is more defensible than claiming impermeable perimeters.

### ADR-002: Information Flow Control (Bell-LaPadula)

**Decision:** Enforce no-read-up and no-write-down on explicit label flows.

**Rationale:** IFC cannot stop all implicit flows through neural mixing, but it prevents *explicit* declassification without gates — a common agent failure mode.

### ADR-003: Field-Level Encryption

**Decision:** Selective encryption of sensitive input fields, not full-payload encryption.

**Rationale:** Reduces in-memory plaintext exposure. Does not eliminate side channels but shrinks blast radius for credential/PII fields.

### ADR-004: Equivariant Encryption (Prototype)

**Decision:** Offline orthogonal similarity transforms for a weight-obfuscation demo.

**Rationale:** Useful for teaching linear equivariance under `T`. **Limitation:** Not encryption, not HE; nonlinear activations are not equivariant under arbitrary orthogonal `T`.

**Physics analogy:** Lossy compression is like turbulent mixing — you cannot unmix, but you can limit what reaches the outlet.

### ADR-005: Multi-Layer Guardians

**Decision:** Stack regex, entropy, canary, and anomaly detection — fail-closed.

**Rationale:** No single detector catches all exfil vectors. Layered defense with throttle/kill degrades rather than silently passes.

### ADR-006: Tamper-Evident Audit

**Decision:** Hash-chained append-only log for every containment decision.

**Rationale:** External reviews and compliance packs need reconstructable audit trails. Optional DP noise applies only to exported aggregates.

### ADR-007: TEE Abstraction

**Decision:** Protocol-based TEE interface with simulation stub.

**Rationale:** Real deployments (TDX, SEV-SNP, NVIDIA CC) vary by platform. Clean interface enables swap without engine rewrite.

## Data Flow

1. **Ingress:** Payload → field encryption → label assignment → IFC clearance check
2. **Execution:** TEE attestation → instrumented runner → model inference
3. **Egress:** Guardian scan → structured verification → egress controller
4. **Audit:** Every layer appends to hash chain → metrics updated

## Meta-Containment

The red-team simulator applies the guardian stack to itself — containment layers are tested by the same adversarial harness they defend against.
