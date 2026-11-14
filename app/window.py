"""Frameless application window, shortcuts, menus, and metadata."""
from pathlib import Path
import os
from datetime import datetime
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QIcon, QKeySequence, QShortcut, QUndoStack
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from .config import APP_NAME, APP_VERSION, PUBLISHER, COPYRIGHT, WEBSITE, asset_path, application_icon_path
from .canvas import Canvas
from .shortcut_help import ShortcutHelp
from .performance import memory_working_set_mb, memory_peak_working_set_mb, memory_private_mb
from .video_diagnostics import video_lifecycle
from .project import ProjectPersistenceMixin
from .window_resize import (EDGE_MARGIN, ResizeHint, resize_cursor,
                            resize_edges_for_point)


class MontaSpace(ProjectPersistenceMixin, QMainWindow):
    RESIZE_MARGIN = EDGE_MARGIN

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(application_icon_path())))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(900, 600)
        self.setMinimumSize(400, 300)
        self.canvas = Canvas(self)
        self.setCentralWidget(self.canvas)
        # The viewport covers almost the entire frameless window. Qt delivers
        # most pointer events to it rather than to QMainWindow.
        self._resize_hint = ResizeHint(self.canvas.viewport())
        self._border_visible = True
        self._resize_hover_edges = Qt.Edge(0)
        self.canvas.setMouseTracking(True)
        self.canvas.viewport().setMouseTracking(True)
        self.canvas.installEventFilter(self)
        self.canvas.viewport().installEventFilter(self)

        self.project_path = None
        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(50)
        self._embedded_sources = set()
        self._temp_extract = None
        self._saved_snapshot = self.project_snapshot()
        self._shortcut_help = None

        for shortcut, callback in (
            ("Ctrl+N", self.new_project),
            ("Ctrl+O", self.open_project),
            ("Ctrl+S", self.save_project),
            ("Ctrl+Shift+S", self.save_project_as),
            ("Ctrl+Z", self.perform_undo),
            ("Ctrl+Y", self.perform_redo),
            ("Ctrl+Shift+Z", self.perform_redo),
            ("Ctrl+D", self.canvas.duplicate_selected),
            ("Ctrl+A", self.select_all),
            ("F1", self.toggle_shortcut_help),
            ("Ctrl+H", self.toggle_shortcut_help),
            ("Ctrl+Shift+B", self.toggle_whiteboard_border),
        ):
            key = QShortcut(QKeySequence(shortcut), self)
            key.activated.connect(callback)

    def toggle_shortcut_help(self):
        """Show/hide a separate non-modal reference, without pausing media."""
        if self._shortcut_help is None:
            self._shortcut_help = ShortcutHelp(self)
        if self._shortcut_help.isVisible():
            self._shortcut_help.hide()
        else:
            self._shortcut_help.show()
            self._shortcut_help.raise_()
            self._shortcut_help.activateWindow()

    def toggle_whiteboard_border(self):
        """Toggle the subtle always-on frameless window boundary."""
        self._border_visible = not self._border_visible
        self._resize_hint.set_border_visible(self._border_visible)

    def show_about(self):
        """Display version and publisher attribution."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h3>{APP_NAME} {APP_VERSION}</h3>"
            "<p>A lightweight, frameless visual workspace for arranging images.</p>"
            f"<p><b>Developed and published by {PUBLISHER}</b><br>"
            f"{COPYRIGHT}<br>"
            f'<a href="{WEBSITE}">{WEBSITE}</a></p>'
            "<p><b>Studio linked projects:</b> .mstudio<br>"
            "<b>Studio portable projects:</b> .mstudiopack<br>"
            "<b>Imports:</b> .mspace, .mspacepack</p>"
            "<p>Built with Python and PySide6 (Qt).<br>"
            "Photos, video playback, A–B looping, and project saving.</p>"
            "<p><small>Copyright in photos imported by users remains with "
            "their respective owners.</small></p>",
        )

    def show_performance_info(self):
        """Copyable process-memory and Qt-object lifecycle report."""
        items = self.canvas.image_stack()
        pixmaps = {i.pixmap.cacheKey(): i.pixmap for i in items}
        estimated_mb = sum(
            p.width() * p.height() * 4 for p in pixmaps.values()
        ) / (1024 * 1024)
        videos = self.canvas.video_items()
        playing = sum(
            video.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            for video in videos
        )
        working = memory_working_set_mb()
        private = memory_private_mb()
        peak = memory_peak_working_set_mb()
        fmt = lambda value: f"{value:.1f} MB" if value is not None else "Not available"
        report = (
            f"MontaSpace Studio {APP_VERSION} diagnostic report\n"
            f"Captured: {datetime.now().isoformat(timespec='seconds')}\n"
            f"Process ID: {os.getpid()}\n"
            f"Images on board: {len(items)}\n"
            f"Videos on board: {len(videos)}\n"
            f"Videos currently playing: {playing}\n"
            f"Unique image previews: {len(pixmaps)}\n"
            f"Estimated decoded image pixels: {estimated_mb:.1f} MB\n"
            f"Current process RAM (Windows working set / macOS RSS): {fmt(working)}\n"
            f"Private memory (Windows committed / macOS physical footprint): {fmt(private)}\n"
            f"Peak process RAM (Windows working set / macOS RSS): {fmt(peak)}\n"
            f"Undo entries: {self.undo_stack.count()}\n\n"
            f"Video geometry (read-only):\n"
            + ("\n".join(f"  {video.geometry_report()}" for video in videos) if videos else "  none")
            + "\n\n"
            + f"{video_lifecycle.report()}\n\n"
            "Qt alive counts are native C++ QObject counts. Zero alive video "
            "objects with high RAM can indicate retained decoder buffers, "
            "allocators, or other native memory (not proof of a leak). "
            "Values are per process, not the Task Manager Python group."
        )
        msg = QMessageBox(self)
        msg.setWindowTitle(f"{APP_NAME} — Performance Info")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(report)
        copy_button = msg.addButton("Copy Report", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Ok)
        msg.exec()
        if msg.clickedButton() is copy_button:
            QApplication.clipboard().setText(report)

    def perform_undo(self):
        if self.canvas.active_crop:
            self.canvas.finish_crop(False)
        self.undo_stack.undo()
        self.update_modified_title()

    def perform_redo(self):
        if self.canvas.active_crop:
            self.canvas.finish_crop(False)
        self.undo_stack.redo()
        self.update_modified_title()

    def select_all(self):
        if not self.canvas.active_crop:
            for item in self.canvas.image_stack():
                item.setSelected(True)

    def update_modified_title(self):
        label = self.project_path.name if self.project_path else "Untitled"
        star = " *" if self.project_is_modified() else ""
        self.setWindowTitle(f"{APP_NAME} — {label}{star}")

    def closeEvent(self, event):
        if self.confirm_discard_changes():
            self.canvas.stop_videos()
            event.accept()
        else:
            event.ignore()

    def resize_edges(self, position):
        return resize_edges_for_point(position, self.width(), self.height())

    def update_resize_hover(self, position):
        """Expose a directional cursor and a small border hint near edges."""
        edges = self.resize_edges(position)
        changed = edges != self._resize_hover_edges
        self._resize_hover_edges = edges
        cursor = resize_cursor(edges)
        # Reapply the border cursor even if the zone has not changed: an image
        # item may update the viewport cursor during graphics-scene hover.
        if cursor is not None:
            self.canvas.viewport().setCursor(cursor)
        elif changed:
            self.canvas.viewport().unsetCursor()
        if changed:
            self._resize_hint.show_edges(edges)

    def clear_resize_hover(self):
        self._resize_hover_edges = Qt.Edge(0)
        self.canvas.viewport().unsetCursor()
        self._resize_hint.show_edges(Qt.Edge(0))

    def eventFilter(self, watched, event):
        # Keep the overlay sized to the actual image viewport and track its
        # pointer events, including when the pointer is over a photo.
        viewport = self.canvas.viewport()
        if watched is viewport:
            if event.type() == QEvent.Type.Resize:
                self._resize_hint.setGeometry(viewport.rect())
            elif event.type() == QEvent.Type.MouseMove:
                self.update_resize_hover(viewport.mapTo(self, event.position().toPoint()))
            elif event.type() == QEvent.Type.Enter:
                from PySide6.QtGui import QCursor
                self.update_resize_hover(viewport.mapTo(self, viewport.mapFromGlobal(QCursor.pos())))
            elif event.type() == QEvent.Type.Leave:
                self.clear_resize_hover()
        elif watched is self.canvas:
            if event.type() == QEvent.Type.MouseMove:
                self.update_resize_hover(self.canvas.mapTo(self, event.position().toPoint()))
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.windowHandle()
            edges = self.resize_edges(event.position().toPoint())
            if handle and edges and handle.startSystemResize(edges):
                event.accept()
                return
            if handle and event.modifiers() & Qt.KeyboardModifier.AltModifier:
                if handle.startSystemMove():
                    event.accept()
                    return
        super().mousePressEvent(event)
