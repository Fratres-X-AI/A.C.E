# A.C.E Extension Roadmap

Honest maturity labels. Items marked done are **prototype-complete**, not production-certified.

## Phase 1 — Core (shipped)

- [x] Core containment engine with layered composition
- [x] Field encryption + weight-obfuscation demo (not HE)
- [x] IFC + agent planner
- [x] Guardian stack + egress controller
- [x] Tamper-proof audit + metrics
- [x] Red-team simulator + canary
- [x] Working demos and CI-gated test suite

## Phase 2 — Prototype hardening (current: v0.3.x)

- [x] Pluggable sandbox backends (bubblewrap / gVisor / Firecracker / Docker / process)
- [x] TEE attestation adapters (Intel TDX / AMD SEV-SNP + auto-detect factory)
- [x] HF local + Inference API integration paths
- [ ] LLM-judge guardian with configurable verifier model
- [ ] Persistent audit as default path for all demos
- [ ] Capability token signing with HSM / KMS integration
- [ ] External eval harness hooks (e.g. Gray Swan-style scenarios)

## Phase 3 — Scale

- [ ] Equivariant encryption for Llama-scale models (batched offline transform)
- [ ] GPU-accelerated equivariant ops
- [ ] Distributed containment for multi-agent systems
- [ ] Federated audit log aggregation

## Phase 4 — Ecosystem

- [ ] Fratres X AI product plugins / adapters
- [ ] Official Ollama / vLLM / RunPod adapters
- [ ] Compliance submission template pack
- [ ] Formal verification hooks (Lean / Coq integration points)
- [ ] Real ZK proof generation for high-stakes math outputs

## Component maturity

| Component | Status | Next step |
|-----------|--------|-----------|
| Core pipeline | Prototype | Broader adversarial coverage |
| Sandbox backends | Prototype | Prefer bubblewrap on bare metal for isolation claims |
| Weight obfuscation | Research demo (not crypto) | Group-correct transforms or drop claims |
| TEE | Adapters; hardware verify fail-closed | DCAP / KDS production verification |
| ZK / proofs | Placeholder digest only | Circom / Noir integration |
| gVisor / Firecracker | Registered stubs | Real rootfs + guest exec |
| LLM judge | Rule-based fallback | Verifier model API |
| DP / Laplace noise | Correct inverse-CDF formula | Crypto-grade calibration / accounting |

## Stance

Aligned with [Fratres X AI](https://www.fratres-x.com): physics and constraints before narrative, prototype honesty, adversarial thinking, defensive systems only.
