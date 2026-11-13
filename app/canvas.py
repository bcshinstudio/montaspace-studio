"""Whiteboard scene, selections, manipulation, drag/drop, and context menus."""
from pathlib import Path
from uuid import uuid4
from PySide6.QtCore import Qt, QRectF, QLineF
from PySide6.QtGui import QColor, QBrush, QPainter
from PySide6.QtWidgets import QFileDialog, QGraphicsScene, QGraphicsView, QMenu, QMessageBox
from .config import IMAGE_FILTER, SUPPORTED_EXTENSIONS, VIDEO_FILTER, VIDEO_EXTENSIONS
from .history import StateCommand
from .image_item import ImageItem
from .imaging import load_preview
from .video_item import VideoItem


class Canvas(QGraphicsView):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.scene_area = QGraphicsScene(self)
        self.scene_area.setSceneRect(-10000, -10000, 20000, 20000)
        self.setScene(self.scene_area)
        self.setBackgroundBrush(QBrush(QColor("white")))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.image_count = 0
        self.active_crop = None
        self._crop_previous_z = None
        self._crop_disabled_items = []
        self._restoring = False
        self._panning_video = None
        self._pan_last_scene = None
        self._last_added_video = None
        self._grip_drag = None
        self._pan_undo_before = None

    def paintEvent(self, event):
        super().paintEvent(event)
        hint = getattr(self.window, "_resize_hint", None)
        if hint is not None and (hint.border_visible or hint.edges):
            painter = QPainter(self.viewport())
            hint.paint(painter)
            painter.end()

    def capture_state(self):
        """One ordered photo/video history, with no video frames or Qt players.

        Photos retain their existing implicitly shared pixmaps via ImageItem.
        Videos use only their ID, file path, and scalar editing settings.
        Removed videos are recreated on undo, never kept alive off-screen.
        """
        photos = tuple(
            (item, item.pos().x(), item.pos().y(), item.scale(), item.rotation(),
             (item.crop_rect.x(), item.crop_rect.y(),
              item.crop_rect.width(), item.crop_rect.height()), item.zValue())
            for item in self.image_stack()
        )
        videos = []
        for item in self.video_items():
            rect = item.crop_rect
            bounds = item.base_rect()
            if bounds.width() <= 0 or bounds.height() <= 0:
                continue
            crop = (rect.x() / bounds.width(), rect.y() / bounds.height(),
                    rect.width() / bounds.width(), rect.height() / bounds.height())
            videos.append((
                item.history_id, item.filename,
                item.pos().x(), item.pos().y(), item.scale(), item.rotation(),
                item.zValue(), crop,
                item.content_zoom,
                item.pan_x / bounds.width(), item.pan_y / bounds.height(),
                item.loop_a_ms, item.loop_b_ms, item.loop_enabled,
                tuple(item.verified_display_size() or ()),
                item.volume_percent, item.muted,
            ))
        return photos, tuple(sorted(videos, key=lambda entry: entry[0]))

    def restore_state(self, state):
        self._restoring = True
        try:
            self.finish_crop(False)
            photos, videos = state
            desired = {entry[0] for entry in photos}
            for item in list(self.image_stack()):
                if item not in desired:
                    self.scene_area.removeItem(item)
            for item, x, y, scale, angle, crop, z in photos:
                if item.scene() is None:
                    self.scene_area.addItem(item)
                item.setPos(x, y)
                item.setScale(scale)
                item.setRotation(angle)
                item.crop_rect = QRectF(*crop)
                item.setZValue(z)
                item._refresh_handles()
                item.update()

            # Video history stores no QObject references: deleted items can
            # release their decoders immediately; Undo recreates on demand.
            requested = {entry[0] for entry in videos}
            current = {item.history_id: item for item in self.video_items()}
            for key, item in list(current.items()):
                if key not in requested:
                    item.release()
                    self.scene_area.removeItem(item)
                    item.deleteLater()
                    del current[key]
            for (key, path, x, y, scale, angle, z, crop,
                 zoom, pan_x, pan_y, loop_a, loop_b, loop_on, display_size,
                 volume, muted) in videos:
                item = current.get(key)
                if item is None:
                    if not self.add_video(path, show_controls=False, record_undo=False):
                        continue  # Source removed externally; don't crash Undo.
                    item = self._last_added_video
                    item.history_id = key
                    current[key] = item
                if display_size:
                    item.restore_display_size(*display_size)
                bounds = item.base_rect()
                item.setPos(x, y)
                item.setScale(scale)
                item.setRotation(angle)
                item.setZValue(z)
                item.set_content_view(
                    zoom=zoom,
                    crop_rect=QRectF(crop[0] * bounds.width(),
                                     crop[1] * bounds.height(),
                                     crop[2] * bounds.width(),
                                     crop[3] * bounds.height()),
                    pan_x=pan_x * bounds.width(), pan_y=pan_y * bounds.height(),
                )
                item.loop_a_ms = loop_a
                item.loop_b_ms = loop_b
                item.set_loop_enabled(loop_on)
                item.set_audio_state(volume=volume, muted=muted)
                if item._controls is not None:
                    item._controls.sync_from_video()
            self.scene_area.clearSelection()
        finally:
            self._restoring = False
        self.viewport().update()
        self.window.update_modified_title()

    def record_edit(self, before, description):
        if self._restoring:
            return
        after = self.capture_state()
        if before != after:
            self.window.undo_stack.push(StateCommand(self, before, after, description))
            self.window.update_modified_title()

    def duplicate_selected(self):
        if self.active_crop:
            return
        selected = self.selected_images()
        if not selected:
            return
        before = self.capture_state()
        highest = max((i.zValue() for i in self.image_stack()), default=-1)
        self.scene_area.clearSelection()
        for original in selected:
            copy = ImageItem(original.pixmap, original.filename)
            copy.crop_rect = QRectF(original.crop_rect)
            copy.setPos(original.pos().x() + 30, original.pos().y() + 30)
            copy.setScale(original.scale())
            copy.setRotation(original.rotation())
            highest += 1
            copy.setZValue(highest)
            self.scene_area.addItem(copy)
            copy.setSelected(True)
            self.image_count += 1
        self.record_edit(before, "Duplicate image")

    def add_image(self, filename, scene_pos=None, record_undo=True):
        before = self.capture_state() if record_undo else None
        # Reuse Qt's implicitly-shared pixel storage when the same source is
        # already present. No permanent image cache: memory can be reclaimed
        # after all copies and Undo references are released.
        source_key = str(Path(filename).resolve())
        pixmap = None
        for existing in self.image_stack():
            if str(Path(existing.filename).resolve()) == source_key:
                pixmap = existing.pixmap
                break
        if pixmap is None:
            pixmap = load_preview(filename)
        if pixmap.isNull():
            return False
        item = ImageItem(pixmap, filename)
        if scene_pos is None:
            scene_pos = self.mapToScene(self.viewport().rect().center())
            offset = (self.image_count % 6) * 24
            scene_pos.setX(scene_pos.x() + offset)
            scene_pos.setY(scene_pos.y() + offset)
        item.setPos(scene_pos)
        item.setZValue(self.image_count)
        self.scene_area.addItem(item)
        self.scene_area.clearSelection()
        item.setSelected(True)
        self.image_count += 1
        if record_undo:
            self.record_edit(before, "Insert image")
        return True

    def insert_image(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Insert Image", "", IMAGE_FILTER)
        if filename and not self.add_image(filename):
            QMessageBox.warning(
                self, "Cannot open image",
                "This image could not be decoded. The format or compression may not "
                "be supported by this installation's image codecs.\n\n"
                "Try another file or convert it to PNG/JPEG."
            )

    def video_items(self):
        return [item for item in self.scene_area.items() if isinstance(item, VideoItem)]

    def selected_videos(self):
        return [item for item in self.scene_area.selectedItems() if isinstance(item, VideoItem)]

    def stop_videos(self):
        """Release videos about to be discarded by New/Open/Close."""
        for video in self.video_items():
            video.release()

    def add_video(self, filename, scene_pos=None, show_controls=True, record_undo=True):
        if Path(filename).suffix.lower() not in VIDEO_EXTENSIONS or not Path(filename).is_file():
            return False
        before = self.capture_state() if record_undo and not self._restoring else None
        item = VideoItem(filename)
        item.history_id = uuid4().hex
        self._last_added_video = item
        if scene_pos is None:
            scene_pos = self.mapToScene(self.viewport().rect().center())
        item.setPos(scene_pos)
        item.setZValue(max((i.zValue() for i in self.scene_area.items()), default=0) + 1)
        self.scene_area.addItem(item)
        self.scene_area.clearSelection()
        # Videos do not show edit handles until the user selects them.
        # Insertion should not guess the decoded display rectangle.
        self.window.update_modified_title()
        if show_controls:
            item.controls(self.window)
        if before is not None:
            self.record_edit(before, "Insert video")
        return True

    def insert_video(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Insert Video", "", VIDEO_FILTER)
        if filename:
            self.add_video(filename)

    def selected_images(self):
        return [i for i in self.scene_area.selectedItems() if isinstance(i, ImageItem)]

    def begin_crop(self, item):
        """Keep the edited item above others and route input to it."""
        if self.active_crop is item:
            return
        if self.active_crop is not None:
            self.finish_crop(True)

        self._before_crop_state = self.capture_state()
        self.scene_area.clearSelection()
        item.setSelected(True)
        self.active_crop = item
        self._crop_previous_z = item.zValue()

        # The crop handles must always be above overlapping media.
        max_z = max((i.zValue() for i in self.scene_area.items()), default=0)
        item.setZValue(max_z + 1)

        # Prevent any other media from intercepting crop-handle clicks.
        self._crop_disabled_items = []
        for other in self.scene_area.items():
            if isinstance(other, (ImageItem, VideoItem)) and other is not item:
                self._crop_disabled_items.append(
                    (other, other.acceptedMouseButtons(), other.acceptHoverEvents())
                )
                other.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                other.setAcceptHoverEvents(False)

        item.start_crop()
        self.setFocus()

    def finish_crop(self, apply):
        """Restore the regular stacking order and mouse interactions."""
        if self.active_crop is None:
            return

        item = self.active_crop
        before_crop = getattr(self, "_before_crop_state", None)
        item.end_crop(apply)
        if self._crop_previous_z is not None:
            item.setZValue(self._crop_previous_z)

        for other, buttons, hover in self._crop_disabled_items:
            if other.scene() is self.scene_area:
                other.setAcceptedMouseButtons(buttons)
                other.setAcceptHoverEvents(hover)

        self._crop_disabled_items = []
        self._crop_previous_z = None
        self.active_crop = None
        self.scene_area.clearSelection()
        item.setSelected(True)
        if apply and before_crop is not None:
            self.record_edit(before_crop, "Crop image" if isinstance(item, ImageItem) else "Crop video")
        else:
            self.window.update_modified_title()
        self._before_crop_state = None

    def delete_selected_items(self):
        self.finish_crop(False)
        before = self.capture_state()
        for item in self.scene_area.selectedItems():
            if isinstance(item, VideoItem):
                item.release()
                self.scene_area.removeItem(item)
                # scene.removeItem only detaches; delete the QObject as well.
                item.deleteLater()
            else:
                self.scene_area.removeItem(item)
        self.window.update_modified_title()
        self.record_edit(before, "Delete media")

    def _video_at_view_pos(self, pos):
        """Resolve a video beneath the pointer, including its placeholder children."""
        point = self.mapToScene(pos)
        for hit in self.scene_area.items(point):
            item = hit
            while item is not None and not isinstance(item, VideoItem):
                item = item.parentItem()
            if isinstance(item, VideoItem) and item.contains(item.mapFromScene(point)):
                return item
        return None

    def mouseDoubleClickEvent(self, event):
        """Photos keep double-click crop; videos use Ctrl+double-click for crop."""
        if event.button() == Qt.MouseButton.LeftButton and not self.active_crop:
            video = self._video_at_view_pos(event.position().toPoint())
            if video is not None:
                self.scene_area.clearSelection()
                video.setSelected(True)
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.begin_crop(video)
                else:
                    video.toggle_playback()
                event.accept()
                return
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, ImageItem) and event.button() == Qt.MouseButton.LeftButton:
            self.begin_crop(item)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def image_stack(self):
        """Return all photos from back to front, using scene order for ties."""
        return [
            item for item in reversed(self.scene_area.items())
            if isinstance(item, ImageItem)
        ]

    def arrange_image(self, item, operation):
        """Move one image within the persistent stacking order."""
        if self.active_crop:
            return

        stack = self.image_stack()
        if item not in stack:
            return
        before = self.capture_state()

        old_index = stack.index(item)
        stack.pop(old_index)
        if operation == "front":
            new_index = len(stack)
        elif operation == "back":
            new_index = 0
        elif operation == "forward":
            new_index = min(old_index + 1, len(stack))
        elif operation == "backward":
            new_index = max(old_index - 1, 0)
        else:
            return

        stack.insert(new_index, item)
        for z, image in enumerate(stack):
            image.setZValue(z)

        self.scene_area.clearSelection()
        item.setSelected(True)
        self.viewport().update()
        self.record_edit(before, "Arrange image")

    def images_at(self, viewport_point):
        """Find all photos covering the clicked pixel, front to back."""
        scene_point = self.mapToScene(viewport_point)
        # Use each image's real visible crop, not its oversized handle bounds.
        result = []
        for image in reversed(self.image_stack()):
            local_point = image.mapFromScene(scene_point)
            if image.crop_rect.contains(local_point):
                result.append(image)
        return result

    def add_arrange_actions(self, menu, image, actions):
        """Add standard layer operations for a specific image."""
        stack = self.image_stack()
        if image not in stack:
            return
        index = stack.index(image)
        labels = (
            ("Bring to Front", "front", index < len(stack) - 1),
            ("Bring Forward", "forward", index < len(stack) - 1),
            ("Send Backward", "backward", index > 0),
            ("Send to Back", "back", index > 0),
        )
        for label, operation, enabled in labels:
            action = menu.addAction(label)
            action.setEnabled(enabled)
            actions[action] = (image, operation)

    def contextMenuEvent(self, event):
        """Select the media under a right-click before building its context menu."""
        if not self.active_crop:
            scene_point = self.mapToScene(event.pos())
            # The scene returns items from front to back. Use the actual media
            # area, not the enlarged image bounding rectangle/resize handles.
            # The existing Images Here submenu still exposes covered photos.
            for item in self.scene_area.items(scene_point):
                if isinstance(item, ImageItem):
                    hit = item.crop_rect.contains(item.mapFromScene(scene_point))
                elif isinstance(item, VideoItem):
                    hit = item.contains(item.mapFromScene(scene_point))
                else:
                    continue
                if hit:
                    if not item.isSelected() or len(self.scene_area.selectedItems()) != 1:
                        self.scene_area.clearSelection()
                        item.setSelected(True)
                    break

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                color: #1f2937;
                border: 1px solid #d9e0e8;
                border-radius: 7px;
                padding: 5px 0;
                font: 10pt 'Segoe UI';
            }
            QMenu::item { padding: 7px 24px 7px 14px; }
            QMenu::item:selected { background: #eef4fd; color: #174f9b; }
            QMenu::item:disabled { color: #9ca3af; }
            QMenu::separator {
                background: #e6eaf0;
                height: 1px;
                margin: 5px 10px;
            }
        """)
        if self.active_crop:
            apply_action = menu.addAction("Apply Crop (Enter)")
            cancel_action = menu.addAction("Cancel Crop (Esc)")
            chosen = menu.exec(event.globalPos())
            if chosen == apply_action:
                self.finish_crop(True)
            elif chosen == cancel_action:
                self.finish_crop(False)
            return

        file_menu = menu.addMenu("File")
        new_action = file_menu.addAction("New\tCtrl+N")
        open_action = file_menu.addAction("Open…\tCtrl+O")
        save_action = file_menu.addAction("Save\tCtrl+S")
        save_as_action = file_menu.addAction("Save As…\tCtrl+Shift+S")
        menu.addSeparator()
        undo_action = menu.addAction("Undo\tCtrl+Z")
        redo_action = menu.addAction("Redo\tCtrl+Y")
        undo_action.setEnabled(self.window.undo_stack.canUndo())
        redo_action.setEnabled(self.window.undo_stack.canRedo())
        menu.addSeparator()

        images_here = self.images_at(event.pos())
        arrange_actions = {}
        select_actions = {}
        crop_actions = {}

        if images_here:
            images_menu = menu.addMenu(f"Images Here ({len(images_here)})")
            for rank, image in enumerate(images_here, 1):
                name = Path(image.filename).name or f"Image {rank}"
                if len(name) > 45:
                    name = name[:42] + "..."
                image_menu = images_menu.addMenu(f"{rank}. {name}")
                action = image_menu.addAction("Select Image")
                select_actions[action] = image
                action = image_menu.addAction("Crop Image")
                crop_actions[action] = image
                image_menu.addSeparator()
                self.add_arrange_actions(image_menu, image, arrange_actions)
            menu.addSeparator()

        insert_menu = menu.addMenu("Insert")
        image_action = insert_menu.addAction("Image...")
        video_action = insert_menu.addAction("MP4 Video...")
        menu.addSeparator()

        selected = self.selected_images()
        selected_videos = self.selected_videos()
        video_actions = {}
        video_crop_actions = {}
        video_mute_actions = {}
        for video in self.video_items():
            if video.contains(video.mapFromScene(self.mapToScene(event.pos()))):
                video_menu = menu.addMenu("Video Here: " + Path(video.filename).name)
                video_actions[video_menu.addAction("Playback Controls...")] = video
                video_mute_actions[video_menu.addAction("Unmute Video" if video.muted else "Mute Video")] = video
                video_crop_actions[video_menu.addAction("Crop Video")] = video
                break
        if selected_videos:
            video_actions[menu.addAction("Selected Video — Playback Controls...")] = selected_videos[0]
            video_mute_actions[menu.addAction("Selected Video — Unmute" if selected_videos[0].muted else "Selected Video — Mute")] = selected_videos[0]
            if len(selected_videos) == 1:
                video_crop_actions[menu.addAction("Selected Video — Crop Video")] = selected_videos[0]
        if len(selected) == 1:
            active = selected[0]
            selected_menu = menu.addMenu("Selected Image")
            crop_selected_action = selected_menu.addAction("Crop Image")
            crop_actions[crop_selected_action] = active
            selected_menu.addSeparator()
            self.add_arrange_actions(selected_menu, active, arrange_actions)

        duplicate_action = menu.addAction("Duplicate Selected\tCtrl+D") if selected else None
        select_all_action = menu.addAction("Select All\tCtrl+A")
        delete_action = menu.addAction("Delete Selected") if selected or selected_videos else None
        menu.addSeparator()
        performance_action = menu.addAction("Performance Info...")
        about_action = menu.addAction("About MontaSpace Studio...")
        minimize_action = menu.addAction("Minimize")
        exit_action = menu.addAction("Exit")

        chosen = menu.exec(event.globalPos())
        if chosen == new_action:
            self.window.new_project()
        elif chosen == open_action:
            self.window.open_project()
        elif chosen == save_action:
            self.window.save_project()
        elif chosen == save_as_action:
            self.window.save_project_as()
        elif chosen == undo_action:
            self.window.perform_undo()
        elif chosen == redo_action:
            self.window.perform_redo()
        elif chosen == image_action:
            self.insert_image()
        elif chosen == video_action:
            self.insert_video()
        elif chosen in video_actions:
            video_actions[chosen].controls(self.window)
        elif chosen in video_mute_actions:
            video = video_mute_actions[chosen]
            before = self.capture_state()
            video.set_audio_state(muted=not video.muted)
            self.record_edit(before, "Toggle video mute")
        elif chosen in video_crop_actions:
            self.begin_crop(video_crop_actions[chosen])
        elif chosen == duplicate_action:
            self.duplicate_selected()
        elif chosen == select_all_action:
            for item in self.image_stack():
                item.setSelected(True)
        elif chosen in select_actions:
            image = select_actions[chosen]
            self.scene_area.clearSelection()
            image.setSelected(True)
        elif chosen in crop_actions:
            self.begin_crop(crop_actions[chosen])
        elif chosen in arrange_actions:
            image, operation = arrange_actions[chosen]
            self.arrange_image(image, operation)
        elif delete_action is not None and chosen == delete_action:
            self.delete_selected_items()
        elif chosen == performance_action:
            self.window.show_performance_info()
        elif chosen == about_action:
            self.window.show_about()
        elif chosen == minimize_action:
            self.window.showMinimized()
        elif chosen == exit_action:
            self.window.close()

    def dragEnterEvent(self, event):
        if any(u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in (SUPPORTED_EXTENSIONS | VIDEO_EXTENSIONS)
               for u in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        pos = self.mapToScene(event.position().toPoint())
        count = 0
        failures = []
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in (SUPPORTED_EXTENSIONS | VIDEO_EXTENSIONS):
                source = url.toLocalFile()
                is_video = Path(source).suffix.lower() in VIDEO_EXTENSIONS
                added = self.add_video(source, pos) if is_video else self.add_image(source, pos)
                if added:
                    count += 1
                    pos.setX(pos.x() + 25)
                    pos.setY(pos.y() + 25)
                elif not is_video:
                    failures.append(Path(source).name)
        if count or failures:
            event.acceptProposedAction()
        else:
            event.ignore()
        if failures:
            QMessageBox.warning(
                self, "Cannot open image",
                "Could not decode the following dropped images:\n"
                + "\n".join(failures[:10])
                + (f"\n...and {len(failures) - 10} more" if len(failures) > 10 else "")
                + "\n\nInstall the image codecs listed in requirements.txt "
                  "(including pillow-heif for HEIC/HEIF), or check whether the files are damaged."
            )

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            before = self.capture_state()
            factor = 1.10 ** (event.angleDelta().y() / 120.0)
            for item in self.selected_images() + self.selected_videos():
                item.setScale(max(item.MIN_SCALE, min(item.MAX_SCALE, item.scale() * factor)))
            self.window.update_modified_title()
            self.record_edit(before, "Resize media")
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if self.active_crop:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.finish_crop(True)
                event.accept()
                return
            if event.key() == Qt.Key.Key_Escape:
                self.finish_crop(False)
                event.accept()
                return
        if event.key() == Qt.Key.Key_Delete and not self.active_crop:
            self.delete_selected_items()
            event.accept()
            return
        super().keyPressEvent(event)

    @staticmethod
    def _cursor_for_grip(grip):
        return {
            "tl": Qt.CursorShape.SizeFDiagCursor,
            "br": Qt.CursorShape.SizeFDiagCursor,
            "tr": Qt.CursorShape.SizeBDiagCursor,
            "bl": Qt.CursorShape.SizeBDiagCursor,
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
            "rotate": Qt.CursorShape.CrossCursor,
        }.get(grip)

    def _selected_grip_at(self, viewport_pos):
        """Single source of truth for cursor AND mouse-press hit-testing.

        QGraphicsScene may route presses to a different item than the one that
        generated the hover cursor. Handle grabs belong to the view instead.
        """
        scene_point = self.mapToScene(viewport_pos)
        selected = [item for item in self.scene_area.selectedItems()
                    if isinstance(item, (ImageItem, VideoItem))]
        # Frontmost selected item wins when two selections overlap.
        selected.sort(key=lambda item: item.zValue(), reverse=True)
        for item in selected:
            grip = item.handle_at(item.mapFromScene(scene_point))
            if grip is not None:
                return item, grip
        return None, None

    def _begin_grip_drag(self, item, grip, scene_point):
        """Capture existing photo/video crop and resize state once per drag."""
        local = item.mapFromScene(scene_point)
        state = {
            "item": item, "grip": grip, "start_local": local,
            "start_crop": QRectF(item.crop_rect),
            "start_scale": item.scale(),
            "start_distance": max(QLineF(
                item.mapToScene(item.transformOriginPoint()), scene_point
            ).length(), 1.0),
            "before": self.capture_state(),
        }
        if grip == "rotate" and isinstance(item, ImageItem) and not item.crop_mode:
            line = QLineF(item.mapToScene(item.transformOriginPoint()), scene_point)
            state["start_angle"] = line.angle()
            state["start_rotation"] = item.rotation()
        self._grip_drag = state
        self.setFocus()

    def _move_grip_drag(self, scene_point):
        state = self._grip_drag
        item, grip = state["item"], state["grip"]
        if grip == "rotate":
            line = QLineF(item.mapToScene(item.transformOriginPoint()), scene_point)
            item.setRotation(state["start_rotation"] + state["start_angle"] - line.angle())
            return

        if not item.crop_mode:
            line = QLineF(item.mapToScene(item.transformOriginPoint()), scene_point)
            new_scale = state["start_scale"] * max(line.length(), 1.0) / state["start_distance"]
            item.setScale(max(item.MIN_SCALE, min(item.MAX_SCALE, new_scale)))
            return

        # Crop distances use the item's original local coordinates, preserving
        # photo and video semantics even when the item is rotated or scaled.
        local = item.mapFromScene(scene_point)
        dx = local.x() - state["start_local"].x()
        dy = local.y() - state["start_local"].y()
        initial = state["start_crop"]
        left, right = initial.left(), initial.right()
        top, bottom = initial.top(), initial.bottom()
        bounds = item.full_rect if isinstance(item, ImageItem) else item.base_rect()
        if grip in ("tl", "bl", "left"):
            left = min(max(left + dx, bounds.left()), right - item.MIN_CROP)
        if grip in ("tr", "br", "right"):
            right = max(min(right + dx, bounds.right()), left + item.MIN_CROP)
        if grip in ("tl", "tr", "top"):
            top = min(max(top + dy, bounds.top()), bottom - item.MIN_CROP)
        if grip in ("bl", "br", "bottom"):
            bottom = max(min(bottom + dy, bounds.bottom()), top + item.MIN_CROP)
        item.crop_rect = QRectF(left, top, right - left, bottom - top)
        if isinstance(item, ImageItem):
            item._refresh_handles()
        else:
            item._clamp_pan()
            item._refresh_placeholder_geometry()
            item._refresh_selection_geometry()
        item.update()
        # The native video paint path can require a viewport repaint after
        # moving crop boundaries; this happens only while actively dragging.
        if isinstance(item, VideoItem):
            self.viewport().update()

    def _end_grip_drag(self):
        state = self._grip_drag
        self._grip_drag = None
        if state is None:
            return
        item = state["item"]
        if not item.crop_mode:
            self.record_edit(state["before"], "Resize or rotate media")
        else:
            self.window.update_modified_title()

    def mouseMoveEvent(self, event):
        if self._grip_drag is not None:
            self._move_grip_drag(self.mapToScene(event.position().toPoint()))
            event.accept()
            return
        if self._panning_video is not None:
            video = self._panning_video
            point = video.mapFromScene(self.mapToScene(event.position().toPoint()))
            delta = point - self._pan_last_scene
            video.set_content_view(pan_x=video.pan_x + delta.x(),
                                   pan_y=video.pan_y + delta.y())
            self._pan_last_scene = point
            self.window.update_modified_title()
            event.accept()
            return
        super().mouseMoveEvent(event)
        # Scene items may change the pointer shape during their hover handling.
        # Window borders should still advertise their resize affordance.
        window_pos = self.mapTo(self.window, event.position().toPoint())
        self.window.update_resize_hover(window_pos)
        # QGraphicsVideoItem/child paint overlays can steal hover events on
        # Windows. Resolve the cursor at the *view* too, so the whole edge
        # shows the expected two-direction arrow even between square handles.
        if not self.window.resize_edges(window_pos) and self._panning_video is None:
            _item, grip = self._selected_grip_at(event.position().toPoint())
            shape = self._cursor_for_grip(grip)
            if shape is not None:
                self.viewport().setCursor(shape)
            else:
                self.viewport().unsetCursor()

    def mouseReleaseEvent(self, event):
        if self._grip_drag is not None and event.button() == Qt.MouseButton.LeftButton:
            self._end_grip_drag()
            event.accept()
            return
        if self._panning_video is not None and event.button() == Qt.MouseButton.LeftButton:
            self._panning_video = None
            self._pan_last_scene = None
            before = getattr(self, "_pan_undo_before", None)
            self._pan_undo_before = None
            if before is not None:
                self.record_edit(before, "Pan video")
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        # Use exactly the same hit-test as the displayed cursor. This also
        # handles the invisible grab zone outside the item's scene shape.
        if event.button() == Qt.MouseButton.LeftButton and not (
                event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.AltModifier)):
            viewport_pos = event.position().toPoint()
            window_pos = self.mapTo(self.window, viewport_pos)
            if not self.window.resize_edges(window_pos):
                item, grip = self._selected_grip_at(viewport_pos)
                if item is not None and grip is not None:
                    self._begin_grip_drag(item, grip, self.mapToScene(viewport_pos))
                    event.accept()
                    return
        # Shift+left-drag pans the CONTENT only; plain dragging still moves video.
        if (event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                and not self.active_crop):
            video = self._video_at_view_pos(event.position().toPoint())
            if video is not None and video.content_zoom > 1.0:
                self.scene_area.clearSelection()
                video.setSelected(True)
                self._pan_undo_before = self.capture_state()
                self._panning_video = video
                self._pan_last_scene = video.mapFromScene(
                    self.mapToScene(event.position().toPoint()))
                event.accept()
                return
        # Middle-click on a video toggles the existing non-modal control dialog.
        # Empty-whiteboard and photo middle-clicks retain their previous behavior.
        if event.button() == Qt.MouseButton.MiddleButton and not self.active_crop:
            video = self._video_at_view_pos(event.position().toPoint())
            if video is not None:
                self.scene_area.clearSelection()
                video.setSelected(True)
                video.toggle_controls(self.window)
                event.accept()
                return
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.mapTo(self.window, event.position().toPoint())
            edges = self.window.resize_edges(pos)
            handle = self.window.windowHandle()
            if edges and handle and handle.startSystemResize(edges):
                event.accept()
                return
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                if handle and handle.startSystemMove():
                    event.accept()
                    return
        super().mousePressEvent(event)
