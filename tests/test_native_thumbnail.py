"""No-GUI regression checks for optional native poster extraction."""
import ast
import os
import tempfile
import unittest
from pathlib import Path

from app.windows_thumbnail import extract_windows_thumbnail

ROOT = Path(__file__).resolve().parents[1]


class NativeThumbnailTests(unittest.TestCase):
    def test_missing_video_does_not_raise(self):
        self.assertIsNone(extract_windows_thumbnail(str(ROOT / 'does-not-exist.mp4')))

    def test_invalid_size_rejected(self):
        self.assertIsNone(extract_windows_thumbnail(__file__, 0))
        self.assertIsNone(extract_windows_thumbnail(__file__, 4096))

    @unittest.skipIf(os.name == 'nt', 'Cross-platform no-op behavior only')
    def test_non_windows_returns_none(self):
        with tempfile.NamedTemporaryFile(suffix='.mp4') as video:
            self.assertIsNone(extract_windows_thumbnail(video.name))

    def test_poster_pipeline_keeps_native_and_ffmpeg_optional(self):
        source = (ROOT / 'app' / 'video_poster.py').read_text(encoding='utf-8')
        self.assertIn('extract_windows_thumbnail(path, MAX_IMAGE_EDGE)', source)
        self.assertIn('daemon=True', source)
        self.assertIn('self._enqueue_qt_or_ffmpeg(path)', source)
        self.assertIn('self.put_image(path, image)', source)
        self.assertIn('native_finished = Signal(str, object)', source)
        ast.parse(source)

    def test_windows_api_called_only_in_windows_guard(self):
        source = (ROOT / 'app' / 'windows_thumbnail.py').read_text(encoding='utf-8')
        self.assertIn("os.name != 'nt'", source)
        self.assertIn('SIIGBF_THUMBNAILONLY', source)
        self.assertIn('CoUninitialize()', source)
        self.assertIn('DeleteObject(bitmap)', source)
        self.assertIn('GetDIBits', source)
        ast.parse(source)


if __name__ == '__main__':
    unittest.main()
