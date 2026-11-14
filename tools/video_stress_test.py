"""Isolated MontaSpace Studio simultaneous video playback benchmark.

Usage: python tools/video_stress_test.py 1
       python tools/video_stress_test.py 5
       python tools/video_stress_test.py 10

Uses an existing MOV file without modifying it. Each invocation is a separate
process; reports are stored under ~/Documents/MontaSpaceStudio_Test_Reports.
"""

import json
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from app.window import MontaSpace
from app.performance import (
    memory_peak_working_set_mb,
    memory_private_mb,
    memory_working_set_mb,
)

SAMPLE = Path.home() / "Projects/Resources/videos/sample-video-480x270-1mb.mov"
COUNTS = (1, 5, 10)


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


def run(count):
    if count not in COUNTS:
        raise ValueError("Choose 1, 5, or 10 videos")
    if not SAMPLE.is_file():
        raise FileNotFoundError(f"Video sample missing: {SAMPLE}")

    app = QApplication.instance() or QApplication([])
    window = MontaSpace()
    window.resize(1000, 700)
    window.show()
    app.processEvents()

    items = []
    errors = []
    baseline = measure()
    insert_start = time.perf_counter()
    try:
        for index in range(count):
            added = window.canvas.add_video(
                str(SAMPLE), show_controls=False, record_undo=False
            )
            if not added:
                raise RuntimeError(f"Insertion rejected at video {index + 1}")
            item = window.canvas._last_added_video
            item.setPos((index % 5) * 185, (index // 5) * 175)
            item.audio.setMuted(True)
            items.append(item)
            item.player.errorOccurred.connect(
                lambda _error, message, i=index: errors.append(
                    {"video": i + 1, "message": message}
                )
            )
        insert_seconds = time.perf_counter() - insert_start

        wait_with_events(1500)
        loaded = measure()
        play_start = time.perf_counter()
        for item in items:
            item.player.play()
        wait_with_events(5000)
        elapsed = time.perf_counter() - play_start

        positions = [item.player.position() for item in items]
        states = [str(item.player.playbackState()) for item in items]
        media_errors = [item.player.errorString() for item in items]
        during = measure()
        progressed = [p >= 500 for p in positions]
        passed = all(progressed) and not errors and not any(media_errors)
    finally:
        for item in items:
            item.release()
        # Process Qt deferred deletion so cleanup memory measurements are useful.
        wait_with_events(300)
        window.canvas.scene_area.clear()
        # Hide instead of closing: Studio may prompt about an unsaved board.
        window.hide()
        wait_with_events(300)

    after = measure()
    report = {
        "application": "MontaSpace Studio",
        "scenario": "simultaneous-MOV-playback",
        "videos": count,
        "sample": SAMPLE.name,
        "playback_window_seconds": round(elapsed, 3),
        "insert_seconds": round(insert_seconds, 3),
        "positions_ms": positions,
        "playback_states_at_measurement": states,
        "error_strings": media_errors,
        "error_signals": errors,
        "all_players_advanced_at_least_500ms": all(progressed),
        "memory_before": baseline,
        "memory_after_load": loaded,
        "memory_during_playback": during,
        "memory_after_release": after,
        "mac_private_metric": "phys_footprint, not Windows private bytes",
        "passed": passed,
    }
    output = Path.home() / "Documents/MontaSpaceStudio_Test_Reports"
    output.mkdir(parents=True, exist_ok=True)
    dest = output / f"MontaSpaceStudio_Video_{time.strftime('%Y%m%d_%H%M%S')}_{count}_{uuid4().hex[:8]}.json"
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report saved: {dest}")
    if not passed:
        raise RuntimeError("One or more players failed to advance without errors")
    print(f"PASS: {count} independent video players advanced")


if __name__ == "__main__":
    try:
        run(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    except Exception as exc:
        print(f"VIDEO STRESS TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
