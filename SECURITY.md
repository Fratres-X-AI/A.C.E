# Security Policy

A.C.E is **defensive** containment software from [Fratres X AI](https://www.fratres-x.com). We assume breach. Reports that demonstrate containment bypass with measurable blast-radius expansion are highest priority.

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | Yes |
| < 0.3   | Best effort |

## Reporting a vulnerability

1. **Do not** open a public GitHub issue for sensitive containment bypasses.
2. Use [GitHub private vulnerability reporting](https://github.com/FratresMedAI/A.C.E/security/advisories/new) on `FratresMedAI/A.C.E`, or contact Fratres X AI via [fratres-x.com](https://www.fratres-x.com).
3. Include: reproduction steps, affected module (e.g. `guardians/`, `ifc/`, `sandbox/`), expected vs actual behavior, and impact assessment.

We aim to acknowledge reports within **72 hours**.

## Scope

**In scope**

- Egress guardian bypass
- IFC label violations that should have been blocked
- Audit log tampering or chain breaks
- Session / sandbox isolation failures attributable to A.C.E
- Cryptographic implementation flaws in A.C.E modules

**Out of scope**

- Vulnerabilities in third-party LLMs or inference providers you connect
- Attacks requiring physical TEE compromise, unless our attestation adapter accepts invalid quotes as valid
- Social engineering of operators
- Denial of service against public infrastructure outside this repository

## Safe harbor

We will not pursue legal action against good-faith researchers who:

- Avoid privacy violations, data destruction, and service disruption beyond what is needed to demonstrate the issue
- Do not exploit the finding beyond proof of concept
- Report promptly and keep details private until a fix or coordinated disclosure window ends

## Philosophy

Perfect perimeter blocking is not the claim. A.C.E succeeds when egress is controlled, measured, and auditable under adversarial pressure.
