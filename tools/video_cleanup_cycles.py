"""MontaSpace Studio repeated video playback/release memory diagnostic.

Run from the MontaSpace Studio project root:
    python tools/video_cleanup_cycles.py

Uses one existing local MOV file, read-only. Does not modify app code or user
projects. Memory growth across cycles is reported, not classified as a leak.
"""

import gc
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from app.window import MontaSpace
from app.performance import (
    memory_working_set_mb,
    memory_peak_working_set_mb,
    memory_private_mb,
)

SAMPLE = Path.home() / "Projects/Resources/videos/sample-video-480x270-1mb.mov"
VIDEO_COUNT = 5
CYCLES = 20


def wait_with_events(milliseconds):
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def measure():
    return {
        "rss_mb": memory_working_set_mb(),
        "peak_rss_mb": memory_peak_working_set_mb(),
        "physical_footprint_mb": memory_private_mb(),
    }


def flush_deletions():
    gc.collect()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    wait_with_events(300)
    gc.collect()


def main():
    if not SAMPLE.is_file():
        raise FileNotFoundError(f"Missing read-only test video: {SAMPLE}")

    app = QApplication.instance() or QApplication([])
    window = MontaSpace()
    window.resize(1100, 700)
    window.show()
    app.processEvents()

    baseline = measure()
    cycle_reports = []
    try:
        for cycle in range(1, CYCLES + 1):
            items = []
            errors = []
            insert_start = time.perf_counter()
            try:
                for index in range(VIDEO_COUNT):
                    if not window.canvas.add_video(
                        str(SAMPLE), show_controls=False, record_undo=False
                    ):
                        raise RuntimeError(f"Cycle {cycle}: video {index + 1} insertion failed")
                    item = window.canvas._last_added_video
                    item.setPos((index % 5) * 190, 100)
                    item.audio.setMuted(True)
                    item.player.errorOccurred.connect(
                        lambda _err, msg, i=index: errors.append(
                            {"video": i + 1, "message": msg}
                        )
                    )
                    items.append(item)
                insert_seconds = time.perf_counter() - insert_start

                wait_with_events(1400)
                after_load = measure()
                for item in items:
                    item.player.play()
                wait_with_events(2500)
                positions = [item.player.position() for item in items]
                states = [str(item.player.playbackState()) for item in items]
                error_strings = [item.player.errorString() for item in items]
                during = measure()
                passed = (
                    len(items) == VIDEO_COUNT
                    and all(pos >= 500 for pos in positions)
                    and all(
                        item.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                        for item in items
                    )
                    and not errors
                    and not any(error_strings)
                )
            finally:
                for item in items:
                    item.release()
                window.canvas.scene_area.clear()
                # The canvas records the last inserted video separately.
                if hasattr(window.canvas, "_last_added_video"):
                    window.canvas._last_added_video = None
                items.clear()
                del items
                flush_deletions()
                wait_with_events(1000)
                after_release = measure()

            record = {
                "cycle": cycle,
                "videos": VIDEO_COUNT,
                "insert_seconds": round(insert_seconds, 3),
                "positions_ms": positions,
                "playback_states": states,
                "error_strings": error_strings,
                "error_signals": errors,
                "memory_after_load": after_load,
                "memory_during_playback": during,
                "memory_after_release": after_release,
                "playback_passed": passed,
            }
            cycle_reports.append(record)
            print(
                f"Cycle {cycle}: {'PASS' if passed else 'FAIL'}; "
                f"after-release RSS={after_release['rss_mb']} MB; "
                f"footprint={after_release['physical_footprint_mb']} MB",
                flush=True,
            )
            if not passed:
                raise RuntimeError(f"Cycle {cycle} playback verification failed")
    finally:
        window.canvas.stop_videos()
        window.canvas.scene_area.clear()
        window.hide()
        flush_deletions()

    first = cycle_reports[0]["memory_after_release"]
    last = cycle_reports[-1]["memory_after_release"]
    def delta(key):
        a, b = first[key], last[key]
        return round(b - a, 3) if a is not None and b is not None else None

    report = {
        "application": "MontaSpace Studio",
        "scenario": "same-process-video-play-release-cycles",
        "sample": SAMPLE.name,
        "cycles": CYCLES,
        "videos_per_cycle": VIDEO_COUNT,
        "baseline": baseline,
        "cycle_results": cycle_reports,
        "after_release_change_first_to_last_mb": {
            "rss": delta("rss_mb"),
            "physical_footprint": delta("physical_footprint_mb"),
        },
        "interpretation": "Memory growth alone does not establish a leak; Qt/FFmpeg may cache resources.",
        "all_playback_passed": all(row["playback_passed"] for row in cycle_reports),
    }
    output = Path.home() / "Documents/MontaSpaceStudio_Test_Reports"
    output.mkdir(parents=True, exist_ok=True)
    dest = output / (
        f"MontaSpaceStudio_VideoCleanup_{time.strftime('%Y%m%d_%H%M%S')}_"
        f"{uuid4().hex[:8]}.json"
    )
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["after_release_change_first_to_last_mb"], indent=2))
    print(f"Report saved: {dest}")
    print("PASS: all three playback cycles" if report["all_playback_passed"] else "FAIL")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"CYCLE TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
