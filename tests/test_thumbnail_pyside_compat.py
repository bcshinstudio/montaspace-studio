"""Source-level regression tests for PySide6 API errors observed on Windows."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'app'


class ThumbnailCompatibilityTests(unittest.TestCase):
    def test_qimage_scaled_uses_positional_enum_args(self):
        tree = ast.parse((ROOT / 'video_poster.py').read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == 'scaled']
        self.assertGreaterEqual(len(calls), 2)
        for node in calls:
            self.assertFalse(any(k.arg in ('transformMode', 'aspectMode') for k in node.keywords))

    def test_orientation_converter_runtime_error_handled(self):
        tree = ast.parse((ROOT / 'video_item.py').read_text(encoding='utf-8'))
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                  and n.name == '_on_media_metadata_changed')
        attempts = [n for n in ast.walk(fn) if isinstance(n, ast.Try) and
                    any(isinstance(x, ast.Attribute) and x.attr == 'Orientation'
                        for x in ast.walk(n))]
        self.assertTrue(attempts)
        handlers = [h for n in attempts for h in n.handlers]
        self.assertTrue(any('RuntimeError' in ast.unparse(h.type) for h in handlers))

    def test_failed_marker_version_bumped(self):
        source = (ROOT / 'video_poster.py').read_text(encoding='utf-8')
        self.assertIn("'.v519.failed'", source)

if __name__ == '__main__':
    unittest.main()
