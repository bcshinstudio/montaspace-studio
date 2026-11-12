r"""Opt-in Windows video whiteboard stress test (does not alter video files).

Run (from project root):
  .venv\Scripts\python.exe tools\video_stability_test.py "C:\path\to\clip.mp4"

For each of 5, 10, and 20 items, measures process memory, validates linked
save/reopen, and checks that Qt video objects are eventually destroyed. No
videos are played automatically. An optional portable run is available for
small projects; embedding N copies can be large and is intentionally opt-in.
"""
import argparse
import gc
import json
import os
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from app.config import APP_VERSION
from app.performance import memory_private_mb, memory_working_set_mb, memory_peak_working_set_mb
from app.video_diagnostics import video_lifecycle
from app.window import MontaSpace


def pump_events(app, seconds=0.15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.025)


def memory():
    return {
        'working_set_mb': memory_working_set_mb(),
        'private_mb': memory_private_mb(),
        'peak_working_set_mb': memory_peak_working_set_mb(),
    }


def measure(app, video, count, portable):
    window = MontaSpace()
    # Tests use a separate hidden whiteboard window, not the user's projects.
    baseline = memory()
    inserted_at = time.perf_counter()
    for i in range(count):
        if not window.canvas.add_video(video, show_controls=False, record_undo=False):
            raise RuntimeError('Video insertion rejected')
        item = window.canvas._last_added_video
        item.setPos((i % 5) * 120, (i // 5) * 100)
    insert_sec = time.perf_counter() - inserted_at
    pump_events(app, 0.4)
    if len(window.canvas.video_items()) != count:
        raise RuntimeError('Video count differs after insert')
    after_insert = memory()
    before_release_alive = {k: len(v) for k, v in video_lifecycle.live.items()}
    with tempfile.TemporaryDirectory(prefix='montaspace-studio-stability-') as folder:
        root = Path(folder)
        linked = root / 'stability.mstudio'
        start = time.perf_counter()
        if not window._write_project(linked):
            raise RuntimeError('Linked save failed')
        linked_save_sec = time.perf_counter() - start
        start = time.perf_counter()
        if not window._read_project(linked):
            raise RuntimeError('Linked reopen failed')
        linked_open_sec = time.perf_counter() - start
        if len(window.canvas.video_items()) != count:
            raise RuntimeError('Video count differs after linked reopen')
        pack_seconds = None
        if portable:
            pack = root / 'stability.mstudiopack'
            start = time.perf_counter()
            if not window._write_project(pack):
                raise RuntimeError('Portable save failed')
            pack_save = time.perf_counter() - start
            start = time.perf_counter()
            if not window._read_project(pack):
                raise RuntimeError('Portable reopen failed')
            pack_open = time.perf_counter() - start
            if len(window.canvas.video_items()) != count:
                raise RuntimeError('Video count differs after portable reopen')
            pack_seconds = {'save_seconds': round(pack_save, 3),
                            'open_seconds': round(pack_open, 3)}
        after_roundtrip = memory()
        window.canvas.stop_videos()
        window.canvas.scene_area.clear()
        window.undo_stack.clear()
        window._temp_extract = None
        pump_events(app, 0.35)
    # Avoid closeEvent: it may show a discard-changes confirmation.
    window.deleteLater()
    del window
    gc.collect()
    pump_events(app, 0.7)
    after_cleanup = memory()
    alive_after = {k: len(v) for k, v in video_lifecycle.live.items()}
    report = {
        'video_count': count, 'insert_seconds': round(insert_sec, 3),
        'linked_save_seconds': round(linked_save_sec, 3),
        'linked_open_seconds': round(linked_open_sec, 3),
        'portable': pack_seconds,
        'baseline': baseline, 'after_insert': after_insert,
        'after_roundtrip': after_roundtrip, 'after_cleanup': after_cleanup,
        'qt_alive_before_cleanup': before_release_alive,
        'qt_alive_after_cleanup': alive_after,
        'note': 'Retained Windows working set alone does not establish a memory leak.',
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path, help='Existing MP4; never modified')
    parser.add_argument('--counts', nargs='+', type=int, default=[5, 10, 20])
    parser.add_argument('--portable', action='store_true',
                        help='Also test potentially large portable video archives')
    args = parser.parse_args()
    video = args.video.resolve()
    if not video.is_file() or video.suffix.lower() != '.mp4':
        parser.error('Provide the path to an existing MP4 file')
    if not args.counts or any(x < 1 or x > 20 for x in args.counts):
        parser.error('Each video count must be between 1 and 20')
    app = QApplication.instance() or QApplication([])
    results = []
    for count in args.counts:
        print(f'Checking {count} video tiles...', flush=True)
        results.append(measure(app, str(video), count, args.portable))
    report = {
        'version': APP_VERSION, 'test': 'video_stability',
        'media_filename': video.name, 'media_bytes': video.stat().st_size,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'results': results,
    }
    output = Path.home() / 'Documents' / 'MontaSpaceStudio_Test_Reports'
    output.mkdir(parents=True, exist_ok=True)
    filename = output / f"Studio_Video_Stability_{time.strftime('%Y%m%d_%H%M%S')}.json"
    filename.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    print(f'Report: {filename}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'STABILITY TEST FAILED: {type(exc).__name__}: {exc}', file=sys.stderr)
        raise SystemExit(1)
