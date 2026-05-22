"""Tests for sandbox worker module."""

from __future__ import annotations

import io
import json
import os
import sys
from unittest.mock import patch

from aegis.sandbox import _worker


def test_worker_echo_mode() -> None:
    payload = json.dumps({"msg": "hello"})
    with patch.object(sys, "stdin", io.StringIO(payload)), patch.object(
        sys,
        "stdout",
        new_callable=io.StringIO,
    ) as out, patch.dict(os.environ, {"ACE_WORKLOAD": "echo"}):
        _worker.main()
    assert json.loads(out.getvalue()) == {"msg": "hello"}


def test_worker_registered_mock_llm() -> None:
    import aegis.execution.mock_model  # noqa: F401 — registers mock_llm

    payload = json.dumps({"query": "summarize"})
    with patch.object(sys, "stdin", io.StringIO(payload)), patch.object(
        sys,
        "stdout",
        new_callable=io.StringIO,
    ) as out, patch.dict(os.environ, {"ACE_WORKLOAD": "mock_llm"}):
        _worker.main()
    assert out.getvalue()
