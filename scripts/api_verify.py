#!/usr/bin/env python3
"""Verify external LLM API env vars before running containment demo."""

from __future__ import annotations

import sys

from aegis.execution.api_llm_workload import verify_api_config


def main() -> None:
    result = verify_api_config()
    if result.get("ok"):
        print(f"OK — model={result.get('model')} url={result.get('url')}")
        sys.exit(0)
    print(f"FAIL — {result.get('error', 'unknown error')}")
    sys.exit(1)


if __name__ == "__main__":
    main()
