"""Window-border hit testing and unobtrusive resize affordances.

The overlay is mouse-transparent: it only draws an indication while hovering
within the resize zone, and never intercepts image editing or drag-and-drop.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


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


class ResizeHint(QWidget):
    """Thin blue line near the hovered window border; never consumes input."""

    def __init__(self, viewport):
        super().__init__(viewport)
        self.edges = Qt.Edge(0)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.hide()

    def show_edges(self, edges):
        if edges == self.edges:
            return
        self.edges = edges
        if edges:
            self.setGeometry(self.parentWidget().rect())
            self.show()
            self.raise_()
            self.update()
        else:
            self.hide()

    def paintEvent(self, event):
        if not self.edges:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor(40, 145, 185, 200), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        extent = 32
        left = 3
        right = self.width() - 4
        top = 3
        bottom = self.height() - 4
        e = self.edges
        # Draw a quiet short line at the engaged edge/corner, not a permanent frame.
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
            painter.drawLine(left, self.height() // 2 - extent, left, self.height() // 2 + extent)
        elif e & Qt.Edge.RightEdge:
            painter.drawLine(right, self.height() // 2 - extent, right, self.height() // 2 + extent)
        elif e & Qt.Edge.TopEdge:
            painter.drawLine(self.width() // 2 - extent, top, self.width() // 2 + extent, top)
        elif e & Qt.Edge.BottomEdge:
            painter.drawLine(self.width() // 2 - extent, bottom, self.width() // 2 + extent, bottom)
        painter.end()
