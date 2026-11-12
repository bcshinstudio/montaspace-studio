"""Window-border hit testing and unobtrusive resize affordances.

The overlay is mouse-transparent: it only draws an indication while hovering
within the resize zone, and never intercepts image editing or drag-and-drop.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen


EDGE_MARGIN = 12
CORNER_MARGIN = 18


def resize_edges_for_point(position, width, height):
    """Return Qt.Edge bit flags for one of the eight border resize zones."""
    x, y = position.x(), position.y()
    edges = Qt.Edge(0)
    if x < 0 or y < 0 or x >= width or y >= height:
        return edges
    # A larger corner square makes it easier to discover diagonal resizing.
    near_left = x < CORNER_MARGIN
    near_right = x >= width - CORNER_MARGIN
    near_top = y < CORNER_MARGIN
    near_bottom = y >= height - CORNER_MARGIN
    if (near_left or near_right) and (near_top or near_bottom):
        edges |= Qt.Edge.LeftEdge if near_left else Qt.Edge.RightEdge
        edges |= Qt.Edge.TopEdge if near_top else Qt.Edge.BottomEdge
        return edges
    if x < EDGE_MARGIN:
        edges |= Qt.Edge.LeftEdge
    elif x >= width - EDGE_MARGIN:
        edges |= Qt.Edge.RightEdge
    if y < EDGE_MARGIN:
        edges |= Qt.Edge.TopEdge
    elif y >= height - EDGE_MARGIN:
        edges |= Qt.Edge.BottomEdge
    return edges


def resize_cursor(edges):
    if not edges:
        return None
    horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
    vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
    if horizontal and vertical:
        # NW/SE => forward diagonal; NE/SW => backward diagonal.
        nw_se = bool(edges & Qt.Edge.LeftEdge) == bool(edges & Qt.Edge.TopEdge)
        return Qt.CursorShape.SizeFDiagCursor if nw_se else Qt.CursorShape.SizeBDiagCursor
    return Qt.CursorShape.SizeHorCursor if horizontal else Qt.CursorShape.SizeVerCursor


class ResizeHint:
    """Draw a quiet boundary on the *existing* viewport paint surface.

    v0.5.12 used a window-sized transparent child QWidget, which could leave
    blank rectangles on Windows at startup. This object owns no native window,
    and its paint() is called by Canvas.paintEvent after scene rendering.
    """

    def __init__(self, viewport):
        self.viewport = viewport
        self.edges = Qt.Edge(0)
        self.border_visible = True

    def setGeometry(self, _rect):
        # Compatibility with the existing window resize-event handling.
        pass

    def set_border_visible(self, visible):
        if self.border_visible != bool(visible):
            self.border_visible = bool(visible)
            self.viewport.update()

    def show_edges(self, edges):
        if edges != self.edges:
            self.edges = edges
            self.viewport.update()

    def paint(self, painter):
        if not self.edges and not self.border_visible:
            return
        rect = self.viewport.rect()
        width, height = rect.width(), rect.height()
        if not width or not height:
            return
        painter.save()
        if self.border_visible:
            pen = QPen(QColor(99, 127, 154, 130))
            pen.setWidthF(1.0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
        if self.edges:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pen = QPen(QColor(40, 145, 185, 200), 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            extent = 32
            left, right, top, bottom = 3, width - 4, 3, height - 4
            e = self.edges
            if (e & Qt.Edge.LeftEdge) and (e & Qt.Edge.TopEdge):
                painter.drawLine(left, top, left + extent, top)
                painter.drawLine(left, top, left, top + extent)
            elif (e & Qt.Edge.RightEdge) and (e & Qt.Edge.TopEdge):
                painter.drawLine(right - extent, top, right, top)
                painter.drawLine(right, top, right, top + extent)
            elif (e & Qt.Edge.LeftEdge) and (e & Qt.Edge.BottomEdge):
                painter.drawLine(left, bottom - extent, left, bottom)
                painter.drawLine(left, bottom, left + extent, bottom)
            elif (e & Qt.Edge.RightEdge) and (e & Qt.Edge.BottomEdge):
                painter.drawLine(right, bottom - extent, right, bottom)
                painter.drawLine(right - extent, bottom, right, bottom)
            elif e & Qt.Edge.LeftEdge:
                painter.drawLine(left, height // 2 - extent, left, height // 2 + extent)
            elif e & Qt.Edge.RightEdge:
                painter.drawLine(right, height // 2 - extent, right, height // 2 + extent)
            elif e & Qt.Edge.TopEdge:
                painter.drawLine(width // 2 - extent, top, width // 2 + extent, top)
            elif e & Qt.Edge.BottomEdge:
                painter.drawLine(width // 2 - extent, bottom, width // 2 + extent, bottom)
        painter.restore()
