"""Egress rate limiting, bandwidth throttling, session kill."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from aegis.utils.typing import ContainmentVerdict


@dataclass
class EgressController:
    """Token-bucket rate limiter with session kill on repeated violations."""

    max_bytes_per_minute: int = 50_000
    max_violations_before_kill: int = 3
    _window_start: float = field(default_factory=time.monotonic)
    _bytes_sent: int = 0
    _violation_count: int = 0
    _killed: bool = False

    @property
    def is_killed(self) -> bool:
        return self._killed

    def reset_window_if_needed(self) -> None:
        now = time.monotonic()
        if now - self._window_start >= 60.0:
            self._window_start = now
            self._bytes_sent = 0

    def check_egress(
        self, output: str, guardian_verdict: ContainmentVerdict
    ) -> ContainmentVerdict:
        if self._killed:
            return ContainmentVerdict.KILL_SESSION

        if guardian_verdict == ContainmentVerdict.KILL_SESSION:
            self._killed = True
            self._violation_count += 1
            return ContainmentVerdict.KILL_SESSION

        if guardian_verdict in {ContainmentVerdict.BLOCK, ContainmentVerdict.THROTTLE}:
            self._violation_count += 1
            if self._violation_count >= self.max_violations_before_kill:
                self._killed = True
                return ContainmentVerdict.KILL_SESSION
            return guardian_verdict

        self.reset_window_if_needed()
        byte_len = len(output.encode("utf-8"))
        if self._bytes_sent + byte_len > self.max_bytes_per_minute:
            self._violation_count += 1
            return ContainmentVerdict.THROTTLE

        self._bytes_sent += byte_len
        return ContainmentVerdict.ALLOW

    def throttle_output(self, output: str) -> str:
        """Degrade output on throttle — containment over silent pass."""
        if len(output) <= 100:
            return "[THROTTLED]"
        return output[:100] + "\n...[EGRESS THROTTLED BY A.C.E]"

    def kill_session(self) -> None:
        self._killed = True
