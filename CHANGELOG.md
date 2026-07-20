# Changelog

All notable changes to A.C.E are documented here.  
Format inspired by [Keep a Changelog](https://keepachangelog.com/). Versioning follows SemVer where practical for a prototype stack.

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

[0.3.0]: https://github.com/FratresMedAI/A.C.E/releases/tag/v0.3.0
