# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

A.C.E is defensive security software. If you find a vulnerability in the containment framework itself:

1. **Do not** open a public GitHub issue for sensitive reports.
2. Email the FratresMedAI maintainers or use GitHub private vulnerability reporting on [FratresMedAI/A.C.E](https://github.com/FratresMedAI/A.C.E).
3. Include reproduction steps, affected module (e.g. `guardians/`, `ifc/`), and impact assessment.

We aim to acknowledge reports within 72 hours.

## Scope

**In scope:** bypass of egress guardians, IFC label violations, audit log tampering, session isolation failures, crypto implementation flaws.

**Out of scope:** vulnerabilities in underlying LLMs you connect via Ollama/RunPod; attacks requiring physical TEE hardware access unless our attestation adapter accepts invalid quotes.

## Philosophy

A.C.E assumes breach. Reports that demonstrate containment bypass with measurable blast-radius expansion are highest priority.
