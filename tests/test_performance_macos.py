"""Cross-platform memory diagnostics contracts; mock the macOS kernel on non-Macs.

Tests do not prove actual Mach behavior; run on an Apple Silicon Mac as well.
"""
import ctypes
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import performance


class MacMemoryTests(unittest.TestCase):
    def test_abi_layouts(self):
        self.assertEqual(ctypes.sizeof(performance._MachTaskBasicInfo), 48)
        self.assertEqual(ctypes.sizeof(performance._MachTaskVMInfoRev1), 152)
        self.assertEqual(performance._MachTaskVMInfoRev1.phys_footprint.offset, 144)

    def test_nonmac_returns_none_without_loading_mach(self):
        with patch.object(performance.sys, 'platform', 'linux'):
            self.assertIsNone(performance._mac_task_info(20, performance._MachTaskBasicInfo))
            self.assertIsNone(performance.memory_working_set_mb())
            self.assertIsNone(performance.memory_private_mb())

    def test_macos_memory_values_and_units(self):
        basic = performance._MachTaskBasicInfo()
        basic.resident_size = 80 * 1024 * 1024
        basic.resident_size_max = 120 * 1024 * 1024
        vm = performance._MachTaskVMInfoRev1()
        vm.phys_footprint = 65 * 1024 * 1024

        def fake_info(flavor, info_type):
            self.assertIn(flavor, (20, 22))
            return vm if flavor == 22 else basic

        with patch.object(performance.sys, 'platform', 'darwin'), patch.object(performance, '_mac_task_info', side_effect=fake_info):
            self.assertEqual(performance.memory_working_set_mb(), 80)
            self.assertEqual(performance.memory_peak_working_set_mb(), 120)
            self.assertEqual(performance.memory_private_mb(), 65)

    def test_kernel_error_returns_none(self):
        with patch.object(performance.sys, 'platform', 'darwin'), patch.object(performance, '_mac_task_info', return_value=None):
            self.assertIsNone(performance.memory_working_set_mb())
            self.assertIsNone(performance.memory_peak_working_set_mb())
            self.assertIsNone(performance.memory_private_mb())

    def test_mach_api_reads_native_buffer(self):
        class FakeSymbol:
            def __init__(self, callback):
                self.callback = callback
            def __call__(self, *args):
                return self.callback(*args)

        class FakeLibrary:
            def __init__(self):
                self.task_info = FakeSymbol(self.fill)
            def fill(self, task, flavor, pointer, count_pointer):
                self_task = 1234
                self.assert_task = task
                if flavor == 20:
                    buffer = performance._MachTaskBasicInfo()
                    buffer.resident_size = 96 * 1024 * 1024
                else:
                    buffer = performance._MachTaskVMInfoRev1()
                    buffer.phys_footprint = 64 * 1024 * 1024
                ctypes.memmove(pointer, ctypes.byref(buffer), ctypes.sizeof(buffer))
                return 0

        fake = FakeLibrary()
        with patch.object(performance.sys, 'platform', 'darwin'), \
             patch.object(performance.ctypes, 'CDLL', return_value=fake), \
             patch.object(performance.ctypes.c_uint32, 'in_dll', return_value=ctypes.c_uint32(1234)):
            self.assertEqual(performance.memory_working_set_mb(), 96)
            self.assertEqual(performance.memory_private_mb(), 64)

    def test_windows_guard_is_retained(self):
        source = (ROOT / 'app/performance.py').read_text()
        self.assertIn('ctypes.WinDLL("kernel32", use_last_error=True)', source)
        self.assertIn('ctypes.WinDLL("psapi", use_last_error=True)', source)
        self.assertIn('"PrivateUsage"', source)


if __name__ == '__main__':
    unittest.main()
