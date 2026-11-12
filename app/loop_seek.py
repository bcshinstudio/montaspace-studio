"""Small, Qt-independent guard against overlapping asynchronous A/B loop seeks.

Only player position/media-status callbacks request loop jumps. Pending is
acknowledged by a position update near A. This class neither decodes frames
nor creates timers; diagnostics are small integer counters.
"""
import time


class LoopSeekGuard:
    def __init__(self):
        self.pending = False
        self.requests = 0
        self.acknowledged = 0
        self.suppressed = 0
        self._last_request_at = float('-inf')

    def reset(self):
        """Reset a pending jump after user changes A, B, or loop state."""
        self.pending = False
        self._last_request_at = float('-inf')

    @staticmethod
    def _ack_margin(a, b):
        # Avoid mistaking B for A on very short A/B selections.
        return max(20, min(200, (b - a) // 5))

    def observe_position(self, position, a, b, enabled, now=None):
        """Return True for exactly one jump request until a seek reaches A."""
        if not enabled or a is None or b is None or b <= a:
            self.reset()
            return False
        now = time.monotonic() if now is None else now
        position = int(position)
        if self.pending:
            if abs(position - a) <= self._ack_margin(a, b):
                self.pending = False
                self.acknowledged += 1
            else:
                self.suppressed += 1
            # Never jump again from the same position update that acknowledged.
            return False
        if position < b - 40:
            return False
        if now - self._last_request_at < 0.3:
            self.suppressed += 1
            return False
        return self._request(now)

    def observe_end(self, position, a, b, enabled, now=None):
        """Handle EndOfMedia without racing with positionChanged callbacks."""
        if not enabled or a is None or b is None or b <= a:
            return False
        now = time.monotonic() if now is None else now
        if self.pending or now - self._last_request_at < 0.3:
            self.suppressed += 1
            return False
        # A delayed EndOfMedia may arrive after the seek has returned to A.
        if int(position) < b - 40:
            return False
        return self._request(now)

    def _request(self, now):
        self.pending = True
        self._last_request_at = now
        self.requests += 1
        return True

    def report(self):
        return (f"loop_seek_requests={self.requests}, "
                f"seek_confirmations={self.acknowledged}, "
                f"duplicate_events_suppressed={self.suppressed}, "
                f"seek_pending={self.pending}")
