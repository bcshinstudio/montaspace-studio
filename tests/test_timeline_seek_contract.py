"""Static regression tests for timeline interaction (GUI needs Windows)."""
import ast
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'app' / 'video_item.py'
TREE = ast.parse(PATH.read_text(encoding='utf-8'))


def method(cls, func):
    for node in TREE.body:
        if isinstance(node, ast.ClassDef) and node.name == cls:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == func:
                    return ast.get_source_segment(PATH.read_text(encoding='utf-8'), item)
    raise AssertionError(f'{cls}.{func} missing')


class TimelineSeekContract(unittest.TestCase):
    def test_track_click_sets_requested_value(self):
        source = method('VideoSeekSlider', 'mousePressEvent')
        self.assertIn('QStyle.sliderValueFromPosition', source)
        self.assertIn('self.setValue(value)', source)
        self.assertIn('handle.contains(pointer)', source)

    def test_user_seeks_are_connected(self):
        source = method('VideoControls', '__init__')
        self.assertIn('self.seek.valueChanged.connect(self._seek_to)', source)
        self.assertNotIn('sliderMoved.connect(video.player.setPosition)', source)

    def test_capture_uses_selected_target(self):
        self.assertIn('self._selected_position()', method('VideoControls', 'capture_a'))
        self.assertIn('self._selected_position()', method('VideoControls', 'capture_b'))

    def test_async_position_does_not_trigger_another_seek(self):
        source = method('VideoControls', 'update_position')
        self.assertIn('self.seek.blockSignals(True)', source)
        self.assertNotIn('self.video.player.setPosition(', source)


if __name__ == '__main__':
    unittest.main()
