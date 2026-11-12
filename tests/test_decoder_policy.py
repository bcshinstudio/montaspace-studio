"""Startup decoder selection without importing Qt or changing the user's machine."""
import unittest
from app.decoder_policy import configure_decoder, QT_DECODER_ENV, STUDIO_DECODER_ENV


class DecoderPolicyTests(unittest.TestCase):
    def test_windows_defaults_to_software(self):
        env = {}
        self.assertEqual(configure_decoder(env, 'win32'), 'software (Windows default)')
        self.assertEqual(env[QT_DECODER_ENV], ',')

    def test_non_windows_uses_native_default(self):
        env = {}
        self.assertEqual(configure_decoder(env, 'darwin'), 'Qt platform default')
        self.assertNotIn(QT_DECODER_ENV, env)

    def test_hardware_override_clears_qt_env(self):
        env = {STUDIO_DECODER_ENV: 'hardware', QT_DECODER_ENV: ','}
        self.assertEqual(configure_decoder(env, 'win32'), 'hardware (override)')
        self.assertNotIn(QT_DECODER_ENV, env)

    def test_explicit_software_on_any_platform(self):
        env = {STUDIO_DECODER_ENV: 'software'}
        self.assertEqual(configure_decoder(env, 'darwin'), 'software (override)')
        self.assertEqual(env[QT_DECODER_ENV], ',')

    def test_qt_environment_has_priority_in_auto_mode(self):
        env = {STUDIO_DECODER_ENV: 'auto', QT_DECODER_ENV: 'd3d11va'}
        self.assertEqual(configure_decoder(env, 'win32'), 'Qt environment override')
        self.assertEqual(env[QT_DECODER_ENV], 'd3d11va')

    def test_invalid_override_rejected(self):
        with self.assertRaises(ValueError):
            configure_decoder({STUDIO_DECODER_ENV: 'gpu-fast'}, 'win32')

    def test_idempotent(self):
        env = {}
        configure_decoder(env, 'win32')
        configure_decoder(env, 'win32')
        self.assertEqual(env[QT_DECODER_ENV], ',')


if __name__ == '__main__':
    unittest.main()
