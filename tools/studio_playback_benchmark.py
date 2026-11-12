"""Automated sustained-loop test using the REAL MontaSpace Studio whiteboard.

Example:
    .venv\\Scripts\\python.exe tools\\studio_playback_benchmark.py "C:\\path\\video.mp4"

Opens one real whiteboard with five independently playing, looping video tiles,
measures working/private memory and CPU for five minutes, writes CSV/JSON,
and exits automatically. Never changes or saves the user's project/video.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.decoder_policy import configure_decoder, STUDIO_DECODER_ENV


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="One existing MP4 used for all video tiles")
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--decoder", choices=("software", "hardware", "auto"), default="software")
    parser.add_argument("--interval", type=int, default=15)
    parser.add_argument("--memory-limit-mb", type=int, default=6000)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.video.is_file() or args.video.suffix.lower() != ".mp4":
        parser.error("Provide an existing .mp4 file")
    if not 5 <= args.seconds <= 3600:
        parser.error("--seconds must be between 5 and 3600")
    if not 1 <= args.count <= 20:
        parser.error("--count must be between 1 and 20")
    if not 1 <= args.interval <= 300:
        parser.error("--interval must be between 1 and 300")
    return args


def run(args):
    os.environ[STUDIO_DECODER_ENV] = args.decoder
    decoding = configure_decoder()
    # Qt imports must be below decoder selection.
    from PySide6.QtCore import QPointF, QTimer
    from PySide6.QtWidgets import QApplication
    from PySide6.QtMultimedia import QMediaPlayer
    from app.config import APP_VERSION
    from app.window import MontaSpace
    from app.performance import memory_private_mb, memory_working_set_mb

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    board = MontaSpace()
    board.resize(1200, 730)
    board.show()
    videos = []
    for i in range(args.count):
        # Each VideoItem is a real QGraphicsVideoItem and QMediaPlayer used by Studio.
        if not board.canvas.add_video(str(args.video.resolve()),
                                      scene_pos=QPointF((i % 5) * 180, (i // 5) * 270),
                                      show_controls=False, record_undo=False):
            raise RuntimeError(f"Could not insert video {i + 1}")
        videos.append(board.canvas._last_added_video)

    outdir = (args.output_dir or
              Path.home() / "Documents" / "MontaSpaceStudio_Test_Reports")
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    name = f"Studio_Loop_{args.decoder}_{args.count}_{stamp}"
    csv_path = outdir / f"{name}.csv"
    json_path = outdir / f"{name}.json"
    fields = ["elapsed_seconds", "working_set_mb", "private_mb", "cpu_percent_one_core",
              "videos_playing", "loop_seek_requests", "seek_confirmations",
              "duplicate_events_suppressed", "pending_seeks"]
    csv_file = csv_path.open("w", encoding="utf-8", newline="", buffering=1)
    writer = csv.DictWriter(csv_file, fieldnames=fields)
    writer.writeheader()
    csv_file.flush()
    rows = []
    done = {"value": False, "reason": "duration completed"}
    started_at = {"wall": None, "cpu": None}
    last_cpu = {"wall": None, "cpu": None}
    startup_at = time.monotonic()
    deadline = {"duration": None}

    def snapshot():
        now = time.monotonic()
        cpu = time.process_time()
        elapsed = now - started_at["wall"]
        delta_wall = now - last_cpu["wall"]
        cpu_percent = (cpu - last_cpu["cpu"]) / delta_wall * 100 if delta_wall > 0 else 0.0
        last_cpu.update(wall=now, cpu=cpu)
        guards = [video._loop_seek for video in videos]
        row = {
            "elapsed_seconds": round(elapsed, 2),
            "working_set_mb": memory_working_set_mb(),
            "private_mb": memory_private_mb(),
            "cpu_percent_one_core": round(cpu_percent, 1),
            "videos_playing": sum(v.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState for v in videos),
            "loop_seek_requests": sum(g.requests for g in guards),
            "seek_confirmations": sum(g.acknowledged for g in guards),
            "duplicate_events_suppressed": sum(g.suppressed for g in guards),
            "pending_seeks": sum(g.pending for g in guards),
        }
        writer.writerow(row)
        csv_file.flush()  # Useful partial report even if the run is interrupted.
        rows.append(row)
        print(f"{row['elapsed_seconds']:6.1f}s  private={row['private_mb']} MB  "
              f"CPU(one core)={cpu_percent:.0f}%  loops={row['loop_seek_requests']}  "
              f"playing={row['videos_playing']}", flush=True)
        if row["private_mb"] is not None and row["private_mb"] >= args.memory_limit_mb:
            done["reason"] = f"stopped at memory safety limit {args.memory_limit_mb} MB"
            finish()
        elif now >= deadline["duration"]:
            finish()

    measure_timer = QTimer()
    measure_timer.setInterval(args.interval * 1000)
    measure_timer.timeout.connect(snapshot)
    # Keep QTimer instances independent of the board: never refer to UI button controls.
    start_timer = QTimer()
    start_timer.setInterval(200)

    def start_playback():
        if done["value"]:
            return
        durations = [v.player.duration() for v in videos]
        if min(durations) <= 0 and time.monotonic() - startup_at < 20:
            return
        start_timer.stop()
        if min(durations) <= 0:
            done["reason"] = "media metadata failed to load"
            finish()
            return
        for v, duration in zip(videos, durations):
            a = 0
            b = max(1000, duration - 250)
            v.set_loop_a(a)
            v.set_loop_b(b)
            v.set_loop_enabled(True)
            v.player.play()
        started_at.update(wall=time.monotonic(), cpu=time.process_time())
        last_cpu.update(wall=started_at["wall"], cpu=started_at["cpu"])
        deadline["duration"] = started_at["wall"] + args.seconds
        print(f"Starting {args.count} simultaneous looping video tiles; "
              f"decoder={decoding}; run={args.seconds}s", flush=True)
        measure_timer.start()
        QTimer.singleShot(1000, snapshot)
        QTimer.singleShot(args.seconds * 1000 + 1500, finish)

    def finish():
        if done["value"]:
            return
        done["value"] = True
        measure_timer.stop()
        start_timer.stop()
        summary = {
            "version": APP_VERSION, "test": "real_studio_simultaneous_loop_playback",
            "decoder": decoding, "count": args.count, "source_name": args.video.name,
            "duration_seconds": args.seconds, "end_reason": done["reason"],
            "measurements": rows,
        }
        json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        csv_file.close()
        print(f"CSV saved: {csv_path}\nJSON saved: {json_path}", flush=True)
        board.canvas.stop_videos()
        board.canvas.scene_area.clear()
        # No closeEvent (which prompts to save changes) for disposable test board.
        board.hide()
        board.deleteLater()
        app.quit()

    start_timer.timeout.connect(start_playback)
    start_timer.start()
    QTimer.singleShot(25000, lambda: finish() if started_at["wall"] is None else None)
    app.exec()
    # This test is only for a disposable board. No projects were opened/saved.
    return 0 if done["reason"] == "duration completed" else 1


def main():
    args = parse_args()
    try:
        return run(args)
    except Exception as exc:
        print(f"PLAYBACK BENCHMARK ERROR: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
