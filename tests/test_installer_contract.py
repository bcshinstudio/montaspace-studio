"""Source-level guardrails for installer build and uninstall safety."""
import re
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

class InstallerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nsi = (ROOT / 'installer/MontaSpaceStudio.nsi').read_text()
        cls.bat = (ROOT / 'build_installer.bat').read_text()
        cls.meta = (ROOT / 'windows_version_info.txt').read_text()
        cls.verify = (ROOT / 'verify_uninstall.bat').read_text()
        cls.config = (ROOT / 'app/config.py').read_text()

    def test_all_versions_match(self):
        self.assertIn('APP_VERSION = "0.6.1"', self.config)
        self.assertIn('!define PRODUCT_VERSION "0.6.1"', self.nsi)
        self.assertIn('VIProductVersion "0.6.1.0"', self.nsi)
        self.assertIn('filevers=(0, 6, 1, 0)', self.meta)
        self.assertIn('prodvers=(0, 6, 1, 0)', self.meta)
        self.assertIn('MontaSpaceStudio_Setup_0.6.1.exe', self.bat)

    def test_cache_opt_in_defaults_off(self):
        self.assertIn('UninstPage custom un.CacheCleanupPageCreate un.CacheCleanupPageLeave', self.nsi)
        self.assertIn('${NSD_Uncheck} $CacheCleanupCheck', self.nsi)
        self.assertIn('${If} $RemoveCache == ${BST_CHECKED}', self.nsi)

    def test_cache_targets_scoped_to_app(self):
        body = self.nsi.split('${If} $RemoveCache == ${BST_CHECKED}')[1].split('${EndIf}')[0]
        self.assertIn('MontaSpaceStudio\\cache\\video-posters', body)
        self.assertIn('.montaspace-studio\\cache\\video-posters', body)
        self.assertNotIn('RMDir /r "$LOCALAPPDATA"', body)
        self.assertNotIn('RMDir /r "$PROFILE"', body)
        self.assertNotIn('*.mstudio', body)

    def test_checker_read_only_and_nonzero_on_failure(self):
        self.assertIn('exit /b %FAIL%', self.verify)
        self.assertIn('reg query ', self.verify)
        self.assertNotRegex(self.verify.lower(), r'(?m)^\s*(?:del|erase|rmdir|rd)\b')

    def test_build_keeps_source_and_env(self):
        for safe in ['if exist "build\\" rmdir', 'if exist "dist\\" rmdir', 'if exist "MontaSpaceStudio.spec" del']:
            self.assertIn(safe, self.bat)
        for protected in ['.git', '.venv']:
            self.assertIn(protected, self.bat)

if __name__ == '__main__':
    unittest.main()
