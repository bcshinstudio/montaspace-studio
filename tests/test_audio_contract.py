"""Compatibility and wiring checks, including platform without GUI support."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class AudioContractTests(unittest.TestCase):
    def test_independent_audio_and_default(self):
        s = (ROOT / 'app/video_item.py').read_text(encoding='utf-8')
        self.assertIn('self.audio = QAudioOutput(self)', s)
        self.assertIn('self.volume_percent = 65', s)
        self.assertIn('self.audio.setMuted(self.muted)', s)

    def test_undo_and_persistence(self):
        self.assertIn('item.volume_percent, item.muted', (ROOT / 'app/canvas.py').read_text(encoding='utf-8'))
        s = (ROOT / 'app/project.py').read_text(encoding='utf-8')
        self.assertIn('record.get("volume", 65)', s)
        self.assertIn('record.get("muted", False)', s)
