"""Small, bounded video poster cache; no autoplay or long-lived extra decoders.

Windows uses the native Explorer thumbnail API first. A one-shot external
FFmpeg process is optional on any platform. Normal playback supplies a poster
when neither native nor FFmpeg extraction succeeds.
"""
import shutil
import os
import threading
from collections import OrderedDict, deque
from pathlib import Path
from weakref import WeakMethod

from PySide6.QtCore import QObject, QProcess, QTimer, QStandardPaths, Qt, Signal, QUrl
from PySide6.QtGui import QImage, QPixmap, QColor

from .windows_thumbnail import extract_windows_thumbnail
from .poster_policy import source_version_key, failed_marker_name
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink

MAX_POSTER_BYTES = 1_500_000
MAX_MEMORY_POSTERS = 12
MAX_DISK_POSTERS = 160
MAX_IMAGE_EDGE = 360
EXTRACTION_TIMEOUT_MS = 3000


POSTER_TARGET_MS = (500, 1000, 2000)
QT_ATTEMPT_TIMEOUT_MS = 1600


def _image_looks_useful(image):
    """Reject obviously empty frames (all black/all white) at tiny cost."""
    if image.isNull():
        return False
    sample = image.scaled(8, 8, Qt.AspectRatioMode.IgnoreAspectRatio,
                          Qt.TransformationMode.FastTransformation)
    sample = sample.convertToFormat(QImage.Format.Format_RGB32)
    values = []
    for y in range(sample.height()):
        for x in range(sample.width()):
            c = QColor(sample.pixel(x, y))
            values.append((c.red() * 299 + c.green() * 587 + c.blue() * 114) // 1000)
    if not values:
        return False
    avg = sum(values) / len(values)
    spread = max(values) - min(values)
    if avg < 10 and spread < 10:
        return False
    if avg > 245 and spread < 8:
        return False
    return True


class _QtPosterJob(QObject):
    """One short-lived hidden playback job to capture an early video frame."""

    finished = Signal(str, object)

    def __init__(self, filename, parent=None):
        super().__init__(parent)
        self.filename = str(Path(filename).resolve())
        self._player = QMediaPlayer(self)
        self._sink = QVideoSink(self)
        self._player.setVideoSink(self._sink)
        self._sink.videoFrameChanged.connect(self._on_frame)
        self._player.mediaStatusChanged.connect(self._on_status)
        try:
            self._player.errorOccurred.connect(self._on_error)
        except AttributeError:
            pass
        self._load_timer = QTimer(self)
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._fail)
        self._attempt_timer = QTimer(self)
        self._attempt_timer.setSingleShot(True)
        self._attempt_timer.timeout.connect(self._next_attempt)
        self._targets = list(POSTER_TARGET_MS)
        self._started = False
        self._current_target = 0

    def start(self):
        self._load_timer.start(EXTRACTION_TIMEOUT_MS + 1500)
        self._player.setSource(QUrl.fromLocalFile(self.filename))

    def _on_status(self, status):
        if status in (QMediaPlayer.MediaStatus.LoadedMedia,
                      QMediaPlayer.MediaStatus.BufferedMedia):
            if not self._started:
                self._started = True
                self._load_timer.stop()
                self._next_attempt()
        elif status in (QMediaPlayer.MediaStatus.InvalidMedia,
                        QMediaPlayer.MediaStatus.NoMedia):
            self._finish(None)
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._next_attempt()

    def _on_error(self, *_args):
        self._finish(None)

    def _next_attempt(self):
        self._attempt_timer.stop()
        if not self._targets:
            self._finish(None)
            return
        target = self._targets.pop(0)
        duration = self._player.duration()
        if duration > 0:
            target = min(target, max(0, duration - 120))
        self._current_target = max(0, int(target))
        self._player.pause()
        self._player.setPosition(self._current_target)
        self._player.play()
        self._attempt_timer.start(QT_ATTEMPT_TIMEOUT_MS)

    def _on_frame(self, frame):
        if not frame.isValid():
            return
        if self._player.position() + 80 < self._current_target:
            return
        try:
            image = frame.toImage()
        except Exception:
            image = QImage()
        if image.isNull():
            return
        if not _image_looks_useful(image) and self._targets:
            self._next_attempt()
            return
        self._finish(image)

    def _fail(self):
        self._finish(None)

    def _finish(self, image):
        if self._player is None:
            return
        self._load_timer.stop()
        self._attempt_timer.stop()
        try:
            self._sink.videoFrameChanged.disconnect(self._on_frame)
        except (RuntimeError, TypeError):
            pass
        try:
            self._player.mediaStatusChanged.disconnect(self._on_status)
        except (RuntimeError, TypeError):
            pass
        try:
            self._player.stop()
        except RuntimeError:
            pass
        player = self._player
        self._player = None
        player.deleteLater()
        self.finished.emit(self.filename, image if image is not None and not image.isNull() else None)
        self.deleteLater()


