# Contributing to A.C.E

Thanks for helping make containment more reviewable. A.C.E is a **defensive** project. Contributions that add offensive capability generation or weapons-facing tooling will be declined.

## Ground rules

1. **Honest maturity** — label research / prototype / production-bound code clearly.
2. **Evidence over narrative** — prefer tests, demos, and measurable catch rates.
3. **Fail closed** — when in doubt, block and audit; do not add silent bypasses.
4. **No secrets in PRs** — never commit tokens, keys, or proprietary model weights.

## Development setup

```bash
git clone https://github.com/FratresMedAI/A.C.E.git
cd A.C.E
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -e ".[dev]"
```

## Before you open a PR

Run the same gates CI runs:

```bash
ruff check src tests examples scripts
mypy src/aegis
pytest --cov=aegis --cov-report=term-missing --cov-fail-under=80
```

## Pull request checklist

- [ ] Clear problem statement and approach
- [ ] Tests for new behavior (or a documented reason why not)
- [ ] Docs updated if APIs, backends, or policy knobs changed
- [ ] No new hard-coded secrets or gated model defaults that require undisclosed tokens
- [ ] Maturity notes updated if you touch prototype surfaces (EE, ZK, TEE verify)

## Sandbox workloads

Callable workloads executed inside isolated backends **must** be registered:

```python
from aegis.sandbox.workloads import register_workload

@register_workload("my_workload")
def my_workload(payload: dict) -> str:
    ...
```

And imported from `aegis.sandbox._worker` (or another built-in load path) so the worker subprocess can resolve them.

## Style

- Python 3.11+ typing; strict mypy on `src/aegis`
- Ruff for lint; follow existing module layout under `src/aegis/`
- Prefer small, focused PRs over multi-concern dumps

## Security issues

Do **not** open a public issue for containment bypasses. See [SECURITY.md](SECURITY.md).

## Questions

Use GitHub Discussions/Issues for design questions, or contact Fratres X AI via [fratres-x.com](https://www.fratres-x.com).
