"""Whiteboard scene, selections, manipulation, drag/drop, and context menus."""
from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QPainter
from PySide6.QtWidgets import QFileDialog, QGraphicsScene, QGraphicsView, QMenu
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

    def capture_state(self):
        """Immutable metadata for active items (pixmaps remain shared in memory)."""
        return tuple(
            (item, item.pos().x(), item.pos().y(), item.scale(), item.rotation(),
             tuple((item.crop_rect.x(), item.crop_rect.y(),
                    item.crop_rect.width(), item.crop_rect.height())), item.zValue())
            for item in self.image_stack()
        )

    def restore_state(self, state):
        self._restoring = True
        try:
            self.finish_crop(False)
            desired = {entry[0] for entry in state}
            for item in list(self.image_stack()):
                if item not in desired:
                    self.scene_area.removeItem(item)
            for item, x, y, scale, angle, crop, z in state:
                if item.scene() is None:
                    self.scene_area.addItem(item)
                item.setPos(x, y)
                item.setScale(scale)
                item.setRotation(angle)
                item.crop_rect = QRectF(*crop)
                item.setZValue(z)
                item.update()
            self.scene_area.clearSelection()
        finally:
            self._restoring = False
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
        if filename:
            self.add_image(filename)

    def video_items(self):
        return [item for item in self.scene_area.items() if isinstance(item, VideoItem)]

    def selected_videos(self):
        return [item for item in self.scene_area.selectedItems() if isinstance(item, VideoItem)]

    def stop_videos(self):
        """Release videos about to be discarded by New/Open/Close."""
        for video in self.video_items():
            video.release()

    def add_video(self, filename, scene_pos=None, show_controls=True):
        if Path(filename).suffix.lower() not in VIDEO_EXTENSIONS or not Path(filename).is_file():
            return False
        item = VideoItem(filename)
        if scene_pos is None:
            scene_pos = self.mapToScene(self.viewport().rect().center())
        item.setPos(scene_pos)
        item.setZValue(max((i.zValue() for i in self.scene_area.items()), default=0) + 1)
        self.scene_area.addItem(item)
        self.scene_area.clearSelection()
        item.setSelected(True)
        self.window.update_modified_title()
        if show_controls:
            item.controls(self.window)
        return True

    def insert_video(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Insert MP4 Video", "", VIDEO_FILTER)
        if filename:
            self.add_video(filename)

    def selected_images(self):
        return [i for i in self.scene_area.selectedItems() if isinstance(i, ImageItem)]

    def begin_crop(self, item):
        """Keep the edited image above others and route input to it."""
        if self.active_crop is item:
            return
        if self.active_crop is not None:
            self.finish_crop(True)

        self._before_crop_state = self.capture_state()
        self.scene_area.clearSelection()
        item.setSelected(True)
        self.active_crop = item
        self._crop_previous_z = item.zValue()

        # The crop handles must always be above overlapping photos.
        max_z = max((i.zValue() for i in self.scene_area.items()), default=0)
        item.setZValue(max_z + 1)

        # Prevent any other photo from intercepting crop-handle clicks.
        self._crop_disabled_items = []
        for other in self.scene_area.items():
            if isinstance(other, ImageItem) and other is not item:
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
            self.record_edit(before_crop, "Crop image")
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
        self.record_edit(before, "Delete image")

    def _video_at_view_pos(self, pos):
        """Resolve a video beneath the pointer, including its placeholder children."""
        point = self.mapToScene(pos)
        for hit in self.scene_area.items(point):
            item = hit
            while item is not None and not isinstance(item, VideoItem):
                item = item.parentItem()
            if isinstance(item, VideoItem) and item.boundingRect().contains(item.mapFromScene(point)):
                return item
        return None

    def mouseDoubleClickEvent(self, event):
        """Double-left-click videos to play/pause; retain photo double-click crop."""
        if event.button() == Qt.MouseButton.LeftButton and not self.active_crop:
            video = self._video_at_view_pos(event.position().toPoint())
            if video is not None:
                self.scene_area.clearSelection()
                video.setSelected(True)
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
                    hit = item.boundingRect().contains(item.mapFromScene(scene_point))
                else:
                    continue
                if hit:
                    if not item.isSelected() or len(self.scene_area.selectedItems()) != 1:
                        self.scene_area.clearSelection()
                        item.setSelected(True)
                    break

        menu = QMenu(self)
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
        new_action = file_menu.addAction("New                  Ctrl+N")
        open_action = file_menu.addAction("Open...              Ctrl+O")
        save_action = file_menu.addAction("Save                 Ctrl+S")
        save_as_action = file_menu.addAction("Save As...        Ctrl+Shift+S")
        menu.addSeparator()
        undo_action = menu.addAction("Undo                  Ctrl+Z")
        redo_action = menu.addAction("Redo                  Ctrl+Y")
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
        for video in self.video_items():
            if video.sceneBoundingRect().contains(self.mapToScene(event.pos())):
                video_menu = menu.addMenu("Video Here: " + Path(video.filename).name)
                video_actions[video_menu.addAction("Playback Controls...")] = video
                break
        if selected_videos:
            video_actions[menu.addAction("Selected Video — Playback Controls...")] = selected_videos[0]
        if len(selected) == 1:
            active = selected[0]
            selected_menu = menu.addMenu("Selected Image")
            crop_selected_action = selected_menu.addAction("Crop Image")
            crop_actions[crop_selected_action] = active
            selected_menu.addSeparator()
            self.add_arrange_actions(selected_menu, active, arrange_actions)

        duplicate_action = menu.addAction("Duplicate Selected    Ctrl+D") if selected else None
        select_all_action = menu.addAction("Select All            Ctrl+A")
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
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in (SUPPORTED_EXTENSIONS | VIDEO_EXTENSIONS):
                source = url.toLocalFile()
                added = (self.add_video(source, pos) if Path(source).suffix.lower() in VIDEO_EXTENSIONS
                         else self.add_image(source, pos))
                if added:
                    count += 1
                    pos.setX(pos.x() + 25)
                    pos.setY(pos.y() + 25)
        if count:
            event.acceptProposedAction()
        else:
            event.ignore()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            before = self.capture_state()
            factor = 1.10 ** (event.angleDelta().y() / 120.0)
            for item in self.selected_images() + self.selected_videos():
                item.setScale(max(item.MIN_SCALE, min(item.MAX_SCALE, item.scale() * factor)))
            self.window.update_modified_title()
            self.record_edit(before, "Resize image")
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

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # Scene items may change the pointer shape during their hover handling.
        # Window borders should still advertise their resize affordance.
        window_pos = self.mapTo(self.window, event.position().toPoint())
        self.window.update_resize_hover(window_pos)

    def mousePressEvent(self, event):
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
