"""Memory-bounded preview decoding shared by MontaSpace and MontaSpace Studio.

Qt handles its native formats first. Pillow + pillow-heif is a fallback for
HEIC/HEIF/AVIF and other formats unsupported by the installed Qt plugins.
The original image file is never converted or overwritten.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader, QPixmap

from .config import PREVIEW_MAX_EDGE


def _pillow_preview(filename):
    """Decode supported Pillow formats into detached Qt-owned RGBA pixels.

    Imports are deliberately lazy: the native Qt path stays lightweight, and
    startup does not initialize an extra image decoder.
    """
    try:
        from PIL import Image, ImageOps
        from pillow_heif import register_heif_opener

        register_heif_opener()
        # AVIF support is supplied by some pillow-heif builds/versions.
        try:
            from pillow_heif import register_avif_opener
        except ImportError:
            pass
        else:
            register_avif_opener()

        with Image.open(filename) as opened:
            # Read only the first frame of multi-frame formats (e.g., GIF).
            opened.seek(0)
            # Apply EXIF rotation once; QImage won't interpret Pillow's metadata.
            oriented = ImageOps.exif_transpose(opened)
            try:
                oriented.thumbnail((PREVIEW_MAX_EDGE, PREVIEW_MAX_EDGE), Image.Resampling.LANCZOS)
                rgba = oriented.convert('RGBA')
                try:
                    raw = rgba.tobytes('raw', 'RGBA')
                    image = QImage(raw, rgba.width, rgba.height,
                                   rgba.width * 4, QImage.Format.Format_RGBA8888)
                    # A copy is mandatory: raw goes out of scope on return.
                    return QPixmap.fromImage(image.copy())
                finally:
                    rgba.close()
            finally:
                if oriented is not opened:
                    oriented.close()
    except (OSError, ValueError, RuntimeError, ImportError, SyntaxError):
        return QPixmap()


def load_preview(filename):
    """Return a preview with at most PREVIEW_MAX_EDGE pixels per dimension."""
    filename = str(Path(filename))
    # Prefer explicit HEIF/AVIF decoding rather than a missing Qt plugin.
    if Path(filename).suffix.lower() in {'.heic', '.heif', '.avif'}:
        pixmap = _pillow_preview(filename)
        if not pixmap.isNull():
            return pixmap

    reader = QImageReader(filename)
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and max(size.width(), size.height()) > PREVIEW_MAX_EDGE:
        reader.setScaledSize(size.scaled(PREVIEW_MAX_EDGE, PREVIEW_MAX_EDGE,
                                         Qt.AspectRatioMode.KeepAspectRatio))
    image = reader.read()
    if not image.isNull():
        return QPixmap.fromImage(image)
    return _pillow_preview(filename)
