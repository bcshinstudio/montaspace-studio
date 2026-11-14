"""Qt-free guardrails for HEIC import, drag/drop feedback, and packaging."""

from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HEICIntegrationContracts(unittest.TestCase):
    def test_decoder_has_real_pillow_heif_fallback(self):
        source = (ROOT / 'app/imaging.py').read_text(encoding='utf-8')
        for required in (
            'from pillow_heif import register_heif_opener',
            'from PIL import Image, ImageOps',
            'ImageOps.exif_transpose',
            'QImage.Format.Format_RGBA8888',
            'image.copy()',
            'PREVIEW_MAX_EDGE',
            'return _pillow_preview(filename)',
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_dragdrop_reports_failures(self):
        """Verify every drop category has a warning, not an old variable name."""
        source = (ROOT / 'app/canvas.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        canvas = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'Canvas'
        )
        methods = {
            node.name: node for node in canvas.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for method in ('_has_local_drop_urls', 'dragEnterEvent', 'dragMoveEvent', 'dropEvent'):
            self.assertIn(method, methods)

        helper = ast.get_source_segment(source, methods['_has_local_drop_urls'])
        enter = ast.get_source_segment(source, methods['dragEnterEvent'])
        move = ast.get_source_segment(source, methods['dragMoveEvent'])
        drop = ast.get_source_segment(source, methods['dropEvent'])

        # The entry handler must allow local files through to the drop handler,
        # including local files with unsupported extensions.
        self.assertIn('isLocalFile()', helper)
        self.assertIn('event.mimeData().urls()', helper)
        self.assertIn('self._has_local_drop_urls(event)', enter)
        self.assertIn('self._has_local_drop_urls(event)', move)
        self.assertIn('acceptProposedAction()', enter)
        self.assertNotIn('SUPPORTED_EXTENSIONS', enter)
        self.assertNotIn('VIDEO_EXTENSIONS', enter)
        self.assertIn('acceptProposedAction()', move)

        for required in (
            'isLocalFile()', 'SUPPORTED_EXTENSIONS', 'VIDEO_EXTENSIONS',
            'add_image(', 'add_video(', 'unsupported.append(',
            'failed_images.append(', 'failed_videos.append(',
            'QMessageBox.warning(', 'acceptProposedAction()',
        ):
            with self.subTest(required=required):
                self.assertIn(required, drop)

        self.assertIn('"Unsupported file type:"', drop)
        self.assertIn('"Could not add video:"', drop)
        self.assertIn('"Could not open image or file is missing:"', drop)

    def test_local_drop_helper_accepts_only_local_urls(self):
        """Exercise the Qt-free helper used by both drag handlers."""
        source = (ROOT / 'app/canvas.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        canvas = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Canvas')
        method = next(n for n in canvas.body if isinstance(n, ast.FunctionDef)
                      and n.name == '_has_local_drop_urls')
        # The helper is a static method using only the event's URL interface.
        self.assertTrue(any(isinstance(n, ast.Name) and n.id == 'event'
                            for n in ast.walk(method)))
        self.assertEqual([arg.arg for arg in method.args.args], ['event'])
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                     '<canvas drop helper>', 'exec'), scope := {})
        helper = scope['_has_local_drop_urls']

        class URL:
            def __init__(self, local):
                self.local = local
            def isLocalFile(self):
                return self.local
        class Mime:
            def __init__(self, urls):
                self._urls = urls
            def urls(self):
                return self._urls
        class Event:
            def __init__(self, urls):
                self._mime = Mime(urls)
            def mimeData(self):
                return self._mime
        self.assertFalse(helper(Event([])))
        self.assertFalse(helper(Event([URL(False)])))
        self.assertTrue(helper(Event([URL(False), URL(True)])))

    def test_dependencies_and_installer_collection(self):
        requirements = (ROOT / 'requirements.txt').read_text(encoding='utf-8')
        self.assertIn('pillow-heif', requirements)
        self.assertIn('Pillow', requirements)
        for batch in ('build_installer.bat', 'build_windows.bat'):
            contents = (ROOT / batch).read_text(encoding='utf-8')
            self.assertIn('--collect-all pillow_heif', contents)
            self.assertIn('tools\\check_image_codecs.py', contents)
        self.assertTrue((ROOT / 'tools/check_image_codecs.py').exists())


if __name__ == '__main__':
    unittest.main()
