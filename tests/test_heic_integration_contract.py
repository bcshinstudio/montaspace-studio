"""Qt-free guardrails for HEIC import and reliable packaging."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HEICIntegrationContracts(unittest.TestCase):
    def test_decoder_has_real_pillow_heif_fallback(self):
        source = (ROOT / 'app/imaging.py').read_text()
        for required in ('from pillow_heif import register_heif_opener',
                         'from PIL import Image, ImageOps', 'ImageOps.exif_transpose',
                         'QImage.Format.Format_RGBA8888', 'image.copy()',
                         'PREVIEW_MAX_EDGE', 'return _pillow_preview(filename)'):
            self.assertIn(required, source)

    def test_dragdrop_reports_failures(self):
        source = (ROOT / 'app/canvas.py').read_text()
        drop = source.split('    def dropEvent(self, event):', 1)[1].split('    def wheelEvent(', 1)[0]
        self.assertIn('failures.append(', drop)
        self.assertIn('QMessageBox.warning(', drop)
        self.assertIn('add_image(', drop)

    def test_dependencies_and_installer_collection(self):
        requirements = (ROOT / 'requirements.txt').read_text()
        self.assertIn('pillow-heif', requirements)
        self.assertIn('Pillow', requirements)
        for batch in ('build_installer.bat', 'build_windows.bat'):
            contents = (ROOT / batch).read_text()
            self.assertIn('--collect-all pillow_heif', contents)
            self.assertIn('tools\\check_image_codecs.py', contents)
        self.assertTrue((ROOT / 'tools/check_image_codecs.py').exists())


if __name__ == '__main__':
    unittest.main()
