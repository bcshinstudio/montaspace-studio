"""Fixed-screen-size photo/video editing handles.

Graphics-item positions follow the media transform, but handle artwork ignores
that transform.  This keeps the small squares identical at any media scale.
Only the parent media item handles mouse events; no new media processing occurs.
"""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem

BLUE = QColor("#1676d2")
HANDLE_NAMES = ("tl", "tr", "bl", "br", "top", "bottom", "left", "right")


def crop_anchors(rect):
    """Return all eight grip locations as points in parent-local coordinates."""
    return {
        "tl": rect.topLeft(),
        "tr": rect.topRight(),
        "bl": rect.bottomLeft(),
        "br": rect.bottomRight(),
        "top": (rect.topLeft() + rect.topRight()) / 2,
        "bottom": (rect.bottomLeft() + rect.bottomRight()) / 2,
        "left": (rect.topLeft() + rect.bottomLeft()) / 2,
        "right": (rect.topRight() + rect.bottomRight()) / 2,
    }


class EditHandles:
    """Small, fixed-pixel boxes; callers own hit-testing and resize logic."""

    BOX_PX = 8.0

    def __init__(self, owner, rotation=False):
        self._boxes = {}
        pen = QPen(BLUE)
        pen.setWidthF(1.0)
        pen.setCosmetic(True)
        for name in HANDLE_NAMES:
            box = QGraphicsRectItem(owner)
            box.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            box.setRect(QRectF(-self.BOX_PX / 2, -self.BOX_PX / 2,
                              self.BOX_PX, self.BOX_PX))
            box.setBrush(QBrush(Qt.GlobalColor.white))
            box.setPen(pen)
            box.setZValue(1001)
            box.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            box.setAcceptHoverEvents(False)
            box.hide()
            self._boxes[name] = box
        self._rotate = None
        if rotation:
            dot = QGraphicsEllipseItem(owner)
            dot.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            dot.setRect(QRectF(-4, -4, 8, 8))
            dot.setBrush(QBrush(Qt.GlobalColor.white))
            dot.setPen(pen)
            dot.setZValue(1001)
            dot.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            dot.setAcceptHoverEvents(False)
            dot.hide()
            self._rotate = dot

    def update(self, rect, selected, crop_mode, rotation_offset=34.0):
        anchors = crop_anchors(rect)
        visible = set(HANDLE_NAMES) if selected else set()
        for name, box in self._boxes.items():
            if name in visible:
                box.setPos(anchors[name])
                box.show()
            else:
                box.hide()
        if self._rotate is not None:
            if selected and not crop_mode:
                self._rotate.setPos(rect.center().x(), rect.top() - rotation_offset)
                self._rotate.show()
            else:
                self._rotate.hide()
