"""Pure, reusable edge/corner hit testing for photo and video editors.

Distances are in *screen pixels*. The caller converts its local coordinates
by the current item scale; no Qt imports, timers, or media work are involved.
"""


def hit_rect_edge(x, y, left, top, right, bottom, tolerance=12.0,
                  corner_tolerance=19.0):
    """Find a resize/crop edge, prioritizing corners over the edge bands.

    Any point in a thin strip along any edge is draggable. Near a corner,
    diagonal resizing wins, even between the visible square and the boundary.
    Return None only for points outside both the edge and corner hit areas.
    """
    if not (left <= right and top <= bottom):
        return None
    if not (left - corner_tolerance <= x <= right + corner_tolerance and
            top - corner_tolerance <= y <= bottom + corner_tolerance):
        return None

    horiz = min(((abs(x - left), "left"), (abs(x - right), "right")))
    vert = min(((abs(y - top), "top"), (abs(y - bottom), "bottom")))
    # On very small media, never let opposing corner zones swallow an
    # entire side: the middle of each edge must remain independently usable.
    corner_x = min(corner_tolerance, (right - left) * 0.25)
    corner_y = min(corner_tolerance, (bottom - top) * 0.25)
    if horiz[0] <= corner_x and vert[0] <= corner_y:
        return {("left", "top"): "tl", ("right", "top"): "tr",
                ("left", "bottom"): "bl", ("right", "bottom"): "br"}[
                    (horiz[1], vert[1])]

    if not (left - tolerance <= x <= right + tolerance and
            top - tolerance <= y <= bottom + tolerance):
        return None
    if horiz[0] <= tolerance and horiz[0] <= vert[0]:
        return horiz[1]
    if vert[0] <= tolerance:
        return vert[1]
    if horiz[0] <= tolerance:
        return horiz[1]
    return None
