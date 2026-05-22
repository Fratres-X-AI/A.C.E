#!/usr/bin/env python3
"""Verify Hugging Face token + model access before loading weights."""

from __future__ import annotations

import sys

from aegis.execution.hf_runtime import hf_model_id, verify_hf_auth


def main() -> None:
    model = hf_model_id()
    result = verify_hf_auth(model)
    if result.get("ok"):
        username = result.get("username")
        if username:
            print(f"OK — logged in as @{username}, can access {model}")
        else:
            print(f"OK — public model {model} (no HF token required)")
        sys.exit(0)
    print(f"FAIL — {result.get('error', 'unknown error')}")
    if result.get("username"):
        print(f"  Token resolves to HF user: @{result['username']}")
    sys.exit(1)


if __name__ == "__main__":
    main()
