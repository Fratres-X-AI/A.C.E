"""Tamper-evident append-only audit logging."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC
from typing import Any

from aegis.utils.typing import AuditEvent


@dataclass
class LogEntry:
    """Single hash-chained log entry."""

    index: int
    event: AuditEvent
    prev_hash: str
    entry_hash: str = ""


@dataclass
class TamperProofLog:
    """Append-only hash-chained tamper-evident audit log.

    ADR: Every containment decision must be reconstructable from the chain.
    Optional DP noise applies only to exported aggregates, never to the chain.
    """

    _entries: list[LogEntry] = field(default_factory=list)
    _genesis_hash: str = "0" * 64

    @property
    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    def append(self, event: AuditEvent) -> LogEntry:
        """Append an audit event and extend the hash chain."""
        prev = self._entries[-1].entry_hash if self._entries else self._genesis_hash
        index = len(self._entries)
        payload = self._serialize(index, event, prev)
        entry_hash = hashlib.sha256(payload.encode()).hexdigest()
        entry = LogEntry(
            index=index, event=event, prev_hash=prev, entry_hash=entry_hash
        )
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """Verify integrity of the full hash chain."""
        prev = self._genesis_hash
        for entry in self._entries:
            if entry.prev_hash != prev:
                return False
            expected = hashlib.sha256(
                self._serialize(entry.index, entry.event, entry.prev_hash).encode(),
            ).hexdigest()
            if entry.entry_hash != expected:
                return False
            prev = entry.entry_hash
        return True

    def export_events(self, dp_epsilon: float | None = None) -> list[dict[str, Any]]:
        """Export events; optional DP noise on numeric metadata only."""
        events = [asdict(e.event) for e in self._entries]
        if dp_epsilon is not None and dp_epsilon > 0:
            from aegis.crypto.primitives import add_laplace_noise

            for ev in events:
                meta = ev.get("metadata", {})
                if isinstance(meta, dict) and "count" in meta:
                    meta["count"] = add_laplace_noise(float(meta["count"]), dp_epsilon)
        return events

    @staticmethod
    def _serialize(index: int, event: AuditEvent, prev_hash: str) -> str:
        ts = event.timestamp.astimezone(UTC).isoformat()
        payload = {
            "index": index,
            "layer": event.layer,
            "action": event.action,
            "detail": event.detail,
            "timestamp": ts,
            "metadata": event.metadata,
            "prev_hash": prev_hash,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))
