"""Isolated image-only performance benchmark for MontaSpace Studio.

Run from the Studio repository root:
  python tools/stress_test.py 25
  python tools/stress_test.py 50
  python tools/stress_test.py 100

Uses generated solid-color JPEGs in a disposable directory. Does not test videos
or performance with real photographs. Each invocation is a fresh Python process.
"""

import json
import math
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from app.config import APP_VERSION
from app.performance import (
    memory_peak_working_set_mb,
    memory_private_mb,
    memory_working_set_mb,
)
from app.window import MontaSpace


COUNT_LIMIT = 100
DIMENSIONS = (1800, 1200)
TRANSFORM_FIELDS = ("x", "y", "scale", "rotation", "z")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def image_transforms(window):
    """A stable snapshot independent of image source paths and selection state."""
    images = [row for row in window.project_snapshot() if row["type"] == "image"]
    return sorted(
        [{field: float(row[field]) for field in TRANSFORM_FIELDS} for row in images],
        key=lambda row: row["z"],
    )


def check_restored(window, expected, stage):
    actual = image_transforms(window)
    require(len(actual) == len(expected), f"{stage}: count {len(actual)} != {len(expected)}")
    for index, (want, got) in enumerate(zip(expected, actual)):
        for field in TRANSFORM_FIELDS:
            require(
                math.isclose(got[field], want[field], rel_tol=1e-7, abs_tol=1e-5),
                f"{stage}: image {index}, {field}: {got[field]} != {want[field]}",
            )


def round_mb(value):
    return round(value, 3) if value is not None else None


def run(count):
    if not 1 <= count <= COUNT_LIMIT:
        raise ValueError(f"Choose an image count from 1 to {COUNT_LIMIT}")

    app = QApplication.instance() or QApplication([])
    window = MontaSpace()
    with tempfile.TemporaryDirectory(prefix="montaspace-studio-image-stress-") as folder:
        root = Path(folder)
        start = time.perf_counter()
        for index in range(count):
            sample = QImage(*DIMENSIONS, QImage.Format.Format_RGB32)
            sample.fill(QColor.fromHsv((index * 37) % 360, 170, 210))
            path = root / f"stress_{index:03d}.jpg"
            require(sample.save(str(path), "JPEG", 83), f"Could not generate {path}")
        generate_seconds = time.perf_counter() - start

        start = time.perf_counter()
        for index in range(count):
            path = root / f"stress_{index:03d}.jpg"
            require(window.canvas.add_image(str(path), record_undo=False), f"Could not insert {path}")
        insert_seconds = time.perf_counter() - start
        app.processEvents()
        require(len(window.canvas.image_stack()) == count, "Image count mismatch after insertion")
        rss_after_insert = memory_working_set_mb()

        for index, item in enumerate(window.canvas.image_stack()):
            item.setPos((index % 10) * 105, (index // 10) * 75)
            item.setRotation((index % 5) * 3)
            item.setScale(0.65 + (index % 3) * 0.1)
        expected = image_transforms(window)

        linked = root / "stress.mstudio"
        start = time.perf_counter()
        require(window._write_project(linked), "Linked project save failed")
        linked_save_seconds = time.perf_counter() - start
        require(linked.is_file() and linked.stat().st_size > 0, "Linked file missing or empty")

        portable = root / "stress.mstudiopack"
        start = time.perf_counter()
        require(window._write_project(portable), "Portable project save failed")
        portable_save_seconds = time.perf_counter() - start
        require(portable.is_file() and portable.stat().st_size > 0, "Portable file missing or empty")

        start = time.perf_counter()
        require(window._read_project(linked), "Linked project reopen failed")
        linked_open_seconds = time.perf_counter() - start
        check_restored(window, expected, "linked reopen")

        start = time.perf_counter()
        require(window._read_project(portable), "Portable project reopen failed")
        portable_open_seconds = time.perf_counter() - start
        check_restored(window, expected, "portable reopen")
        app.processEvents()

        rss_after_test = memory_working_set_mb()
        peak_rss = memory_peak_working_set_mb()
        footprint = memory_private_mb()
        if sys.platform == "darwin":
            for name, value in (
                ("rss_after_insert", rss_after_insert),
                ("rss_after_test", rss_after_test),
                ("peak_rss", peak_rss),
                ("physical_footprint", footprint),
            ):
                require(
                    value is not None and math.isfinite(value) and value > 0,
                    f"macOS memory reading unavailable: {name}={value!r}",
                )

        report = {
            "app": "MontaSpace Studio",
            "version": APP_VERSION,
            "scenario": "synthetic-image-only",
            "images": count,
            "image_dimensions": f"{DIMENSIONS[0]}x{DIMENSIONS[1]}",
            "generate_seconds": round(generate_seconds, 5),
            "insert_seconds": round(insert_seconds, 5),
            "linked_save_seconds": round(linked_save_seconds, 5),
            "portable_save_seconds": round(portable_save_seconds, 5),
            "linked_open_seconds": round(linked_open_seconds, 5),
            "portable_open_seconds": round(portable_open_seconds, 5),
            "working_set_after_insert_mb": round_mb(rss_after_insert),
            "working_set_after_test_mb": round_mb(rss_after_test),
            "peak_working_set_mb": round_mb(peak_rss),
            "private_memory_mb": round_mb(footprint),
            "private_memory_definition": (
                "macOS physical footprint (phys_footprint)" if sys.platform == "darwin"
                else "Windows private committed bytes" if sys.platform == "win32"
                else "unavailable"
            ),
            "linked_size_mb": round(linked.stat().st_size / (1024 * 1024), 5),
            "portable_size_mb": round(portable.stat().st_size / (1024 * 1024), 5),
            "transform_verification": "linked and portable passed",
        }

        # Make sure Qt objects holding extracted files are gone before cleanup.
        window.canvas.scene_area.clear()
        window._temp_extract = None
        window.undo_stack.clear()

    output = Path.home() / "Documents" / "MontaSpaceStudio_Test_Reports"
    output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target = output / f"MontaSpaceStudio_Stress_{timestamp}_{count}_{uuid4().hex[:8]}.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"PASS: {count} images, both project formats, transform preservation")
    print(f"Report saved: {target}")
    return report


if __name__ == "__main__":
    try:
        selected = int(sys.argv[1]) if len(sys.argv) > 1 else 25
        run(selected)
    except Exception as exc:
        print(f"STRESS TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
