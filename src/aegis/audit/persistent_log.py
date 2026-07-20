"""SQLite-backed persistent tamper-evident audit log."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aegis.audit.tamper_proof_log import LogEntry, TamperProofLog
from aegis.utils.typing import AuditEvent


@dataclass
class PersistentTamperProofLog(TamperProofLog):
    """Tamper-proof log that persists hash chain entries to SQLite.

    Survives process restarts — suitable for local audits without cloud infra.
    """

    db_path: Path = field(default_factory=lambda: Path("aegis_audit.db"))

    def __post_init__(self) -> None:
        self._ensure_schema()
        self._load_from_disk()

    def append(self, event: AuditEvent) -> LogEntry:
        entry = super().append(event)
        self._write_entry(entry)
        return entry

    def _ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_chain (
                    idx INTEGER PRIMARY KEY,
                    layer TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL
                )
                """,
            )
            conn.commit()

    def _write_entry(self, entry: LogEntry) -> None:
        ev = entry.event
        meta = json.dumps(ev.metadata, sort_keys=True)
        ts = ev.timestamp.astimezone(UTC).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_chain (
                    idx, layer, action, detail, timestamp,
                    metadata_json, prev_hash, entry_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.index,
                    ev.layer,
                    ev.action,
                    ev.detail,
                    ts,
                    meta,
                    entry.prev_hash,
                    entry.entry_hash,
                ),
            )
            conn.commit()

    def _load_from_disk(self) -> None:
        if not self.db_path.exists():
            return
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT idx, layer, action, detail, timestamp, metadata_json, "
                "prev_hash, entry_hash FROM audit_chain ORDER BY idx",
            ).fetchall()
        loaded: list[LogEntry] = []
        for row in rows:
            idx, layer, action, detail, ts, meta_json, prev_hash, entry_hash = row
            metadata: dict[str, Any] = json.loads(meta_json)
            event = AuditEvent(
                layer=layer,
                action=action,
                detail=detail,
                timestamp=datetime.fromisoformat(ts),
                metadata=metadata,
            )
            loaded.append(
                LogEntry(
                    index=idx,
                    event=event,
                    prev_hash=prev_hash,
                    entry_hash=entry_hash,
                ),
            )
        self._entries = loaded

    def export_db_snapshot(self) -> dict[str, Any]:
        """Export DB metadata for compliance packs."""
        return {
            "db_path": str(self.db_path),
            "entry_count": len(self._entries),
            "chain_valid": self.verify_chain(),
        }
