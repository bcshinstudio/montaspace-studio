"""Movable, rotatable, scalable, non-destructively croppable photo item."""
from PySide6.QtCore import Qt, QRectF, QLineF
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import QGraphicsItem
from .edit_handles import EditHandles, crop_anchors
from .edge_hit import hit_rect_edge


class ImageItem(QGraphicsItem):
    """One movable image. Cropping changes the view, not the image file."""

    HANDLE_SIZE = 12.0

    CROP_HANDLE_SIZE = 20.0

    CROP_GRAB_MARGIN = 12.0

    ROTATE_OFFSET = 34.0

    MIN_SCALE = 0.05

    MAX_SCALE = 20.0

    MIN_CROP = 12.0

    def __init__(self, pixmap, filename=""):
        super().__init__()
        self.filename = str(filename)
        self.pixmap = pixmap
        self.full_rect = QRectF(0, 0, pixmap.width(), pixmap.height())
        self.crop_rect = QRectF(self.full_rect)
        self.crop_mode = False
        self.crop_before_edit = None
        self._mode = None
        self._handle = None
        self._start_scale = 1.0
        self._start_rotation = 0.0
        self._start_angle = 0.0
        self._start_distance = 1.0
        self._crop_start_rect = None
        self._press_pos = None
        self._undo_start = None

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setTransformOriginPoint(self.full_rect.center())
        self._edit_handles = EditHandles(self, rotation=True)
        self._refresh_handles()

    def _refresh_handles(self):
        self._edit_handles.update(self.crop_rect, self.isSelected(),
                                  self.crop_mode, self.ROTATE_OFFSET)

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change in (QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged,
                      QGraphicsItem.GraphicsItemChange.ItemScaleHasChanged):
            self._refresh_handles()
            self.update()
        return result

    def handles(self):
        """All eight resize/crop positions; rotation remains photo-only."""
        size = 8.0 / max(self.scale(), 0.05)
        half = size / 2
        result = {
            name: QRectF(point.x() - half, point.y() - half, size, size)
            for name, point in crop_anchors(self.crop_rect).items()
        }
        if not self.crop_mode:
            point = self.crop_rect.center()
            result["rotate"] = QRectF(point.x() - half,
                                      self.crop_rect.top() - self.ROTATE_OFFSET - half,
                                      size, size)
        return result

    def boundingRect(self):
        margin = self.ROTATE_OFFSET + self.HANDLE_SIZE + 6
        if self.crop_mode:
            margin = max(margin, self.CROP_HANDLE_SIZE / max(self.scale(), 0.05))
        return self.full_rect.adjusted(-margin, -margin, margin, margin)

    def shape(self):
        path = QPainterPath()
        path.addRect(self.full_rect if self.crop_mode else self.crop_rect)
        if self.isSelected():
            padding = self.CROP_GRAB_MARGIN / max(self.scale(), 0.05)
            for rect in self.handles().values():
                path.addRect(rect.adjusted(-padding, -padding, padding, padding))
        return path

    def handle_at(self, pos):
        """Use the entire border, not just the visible eight handle squares."""
        if not self.isSelected():
            return None
        # Preserve the photo-only rotation control in its existing location.
        if hasattr(self, "_edit_handles") and getattr(self._edit_handles, "_rotate", None) is not None and not self.crop_mode:
            rotate_rect = self.handles().get("rotate")
            if rotate_rect is not None:
                padding = 7.0 / max(self.scale(), 0.05)
                if rotate_rect.adjusted(-padding, -padding, padding, padding).contains(pos):
                    return "rotate"
        r = self.crop_rect
        scale = max(self.scale(), 0.05)
        return hit_rect_edge(pos.x(), pos.y(), r.left(), r.top(), r.right(), r.bottom(),
                             tolerance=13.0 / scale, corner_tolerance=20.0 / scale)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if self.crop_mode:
            painter.setOpacity(0.30)
            painter.drawPixmap(self.full_rect, self.pixmap, self.full_rect)
            painter.setOpacity(1.0)

        painter.save()
        painter.setClipRect(self.crop_rect)
        painter.drawPixmap(self.full_rect, self.pixmap, self.full_rect)
        painter.restore()

        if not self.isSelected():
            return
        # All handle squares are separate fixed-size children. Only the
        # border and photo rotation stem are painted in item coordinates.
        pen = QPen(QColor("#1676d2"))
        pen.setWidthF(1.0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.crop_rect)
        if not self.crop_mode:
            painter.drawLine(
                self.crop_rect.center().x(), self.crop_rect.top(),
                self.crop_rect.center().x(), self.crop_rect.top() - self.ROTATE_OFFSET,
            )

    def start_crop(self):
        if self.crop_mode:
            return
        self.crop_before_edit = QRectF(self.crop_rect)
        self.crop_mode = True
        self.setSelected(True)
        self._refresh_handles()
        self.update()

    def end_crop(self, apply):
        if not self.crop_mode:
            return
        if not apply:
            self.crop_rect = QRectF(self.crop_before_edit)
        self.crop_before_edit = None
        self.crop_mode = False
        self._mode = None
        self._refresh_handles()
        self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Route through Canvas so editing gets priority over overlapping images.
            views = self.scene().views() if self.scene() else []
            if views and hasattr(views[0], "begin_crop"):
                views[0].begin_crop(self)
            else:
                self.start_crop()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.scene():
            self._undo_start = self.scene().views()[0].capture_state()
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.handle_at(event.pos())
            if handle:
                self._handle = handle
                self._press_pos = event.pos()
                if self.crop_mode:
                    self._mode = "crop"
                    self._crop_start_rect = QRectF(self.crop_rect)
                else:
                    center = self.mapToScene(self.transformOriginPoint())
                    line = QLineF(center, event.scenePos())
                    if handle == "rotate":
                        self._mode = "rotate"
                        self._start_rotation = self.rotation()
                        self._start_angle = line.angle()
                    else:
                        self._mode = "resize"
                        self._start_scale = self.scale()
                        self._start_distance = max(line.length(), 1.0)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mode == "crop":
            dx = event.pos().x() - self._press_pos.x()
            dy = event.pos().y() - self._press_pos.y()
            r = self._crop_start_rect
            left, right, top, bottom = r.left(), r.right(), r.top(), r.bottom()
            if self._handle in ("tl", "bl", "left"):
                left = min(max(left + dx, self.full_rect.left()), right - self.MIN_CROP)
            if self._handle in ("tr", "br", "right"):
                right = max(min(right + dx, self.full_rect.right()), left + self.MIN_CROP)
            if self._handle in ("tl", "tr", "top"):
                top = min(max(top + dy, self.full_rect.top()), bottom - self.MIN_CROP)
            if self._handle in ("bl", "br", "bottom"):
                bottom = max(min(bottom + dy, self.full_rect.bottom()), top + self.MIN_CROP)
            self.crop_rect = QRectF(left, top, right - left, bottom - top)
            self._refresh_handles()
            self.update()
            event.accept()
            return

        if self._mode in ("resize", "rotate"):
            center = self.mapToScene(self.transformOriginPoint())
            line = QLineF(center, event.scenePos())
            if self._mode == "rotate":
                self.setRotation(self._start_rotation + self._start_angle - line.angle())
            else:
                scale = self._start_scale * max(line.length(), 1.0) / self._start_distance
                self.setScale(max(self.MIN_SCALE, min(self.MAX_SCALE, scale)))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_editing = bool(self._mode)
        self._mode = None
        self._handle = None
        if not was_editing:
            super().mouseReleaseEvent(event)
        else:
            event.accept()
        if self._undo_start is not None and self.scene():
            canvas = self.scene().views()[0]
            if not self.crop_mode:
                canvas.record_edit(self._undo_start, "Move / transform image")
            self._undo_start = None

    def hoverMoveEvent(self, event):
        name = self.handle_at(event.pos())
        if name in ("tl", "br"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif name in ("tr", "bl"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif name in ("left", "right"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif name in ("top", "bottom"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif name == "rotate":
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)
