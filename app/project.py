"""Linked and portable project file persistence (.mspace / .mspacepack)."""
import json
import os
import tempfile
import math
import zipfile
import hashlib
import shutil
from pathlib import Path
from PySide6.QtCore import QRectF, QTemporaryDir
from PySide6.QtWidgets import QMessageBox, QFileDialog
from .config import PROJECT_FILTER, APP_NAME


class ProjectPersistenceMixin(object):
    def project_snapshot(self):
        """Capture project state; selection itself is not a change."""
        images = []
        for item in self.canvas.image_stack():
            rect = item.crop_rect
            images.append({
                "source": str(Path(item.filename).resolve()),
                "x": item.pos().x(),
                "y": item.pos().y(),
                "scale": item.scale(),
                "rotation": item.rotation(),
                "crop": [rect.x(), rect.y(), rect.width(), rect.height()],
                "z": item.zValue(),
            })
        # Video records participate in the unsaved-changes check, but are not
        # yet serialized in v0.2.0. Saving a video board is explicitly blocked.
        for video in self.canvas.video_items():
            images.append({"video_unsaved": video.filename, "x": video.pos().x(),
                           "y": video.pos().y(), "scale": video.scale()})
        return images

    def project_is_modified(self):
        return self.project_snapshot() != self._saved_snapshot

    def confirm_discard_changes(self):
        """Allow Save, Discard, or Cancel before losing changes."""
        if not self.project_is_modified():
            return True
        answer = QMessageBox.question(
            self, "Unsaved changes",
            f"Save the current {APP_NAME} project before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return True

    def new_project(self):
        if not self.confirm_discard_changes():
            return
        self.canvas.finish_crop(True)
        self.canvas.stop_videos()
        self.canvas.scene_area.clear()
        self.canvas.image_count = 0
        self.undo_stack.clear()
        self.project_path = None
        self._embedded_sources.clear()
        self._temp_extract = None
        self._saved_snapshot = self.project_snapshot()
        self.setWindowTitle(f"{APP_NAME} — Untitled")

    def save_project(self):
        if self.project_path is None:
            return self.save_project_as()
        return self._write_project(self.project_path)

    def save_project_as(self):
        suggested = str(self.project_path or (Path.home() / "Documents" / "Untitled.mspace"))
        filename, chosen_filter = QFileDialog.getSaveFileName(
            self, f"Save {APP_NAME} Project", suggested, PROJECT_FILTER,
        )
        if not filename:
            return False
        target = Path(filename)
        extension = ".mspacepack" if "Portable" in chosen_filter else ".mspace"
        if target.suffix.lower() != extension:
            target = target.with_suffix(extension)
        return self._write_project(target)

    def _build_payload(self, target, portable):
        records = self.project_snapshot()
        for record in records:
            src = Path(record["source"])
            if not src.is_file():
                raise FileNotFoundError(f"Original image not found:\n{src}")
            if not portable:
                # Embedded images from an opened pack need durable, linked copies.
                if str(src.resolve()) in self._embedded_sources:
                    assets_dir = target.parent / f"{target.stem}_assets"
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    digest = hashlib.sha256(str(src).encode()).hexdigest()[:12]
                    dest = assets_dir / f"{digest}_{src.name}"
                    if src.resolve() != dest.resolve():
                        shutil.copy2(src, dest)
                    src = dest
                record["source"] = os.path.relpath(str(src), target.parent)
        return records

    def _write_project(self, target):
        if self.canvas.video_items():
            QMessageBox.warning(
                self, "Video saving not available yet",
                "MontaSpace Studio v0.3.0 supports video insertion, playback, and A/B looping, "
                "but cannot save boards containing videos yet.\n\n"
                "Your existing photo projects are unchanged. Video project "
                "saving will be added in the next milestone.",
            )
            return False
        self.canvas.finish_crop(True)
        target = Path(target).resolve()
        portable = target.suffix.lower() == ".mspacepack"
        if target.suffix.lower() not in (".mspace", ".mspacepack"):
            QMessageBox.warning(self, "Invalid extension", "Choose .mspace or .mspacepack")
            return False
        temp_path = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            records = self._build_payload(target, portable)
            payload = {"format": "MontaSpace", "version": 1, "images": records}
            if portable:
                assets = {}
                for record in records:
                    source = Path(record["source"])
                    # Use stable entry names; identical source files are included once.
                    if source not in assets:
                        digest = hashlib.sha256(str(source).encode()).hexdigest()[:16]
                        assets[source] = f"images/{digest}{source.suffix.lower()}"
                    record["source"] = assets[source]
                payload["portable"] = True

            with tempfile.NamedTemporaryFile(
                suffix=".tmp", prefix=".montaspace-", dir=target.parent,
                delete=False,
            ) as stream:
                temp_path = Path(stream.name)
            if portable:
                with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED,
                                     compresslevel=4, allowZip64=True) as package:
                    package.writestr("project.json", json.dumps(payload, indent=2))
                    for src, arcname in assets.items():
                        package.write(src, arcname=arcname)
            else:
                with temp_path.open("w", encoding="utf-8") as stream:
                    json.dump(payload, stream, indent=2, ensure_ascii=False)
                    stream.write("\n")
            os.replace(temp_path, target)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return False
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

        self.project_path = target
        self._saved_snapshot = self.project_snapshot()
        self.undo_stack.setClean()
        self.update_modified_title()
        return True

    def open_project(self):
        if not self.confirm_discard_changes():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, f"Open {APP_NAME} Project", str(Path.home() / "Documents"),
            f"{APP_NAME} Projects (*.mspace *.mspacepack)",
        )
        if not filename:
            return
        self._read_project(Path(filename))

    def _read_project(self, target):
        """Load either file type; extract embedded files to temporary storage."""
        target = Path(target).resolve()
        portable = target.suffix.lower() == ".mspacepack"
        temporary = None
        embedded_paths = set()
        try:
            if portable:
                temporary = QTemporaryDir()
                if not temporary.isValid():
                    raise OSError("Could not create a temporary directory for images.")
                with zipfile.ZipFile(target, "r") as package:
                    data = json.loads(package.read("project.json").decode("utf-8"))
                    if not isinstance(data, dict):
                        raise ValueError("Invalid project metadata.")
                    files = {info.filename: info for info in package.infolist()}
                    if len(files) > 10001:
                        raise ValueError("Portable project contains too many files.")
                    names = {rec["source"] for rec in data.get("images", [])}
                    if sum(files[n].file_size for n in names if n in files) > 2_000_000_000:
                        raise ValueError("Portable project exceeds the 2 GB extraction limit.")
                    for name in names:
                        if (not isinstance(name, str) or not name.startswith("images/")
                                or "/" in name[7:] or ".." in name):
                            raise ValueError("Unsafe portable image path.")
                        info = files.get(name)
                        if info is None or info.is_dir() or info.file_size > 1_000_000_000:
                            raise ValueError(f"Missing or oversized embedded image: {name}")
                        dest = Path(temporary.path()) / name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with package.open(info) as src, dest.open("wb") as dst:
                            shutil.copyfileobj(src, dst, length=1024*1024)
                        embedded_paths.add(str(dest.resolve()))
            else:
                with target.open("r", encoding="utf-8") as stream:
                    data = json.load(stream)
            if (not isinstance(data, dict) or data.get("format") != "MontaSpace"
                    or data.get("version") != 1 or not isinstance(data.get("images"), list)):
                raise ValueError("Not a supported MontaSpace project file.")
            if len(data["images"]) > 10000:
                raise ValueError("This project contains too many image records.")
            parsed = []
            for record in data["images"]:
                source = Path(record["source"])
                if portable:
                    source = Path(temporary.path()) / source
                elif not source.is_absolute():
                    source = target.parent / source
                nums = [float(record[k]) for k in ("x", "y", "scale", "rotation", "z")]
                crop = [float(n) for n in record["crop"]]
                if len(crop) != 4 or not all(math.isfinite(n) for n in nums + crop):
                    raise ValueError("Invalid image transform or crop.")
                if not 0.05 <= nums[2] <= 20:
                    raise ValueError("Invalid image scale.")
                parsed.append((source, nums, crop))
        except (OSError, ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError,
                zipfile.BadZipFile, RuntimeError) as exc:
            QMessageBox.critical(self, "Open failed", str(exc))
            return False

        self.canvas.finish_crop(False)
        self.canvas.stop_videos()
        self.canvas.scene_area.clear()
        self.canvas.image_count = 0
        missing = []
        for source, nums, crop in parsed:
            if not self.canvas.add_image(str(source), record_undo=False):
                missing.append(str(source))
                continue
            item = self.canvas.selected_images()[0]
            item.setPos(nums[0], nums[1])
            item.setScale(nums[2])
            item.setRotation(nums[3])
            item.setZValue(nums[4])
            rect = QRectF(*crop).intersected(item.full_rect)
            if rect.width() >= item.MIN_CROP and rect.height() >= item.MIN_CROP:
                item.crop_rect = rect
                item.update()
        self.canvas.scene_area.clearSelection()
        self.project_path = target
        self._temp_extract = temporary
        self._embedded_sources = embedded_paths
        self.undo_stack.clear()
        self._saved_snapshot = self.project_snapshot()
        self.update_modified_title()
        if missing:
            shown = "\n".join(missing[:8])
            QMessageBox.warning(self, "Missing images",
                f"{len(missing)} image(s) could not load:\n{shown}\n\n"
                "Please locate or restore these images before saving.")
            self._saved_snapshot = None
        return True
