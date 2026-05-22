"""Named workload registry for isolated sandbox worker execution."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

_REGISTRY: dict[str, Callable[[dict[str, Any]], str]] = {}
_REVERSE: dict[int, str] = {}


def register_workload(
    name: str,
) -> Callable[[Callable[[dict[str, Any]], str]], Callable[[dict[str, Any]], str]]:
    """Decorator to register a named workload callable."""

    def decorator(
        fn: Callable[[dict[str, Any]], str],
    ) -> Callable[[dict[str, Any]], str]:
        _REGISTRY[name] = fn
        _REVERSE[id(fn)] = name
        return fn

    return decorator


def get_workload(name: str) -> Callable[[dict[str, Any]], str]:
    if name not in _REGISTRY:
        msg = f"Workload {name!r} not registered"
        raise KeyError(msg)
    return _REGISTRY[name]


def resolve_workload_name(fn: Callable[[dict[str, Any]], str]) -> str | None:
    return _REVERSE.get(id(fn))


def list_workloads() -> list[str]:
    return sorted(_REGISTRY.keys())


def run_workload(name: str, payload: dict[str, Any]) -> str:
    return get_workload(name)(payload)


@register_workload("echo")
def _echo(payload: dict[str, Any]) -> str:
    return json.dumps(payload)
