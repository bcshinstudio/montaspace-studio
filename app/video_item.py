"""Video scene item and non-modal playback dialog with A/B loop controls."""
from pathlib import Path

from PySide6.QtCore import Qt, QSizeF, QUrl
from PySide6.QtWidgets import (
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
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from .video_diagnostics import video_lifecycle


def fmt_time(ms):
    seconds = max(0, int(ms) // 1000)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class VideoItem(QGraphicsVideoItem):
    """One video, decoded by Qt on demand (not copied into an image pixmap)."""

    MIN_SCALE = 0.15
    MAX_SCALE = 8.0

    def __init__(self, filename):
        super().__init__()
        self.filename = str(Path(filename).resolve())
        self.setSize(QSizeF(420, 236))
        self.setTransformOriginPoint(self.boundingRect().center())
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.65)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self)
        self.player.setSource(QUrl.fromLocalFile(self.filename))
        self.player.positionChanged.connect(self._handle_position_changed)
        self.player.mediaStatusChanged.connect(self._handle_media_status)
        self._controls = None
        self.loop_a_ms = None
        self.loop_b_ms = None
        self.loop_enabled = False
        self._loop_guard = False
        self._released = False
        self._diagnostic_token = video_lifecycle.observe(self, "video item")
        video_lifecycle.observe(self.player, "media player")
        video_lifecycle.observe(self.audio, "audio output")

    def controls(self, parent):
        if self._controls is None:
            self._controls = VideoControls(self, parent)
            self._controls.finished.connect(lambda _result: setattr(self, '_controls', None))
        self._controls.show()
        self._controls.raise_()
        self._controls.activateWindow()

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

        # The dialog owns signal connections to QMediaPlayer, and is parented
        # to the main window. Close/delete it so it cannot retain this video.
        if self._controls is not None:
            dialog = self._controls
            self._controls = None
            dialog.close()
            dialog.deleteLater()

        # Remove signals that could seek or restart the player during shutdown.
        try:
            self.player.positionChanged.disconnect(self._handle_position_changed)
        except (RuntimeError, TypeError):
            pass
        try:
            self.player.mediaStatusChanged.disconnect(self._handle_media_status)
        except (RuntimeError, TypeError):
            pass

        self.player.stop()
        # Clearing the media source releases the native decoding pipeline.
        # Simply stopping playback can leave FFmpeg buffers allocated.
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
        self.loop_a_ms = max(0, int(value_ms))
        if self.loop_b_ms is not None and self.loop_b_ms <= self.loop_a_ms:
            self.loop_enabled = False

    def set_loop_b(self, value_ms):
        self.loop_b_ms = max(0, int(value_ms))
        if self.loop_a_ms is not None and self.loop_b_ms <= self.loop_a_ms:
            self.loop_enabled = False

    def clear_loop(self):
        self.loop_a_ms = None
        self.loop_b_ms = None
        self.loop_enabled = False

    def set_loop_enabled(self, enabled):
        self.loop_enabled = bool(enabled) and self.has_valid_loop()

    def _jump_to_loop_start(self):
        if not (self.loop_enabled and self.has_valid_loop()) or self._loop_guard:
            return
        self._loop_guard = True
        try:
            self.player.setPosition(self.loop_a_ms)
            # Keep playback running even after reaching end-of-media.
            if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self.player.play()
        finally:
            self._loop_guard = False

    def _handle_position_changed(self, pos):
        if not (self.loop_enabled and self.has_valid_loop()):
            return
        # A small tolerance avoids overshoot jitter around the loop end.
        if pos >= self.loop_b_ms - 40:
            self._jump_to_loop_start()

    def _handle_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.loop_enabled and self.has_valid_loop():
            self._jump_to_loop_start()


class VideoControls(QDialog):
    """Non-modal player controls with A/B loop controls."""

    def __init__(self, video, parent):
        super().__init__(parent)
        self.video = video
        video_lifecycle.observe(self, "controls")
        # Closing a controls dialog must destroy it, rather than leave a
        # hidden child of the main window holding playback signal connections.
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle(f"Video — {Path(video.filename).name}")
        self.resize(470, 190)
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

        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setRange(0, max(video.player.duration(), 0))
        self.seek.sliderMoved.connect(video.player.setPosition)
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

    def toggle_playback(self):
        if self.video.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.video.player.pause()
        else:
            self.video.player.play()

    def seek_by(self, delta):
        player = self.video.player
        player.setPosition(max(0, min(player.duration(), player.position() + delta)))

    def capture_a(self):
        self.video.set_loop_a(self.video.player.position())
        self.refresh_loop_ui()

    def capture_b(self):
        self.video.set_loop_b(self.video.player.position())
        self.refresh_loop_ui()

    def go_a(self):
        if self.video.loop_a_ms is not None:
            self.video.player.setPosition(self.video.loop_a_ms)

    def go_b(self):
        if self.video.loop_b_ms is not None:
            self.video.player.setPosition(self.video.loop_b_ms)

    def clear_loop(self):
        self.video.clear_loop()
        self.refresh_loop_ui()

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
        self.video.set_loop_enabled(checked)
        self.refresh_loop_ui()

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
        if not self.seek.isSliderDown():
            self.seek.setValue(pos)
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
        """Disconnect controls from the player when the dialog closes."""
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
