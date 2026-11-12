"""Real whiteboard regression checks. Run via run_regression_tests.bat on Windows.

Creates temporary media and projects; never touches user files. These tests exercise
Qt scene operations but are NOT a substitute for visual/audio playback verification.
"""
import json
import os
import tempfile
import shutil
import unittest
from pathlib import Path

try:
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QImage, QColor
    from PySide6.QtWidgets import QApplication
    from PySide6.QtMultimedia import QMediaPlayer
    from app.window import MontaSpace
    from app.video_poster import poster_cache
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

SAMPLE_VIDEO = Path(__file__).resolve().parent / 'fixtures' / 'sample.mp4'


@unittest.skipUnless(QT_AVAILABLE, 'PySide6 not installed; GUI tests must run on Windows .venv')
class RealWhiteboardRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='studio-regression-')
        self.root = Path(self.temp.name)
        photo = QImage(120, 80, QImage.Format.Format_RGB32)
        photo.fill(QColor('#487cb0'))
        self.photo = self.root / 'test_photo.png'
        self.assertTrue(photo.save(str(self.photo)))
        self.video_file = self.root / 'test_video.mp4'
        shutil.copyfile(SAMPLE_VIDEO, self.video_file)
        self.board = MontaSpace()
        self.board.resize(850, 600)
        self.board.show()
        self.app.processEvents()

    def tearDown(self):
        # Cleanup is never allowed to prompt for saving from an automated test.
        self.board.confirm_discard_changes = lambda: True
        self.board.new_project()
        self.board.close()
        self.board.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def add_photo(self):
        self.assertTrue(self.board.canvas.add_image(str(self.photo), scene_pos=QPointF(50, 60)))
        return self.board.canvas.image_stack()[0]

    def add_video(self):
        self.assertTrue(SAMPLE_VIDEO.is_file(), 'Tiny bundled MP4 fixture is missing')
        self.assertTrue(self.board.canvas.add_video(str(self.video_file), scene_pos=QPointF(80, 90), show_controls=False))
        return self.board.canvas._last_added_video


    def test_independent_video_audio_and_undo_redo(self):
        first = self.add_video()
        second_path = self.root / 'second.mp4'
        shutil.copyfile(self.video_file, second_path)
        self.assertTrue(self.board.canvas.add_video(str(second_path), show_controls=False))
        second = self.board.canvas._last_added_video
        self.assertEqual(first.volume_percent, 65)
        self.assertFalse(first.muted)
        before = self.board.canvas.capture_state()
        first.set_audio_state(volume=24, muted=True)
        self.board.canvas.record_edit(before, 'Change audio')
        self.assertEqual((first.volume_percent, first.muted), (24, True))
        self.assertEqual((second.volume_percent, second.muted), (65, False))
        self.assertAlmostEqual(first.audio.volume(), 0.24)
        self.assertTrue(first.audio.isMuted())
        self.board.perform_undo()
        self.assertEqual((first.volume_percent, first.muted), (65, False))
        self.board.perform_redo()
        self.assertEqual((first.volume_percent, first.muted), (24, True))
        self.assertEqual((second.volume_percent, second.muted), (65, False))

    def test_audio_settings_linked_and_portable_roundtrip(self):
        for suffix in ('.mstudio', '.mstudiopack'):
            self.board.new_project()
            item = self.add_video()
            item.set_audio_state(volume=33, muted=True)
            target = self.root / ('audio' + suffix)
            self.assertTrue(self.board._write_project(target))
            self.assertTrue(self.board._read_project(target))
            restored = self.board.canvas.video_items()[0]
            self.assertEqual((restored.volume_percent, restored.muted), (33, True))
            self.assertAlmostEqual(restored.audio.volume(), .33)
            self.assertTrue(restored.audio.isMuted())

    def test_audio_old_project_defaults_and_invalid_validation(self):
        item = self.add_video()
        destination = self.root / 'old.mstudio'
        self.assertTrue(self.board._write_project(destination))
        payload = json.loads(destination.read_text(encoding='utf-8'))
        payload['items'][0].pop('volume')
        payload['items'][0].pop('muted')
        destination.write_text(json.dumps(payload), encoding='utf-8')
        self.assertTrue(self.board._read_project(destination))
        restored = self.board.canvas.video_items()[0]
        self.assertEqual((restored.volume_percent, restored.muted), (65, False))
        for invalid in (-1, 101, '50', True):
            payload['items'][0]['volume'] = invalid
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    self.board._parse_studio_records(payload, destination, False)

    def test_photo_insert_and_non_destructive_transform(self):
        photo = self.add_photo()
        photo.setPos(QPointF(95, 115))
        photo.setRotation(32)
        photo.setScale(1.5)
        photo.start_crop()
        photo.crop_rect = QRectF(12, 8, 80, 56)
        photo.end_crop(True)
        self.assertEqual((round(photo.pos().x()), round(photo.pos().y())), (95, 115))
        self.assertEqual(photo.rotation(), 32)
        self.assertEqual(photo.scale(), 1.5)
        self.assertLess(photo.crop_rect.width(), photo.full_rect.width())
        self.assertTrue(self.photo.is_file())

    def test_photo_undo_redo(self):
        self.add_photo()
        self.assertEqual(len(self.board.canvas.image_stack()), 1)
        self.board.perform_undo()
        self.assertEqual(len(self.board.canvas.image_stack()), 0)
        self.board.perform_redo()
        self.assertEqual(len(self.board.canvas.image_stack()), 1)

    def test_photo_duplicate_and_undo(self):
        photo = self.add_photo()
        photo.setSelected(True)
        self.board.canvas.duplicate_selected()
        self.assertEqual(len(self.board.canvas.image_stack()), 2)
        self.board.perform_undo()
        self.assertEqual(len(self.board.canvas.image_stack()), 1)

    def test_photo_linked_roundtrip(self):
        photo = self.add_photo()
        photo.setRotation(15)
        photo.setScale(1.2)
        destination = self.root / 'test.mstudio'
        self.assertTrue(self.board._write_project(destination))
        self.assertTrue(self.board._read_project(destination))
        result = self.board.canvas.image_stack()
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0].rotation(), 15)
        self.assertAlmostEqual(result[0].scale(), 1.2)

    def test_photo_portable_roundtrip(self):
        self.add_photo()
        destination = self.root / 'test.mstudiopack'
        self.assertTrue(self.board._write_project(destination))
        self.assertTrue(self.board._read_project(destination))
        self.assertEqual(len(self.board.canvas.image_stack()), 1)

    def test_linked_missing_media_cancel_preserves_open_board(self):
        from unittest.mock import patch
        self.add_photo()
        project = self.root / 'missing.mstudio'
        self.assertTrue(self.board._write_project(project))
        data = json.loads(project.read_text(encoding='utf-8'))
        data['items'][0]['source'] = 'missing_photo.jpg'
        project.write_text(json.dumps(data), encoding='utf-8')
        old_project = self.board.project_path
        old_snapshot = self.board.project_snapshot()
        with patch.object(self.board, '_recover_missing_sources', return_value=None):
            self.assertFalse(self.board._read_project(project))
        self.assertEqual(self.board.project_path, old_project)
        self.assertEqual(self.board.project_snapshot(), old_snapshot)

    def test_linked_missing_media_recovery_preserves_layout(self):
        from unittest.mock import patch
        photo = self.add_photo()
        photo.setPos(QPointF(123, 177))
        project = self.root / 'recovery.mstudio'
        self.assertTrue(self.board._write_project(project))
        data = json.loads(project.read_text(encoding='utf-8'))
        data['items'][0]['source'] = 'old/location/test_photo.png'
        project.write_text(json.dumps(data), encoding='utf-8')
        from app.project_reliability import apply_relocations
        def fake_recover(records):
            return apply_relocations(records, {records[0]['source']: str(self.photo)})
        with patch.object(self.board, '_recover_missing_sources', side_effect=fake_recover):
            self.assertTrue(self.board._read_project(project))
        restored = self.board.canvas.image_stack()
        self.assertEqual(len(restored), 1)
        self.assertAlmostEqual(restored[0].pos().x(), 123)
        self.assertAlmostEqual(restored[0].pos().y(), 177)
        self.assertTrue(self.board.project_is_modified())
        # Saving commits the recovered links for subsequent opens.
        self.assertTrue(self.board.save_project())
        self.assertFalse(self.board.project_is_modified())
        self.assertTrue(self.board._read_project(project))
        self.assertEqual(len(self.board.canvas.image_stack()), 1)

    def test_corrupt_project_preserves_existing_board(self):
        self.add_photo()
        saved = self.board.project_snapshot()
        corrupt = self.root / 'corrupt.mstudio'
        corrupt.write_text('{garbled', encoding='utf-8')
        from unittest.mock import patch
        with patch('app.project.QMessageBox.critical'):
            self.assertFalse(self.board._read_project(corrupt))
        self.assertEqual(self.board.project_snapshot(), saved)

    def test_legacy_missing_photo_cancel_preserves_existing_board(self):
        self.add_photo()
        before = self.board.project_snapshot()
        legacy = self.root / 'legacy.mspace'
        legacy.write_text(json.dumps({
            'format': 'MontaSpace', 'version': 1,
            'images': [{'source': 'not_here.jpg', 'x': 0, 'y': 0, 'scale': 1,
                        'rotation': 0, 'z': 0, 'crop': [0, 0, 20, 20]}]
        }), encoding='utf-8')
        from unittest.mock import patch
        with patch.object(self.board, '_recover_missing_sources', return_value=None):
            self.assertFalse(self.board._read_project(legacy))
        self.assertEqual(self.board.project_snapshot(), before)

    def test_video_does_not_autoplay_on_insert(self):
        video = self.add_video()
        self.assertNotEqual(video.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
        self.assertEqual(len(self.board.canvas.video_items()), 1)

    def test_video_undo_redo_reconstructs_item(self):
        self.add_video()
        self.board.perform_undo()
        self.app.processEvents()
        self.assertEqual(len(self.board.canvas.video_items()), 0)
        self.board.perform_redo()
        self.app.processEvents()
        self.assertEqual(len(self.board.canvas.video_items()), 1)
        self.assertNotEqual(self.board.canvas.video_items()[0].player.playbackState(),
                            QMediaPlayer.PlaybackState.PlayingState)

    def test_video_view_crop_and_loop_state(self):
        video = self.add_video()
        bounds = video.base_rect()
        video.set_content_view(zoom=1.7,
                               crop_rect=QRectF(8, 8, bounds.width()-16, bounds.height()-16),
                               pan_x=4, pan_y=4)
        video.set_loop_a(200)
        video.set_loop_b(1200)
        video.set_loop_enabled(True)
        self.assertAlmostEqual(video.content_zoom, 1.7)
        self.assertLess(video.crop_rect.width(), bounds.width())
        self.assertTrue(video.loop_enabled)
        self.assertEqual((video.loop_a_ms, video.loop_b_ms), (200, 1200))

    def test_video_controls_capture_pending_seek(self):
        video = self.add_video()
        video.controls(self.board)
        panel = video._controls
        # Synchronous selection must not depend on asynchronous Qt seek completion.
        panel._pending_seek_ms = 200
        panel.capture_a()
        panel._pending_seek_ms = 1200
        panel.capture_b()
        self.assertEqual((video.loop_a_ms, video.loop_b_ms), (200, 1200))
        panel.close()
        self.app.processEvents()

    def test_video_linked_roundtrip_preserves_edit_state(self):
        video = self.add_video()
        video.setPos(135, 175)
        video.setScale(1.2)
        video.restore_display_size(160, 90)
        video.set_loop_a(200)
        video.set_loop_b(1500)
        video.set_loop_enabled(True)
        video.set_content_view(zoom=1.5, crop=0.1)
        dest = self.root / 'mixed.mstudio'
        self.assertTrue(self.board._write_project(dest))
        saved = json.loads(dest.read_text(encoding='utf-8'))
        self.assertEqual(sum(i['type']=='video' for i in saved['items']), 1)
        self.assertTrue(self.board._read_project(dest))
        restored = self.board.canvas.video_items()
        self.assertEqual(len(restored), 1)
        self.assertTrue(restored[0].loop_enabled)
        self.assertEqual((restored[0].loop_a_ms, restored[0].loop_b_ms), (200, 1500))
        self.assertAlmostEqual(restored[0].content_zoom, 1.5)
        self.assertAlmostEqual(restored[0].pos().x(), 135)
        self.assertAlmostEqual(restored[0].scale(), 1.2)
        self.assertNotEqual(restored[0].player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)

    def test_mixed_portable_roundtrip(self):
        self.add_photo()
        self.add_video()
        dest = self.root / 'mixed.mstudiopack'
        self.assertTrue(self.board._write_project(dest))
        self.assertTrue(self.board._read_project(dest))
        self.assertEqual(len(self.board.canvas.image_stack()), 1)
        self.assertEqual(len(self.board.canvas.video_items()), 1)

    def test_cached_video_poster_is_stored_and_retrievable(self):
        image = QImage(70, 40, QImage.Format.Format_RGB32)
        image.fill(QColor('darkcyan'))
        poster_cache.put_image(str(self.video_file), image)
        cached = poster_cache.get(str(self.video_file))
        self.assertIsNotNone(cached)
        self.assertFalse(cached.isNull())
        self.assertLessEqual(max(cached.width(), cached.height()), 360)

    def test_new_board_clears_all_media(self):
        self.add_photo()
        self.add_video()
        self.board.confirm_discard_changes = lambda: True
        self.board.new_project()
        self.app.processEvents()
        self.assertEqual(len(self.board.canvas.image_stack()), 0)
        self.assertEqual(len(self.board.canvas.video_items()), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
