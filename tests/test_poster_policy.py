"""No-GUI tests for the bounded poster retry identity policy."""
import tempfile
import unittest
from pathlib import Path
from app.poster_policy import source_version_key, failed_marker_name


class PosterPolicyTests(unittest.TestCase):
    def test_same_source_version_reuses_key(self):
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / 'clip.mp4'
            video.write_bytes(b'first-version')
            self.assertEqual(source_version_key(video), source_version_key(video))

    def test_modified_source_allows_new_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / 'clip.mp4'
            video.write_bytes(b'first-version')
            original = source_version_key(video)
            video.write_bytes(b'second-version-expanded')
            self.assertNotEqual(original, source_version_key(video))

    def test_failed_marker_is_safely_namespaced(self):
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / 'clip.mp4'
            video.write_bytes(b'sample')
            key = source_version_key(video)
            self.assertEqual(failed_marker_name(key), key + '.failed')
            with self.assertRaises(ValueError):
                failed_marker_name('../escape')

    def test_no_such_source_cannot_be_marked(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(OSError):
                source_version_key(Path(d) / 'missing.mp4')


if __name__ == '__main__':
    unittest.main()
