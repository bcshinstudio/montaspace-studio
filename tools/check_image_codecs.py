"""Diagnose real image decoding with the exact project Python environment.

Usage: python tools/check_image_codecs.py example.HEIC
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    try:
        import PIL
        import pillow_heif
        from PySide6.QtWidgets import QApplication
        from app.imaging import load_preview
    except ImportError as exc:
        print(f"FAIL: Missing image decoder dependency: {exc}")
        print("Install dependencies: .venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return 2
    print('Pillow:', PIL.__version__)
    print('pillow-heif:', getattr(pillow_heif, '__version__', 'installed'))
    app = QApplication.instance() or QApplication([])
    if len(sys.argv) < 2:
        print('Image decoder dependencies are present. Supply a file to test real decoding.')
        return 0
    source = Path(sys.argv[1])
    if not source.is_file():
        print('FAIL: File not found:', source)
        return 2
    pixmap = load_preview(source)
    if pixmap.isNull():
        print('FAIL: Could not decode:', source)
        return 1
    print(f'PASS: Decoded {source.name} at {pixmap.width()}x{pixmap.height()} preview pixels')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
