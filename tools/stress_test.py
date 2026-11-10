"""MontaSpace isolated stress test. Generates images ONLY in temporary directory.
Run: python tools/stress_test.py 50
Does not modify user photos, projects, or the normal application window.
"""
import csv
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from app.window import MontaSpace
from app.performance import memory_working_set_mb, memory_peak_working_set_mb


def run(count):
    if not 1 <= count <= 100:
        raise ValueError("Choose an image count from 1 to 100")
    app = QApplication.instance() or QApplication([])
    window = MontaSpace()
    samples = []
    with tempfile.TemporaryDirectory(prefix="montaspace-test-") as folder:
        root = Path(folder)
        start = time.perf_counter()
        for i in range(count):
            image = QImage(1800, 1200, QImage.Format.Format_RGB32)
            image.fill(QColor.fromHsv((i * 37) % 360, 170, 210))
            path = root / f"stress_{i:03d}.jpg"
            if not image.save(str(path), "JPEG", 83):
                raise RuntimeError(f"Could not generate {path}")
        generated_sec = time.perf_counter() - start
        start = time.perf_counter()
        for i in range(count):
            path = root / f"stress_{i:03d}.jpg"
            if not window.canvas.add_image(str(path), record_undo=False):
                raise RuntimeError(f"Could not insert {path}")
        load_sec = time.perf_counter() - start
        app.processEvents()
        loaded_ram = memory_working_set_mb()
        # Include a few transforms; do not alter any original files.
        for i, item in enumerate(window.canvas.image_stack()):
            item.setPos((i % 10) * 105, (i // 10) * 75)
            item.setRotation((i % 5) * 3)
            item.setScale(0.65 + (i % 3) * 0.1)
        start = time.perf_counter()
        linked = root / "stress.mspace"
        assert window._write_project(linked), "Linked project save failed"
        linked_sec = time.perf_counter() - start
        start = time.perf_counter()
        pack = root / "stress.mspacepack"
        assert window._write_project(pack), "Portable project save failed"
        portable_sec = time.perf_counter() - start
        start = time.perf_counter()
        assert window._read_project(linked), "Linked project open failed"
        linked_open_sec = time.perf_counter() - start
        assert len(window.canvas.image_stack()) == count, "Image count mismatch after reopen"
        start = time.perf_counter()
        assert window._read_project(pack), "Portable project open failed"
        portable_open_sec = time.perf_counter() - start
        assert len(window.canvas.image_stack()) == count, "Image count mismatch after portable reopen"
        report = {
            "version": "0.8.1", "images": count,
            "generated_seconds": round(generated_sec, 3),
            "insert_seconds": round(load_sec, 3),
            "linked_save_seconds": round(linked_sec, 3),
            "portable_save_seconds": round(portable_sec, 3),
            "linked_open_seconds": round(linked_open_sec, 3),
            "portable_open_seconds": round(portable_open_sec, 3),
            "ram_after_insert_mb": round(loaded_ram, 1) if loaded_ram is not None else None,
            "ram_after_test_mb": round(memory_working_set_mb() or 0, 1),
            "peak_ram_mb": round(memory_peak_working_set_mb() or 0, 1),
        }
        # Reset references before temporary files are deleted.
        window.canvas.scene_area.clear()
        window._temp_extract = None
        window.undo_stack.clear()
    print(json.dumps(report, indent=2))
    # Store reports OUTSIDE the source tree and don't overwrite previous reports.
    output = Path.home() / "Documents" / "MontaSpaceStudio_Test_Reports"
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"MontaSpaceStudio_Stress_{time.strftime('%Y%m%d_%H%M%S')}_{count}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report saved: {path}")
    # Avoid closing window (may show an unsaved-changes dialog).
    return report


if __name__ == "__main__":
    try:
        n = int(sys.argv[1]) if len(sys.argv) > 1 else 25
        run(n)
    except Exception as exc:
        print(f"STRESS TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
