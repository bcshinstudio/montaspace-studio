"""Optimized thumbnail/image preview decoding."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImageReader
from .config import PREVIEW_MAX_EDGE


def load_preview(filename):
    """Decode images at display resolution rather than full camera resolution.

    This reduces peak RAM when opening large photos. Image transforms and crops
    remain non-destructive; original files are kept for portable project saving.
    """
    reader = QImageReader(str(filename))
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and max(size.width(), size.height()) > PREVIEW_MAX_EDGE:
        reader.setScaledSize(size.scaled(
            PREVIEW_MAX_EDGE,
            PREVIEW_MAX_EDGE,
            Qt.AspectRatioMode.KeepAspectRatio,
        ))
    image = reader.read()
    return QPixmap.fromImage(image) if not image.isNull() else QPixmap()
