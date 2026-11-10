"""Lifecycle-only diagnostics for native Qt video objects.

Signals record destruction without retaining player, audio, dialog, or scene
objects. Counters are intentionally observation-only (no forced GC/pauses).
"""
from collections import Counter
from datetime import datetime


class VideoLifecycleDiagnostics:
    def __init__(self):
        self.next_id = 0
        self.live = {kind: set() for kind in ("video item", "media player", "audio output", "controls")}
        self.created = Counter()
        self.destroyed = Counter()
        self.release_calls = 0
        self.release_requested = set()
        self.events = []

    def observe(self, obj, kind):
        """Track C++ QObject destruction, not Python wrapper collection."""
        self.next_id += 1
        token = self.next_id
        self.live[kind].add(token)
        self.created[kind] += 1
        obj.destroyed.connect(lambda _obj=None, k=kind, t=token: self.mark_destroyed(k, t))
        return token

    def mark_destroyed(self, kind, token):
        self.live[kind].discard(token)
        self.destroyed[kind] += 1
        if kind == "video item":
            self.release_requested.discard(token)
        self.events.append((datetime.now().isoformat(timespec="seconds"), "destroyed", kind))
        if len(self.events) > 100:
            self.events.pop(0)

    def mark_release(self, token):
        self.release_calls += 1
        self.release_requested.add(token)

    def report(self):
        lines = ["Qt video lifecycle (since launch):"]
        for kind in self.live:
            lines.append(
                f"  {kind}: created {self.created[kind]}, "
                f"destroyed {self.destroyed[kind]}, still alive {len(self.live[kind])}"
            )
        lines.append(f"  release calls: {self.release_calls}")
        lines.append(f"  video items released but not destroyed: {len(self.release_requested)}")
        return "\n".join(lines)


video_lifecycle = VideoLifecycleDiagnostics()
