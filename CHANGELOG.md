# Changelog

All notable changes to A.C.E are documented here.  
Format inspired by [Keep a Changelog](https://keepachangelog.com/). Versioning follows SemVer where practical for a prototype stack.

## [Unreleased]

## [0.3.1] — 2026-07-20

### Fixed

- Laplace DP noise now uses correct inverse-CDF sampling (was not Laplace)
- Field encryption keeps ciphertext until explicit `decrypt_for_inference`
- TEE verification fails closed for hardware-backed quotes (no length check)
- IFC integrity: `dominates()` on READ; join uses Biba meet (min integrity)
- Exfil tests prove tunnel/guardian blocks, not IFC short-circuits
- Compliance artifact version field tracks package version

### Changed

- Renamed ZK attach API to proof placeholder (legacy `zk_proof` key retained)
- Math outputs report `sympy_parsed` (not “verified” as proof)
- Equivariant module documented as weight obfuscation demo; random seed
- gVisor / Firecracker `is_available()` always False until functional
- Linux auto-order: bubblewrap → docker → process
- Docs: compliance export wording (no DIU-specific framing)

## [0.3.0] — 2026-05-22

### Added

- Pluggable sandbox registry: bubblewrap, gVisor, Firecracker, Docker, Windows Sandbox, process (RunPod nested-container fallback)
- Hugging Face local runtime + loopback server workload (`hf_llm`)
- OpenAI-compatible Inference API workload (`api_llm`) with HF Router defaults
- RunPod smoke / HF / API setup scripts and quickstart docs
- Registered `exfil_demo` workload for sandbox exfil demos
- Draft brand assets under `docs/assets/`

### Fixed

- RunPod IFC block on HF demo (`PUBLIC`/`PUBLIC` labels for smoke path)
- HF auth token pass-through and ungated Qwen default for local weights
- Sandbox worker registration for HF / API / exfil workloads
- CI ruff / mypy issues around optional HF dependencies

### Changed

- README compliance section renamed (generic compliance notes)
- Default API path uses `https://router.huggingface.co/v1` + `HF_TOKEN`

## [0.2.0] — prior

- Integrated sandbox + tunnel pipeline (`process_integrated`)
- TEE platform adapters (Intel TDX / AMD SEV-SNP + factory)
- Persistent audit log and compliance export helpers

## [0.1.0] — prior

- Core containment engine, IFC, guardians, audit, red-team simulator
- Initial demos and test suite

[0.3.0]: https://github.com/Fratres-X-AI/A.C.E/releases/tag/v0.3.0
