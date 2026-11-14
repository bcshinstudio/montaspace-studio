"""Pure-Python tests: enforce platform icon resources and build contract."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import application_icon_path

class MacPortabilityContract(unittest.TestCase):
    def test_icon_assets_exist(self):
        for ext in ('.ico', '.png', '.icns'):
            self.assertGreater((ROOT / 'assets' / ('MontaSpaceStudio' + ext)).stat().st_size, 100)

    def test_platform_icon_selection(self):
        with patch('app.config.sys.platform', 'darwin'):
            self.assertEqual(application_icon_path().suffix, '.png')
        with patch('app.config.sys.platform', 'win32'):
            self.assertEqual(application_icon_path().suffix, '.ico')

    def test_macos_build_contract(self):
        script = (ROOT / 'build_macos.sh').read_text()
        self.assertIn('uname -s', script)
        self.assertIn('--collect-all pillow_heif', script)
        self.assertIn('--windowed', script)
        self.assertIn('dist/MontaSpaceStudio.app', script)
        self.assertIn('test_macos_portability.py', script)

if __name__ == '__main__':
    unittest.main()
