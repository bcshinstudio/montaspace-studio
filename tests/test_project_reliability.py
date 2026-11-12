"""Deterministic tests for project recovery and safe staged writes."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.project_reliability import (resolve_sources, missing_sources,
                                     candidate_relocations, apply_relocations,
                                     verify_staged_project)


class ProjectReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ms-reliability-')
        self.root = Path(self.temp.name)
        self.project = self.root / 'projects'
        self.project.mkdir()
        self.media = self.root / 'moved-media'
        self.media.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_relative_path_survives_move_as_unit(self):
        source = self.project / 'media' / 'movie.mp4'
        source.parent.mkdir()
        source.write_bytes(b'test')
        items = resolve_sources([{'source': 'media/movie.mp4'}], self.project)
        self.assertEqual(missing_sources(items), [])
        self.assertEqual(items[0]['source'], str(source.resolve()))

    def test_portable_file_relative_to_extraction(self):
        items = resolve_sources([{'source': 'videos/movie.mp4'}], self.project, self.media)
        self.assertEqual(items[0]['source'], str((self.media / 'videos' / 'movie.mp4').resolve()))

    def test_missing_deduplicates_paths(self):
        path = str(self.root / 'absent.jpg')
        self.assertEqual(missing_sources([{'source': path}, {'source': path}]), [path])

    def test_recovery_recognizes_single_file(self):
        missing = str(self.root / 'old' / 'movie.mp4')
        correct = self.media / 'movie.mp4'
        correct.write_bytes(b'video')
        self.assertEqual(candidate_relocations([missing], self.media), {missing: str(correct.resolve())})

    def test_recovery_matches_nested_folder(self):
        nested = self.media / 'phone' / '2026'
        nested.mkdir(parents=True)
        file = nested / 'clip.mp4'
        file.write_bytes(b'clip')
        missing = str(self.root / 'old' / 'clip.mp4')
        self.assertEqual(candidate_relocations([missing], self.media)[missing], str(file.resolve()))

    def test_recovery_avoids_ambiguous_duplicate_filenames(self):
        for folder in ('a', 'b'):
            path = self.media / folder
            path.mkdir()
            (path / 'clip.mp4').write_bytes(b'video')
        self.assertEqual(candidate_relocations([str(self.root / 'clip.mp4')], self.media), {})

    def test_recovery_scan_is_bounded(self):
        (self.media / 'clip.mp4').write_bytes(b'video')
        (self.media / 'z-other.jpg').write_bytes(b'photo')
        self.assertEqual(candidate_relocations([str(self.root / 'clip.mp4')], self.media, max_entries=1), {})

    def test_recovery_does_not_change_input_records(self):
        old = str(self.root / 'old.mp4')
        new = str(self.media / 'new.mp4')
        source = [{'type': 'video', 'source': old, 'scale': 1.2}]
        result = apply_relocations(source, {old: new})
        self.assertEqual(source[0]['source'], old)
        self.assertEqual(result[0]['source'], new)
        self.assertEqual(result[0]['scale'], 1.2)

    def _payload(self, portable):
        return {'format': 'MontaSpaceStudio', 'version': 1, 'portable': portable,
                'items': [{'type': 'image', 'source': 'images/one.jpg'}]}

    def test_verify_staged_linked(self):
        filename = self.root / 'staged.tmp'
        filename.write_text(json.dumps(self._payload(False)), encoding='utf-8')
        verify_staged_project(filename, 1, 0, False)

    def test_verify_staged_portable(self):
        filename = self.root / 'staged.tmp'
        with zipfile.ZipFile(filename, 'w') as archive:
            archive.writestr('project.json', json.dumps(self._payload(True)))
            archive.writestr('images/one.jpg', b'photo')
        verify_staged_project(filename, 1, 0, True)

    def test_missing_staged_embedded_media_fails(self):
        filename = self.root / 'staged.tmp'
        with zipfile.ZipFile(filename, 'w') as archive:
            archive.writestr('project.json', json.dumps(self._payload(True)))
        with self.assertRaisesRegex(ValueError, 'missing embedded'):
            verify_staged_project(filename, 1, 0, True)

    def test_wrong_staged_record_count_fails(self):
        filename = self.root / 'staged.tmp'
        filename.write_text(json.dumps(self._payload(False)), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'verification failed'):
            verify_staged_project(filename, 2, 0, False)

    def test_bad_json_fails_before_replacement(self):
        filename = self.root / 'staged.tmp'
        filename.write_text('{invalid', encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError):
            verify_staged_project(filename, 0, 0, False)


if __name__ == '__main__':
    unittest.main()