def _file_key(filename):
    return source_version_key(filename)


def _poster_directory():
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
    if not base:
        base = str(Path.home() / '.montaspace-studio' / 'cache')
    return Path(base) / 'video-posters'


class VideoPosterCache(QObject):
    """One shared poster cache; Windows Shell work runs outside the UI thread."""

    native_finished = Signal(str, object)

    def __init__(self):
        super().__init__()
        self._memory = OrderedDict()
        self._queue = deque()
        self._waiting = {}
        self._process = None
        self._active = None
        self._output = bytearray()
        self._ffmpeg = shutil.which('ffmpeg')
        self._cleaned = False
        self._native_queue = deque()
        self._native_active = False
        self._native_current = None
        self._failed_memory = set()
        self._failure_write_count = 0
        self._native_timed_out = set()
        self._native_blocked = False
        self._qt_queue = deque()
        self._qt_job = None
        self._qt_attempted = set()
        self._ffmpeg_attempted = set()
        self.native_finished.connect(self._native_result)

    def _cache_path(self, filename):
        try:
            return _poster_directory() / (_file_key(filename) + '.jpg')
        except OSError:
            return None

    def _failure_path(self, key):
        # Old versions incorrectly marked successful native extractions as
        # failures after image.scaled raised TypeError. Do not let their
        # .failed markers suppress the corrected 0.5.19 pipeline.
        return _poster_directory() / failed_marker_name(key).replace(
            '.failed', '.v519.failed')

    def _has_failed(self, key):
        if key in self._failed_memory:
            return True
        try:
            failed = self._failure_path(key).is_file()
        except OSError:
            failed = False
        if failed:
            self._failed_memory.add(key)
        return failed

    def _mark_failed(self, filename):
        """Do not retry this *version* of a failed source on later opens/Undo."""
        path = self._cache_path(filename)
        if path is None:
            return
        key = path.stem
        self._failed_memory.add(key)
        try:
            marker = self._failure_path(key)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch(exist_ok=True)
            self._failure_write_count += 1
            if self._failure_write_count % 32 == 0:
                self._prune_failure_markers()
        except OSError:
            pass

    def _prune_failure_markers(self):
        try:
            files = sorted(_poster_directory().glob('*.failed'),
                           key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[MAX_DISK_POSTERS:]:
                self._failed_memory.discard(old.stem)
                old.unlink(missing_ok=True)
        except OSError:
            pass

    def _clear_failed(self, filename):
        path = self._cache_path(filename)
        if path is None:
            return
        self._failed_memory.discard(path.stem)
        try:
            self._failure_path(path.stem).unlink(missing_ok=True)
        except OSError:
            pass

    def _from_memory(self, key):
        pixmap = self._memory.get(key)
        if pixmap is not None:
            self._memory.move_to_end(key)
        return pixmap

    def _remember(self, key, image):
        if image.isNull():
            return None
        pixmap = QPixmap.fromImage(image)
        self._memory[key] = pixmap
        self._memory.move_to_end(key)
        while len(self._memory) > MAX_MEMORY_POSTERS:
            self._memory.popitem(last=False)
        return pixmap

    def get(self, filename):
        path = self._cache_path(filename)
        if path is None:
            return None
        key = path.stem
        poster = self._from_memory(key)
        if poster is not None:
            return poster
        if path.is_file() and path.stat().st_size <= MAX_POSTER_BYTES:
            image = QImage(str(path))
            if not image.isNull() and max(image.width(), image.height()) <= MAX_IMAGE_EDGE * 2:
                return self._remember(key, image)
        return None

    def file_for(self, filename):
        path = self._cache_path(filename)
        return path if path is not None and path.is_file() and path.stat().st_size <= MAX_POSTER_BYTES else None

    def install_bytes(self, filename, content):
        """Used for optional tiny poster files embedded in portable projects."""
        if not (content and len(content) <= MAX_POSTER_BYTES):
            return False
        image = QImage.fromData(content, 'JPG')
        if image.isNull() or max(image.width(), image.height()) > MAX_IMAGE_EDGE * 2:
            return False
        self.put_image(filename, image)
        return True

    def put_image(self, filename, image):
        if image.isNull():
            return
        # Qt/PySide6's QImage.scaled() does not accept the keyword
        # `transformMode` (and some releases reject `aspectMode` as well).
        # Positional arguments work across supported PySide6 versions.
        small = image.scaled(MAX_IMAGE_EDGE, MAX_IMAGE_EDGE,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        path = self._cache_path(filename)
        if path is None:
            return
        self._remember(path.stem, small)
        self._clear_failed(filename)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix('.tmp')
            if small.save(str(temporary), 'JPG', 72) and temporary.stat().st_size <= MAX_POSTER_BYTES:
                temporary.replace(path)
            else:
                temporary.unlink(missing_ok=True)
            self._prune()
        except OSError:
            pass
        self._notify(filename)

    def request(self, filename, callback):
        """One bounded extraction per source version, shared by all users."""
        poster = self.get(filename)
        if poster is not None:
            callback(poster)
            return
        cache_path = self._cache_path(filename)
        if cache_path is None:
            return
        key = cache_path.stem
        if self._has_failed(key):
            return
        path = str(Path(filename).resolve())
        waiting = self._waiting.setdefault(path, [])
        waiting.append(WeakMethod(callback))
        if len(waiting) != 1:
            return
        self._qt_attempted.discard(path)
        self._ffmpeg_attempted.discard(path)
        if os.name == 'nt' and self._native_blocked:
            self._enqueue_qt_or_ffmpeg(path)
        elif os.name == 'nt' and not self._native_active:
            self._native_queue.append((path, key))
            self._advance_native()
        elif os.name == 'nt' and self._native_active:
            # The pending queue is bounded by one shared request per file.
            self._native_queue.append((path, key))
        else:
            self._enqueue_qt_or_ffmpeg(path)

    def _advance_native(self):
        """At most one Shell worker; no UI-thread decoding or polling."""
        if self._native_active or self._native_blocked or self._process is not None:
            return
        while self._native_queue:
            path, cache_key = self._native_queue.popleft()
            if path not in self._waiting:
                continue
            if self.get(path) is not None:
                self._notify(path)
                continue
            if self._has_failed(cache_key):
                self._waiting.pop(path, None)
                continue
            self._native_active = True
            self._native_current = (path, cache_key)
            threading.Thread(target=self._native_worker,
                             args=(path, cache_key), daemon=True).start()
            # A Shell provider might hang. Do not spawn a second Shell worker
            # until the first actually returns; resolve waiting callers in 3s.
            QTimer.singleShot(EXTRACTION_TIMEOUT_MS,
                              lambda p=path, k=cache_key: self._native_timeout(p, k))
            break

    def _native_timeout(self, path, cache_key):
        if (not self._native_active or self._native_current != (path, cache_key)
                or path not in self._waiting):
            return
        self._native_timed_out.add((path, cache_key))
        self._native_blocked = True
        # A stuck native handler might still be decoding. Never start another
        # extractor until it returns, to avoid unbounded background CPU use.
        self._mark_failed(path)
        self._waiting.pop(path, None)
        while self._native_queue:
            queued_path, _key = self._native_queue.popleft()
            if queued_path in self._waiting:
                self._mark_failed(queued_path)
                self._waiting.pop(queued_path, None)

    def _native_worker(self, path, cache_key):
        try:
            result = extract_windows_thumbnail(path, MAX_IMAGE_EDGE)
        except Exception:
            result = None
        try:
            self.native_finished.emit(path, (cache_key, result))
        except RuntimeError:
            # Application may have exited while a Shell thumbnail handler ran.
            pass

    def _native_result(self, path, packet):
        """Back on Qt's GUI thread; ignore late timed-out worker results."""
        cache_key, result = packet
        expired = (path, cache_key) in self._native_timed_out
        self._native_timed_out.discard((path, cache_key))
        self._native_active = False
        self._native_current = None
        self._native_blocked = False
        if not expired and result is not None and path in self._waiting:
            data, width, height = result
            if 0 < width <= 1024 and 0 < height <= 1024 and len(data) == width * height * 4:
                try:
                    image = QImage(data, width, height, width * 4,
                                   QImage.Format.Format_RGB32).copy()
                    if not image.isNull():
                        self.put_image(path, image)
                except (RuntimeError, TypeError, ValueError):
                    pass
        if not expired and path in self._waiting:
            self._enqueue_qt_or_ffmpeg(path)
        self._advance_native()

    def _enqueue_qt_or_ffmpeg(self, path):
        if path not in self._waiting:
            return
        if path not in self._qt_attempted:
            self._qt_attempted.add(path)
            if path not in self._qt_queue:
                self._qt_queue.append(path)
            self._advance_qt()
            return
        if self._ffmpeg and path not in self._ffmpeg_attempted:
            self._ffmpeg_attempted.add(path)
            if path not in self._queue and path != self._active:
                self._queue.append(path)
            self._advance()
            return
        self._mark_failed(path)
        self._waiting.pop(path, None)

    def _advance_qt(self):
        if self._qt_job is not None:
            return
        while self._qt_queue:
            filename = self._qt_queue.popleft()
            if filename not in self._waiting or not Path(filename).is_file():
                self._waiting.pop(filename, None)
                continue
            if self.get(filename) is not None:
                self._notify(filename)
                continue
            job = _QtPosterJob(filename, self)
            self._qt_job = job
            job.finished.connect(self._qt_finished)
            job.start()
            break

    def _qt_finished(self, filename, image):
        job = self._qt_job
        self._qt_job = None
        if image is not None and not image.isNull():
            self.put_image(filename, image)
        if filename in self._waiting and self.get(filename) is None:
            if self._ffmpeg and filename not in self._ffmpeg_attempted:
                self._ffmpeg_attempted.add(filename)
                if filename not in self._queue and filename != self._active:
                    self._queue.append(filename)
                self._advance()
            else:
                self._mark_failed(filename)
                self._waiting.pop(filename, None)
        if job is not None:
            try:
                job.finished.disconnect(self._qt_finished)
            except (RuntimeError, TypeError):
                pass
        self._advance_qt()

    def _notify(self, filename):
        path = str(Path(filename).resolve())
        self._qt_attempted.discard(path)
        self._ffmpeg_attempted.discard(path)
        callbacks = self._waiting.pop(path, [])
        poster = self.get(path)
        if poster is not None:
            for weak_callback in callbacks:
                callback = weak_callback()
                if callback is not None:
                    callback(poster)

    def _advance(self):
        if self._process is not None:
            return
        while self._queue:
            filename = self._queue.popleft()
            if filename not in self._waiting or not Path(filename).is_file():
                self._waiting.pop(filename, None)
                continue
            if self.get(filename) is not None:
                self._notify(filename)
                continue
            self._active = filename
            self._output = bytearray()
            process = QProcess(self)
            self._process = process
            process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
            process.readyReadStandardOutput.connect(self._read_output)
            process.finished.connect(self._finished)
            process.errorOccurred.connect(self._error)
            # One frame near the beginning, scaled by FFmpeg. Auto-rotation
            # handles metadata-based phone orientation. No MP4 modification.
            process.start(self._ffmpeg, [
                '-hide_banner', '-loglevel', 'error', '-nostdin', '-threads', '1',
                '-i', filename, '-map', '0:v:0', '-frames:v', '1',
                '-vf', f'scale={MAX_IMAGE_EDGE}:{MAX_IMAGE_EDGE}:force_original_aspect_ratio=decrease',
                '-f', 'image2pipe', '-vcodec', 'mjpeg', '-q:v', '5', 'pipe:1',
            ])
            QTimer.singleShot(EXTRACTION_TIMEOUT_MS,
                              lambda proc=process: self._timeout(proc))
            break

    def _read_output(self):
        if self._process is None:
            return
        chunk = bytes(self._process.readAllStandardOutput())
        if len(self._output) + len(chunk) <= MAX_POSTER_BYTES:
            self._output.extend(chunk)
        else:
            self._output.clear()
            self._process.kill()

    def _timeout(self, process):
        if self._process is process and process.state() != QProcess.ProcessState.NotRunning:
            process.kill()

    def _finished(self, *_):
        process = self._process
        if process is None:
            return
        self._read_output()
        filename = self._active
        data = bytes(self._output)
        self._process = None
        self._active = None
        self._output.clear()
        process.deleteLater()
        if filename is not None and data:
            image = QImage.fromData(data, 'JPG')
            if not image.isNull():
                self.put_image(filename, image)
        if filename is not None and filename in self._waiting and self.get(filename) is None:
            self._enqueue_qt_or_ffmpeg(filename)
        else:
            self._waiting.pop(filename, None)
        self._advance()
        self._advance_native()
        self._advance_qt()

    def _error(self, *_):
        # FailedToStart can arrive without finished; release the queue slot.
        # For a running decoder, finished handles normal cleanup.
        if (self._process is not None
                and self._process.state() == QProcess.ProcessState.NotRunning):
            self._finished()

    def _prune(self):
        if self._cleaned:
            return
        self._cleaned = True
        try:
            for pattern in ('*.jpg', '*.failed'):
                files = sorted(_poster_directory().glob(pattern),
                               key=lambda p: p.stat().st_mtime, reverse=True)
                for path in files[MAX_DISK_POSTERS:]:
                    path.unlink(missing_ok=True)
        except OSError:
            pass


poster_cache = VideoPosterCache()
