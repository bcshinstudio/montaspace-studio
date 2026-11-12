"""Video scene item and non-modal playback dialog with A/B loop controls."""
from pathlib import Path
import math
import time

from PySide6.QtCore import Qt, QSizeF, QSize, QUrl, QRectF, QLineF
from PySide6.QtGui import QBrush, QColor, QPen, QPainterPath, QFont, QPixmap
from PySide6.QtWidgets import (
    QStyle,
    QStyleOptionSlider,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
    QGraphicsPixmapItem,
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QGraphicsItem,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QMediaMetaData
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from .video_diagnostics import video_lifecycle
from .loop_seek import LoopSeekGuard
from .video_geometry import effective_frame_size, fit_video_size
from .edit_handles import EditHandles, crop_anchors
from .edge_hit import hit_rect_edge
from .video_poster import poster_cache


def fmt_time(ms):
    seconds = max(0, int(ms) // 1000)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class VideoItem(QGraphicsVideoItem):
    """One video, decoded by Qt on demand (not copied into an image pixmap)."""

    MIN_SCALE = 0.15
    MAX_SCALE = 8.0
    MIN_CROP = 12.0
    CROP_HANDLE_SIZE = 20.0
    HANDLE_SIZE = 12.0
    CROP_GRAB_MARGIN = 14.0

    def __init__(self, filename):
        super().__init__()
        self.filename = str(Path(filename).resolve())
        self.setSize(QSizeF(420, 236))
        # Keep a neutral renderer until we know the video's presentation ratio.
        # After orientation is resolved we set the *same* aspect for the native
        # video surface and selection handles, with no intermediate letterbox.
        self.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.setTransformOriginPoint(self.boundingRect().center())
        self.crop_rect = QRectF(self.boundingRect())
        self.crop_mode = False
        self.crop_before_edit = None
        self._mode = None
        self._handle = None
        self._crop_start_rect = None
        self._press_pos = None
        self._resume_after_crop = False
        self._frame_presentation_size = None
        self._frame_geometry_locked = False
        self._project_geometry_pinned = False
        self._poster_geometry_confirmed = False
        self._cached_frame_geometry = None
        self._video_metadata_rotation = 0
        self._crop_clip_on = False
        self._video_metadata_size = None
        self._start_scale = 1.0
        self._start_distance = 1.0
        # Independent view-only settings. Never modify or re-encode the MP4.
        self.content_zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )
        self.setAcceptHoverEvents(True)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.65)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self)
        self.player.setSource(QUrl.fromLocalFile(self.filename))
        # QGraphicsVideoItem may paint no visible frame until playback begins.
        # Keep a clearly identifiable video tile visible on a reopened board,
        # without starting playback or allocating a decoded video thumbnail.
        self._placeholder = QGraphicsRectItem(self.crop_rect, self)
        self._placeholder.setBrush(QBrush(QColor(32, 43, 56)))
        self._placeholder.setPen(QPen(QColor(90, 108, 123)))
        self._placeholder.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)
        self._placeholder.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._poster_pixmap = None
        self._poster_image = QGraphicsPixmapItem(self._placeholder)
        self._poster_image.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._poster_image.hide()
        # The fallback deliberately has no multiline description extending
        # outside the video tile. A real poster is shown without any overlay.
        self._placeholder_icon = QGraphicsSimpleTextItem('▶', self._placeholder)
        self._placeholder_icon.setBrush(QBrush(QColor(216, 228, 243)))
        icon_font = QFont()
        icon_font.setPointSize(22)
        self._placeholder_icon.setFont(icon_font)
        self._placeholder_icon.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._placeholder_text = QGraphicsSimpleTextItem('', self._placeholder)
        self._placeholder_text.setBrush(QBrush(QColor(216, 228, 243)))
        label_font = QFont()
        label_font.setPointSize(9)
        self._placeholder_text.setFont(label_font)
        self._placeholder_text.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        # Selection/crop handles are child graphics items, not transient paint
        # commands on the video texture. Qt tracks their old and new regions.
        self._selection_border = QGraphicsRectItem(self)
        self._selection_border.setBrush(Qt.BrushStyle.NoBrush)
        border_pen = QPen(QColor("#1676d2"))
        border_pen.setWidthF(1.0)
        border_pen.setCosmetic(True)
        self._selection_border.setPen(border_pen)
        self._selection_border.setZValue(1000)
        self._selection_border.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._selection_border.hide()
        # One lightweight overlay per video; handles stay 8 screen pixels
        # regardless of the video scale, instead of growing with the MP4.
        self._edit_handles = EditHandles(self)
        # Hide the tile as soon as Qt renders a decoded frame.
        self.videoSink().videoFrameChanged.connect(self._on_video_frame)
        # Qt's nativeSize accounts for the presentation format of video frames.
        # Metadata can arrive before the first decoded frame, so read it as well.
        self.nativeSizeChanged.connect(self._on_native_size_changed)
        self.player.metaDataChanged.connect(self._on_media_metadata_changed)
        self.player.positionChanged.connect(self._handle_position_changed)
        self.player.mediaStatusChanged.connect(self._handle_media_status)
        self._controls = None
        self.loop_a_ms = None
        self.loop_b_ms = None
        self.loop_enabled = False
        self._loop_seek = LoopSeekGuard()
        self._released = False
        self.history_id = None  # Assigned by Canvas; never stored as a QObject in Undo.
        self._move_undo_before = None
        self._diagnostic_token = video_lifecycle.observe(self, "video item")
        video_lifecycle.observe(self.player, "media player")
        video_lifecycle.observe(self.audio, "audio output")
        self._refresh_placeholder_geometry()
        self._refresh_selection_geometry()
        self._sync_crop_clip()
        # A single optional background poster extraction is shared by all
        # videos. If ffmpeg is unavailable, the fallback remains until play.
        poster_cache.request(self.filename, self._set_poster)

    def base_rect(self):
        return QRectF(self.boundingRect())

    def visible_rect(self):
        """The active video aperture in local scene units."""
        return QRectF(self.crop_rect)

    @staticmethod
    def _degrees(rotation):
        """Convert QtVideo::Rotation and older angle enums to an integer."""
        try:
            return int(getattr(rotation, "value", rotation)) % 360
        except (TypeError, ValueError):
            return 0

    def _on_native_size_changed(self, native_size):
        """Early sizing hint before a decoded frame exists."""
        if self._released or self._frame_geometry_locked or self._project_geometry_pinned:
            return
        if native_size.width() <= 0 or native_size.height() <= 0:
            return
        width, height = native_size.width(), native_size.height()
        if self._video_metadata_size is not None:
            # Use metadata if available; native size may be encoded landscape
            # for a rotated portrait smartphone recording.
            width, height = self._video_metadata_size
        elif self._video_metadata_rotation in (90, 270):
            width, height = height, width
        self._resize_to_presentation(width, height)

    def refresh_display_geometry(self):
        """One-shot geometry check on selection; never starts the decoder."""
        if self._released or self._project_geometry_pinned:
            return
        if self._cached_frame_geometry is not None:
            self._resize_to_presentation(*self._cached_frame_geometry)
        elif self._video_metadata_size is not None:
            self._resize_to_presentation(*self._video_metadata_size)
        else:
            size = self.nativeSize()
            if size.width() > 0 and size.height() > 0:
                width, height = size.width(), size.height()
                if self._video_metadata_rotation in (90, 270):
                    width, height = height, width
                self._resize_to_presentation(width, height)
        self._refresh_selection_geometry()

    def _resize_to_presentation(self, width, height):
        if self._project_geometry_pinned:
            return
        desired = fit_video_size(width, height)
        if desired is None:
            return
        old = self.base_rect()
        if old.width() <= 0 or old.height() <= 0:
            return
        new_width, new_height = desired
        if abs(old.width() - new_width) < 0.1 and abs(old.height() - new_height) < 0.1:
            # A known display ratio allows Qt to fill the same edit rectangle.
            self.setAspectRatioMode(Qt.AspectRatioMode.IgnoreAspectRatio)
            return

        def rebase(rect):
            return QRectF(
                (rect.x() - old.x()) / old.width() * new_width,
                (rect.y() - old.y()) / old.height() * new_height,
                rect.width() / old.width() * new_width,
                rect.height() / old.height() * new_height,
            )

        next_crop = rebase(self.crop_rect)
        before = rebase(self.crop_before_edit) if self.crop_before_edit is not None else None
        # Full repaint ONCE before/after geometry changes clears the old pixels
        # and old selection handles. Never do this for every video frame.
        views = list(self.scene().views()) if self.scene() is not None else []
        for view in views:
            view.viewport().update()
        self.setSize(QSizeF(new_width, new_height))
        self.setAspectRatioMode(Qt.AspectRatioMode.IgnoreAspectRatio)
        self.setTransformOriginPoint(self.base_rect().center())
        self.crop_rect = self._normalized_crop_rect(next_crop)
        self.crop_before_edit = before
        self._clamp_pan()
        self._refresh_placeholder_geometry()
        self._refresh_selection_geometry()
        self._sync_crop_clip()
        self.update()
        for view in views:
            view.viewport().update()
        if self.scene() is not None:
            for view in views:
                if hasattr(view, "window") and hasattr(view.window, "update_modified_title"):
                    view.window.update_modified_title()

    def verified_display_size(self):
        """Store only resolved display geometry, never the temporary 420x236 tile."""
        if self._frame_geometry_locked or self._poster_geometry_confirmed or self._project_geometry_pinned:
            size = self.size()
            if size.width() > 0 and size.height() > 0:
                return [round(size.width(), 4), round(size.height(), 4)]
        return None

    def restore_display_size(self, width, height):
        """Freeze saved display ratio until the first decoded frame without autoplay.

        The Qt renderer is allowed to change decoded frames, but native-size
        metadata arriving asynchronously must not change the whiteboard edit
        rectangle that was saved by the user.
        """
        if self._released or width <= 0 or height <= 0:
            return
        if self._project_geometry_pinned:
            return
        self._resize_to_presentation(width, height)
        self._project_geometry_pinned = True
        self._refresh_selection_geometry()

    def restore_saved_crop(self, crop, saved_size):
        """Map crop geometry saved under older aspect ratios to the current item."""
        sw, sh = float(saved_size[0]), float(saved_size[1])
        bounds = self.base_rect()
        rect = QRectF(crop)
        converted = QRectF(
            rect.x() / sw * bounds.width(),
            rect.y() / sh * bounds.height(),
            rect.width() / sw * bounds.width(),
            rect.height() / sh * bounds.height(),
        )
        self.set_content_view(crop_rect=converted)

    def _normalized_crop_rect(self, rect):
        bounds = self.base_rect()
        left = max(bounds.left(), min(rect.left(), bounds.right() - self.MIN_CROP))
        top = max(bounds.top(), min(rect.top(), bounds.bottom() - self.MIN_CROP))
        right = min(bounds.right(), max(rect.right(), left + self.MIN_CROP))
        bottom = min(bounds.bottom(), max(rect.bottom(), top + self.MIN_CROP))
        return QRectF(left, top, right - left, bottom - top)

    def _sync_crop_clip(self):
        """Clip the underlying Qt video item to its crop, not just the overlay.

        QGraphicsVideoItem can use a native paint path. Enforce QGraphicsItem's
        shape clipping when cropped to prevent picture extending beyond handles.
        Leave clipping disabled for an unedited video (lower paint overhead).
        """
        clipped = not self.crop_mode and self.visible_rect() != self.base_rect()
        if clipped == self._crop_clip_on:
            return
        self._crop_clip_on = clipped
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsToShape, clipped)
        # One full viewport repaint after changing clip state erases previous
        # native-video pixels. This is not done for ordinary playback frames.
        if self.scene() is not None:
            for view in self.scene().views():
                view.viewport().update()

    def geometry_report(self):
        """Read-only diagnostics; no extra frame decoding or media allocations."""
        size = self.size()
        native = self.nativeSize()
        rect = self.visible_rect()
        frame = self._frame_presentation_size
        return (f"file={Path(self.filename).name}, "
                f"item={size.width():.1f}x{size.height():.1f}, "
                f"native={native.width():.1f}x{native.height():.1f}, "
                f"frame={frame}, "
                f"crop=({rect.x():.1f},{rect.y():.1f},"
                f"{rect.width():.1f},{rect.height():.1f}), "
                f"crop_mode={self.crop_mode}, "
                f"geometry_locked={self._frame_geometry_locked}, "
                f"{self._loop_seek.report()}")

    def _set_poster(self, pixmap):
        """Show an already cached low-resolution image (never start playback)."""
        if self._released or pixmap is None or pixmap.isNull():
            return
        self._poster_pixmap = pixmap
        if (not self._frame_geometry_locked and not self._project_geometry_pinned
                and pixmap.width() > 0 and pixmap.height() > 0):
            self._resize_to_presentation(pixmap.width(), pixmap.height())
            self._poster_geometry_confirmed = True
        self._poster_image.show()
        self._placeholder_icon.hide()
        self._placeholder_text.hide()
        self._refresh_placeholder_geometry()

    def _refresh_placeholder_geometry(self):
        if self._placeholder is None:
            return
        crop = self.visible_rect()
        self._placeholder.setRect(crop)
        bounds = self.base_rect()
        if self._poster_pixmap is not None and not self._poster_pixmap.isNull():
            # Draw poster in the same full video frame as the Qt player; the
            # placeholder parent's shape clips it to the current crop.
            scaled = self._poster_pixmap.scaled(
                QSize(max(1, round(bounds.width())), max(1, round(bounds.height()))),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._poster_image.setPixmap(scaled)
            self._poster_image.setPos(bounds.center().x() - scaled.width() / 2,
                                      bounds.center().y() - scaled.height() / 2)
            return
        self._placeholder_icon.setPos(
            crop.center().x() - self._placeholder_icon.boundingRect().width() / 2,
            crop.center().y() - 33,
        )
        filename = Path(self.filename).name
        font_metrics = self._placeholder_text.font()
        from PySide6.QtGui import QFontMetrics
        label = QFontMetrics(font_metrics).elidedText(
            filename, Qt.TextElideMode.ElideMiddle, max(10, int(crop.width() - 18))
        )
        self._placeholder_text.setText(label)
        self._placeholder_text.setPos(
            crop.center().x() - self._placeholder_text.boundingRect().width() / 2,
            crop.center().y() + 12,
        )

    def _refresh_selection_geometry(self):
        """Update screen-sized handles and the thin, noninteractive border."""
        selected = self.isSelected()
        if selected:
            self._selection_border.setRect(self.visible_rect())
        self._selection_border.setVisible(selected)
        self._edit_handles.update(self.crop_rect, selected, self.crop_mode)

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if bool(value):
                self.refresh_display_geometry()
            self._refresh_selection_geometry()
            if self.scene() is not None:
                for view in self.scene().views():
                    view.viewport().update()
        elif change == QGraphicsItem.GraphicsItemChange.ItemScaleHasChanged:
            self._refresh_selection_geometry()
        return result

    def handles(self):
        """Media-local hit regions around the fixed-screen-size handle points."""
        size = 8.0 / max(self.scale(), 0.05)
        half = size / 2.0
        return {
            name: QRectF(point.x() - half, point.y() - half, size, size)
            for name, point in crop_anchors(self.crop_rect).items()
        }

    def shape(self):
        path = QPainterPath()
        path.addRect(self.base_rect() if self.crop_mode else self.visible_rect())
        if self.isSelected():
            padding = self.CROP_GRAB_MARGIN / max(self.scale(), 0.05)
            for rect in self.handles().values():
                path.addRect(rect.adjusted(-padding, -padding, padding, padding))
        return path

    def contains(self, point):
        return self.visible_rect().contains(point)

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

    def _clamp_pan(self):
        """Pan stays inside the cropped area enlarged by content zoom."""
        extent_x = (self.content_zoom - 1.0) * self.visible_rect().width() / 2.0
        extent_y = (self.content_zoom - 1.0) * self.visible_rect().height() / 2.0
        self.pan_x = max(-extent_x, min(extent_x, self.pan_x))
        self.pan_y = max(-extent_y, min(extent_y, self.pan_y))

    def set_content_view(self, zoom=None, crop=None, crop_rect=None, pan_x=None, pan_y=None):
        """Apply only scene rendering changes; leave QMediaPlayer untouched."""
        if zoom is not None:
            self.content_zoom = max(1.0, min(4.0, float(zoom)))
        if crop_rect is not None:
            self.crop_rect = self._normalized_crop_rect(QRectF(crop_rect))
        elif crop is not None:
            # Backward compatibility with older symmetric crop persistence.
            inset = max(0.0, min(0.30, float(crop)))
            base = self.base_rect()
            self.crop_rect = self._normalized_crop_rect(
                base.adjusted(base.width() * inset, base.height() * inset,
                              -base.width() * inset, -base.height() * inset)
            )
        if pan_x is not None:
            self.pan_x = float(pan_x)
        if pan_y is not None:
            self.pan_y = float(pan_y)
        self._clamp_pan()
        self._refresh_placeholder_geometry()
        self._refresh_selection_geometry()
        self._sync_crop_clip()
        self.update()
        if self.scene() is not None:
            self.scene().update(self.sceneBoundingRect())

    def paint(self, painter, option, widget=None):
        """Crop and zoom live Qt video painting without rendering extra frames."""
        full = self.base_rect()
        cropped = self.visible_rect()
        default_crop = cropped == full

        if self.crop_mode:
            painter.save()
            painter.setOpacity(0.30)
            super().paint(painter, option, widget)
            painter.restore()

        if self.content_zoom == 1.0 and default_crop and not self.crop_mode:
            super().paint(painter, option, widget)
        else:
            painter.save()
            painter.setClipRect(cropped)
            center = cropped.center()
            painter.translate(center.x() + self.pan_x, center.y() + self.pan_y)
            painter.scale(self.content_zoom, self.content_zoom)
            painter.translate(-center.x(), -center.y())
            super().paint(painter, option, widget)
            painter.restore()

    def _on_media_metadata_changed(self):
        """Read metadata without decoding an extra frame."""
        if self._released:
            return
        meta = self.player.metaData()
        try:
            size = meta.value(QMediaMetaData.Key.Resolution)
        except RuntimeError:
            size = None
        # Some PySide6 wheels cannot convert QtVideo::Rotation to Python.
        # Keep metadata optional; the first valid video frame provides
        # presentation geometry when playback begins.
        try:
            orientation = meta.value(QMediaMetaData.Key.Orientation)
        except (RuntimeError, TypeError):
            orientation = None
        degrees = self._degrees(orientation)
        self._video_metadata_rotation = degrees
        if size is not None and hasattr(size, "width"):
            width, height = size.width(), size.height()
            if width > 0 and height > 0:
                if degrees in (90, 270):
                    width, height = height, width
                self._video_metadata_size = (width, height)
        if not self._frame_geometry_locked and not self._project_geometry_pinned and self._video_metadata_size is not None:
            self._resize_to_presentation(*self._video_metadata_size)

    def _on_video_frame(self, frame):
        """Inspect only the FIRST valid frame; no per-frame Python processing."""
        if self._frame_geometry_locked or self._released or not frame.isValid():
            return
        self._placeholder.hide()
        size = frame.size()
        if size.width() <= 0 or size.height() <= 0:
            return
        surface_rotation = 0
        frame_rotation = 0
        try:
            surface_rotation = self._degrees(frame.surfaceFormat().rotation())
        except (AttributeError, RuntimeError):
            pass
        try:
            frame_rotation = self._degrees(frame.rotation())
        except (AttributeError, RuntimeError):
            pass
        proposed = effective_frame_size(
            size.width(), size.height(), surface_rotation, frame_rotation,
            metadata_size=self._video_metadata_size,
            metadata_rotation=self._video_metadata_rotation,
        )
        if proposed is None:
            return
        self._cached_frame_geometry = proposed
        self._frame_presentation_size = proposed
        self._frame_geometry_locked = True
        self._resize_to_presentation(*proposed)
        # Poster extraction is a separate one-shot, time-bounded operation.
        # Do not convert playback frames on each reopen/Undo: repeated native
        # conversions can be expensive on hardware-backed QVideoFrames.
        try:
            self.videoSink().videoFrameChanged.disconnect(self._on_video_frame)
        except (RuntimeError, TypeError):
            pass

    def controls(self, parent):
        if self._controls is None:
            self._controls = VideoControls(self, parent)
            self._controls.finished.connect(lambda _result: setattr(self, '_controls', None))
        self._controls.show()
        self._controls.raise_()
        self._controls.activateWindow()

    def toggle_controls(self, parent):
        """Open/close this video's playback dialog without changing playback."""
        if self._released:
            return
        if self._controls is not None:
            dialog = self._controls
            self._controls = None
            dialog.close()
        else:
            self.controls(parent)

    def toggle_playback(self):
        """Play/pause on demand; do not create or display playback controls."""
        if self._released:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def start_crop(self):
        if self.crop_mode:
            return
        self.crop_before_edit = QRectF(self.crop_rect)
        self.crop_mode = True
        self._sync_crop_clip()  # Show the full video while choosing crop edges.
        self._mode = None
        self._handle = None
        self._crop_start_rect = None
        self._press_pos = None
        self._resume_after_crop = (
            self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        )
        if self._resume_after_crop:
            self.player.pause()
        self.setSelected(True)
        self._refresh_selection_geometry()
        self.update()

    def end_crop(self, apply):
        if not self.crop_mode:
            return
        if not apply and self.crop_before_edit is not None:
            self.crop_rect = QRectF(self.crop_before_edit)
            self._clamp_pan()
            self._refresh_placeholder_geometry()
        self.crop_before_edit = None
        self.crop_mode = False
        self._sync_crop_clip()
        self._mode = None
        self._handle = None
        self._crop_start_rect = None
        self._press_pos = None
        if self._resume_after_crop and not self._released:
            self.player.play()
        self._resume_after_crop = False
        self._refresh_selection_geometry()
        self.update()
        if self.scene() is not None:
            self.scene().update(self.sceneBoundingRect())

    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.LeftButton and not self.crop_mode
                and self.scene() is not None and self.scene().views()):
            canvas = self.scene().views()[0]
            if not canvas._restoring:
                self._move_undo_before = canvas.capture_state()
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.handle_at(event.pos())
            if handle:
                self._handle = handle
                self._press_pos = event.pos()
                if self.crop_mode:
                    self._mode = "crop"
                    self._crop_start_rect = QRectF(self.crop_rect)
                else:
                    self._mode = "resize"
                    self._start_scale = self.scale()
                    center = self.mapToScene(self.transformOriginPoint())
                    line = QLineF(center, event.scenePos())
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
            base = self.base_rect()
            if self._handle in ("tl", "bl", "left"):
                left = min(max(left + dx, base.left()), right - self.MIN_CROP)
            if self._handle in ("tr", "br", "right"):
                right = max(min(right + dx, base.right()), left + self.MIN_CROP)
            if self._handle in ("tl", "tr", "top"):
                top = min(max(top + dy, base.top()), bottom - self.MIN_CROP)
            if self._handle in ("bl", "br", "bottom"):
                bottom = max(min(bottom + dy, base.bottom()), top + self.MIN_CROP)
            self.crop_rect = QRectF(left, top, right - left, bottom - top)
            self._clamp_pan()
            self._refresh_placeholder_geometry()
            self._refresh_selection_geometry()
            self.update()
            if self.scene() is not None:
                for view in self.scene().views():
                    view.viewport().update()
            event.accept()
            return
        if self._mode == "resize":
            center = self.mapToScene(self.transformOriginPoint())
            line = QLineF(center, event.scenePos())
            new_scale = self._start_scale * max(line.length(), 1.0) / self._start_distance
            self.setScale(max(self.MIN_SCALE, min(self.MAX_SCALE, new_scale)))
            self._refresh_selection_geometry()
            if self.scene() is not None:
                for view in self.scene().views():
                    view.viewport().update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._mode in ("crop", "resize"):
            editing = self._mode
            self._mode = None
            self._handle = None
            before = self._move_undo_before
            self._move_undo_before = None
            if self.scene() is not None:
                canvas = self.scene().views()[0]
                if editing == "resize" and before is not None:
                    canvas.record_edit(before, "Resize video")
                else:
                    canvas.window.update_modified_title()
            event.accept()
            return
        super().mouseReleaseEvent(event)
        if self._move_undo_before is not None and self.scene() is not None:
            before = self._move_undo_before
            self._move_undo_before = None
            self.scene().views()[0].record_edit(before, "Move video")

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
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    def release(self):
        """Permanently release Qt/FFmpeg resources before removing the video.

        This is only called for deletion, New/Open, or application shutdown;
        regular Pause/Play and A–B looping are unaffected.
        """
        if self._released:
            return
        self._released = True
        video_lifecycle.mark_release(self._diagnostic_token)
        self.loop_enabled = False
        self._loop_seek.reset()

        if self._controls is not None:
            dialog = self._controls
            self._controls = None
            dialog.close()
            dialog.deleteLater()

        try:
            self.player.positionChanged.disconnect(self._handle_position_changed)
        except (RuntimeError, TypeError):
            pass
        try:
            self.player.mediaStatusChanged.disconnect(self._handle_media_status)
        except (RuntimeError, TypeError):
            pass

        self.player.stop()
        self.player.setSource(QUrl())
        self.player.setVideoOutput(None)
        self.player.setAudioOutput(None)
        self.player.deleteLater()
        self.audio.deleteLater()

    def stop(self):
        """Backward-compatible alias used by existing project operations."""
        self.release()

    def has_valid_loop(self):
        return (
            self.loop_a_ms is not None
            and self.loop_b_ms is not None
            and self.loop_b_ms > self.loop_a_ms
        )

    def set_loop_a(self, value_ms):
        self._loop_seek.reset()
        self.loop_a_ms = max(0, int(value_ms))
        if self.loop_b_ms is not None and self.loop_b_ms <= self.loop_a_ms:
            self.loop_enabled = False

    def set_loop_b(self, value_ms):
        self._loop_seek.reset()
        self.loop_b_ms = max(0, int(value_ms))
        if self.loop_a_ms is not None and self.loop_b_ms <= self.loop_a_ms:
            self.loop_enabled = False

    def clear_loop(self):
        self._loop_seek.reset()
        self.loop_a_ms = None
        self.loop_b_ms = None
        self.loop_enabled = False

    def set_loop_enabled(self, enabled):
        self._loop_seek.reset()
        self.loop_enabled = bool(enabled) and self.has_valid_loop()

    def _jump_to_loop_start(self):
        """Perform an already-authorized loop seek; never issue a second one."""
        if self._released or not (self.loop_enabled and self.has_valid_loop()):
            return
        self.player.setPosition(self.loop_a_ms)
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self.player.play()

    def _handle_position_changed(self, pos):
        if self._released:
            return
        if self._loop_seek.observe_position(
                pos, self.loop_a_ms, self.loop_b_ms,
                self.loop_enabled and self.has_valid_loop()):
            self._jump_to_loop_start()

    def _handle_media_status(self, status):
        if self._released:
            return
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self._loop_seek.observe_end(
                self.player.position(), self.loop_a_ms, self.loop_b_ms,
                self.loop_enabled and self.has_valid_loop()):
            self._jump_to_loop_start()


