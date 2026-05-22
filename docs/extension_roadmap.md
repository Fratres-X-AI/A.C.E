# A.C.E Extension Roadmap

## Phase 1 — Current (v0.1.0)

- [x] Core containment engine with layered composition
- [x] Field encryption + equivariant prototype
- [x] IFC + agent planner
- [x] Guardian stack + egress controller
- [x] Tamper-proof audit + metrics
- [x] Red-team simulator + canary
- [x] Working demos and test suite

## Phase 2 — Production Hardening

- [x] Real TEE attestation adapters (Intel TDX / AMD SEV-SNP + auto-detect factory)
- [ ] LLM-judge guardian with configurable verifier model
- [ ] Persistent audit log storage (SQLite / append-only file)
- [ ] Capability token signing with HSM integration
- [ ] Gray Swan evaluation harness integration

## Phase 3 — Scale

- [ ] Equivariant encryption for Llama-scale models (batched offline transform)
- [ ] GPU-accelerated equivariant ops
- [ ] Distributed containment for multi-agent systems
- [ ] Federated audit log aggregation

## Phase 4 — Ecosystem

- [ ] FratresCustosAI integration plugin
- [ ] Ollama / vLLM / RunPod official adapters
- [ ] DIU OT submission template pack
- [ ] Formal verification hooks (Lean / Coq integration points)
- [ ] Real ZK proof generation for high-stakes math outputs

## Known Limitations

| Component | Status | Next Step |
|-----------|--------|-----------|
| Equivariant Encryption | Research prototype | Scale + security audit |
| TEE | Intel TDX + AMD SEV-SNP adapters | DCAP/KDS production verification |
| ZK Proofs | No-op hook | Circom / Noir integration |
| LLM Judge | Rule-based fallback | Verifier model API |
| DP/Caecator | Lightweight stubs | Production noise calibration |
