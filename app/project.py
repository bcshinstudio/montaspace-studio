"""MontaSpace Studio linked and portable project persistence.

Studio files use a separate media-aware format. Original MontaSpace photo-only
projects retain their original reader and are never overwritten by Studio.
"""
import hashlib
import json
import math
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from PySide6.QtCore import QRectF, QTemporaryDir
from PySide6.QtWidgets import QFileDialog, QMessageBox

from .config import APP_NAME, PROJECT_FILTER, SUPPORTED_EXTENSIONS, VIDEO_EXTENSIONS
from .video_poster import poster_cache, MAX_POSTER_BYTES
from .project_reliability import (resolve_sources, missing_sources, candidate_relocations,
                                  apply_relocations, verify_staged_project)

STUDIO_EXTENSIONS = {".mstudio", ".mstudiopack"}
LEGACY_EXTENSIONS = {".mspace", ".mspacepack"}
PACK_MAX_CONTENT_BYTES = 30 * (1024 ** 3)
PACK_MAX_SINGLE_FILE_BYTES = 20 * (1024 ** 3)
MAX_MEDIA_ITEMS = 10000


class ProjectPersistenceMixin:
    def project_snapshot(self):
        """Stable, selection-independent metadata for all board media."""
        records = []
        for item in self.canvas.image_stack():
            crop = item.crop_rect
            records.append({
                "type": "image",
                "source": str(Path(item.filename).resolve()),
                "x": item.pos().x(), "y": item.pos().y(),
                "scale": item.scale(), "rotation": item.rotation(),
                "z": item.zValue(),
                "crop": [crop.x(), crop.y(), crop.width(), crop.height()],
            })
        for video in self.canvas.video_items():
            crop = video.crop_rect
            full = video.base_rect()
            # Relative crop coordinates survive asynchronous native aspect changes.
            crop_fraction = [
                round(crop.x() / full.width(), 8),
                round(crop.y() / full.height(), 8),
                round(crop.width() / full.width(), 8),
                round(crop.height() / full.height(), 8),
            ]
            records.append({
                "type": "video",
                "source": str(Path(video.filename).resolve()),
                "x": video.pos().x(), "y": video.pos().y(),
                "scale": video.scale(), "rotation": video.rotation(),
                "z": video.zValue(),
                "display_size": video.verified_display_size(),
                "loop_a_ms": video.loop_a_ms,
                "loop_b_ms": video.loop_b_ms,
                "loop_enabled": video.loop_enabled,
                "content_zoom": video.content_zoom,
                "crop": crop_fraction,
                "crop_unit": "relative",
                "pan_x": video.pan_x,
                "pan_y": video.pan_y,
            })
        # Make snapshots reproducible regardless of QGraphicsScene iteration order.
        records.sort(key=lambda r: (r["z"], r["type"], r["source"], r["x"], r["y"]))
        return records

    def project_is_modified(self):
        return self.project_snapshot() != self._saved_snapshot

    def confirm_discard_changes(self):
        if not self.project_is_modified():
            return True
        answer = QMessageBox.question(
            self, "Unsaved changes", f"Save the current {APP_NAME} project before continuing?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
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
        if self.project_path is None or self.project_path.suffix.lower() in LEGACY_EXTENSIONS:
            # Never overwrite a photo-only MontaSpace project with Studio media data.
            return self.save_project_as()
        return self._write_project(self.project_path)

    def save_project_as(self):
        if self.project_path:
            suggested = str(self.project_path.with_suffix(".mstudio"))
        else:
            suggested = str(Path.home() / "Documents" / "Untitled.mstudio")
        filename, chosen_filter = QFileDialog.getSaveFileName(
            self, f"Save {APP_NAME} Project", suggested, PROJECT_FILTER,
        )
        if not filename:
            return False
        target = Path(filename)
        extension = ".mstudiopack" if "Portable" in chosen_filter else ".mstudio"
        if target.suffix.lower() != extension:
            target = target.with_suffix(extension)
        return self._write_project(target)

    def _build_payload(self, target, portable):
        records = self.project_snapshot()
        media_paths = {}
        for record in records:
            source = Path(record["source"])
            if not source.is_file():
                raise FileNotFoundError(f"Original media file not found:\n{source}")
            resolved = source.resolve()
            if portable:
                key = str(resolved)
                if key not in media_paths:
                    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
                    folder = "videos" if record["type"] == "video" else "images"
                    media_paths[key] = (resolved, f"{folder}/{digest}{source.suffix.lower()}")
                record["source"] = media_paths[key][1]
            else:
                if str(resolved) in self._embedded_sources:
                    # A linked project can't reference an ephemeral pack extraction.
                    assets_dir = target.parent / f"{target.stem}_assets"
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    digest = hashlib.sha256(str(resolved).encode()).hexdigest()[:12]
                    dest = assets_dir / f"{digest}_{source.name}"
                    if resolved != dest.resolve():
                        shutil.copy2(resolved, dest)
                    resolved = dest
                record["source"] = os.path.relpath(str(resolved), str(target.parent))
        return {"format": "MontaSpaceStudio", "version": 1, "items": records,
                "portable": bool(portable)}, media_paths

    def _write_project(self, target):
        self.canvas.finish_crop(True)
        target = Path(target).resolve()
        if target.suffix.lower() not in STUDIO_EXTENSIONS:
            QMessageBox.warning(self, "Invalid extension", "Choose .mstudio or .mstudiopack")
            return False
        portable = target.suffix.lower() == ".mstudiopack"
        temp_path = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            payload, media_paths = self._build_payload(target, portable)
            if portable:
                estimated = sum(src.stat().st_size for src, _arc in media_paths.values())
                if estimated > PACK_MAX_CONTENT_BYTES:
                    raise ValueError("Portable project is larger than the 30 GiB supported limit.")
                if any(src.stat().st_size > PACK_MAX_SINGLE_FILE_BYTES for src, _arc in media_paths.values()):
                    raise ValueError("A media file exceeds the 20 GiB supported portable-file limit.")
                if estimated >= 100 * 1024 * 1024:
                    mb = estimated / (1024 ** 2)
                    confirm = QMessageBox.question(
                        self, "Create portable project?",
                        f"This will embed the original media files (about {mb:,.0f} MB) "
                        "in the project archive.\n\nThe originals remain unchanged. Continue?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if confirm != QMessageBox.StandardButton.Yes:
                        return False
            with tempfile.NamedTemporaryFile(
                suffix=".tmp", prefix=".mstudio-", dir=target.parent, delete=False,
            ) as handle:
                temp_path = Path(handle.name)
            if portable:
                with zipfile.ZipFile(temp_path, "w", allowZip64=True) as archive:
                    archive.writestr("project.json", json.dumps(payload, indent=2, ensure_ascii=False))
                    for src, arcname in media_paths.values():
                        # MP4 is already compressed; don't waste CPU trying to recompress it.
                        method = (zipfile.ZIP_STORED if src.suffix.lower() in VIDEO_EXTENSIONS
                                  else zipfile.ZIP_DEFLATED)
                        archive.write(src, arcname=arcname, compress_type=method)
                        if src.suffix.lower() in VIDEO_EXTENSIONS:
                            poster = poster_cache.file_for(src)
                            if poster is not None:
                                poster_name = 'posters/' + Path(arcname).stem + '.jpg'
                                archive.write(poster, arcname=poster_name,
                                              compress_type=zipfile.ZIP_STORED)
            else:
                with temp_path.open("w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
            # Check the temporary artifact before touching the user's last good copy.
            verify_staged_project(
                temp_path, len(payload['items']),
                sum(row['type'] == 'video' for row in payload['items']), portable)
            os.replace(temp_path, target)
        except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
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
            "Studio and MontaSpace Projects (*.mstudio *.mstudiopack *.mspace *.mspacepack)",
        )
        if filename:
            self._read_project(Path(filename))

    def _read_project(self, target):
        if Path(target).suffix.lower() in LEGACY_EXTENSIONS:
            return self._read_legacy_project(target)
        return self._read_studio_project(target)

    def _recover_missing_sources(self, resolved):
        """Recover linked media before changing the current board.

        Cancel leaves the complete existing whiteboard untouched. No missing
        objects are silently discarded; only unambiguous matches are accepted.
        """
        remaining = missing_sources(resolved)
        if not remaining:
            return resolved
        while remaining:
            shown = "\n".join(f"• {Path(name).name}" for name in remaining[:12])
            if len(remaining) > 12:
                shown += f"\n… and {len(remaining) - 12} more"
            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Icon.Warning)
            dialog.setWindowTitle("Missing project media")
            dialog.setText(f"{len(remaining)} linked media file(s) are missing.\n\n{shown}")
            dialog.setInformativeText(
                "Locate the folder containing the moved files. Studio will "
                "match unique filenames and preserve the board layout. "
                "Cancel keeps the current project unchanged."
            )
            locate = dialog.addButton("Locate Folder…", QMessageBox.ButtonRole.AcceptRole)
            dialog.addButton(QMessageBox.StandardButton.Cancel)
            dialog.exec()
            if dialog.clickedButton() is not locate:
                return None
            selected = QFileDialog.getExistingDirectory(
                self, "Select folder containing missing media", str(Path.home()))
            if not selected:
                return None
            mapping = candidate_relocations(remaining, selected)
            resolved = apply_relocations(resolved, mapping)
            next_remaining = missing_sources(resolved)
            if len(next_remaining) == len(remaining):
                QMessageBox.information(
                    self, "No unique matches",
                    "No missing files could be matched uniquely in that folder. "
                    "Try their original parent folder or a more specific location."
                )
            remaining = next_remaining
        return resolved

    def _read_studio_project(self, target):
        """Validate all records before modifying the current whiteboard."""
        target = Path(target).resolve()
        if target.suffix.lower() not in STUDIO_EXTENSIONS:
            QMessageBox.critical(self, "Open failed", "Unsupported project extension.")
            return False
        portable = target.suffix.lower() == ".mstudiopack"
        temp_dir = None
        embedded_paths = set()
        embedded_posters = {}
        try:
            if portable:
                temp_dir = QTemporaryDir()
                if not temp_dir.isValid():
                    raise OSError("Could not create temporary directory.")
                with zipfile.ZipFile(target, "r") as archive:
                    data = json.loads(archive.read("project.json").decode("utf-8"))
                    parsed = self._parse_studio_records(data, target, portable=True)
                    names = {record["source"] for record in parsed}
                    files = {i.filename: i for i in archive.infolist()}
                    # In addition to each media file, a v0.5.14 portable
                    # project may contain one tiny JPEG poster per video.
                    if len(files) > 2 * MAX_MEDIA_ITEMS + 1 or len(files) != len(archive.infolist()):
                        raise ValueError("Invalid or oversized archive file list.")
                    total = 0
                    for name in names:
                        if (not isinstance(name, str) or not name.startswith(("images/", "videos/"))
                                or ".." in name or name.count("/") != 1 or "\\" in name):
                            raise ValueError("Unsafe portable media path.")
                        info = files.get(name)
                        if info is None or info.is_dir():
                            raise ValueError(f"Embedded media missing: {name}")
                        if info.file_size > PACK_MAX_SINGLE_FILE_BYTES:
                            raise ValueError("Embedded media file exceeds supported size.")
                        total += info.file_size
                        if total > PACK_MAX_CONTENT_BYTES:
                            raise ValueError("Portable project exceeds supported size.")
                        suffix = Path(name).suffix.lower()
                        record_types = {r["type"] for r in parsed if r["source"] == name}
                        if any(suffix not in (VIDEO_EXTENSIONS if typ == "video" else SUPPORTED_EXTENSIONS)
                               for typ in record_types):
                            raise ValueError("Embedded file type does not match media type.")
                    # Optional poster bytes are small, untrusted images: only
                    # load strict names corresponding to embedded MP4s.
                    embedded_posters = {}
                    for name in names:
                        if name.startswith('videos/'):
                            poster_name = 'posters/' + Path(name).stem + '.jpg'
                            poster_info = files.get(poster_name)
                            if (poster_info is not None and not poster_info.is_dir()
                                    and poster_info.file_size <= MAX_POSTER_BYTES):
                                embedded_posters[name] = archive.read(poster_info)
                    for name in names:
                        dest = Path(temp_dir.path()) / name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(files[name]) as source, dest.open("wb") as destination:
                            shutil.copyfileobj(source, destination, length=1024 * 1024)
                        embedded_paths.add(str(dest.resolve()))
            else:
                with target.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                parsed = self._parse_studio_records(data, target, portable=False)

            resolved = resolve_sources(parsed, target.parent,
                                       temp_dir.path() if portable else None)
        except (OSError, ValueError, TypeError, KeyError, IndexError,
                json.JSONDecodeError, zipfile.BadZipFile, RuntimeError) as exc:
            QMessageBox.critical(self, "Open failed", str(exc))
            return False

        had_missing_linked_media = not portable and bool(missing_sources(resolved))
        if not portable:
            resolved = self._recover_missing_sources(resolved)
            if resolved is None:
                return False
        elif missing_sources(resolved):
            QMessageBox.critical(self, "Open failed", "Portable project media could not be extracted.")
            return False

        self.canvas.finish_crop(False)
        self.canvas.stop_videos()
        self.canvas.scene_area.clear()
        self.canvas.image_count = 0
        self.undo_stack.clear()
        missing = []
        for record in resolved:
            src = record["source"]
            if record["type"] == "image":
                if not self.canvas.add_image(src, record_undo=False):
                    missing.append(src)
                    continue
                item = self.canvas.selected_images()[0]
                crop = QRectF(*record["crop"]).intersected(item.full_rect)
                if crop.width() >= item.MIN_CROP and crop.height() >= item.MIN_CROP:
                    item.crop_rect = crop
                    item.update()
            else:
                if portable:
                    # Use the archive-local name, not the extracted temp path.
                    poster_name = 'videos/' + Path(src).name
                    content = embedded_posters.get(poster_name)
                    if content:
                        poster_cache.install_bytes(src, content)
                if not self.canvas.add_video(src, show_controls=False, record_undo=False):
                    missing.append(src)
                    continue
                item = self.canvas._last_added_video
                display_size = record.get("display_size")
                if display_size is not None:
                    item.restore_display_size(*display_size)
                item.loop_a_ms = record["loop_a_ms"]
                item.loop_b_ms = record["loop_b_ms"]
                item.set_loop_enabled(record["loop_enabled"])
                item.set_content_view(zoom=record["content_zoom"],
                                      pan_x=record["pan_x"], pan_y=record["pan_y"])
                item.restore_saved_crop(QRectF(*record["crop"]), (1.0, 1.0))
            item.setPos(record["x"], record["y"])
            item.setScale(record["scale"])
            item.setRotation(record["rotation"])
            item.setZValue(record["z"])
        self.canvas.scene_area.clearSelection()
        self.project_path = target
        self._temp_extract = temp_dir
        self._embedded_sources = embedded_paths
        # Recovery changes saved file references; make the user save the repaired
        # links rather than silently treating the old project as up to date.
        self._saved_snapshot = (None if missing or had_missing_linked_media
                                else self.project_snapshot())
        self.update_modified_title()
        if missing:
            QMessageBox.warning(self, "Missing media",
                f"{len(missing)} media file(s) could not load:\n" + "\n".join(missing[:8]) +
                "\n\nPlease restore them before saving this project.")
        return True

    @staticmethod
    def _parse_studio_records(data, target, portable):
        if (not isinstance(data, dict) or data.get("format") != "MontaSpaceStudio"
                or data.get("version") != 1 or data.get("portable") is not portable
                or not isinstance(data.get("items"), list)):
            raise ValueError("Not a supported MontaSpace Studio project file.")
        if len(data["items"]) > MAX_MEDIA_ITEMS:
            raise ValueError("Project contains too many media items.")
        parsed = []
        for record in data["items"]:
            if not isinstance(record, dict) or record.get("type") not in ("image", "video"):
                raise ValueError("Invalid media type.")
            typ = record["type"]
            source = record["source"]
            if not isinstance(source, str) or not source or "\x00" in source:
                raise ValueError("Invalid source filename.")
            extensions = VIDEO_EXTENSIONS if typ == 'video' else SUPPORTED_EXTENSIONS
            if Path(source).suffix.lower() not in extensions:
                raise ValueError("Unsupported project media extension.")
            values = {k: float(record[k]) for k in ("x", "y", "scale", "rotation", "z")}
            if not all(math.isfinite(value) for value in values.values()):
                raise ValueError("Invalid item transform.")
            if not 0.05 <= values["scale"] <= 20:
                raise ValueError("Invalid item scale.")
            item = {"type": typ, "source": source, **values}
            if typ == "image":
                crop = [float(v) for v in record["crop"]]
                if (len(crop) != 4 or not all(math.isfinite(v) for v in crop)
                        or crop[2] <= 0 or crop[3] <= 0):
                    raise ValueError("Invalid image crop values.")
                item["crop"] = crop
            else:
                a, b = record.get("loop_a_ms"), record.get("loop_b_ms")
                for val in (a, b):
                    if val is not None and (not isinstance(val, int) or isinstance(val, bool)
                                            or val < 0 or val > 86_400_000):
                        raise ValueError("Invalid video loop marker.")
                enabled = record.get("loop_enabled", False)
                if not isinstance(enabled, bool) or (enabled and (a is None or b is None or a >= b)):
                    raise ValueError("Invalid A–B loop state.")
                view = {}
                for name, default, low, high in (
                    ("content_zoom", 1.0, 1.0, 4.0),
                    ("pan_x", 0.0, -5000.0, 5000.0),
                    ("pan_y", 0.0, -5000.0, 5000.0),
                ):
                    value = float(record.get(name, default))
                    if not math.isfinite(value) or not low <= value <= high:
                        raise ValueError(f"Invalid video view setting: {name}")
                    view[name] = value
                crop = record.get("crop")
                if crop is not None:
                    if not isinstance(crop, list) or len(crop) != 4:
                        raise ValueError("Invalid video crop values.")
                    crop = [float(v) for v in crop]
                    if not all(math.isfinite(v) for v in crop):
                        raise ValueError("Invalid video crop values.")
                    unit = record.get("crop_unit")
                    if unit == "relative":
                        pass
                    elif unit is None:
                        # v0.5.1 stored raw coordinates on a 420x236 graphics item.
                        crop = [crop[0] / 420.0, crop[1] / 236.0,
                                crop[2] / 420.0, crop[3] / 236.0]
                    else:
                        raise ValueError("Unknown video crop unit.")
                else:
                    # v0.5.0 stored one symmetric crop inset per edge.
                    inset = float(record.get("crop_inset", 0.0))
                    if not math.isfinite(inset) or not 0.0 <= inset <= 0.30:
                        raise ValueError("Invalid video view setting: crop_inset")
                    crop = [inset, inset, 1.0 - 2.0 * inset, 1.0 - 2.0 * inset]
                if (not 0 <= crop[0] < 1 or not 0 <= crop[1] < 1
                        or not 0 < crop[2] <= 1 or not 0 < crop[3] <= 1
                        or crop[0] + crop[2] > 1.00001
                        or crop[1] + crop[3] > 1.00001):
                    raise ValueError("Video crop exceeds video frame.")
                display_size = record.get("display_size")
                if display_size is not None:
                    if (not isinstance(display_size, list) or len(display_size) != 2
                            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                                   for v in display_size)):
                        raise ValueError("Invalid saved video display dimensions.")
                    display_size = [float(v) for v in display_size]
                    if (not all(math.isfinite(v) and 10 <= v <= 10000 for v in display_size)
                            or not 0.1 <= display_size[0] / display_size[1] <= 10):
                        raise ValueError("Saved video display dimensions are out of range.")
                item.update(loop_a_ms=a, loop_b_ms=b, loop_enabled=enabled,
                            crop=crop, display_size=display_size, **view)
            parsed.append(item)
        return parsed

    def _read_legacy_project(self, target):
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

        had_missing_linked_media = not portable and any(
            not Path(src).is_file() for src, _nums, _crop in parsed)
        if not portable:
            records = [{'source': str(src.resolve())} for src, _nums, _crop in parsed]
            recovered = self._recover_missing_sources(records)
            if recovered is None:
                return False
            parsed = [(Path(row['source']), nums, crop)
                      for row, (_src, nums, crop) in zip(recovered, parsed)]

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
        self._saved_snapshot = None if had_missing_linked_media else self.project_snapshot()
        self.update_modified_title()
        if missing:
            shown = "\n".join(missing[:8])
            QMessageBox.warning(self, "Missing images",
                f"{len(missing)} image(s) could not load:\n{shown}\n\n"
                "Please locate or restore these images before saving.")
            self._saved_snapshot = None
        return True
