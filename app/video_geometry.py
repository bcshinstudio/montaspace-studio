"""Pure geometry helpers for Qt video presentation (no decoding or GUI state)."""
import math


def effective_frame_size(width, height, surface_rotation=0, frame_rotation=0,
                         metadata_size=None, metadata_rotation=0):
    """Return displayed pixel dimensions, applying Qt's frame rotations once.

    QVideoFrame rotation is applied on top of QVideoFrameFormat rotation.
    Metadata orientation is a fallback when the decoder reports no rotation;
    metadata resolution may already be rotated to presentation orientation.
    """
    width, height = float(width), float(height)
    if not (math.isfinite(width) and math.isfinite(height) and width > 0 and height > 0):
        return None
    surface = int(surface_rotation) % 360
    frame = int(frame_rotation) % 360
    angle = (surface + frame) % 360
    if not angle and metadata_rotation:
        angle = int(metadata_rotation) % 360
    if angle in (90, 270):
        width, height = height, width
    if metadata_size is not None:
        mw, mh = metadata_size
        if mw > 0 and mh > 0:
            # Qt backends vary in whether they report encoded or presented
            # resolution. Only enforce this when the independent metadata
            # explicitly reports portrait vs landscape (rather than square).
            md_portrait = mw < mh
            frame_portrait = width < height
            if md_portrait != frame_portrait and not (surface or frame or metadata_rotation):
                width, height = height, width
    return width, height


def fit_video_size(width, height, nominal_height=236.0):
    """Use a single presentation ratio for the video item and edit handles."""
    if not width or not height or width <= 0 or height <= 0:
        return None
    return nominal_height * float(width) / float(height), float(nominal_height)


def scaled_crop(crop, old_size, new_size):
    """Rebase a non-destructive crop when actual frame dimensions arrive."""
    ox, oy, ow, oh = crop
    old_w, old_h = old_size
    new_w, new_h = new_size
    return (ox * new_w / old_w, oy * new_h / old_h,
            ow * new_w / old_w, oh * new_h / old_h)
