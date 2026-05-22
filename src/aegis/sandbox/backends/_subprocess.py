"""Shared subprocess helpers for sandbox backends."""

from __future__ import annotations

import subprocess


def run_command(
    cmd: list[str],
    *,
    timeout: int = 120,
    input_text: str | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    import os

    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        input=input_text,
        cwd=cwd,
        env=merged,
    )


def command_succeeded(result: subprocess.CompletedProcess[str]) -> bool:
    return result.returncode == 0


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stdout or result.stderr or "").strip()


def which(binary: str) -> str | None:
    import shutil

    return shutil.which(binary)


def docker_available() -> bool:
    try:
        result = run_command(["docker", "info"], timeout=10)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