class VideoSeekSlider(QSlider):
    """Seek to the clicked track position, not just a relative page step.

    QSlider.sliderMoved fires for thumb drags but not for ordinary groove clicks.
    Respect normal handle dragging; translate a groove click to the exact
    timestamp, matching mainstream media player timeline behavior.
    """

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        pointer = event.position().toPoint()
        handle = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, option,
            QStyle.SubControl.SC_SliderHandle, self,
        )
        if handle.contains(pointer):
            super().mousePressEvent(event)
            return
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, option,
            QStyle.SubControl.SC_SliderGroove, self,
        )
        if self.orientation() == Qt.Orientation.Horizontal:
            half = handle.width() // 2
            start = groove.x() + half
            span = max(1, groove.width() - handle.width())
            at = pointer.x() - start
        else:
            half = handle.height() // 2
            start = groove.y() + half
            span = max(1, groove.height() - handle.height())
            at = pointer.y() - start
        value = QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), at, span,
            self.invertedAppearance(),
        )
        self.setValue(value)
        event.accept()


class VideoControls(QDialog):
    """Non-modal player controls with A/B loop and view controls."""

    def __init__(self, video, parent):
        super().__init__(parent)
        self.video = video
        self._view_before = None
        video_lifecycle.observe(self, "controls")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle(f"Video — {Path(video.filename).name}")
        self.resize(490, 320)
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.play = QPushButton('Play')
        self.play.clicked.connect(self.toggle_playback)
        row.addWidget(self.play)
        self.backward = QPushButton('−5 s')
        self.backward.clicked.connect(lambda: self.seek_by(-5000))
        row.addWidget(self.backward)
        self.forward = QPushButton('+5 s')
        self.forward.clicked.connect(lambda: self.seek_by(5000))
        row.addWidget(self.forward)
        layout.addLayout(row)

        self.seek = VideoSeekSlider(Qt.Orientation.Horizontal)
        self.seek.setRange(0, max(video.player.duration(), 0))
        self._pending_seek_ms = None
        self._pending_seek_at = 0.0
        self.seek.valueChanged.connect(self._seek_to)
        layout.addWidget(self.seek)

        self.clock = QLabel('00:00 / 00:00')
        layout.addWidget(self.clock)

        loop_grid = QGridLayout()
        self.set_a = QPushButton('Set A')
        self.set_a.clicked.connect(self.capture_a)
        loop_grid.addWidget(self.set_a, 0, 0)
        self.a_label = QLabel('A: not set')
        loop_grid.addWidget(self.a_label, 0, 1)
        self.goto_a = QPushButton('Go A')
        self.goto_a.clicked.connect(self.go_a)
        loop_grid.addWidget(self.goto_a, 0, 2)

        self.set_b = QPushButton('Set B')
        self.set_b.clicked.connect(self.capture_b)
        loop_grid.addWidget(self.set_b, 1, 0)
        self.b_label = QLabel('B: not set')
        loop_grid.addWidget(self.b_label, 1, 1)
        self.goto_b = QPushButton('Go B')
        self.goto_b.clicked.connect(self.go_b)
        loop_grid.addWidget(self.goto_b, 1, 2)
        layout.addLayout(loop_grid)

        bottom = QHBoxLayout()
        self.enable_loop = QCheckBox('Loop A–B')
        self.enable_loop.toggled.connect(self.toggle_loop)
        bottom.addWidget(self.enable_loop)
        self.clear = QPushButton('Clear loop')
        self.clear.clicked.connect(self.clear_loop)
        bottom.addWidget(self.clear)
        bottom.addStretch(1)
        layout.addLayout(bottom)

        view_grid = QGridLayout()
        view_grid.addWidget(QLabel('Content zoom'), 0, 0)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(100, 400)
        self.zoom_slider.setSingleStep(25)
        self.zoom_slider.setValue(round(video.content_zoom * 100))
        self.zoom_slider.valueChanged.connect(self.update_view)
        self.zoom_slider.sliderPressed.connect(self._begin_view_drag)
        self.zoom_slider.sliderReleased.connect(self._end_view_drag)
        view_grid.addWidget(self.zoom_slider, 0, 1)
        self.zoom_label = QLabel(f'{video.content_zoom:.2f}×')
        view_grid.addWidget(self.zoom_label, 0, 2)
        reset_view_button = QPushButton('Reset View')
        reset_view_button.clicked.connect(self.reset_view)
        view_grid.addWidget(reset_view_button, 1, 1)
        layout.addLayout(view_grid)

        self.help_label = QLabel('Set point A and point B, then enable Loop A–B.')
        layout.addWidget(self.help_label)

        video.player.positionChanged.connect(self.update_position)
        video.player.durationChanged.connect(self.update_duration)
        video.player.playbackStateChanged.connect(self.update_button)
        video.player.errorOccurred.connect(self.report_error)
        self.update_duration(video.player.duration())
        self.update_position(video.player.position())
        self.update_button(video.player.playbackState())
        self.refresh_loop_ui()

    def _canvas(self):
        return self.video.scene().views()[0] if self.video.scene() and self.video.scene().views() else None

    def _begin_view_drag(self):
        canvas = self._canvas()
        self._view_before = canvas.capture_state() if canvas else None

    def _end_view_drag(self):
        canvas = self._canvas()
        if canvas is not None and self._view_before is not None:
            canvas.record_edit(self._view_before, "Zoom video content")
        self._view_before = None

    def _begin_edit(self):
        canvas = self._canvas()
        return canvas.capture_state() if canvas else None

    def _finish_edit(self, before, label):
        canvas = self._canvas()
        if canvas is not None and before is not None:
            canvas.record_edit(before, label)
        else:
            self._notify_project_change()

    def sync_from_video(self):
        """Update the open dialog after Undo/Redo without writing new history."""
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(round(self.video.content_zoom * 100))
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f'{self.video.content_zoom:.2f}×')
        self.refresh_loop_ui()

    def update_view(self, _value=None):
        before = None if self.zoom_slider.isSliderDown() else self._begin_edit()
        self.video.set_content_view(zoom=self.zoom_slider.value() / 100.0)
        self.zoom_label.setText(f'{self.video.content_zoom:.2f}×')
        if before is not None:
            # Keyboard/wheel slider changes are discrete edits.
            self._finish_edit(before, "Zoom video content")
        else:
            self._notify_project_change()

    def reset_view(self):
        before = self._begin_edit()
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(100)
        self.zoom_slider.blockSignals(False)
        self.video.set_content_view(zoom=1.0, crop_rect=self.video.base_rect(), pan_x=0.0, pan_y=0.0)
        self.zoom_label.setText('1.00×')
        self._finish_edit(before, "Reset video view")

    def toggle_playback(self):
        if self.video.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.video.player.pause()
        else:
            self.video.player.play()

    def _seek_to(self, position):
        """Keep the requested seek available until Qt confirms its new position."""
        position = max(0, min(int(position), max(0, self.video.player.duration())))
        self._pending_seek_ms = position
        self._pending_seek_at = time.monotonic()
        self.video.player.setPosition(position)
        self.clock.setText(f'{fmt_time(position)} / {fmt_time(self.video.player.duration())}')

    def _selected_position(self):
        """Use the position shown by the control, including a pending seek."""
        if self._pending_seek_ms is not None:
            return self._pending_seek_ms
        return self.video.player.position()

    def seek_by(self, delta):
        position = self._selected_position() + delta
        position = max(0, min(self.video.player.duration(), position))
        self.seek.setValue(position)
        self._seek_to(position)

    def capture_a(self):
        before = self._begin_edit()
        self.video.set_loop_a(self._selected_position())
        self.refresh_loop_ui()
        self._finish_edit(before, 'Set video loop A')

    def capture_b(self):
        before = self._begin_edit()
        self.video.set_loop_b(self._selected_position())
        self.refresh_loop_ui()
        self._finish_edit(before, 'Set video loop B')

    def go_a(self):
        if self.video.loop_a_ms is not None:
            self.seek.setValue(self.video.loop_a_ms)
            self._seek_to(self.video.loop_a_ms)

    def go_b(self):
        if self.video.loop_b_ms is not None:
            self.seek.setValue(self.video.loop_b_ms)
            self._seek_to(self.video.loop_b_ms)

    def clear_loop(self):
        before = self._begin_edit()
        self.video.clear_loop()
        self.refresh_loop_ui()
        self._finish_edit(before, 'Clear video loop')

    def toggle_loop(self, checked):
        if checked and not self.video.has_valid_loop():
            QMessageBox.information(
                self,
                'Loop A–B',
                'Please set both loop points first, and make sure point B is after point A.',
            )
            self.enable_loop.blockSignals(True)
            self.enable_loop.setChecked(False)
            self.enable_loop.blockSignals(False)
            return
        before = self._begin_edit()
        self.video.set_loop_enabled(checked)
        self.refresh_loop_ui()
        self._finish_edit(before, 'Toggle video loop')

    def _notify_project_change(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, "update_modified_title"):
            parent.update_modified_title()

    def refresh_loop_ui(self):
        a_ms = self.video.loop_a_ms
        b_ms = self.video.loop_b_ms
        self.a_label.setText('A: ' + (fmt_time(a_ms) if a_ms is not None else 'not set'))
        self.b_label.setText('B: ' + (fmt_time(b_ms) if b_ms is not None else 'not set'))
        valid = self.video.has_valid_loop()
        self.goto_a.setEnabled(a_ms is not None)
        self.goto_b.setEnabled(b_ms is not None)
        self.enable_loop.setEnabled(valid)
        if not valid:
            self.video.loop_enabled = False
        self.enable_loop.blockSignals(True)
        self.enable_loop.setChecked(self.video.loop_enabled and valid)
        self.enable_loop.blockSignals(False)
        if a_ms is not None and b_ms is not None and not valid:
            self.help_label.setText('Point B must be later than point A.')
        elif self.video.loop_enabled and valid:
            self.help_label.setText('Looping from ' + fmt_time(a_ms) + ' to ' + fmt_time(b_ms) + '.')
        else:
            self.help_label.setText('Set point A and point B, then enable Loop A–B.')

    def update_position(self, pos):
        pending = self._pending_seek_ms
        if pending is not None:
            if abs(int(pos) - pending) <= 200 or time.monotonic() - self._pending_seek_at >= 2.0:
                self._pending_seek_ms = None
            else:
                # Qt can report the old position while seeking asynchronously.
                # Do not roll the handle back to 00:00 before the seek completes.
                self.clock.setText(
                    f'{fmt_time(pending)} / {fmt_time(self.video.player.duration())}'
                )
                return
        if not self.seek.isSliderDown():
            previous = self.seek.blockSignals(True)
            self.seek.setValue(pos)
            self.seek.blockSignals(previous)
        self.clock.setText(f'{fmt_time(pos)} / {fmt_time(self.video.player.duration())}')

    def update_duration(self, duration):
        self.seek.setMaximum(max(0, duration))
        self.update_position(self.video.player.position())

    def update_button(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play.setText('Pause' if playing else 'Play')

    def report_error(self, *_):
        self.clock.setText('Playback error: ' + self.video.player.errorString())

    def closeEvent(self, event):
        for signal, slot in (
            (self.video.player.positionChanged, self.update_position),
            (self.video.player.durationChanged, self.update_duration),
            (self.video.player.playbackStateChanged, self.update_button),
            (self.video.player.errorOccurred, self.report_error),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        super().closeEvent(event)
