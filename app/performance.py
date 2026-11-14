"""On-demand per-process memory diagnostics for Windows and macOS.

The existing Windows values are preserved. On macOS, working set means Mach
resident size; peak means Mach maximum resident size; and the private-memory
slot reports ``phys_footprint`` (physical footprint), NOT Windows private
committed bytes. These statistics must not be compared as equivalent.

No additional packages or administrator privileges are required.
"""
import sys
import ctypes
from ctypes import wintypes

_MB = 1024 * 1024


class _MachTimeValue(ctypes.Structure):
    _fields_ = [("seconds", ctypes.c_int32), ("microseconds", ctypes.c_int32)]


class _MachTaskBasicInfo(ctypes.Structure):
    """mach_task_basic_info, MACH_TASK_BASIC_INFO (20), 48 bytes."""
    _fields_ = [
        ("virtual_size", ctypes.c_uint64),
        ("resident_size", ctypes.c_uint64),
        ("resident_size_max", ctypes.c_uint64),
        ("user_time", _MachTimeValue),
        ("system_time", _MachTimeValue),
        ("policy", ctypes.c_int32),
        ("suspend_count", ctypes.c_int32),
    ]


class _MachTaskVMInfoRev1(ctypes.Structure):
    """task_vm_info through rev1 phys_footprint, TASK_VM_INFO (22)."""
    _fields_ = [
        ("virtual_size", ctypes.c_uint64),
        ("region_count", ctypes.c_int32),
        ("page_size", ctypes.c_int32),
        ("resident_size", ctypes.c_uint64),
        ("resident_size_peak", ctypes.c_uint64),
        ("device", ctypes.c_uint64),
        ("device_peak", ctypes.c_uint64),
        ("internal", ctypes.c_uint64),
        ("internal_peak", ctypes.c_uint64),
        ("external", ctypes.c_uint64),
        ("external_peak", ctypes.c_uint64),
        ("reusable", ctypes.c_uint64),
        ("reusable_peak", ctypes.c_uint64),
        ("purgeable_volatile_pmap", ctypes.c_uint64),
        ("purgeable_volatile_resident", ctypes.c_uint64),
        ("purgeable_volatile_virtual", ctypes.c_uint64),
        ("compressed", ctypes.c_uint64),
        ("compressed_peak", ctypes.c_uint64),
        ("compressed_lifetime", ctypes.c_uint64),
        ("phys_footprint", ctypes.c_uint64),
    ]


def _mac_task_info(flavor, info_type):
    """Return Mach self task info or None on kernel/API failure.

    Mach counts use 32-bit natural_t elements, not bytes. A rev1-sized
    TASK_VM_INFO response works with newer macOS kernels as well.
    """
    if sys.platform != "darwin":
        return None
    try:
        lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
        task = ctypes.c_uint32.in_dll(lib, 'mach_task_self_').value
        task_info = lib.task_info
        task_info.argtypes = [
            ctypes.c_uint32, ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_uint32),
        ]
        task_info.restype = ctypes.c_int32
        result = info_type()
        count = ctypes.c_uint32(ctypes.sizeof(result) // ctypes.sizeof(ctypes.c_int32))
        status = task_info(task, flavor, ctypes.cast(ctypes.byref(result), ctypes.POINTER(ctypes.c_int32)), ctypes.byref(count))
        if status != 0 or count.value < ctypes.sizeof(result) // 4:
            return None
        return result
    except (OSError, AttributeError, ValueError):
        return None


def memory_working_set_mb():
    """Current process resident memory (Windows working set / macOS RSS)."""
    if sys.platform == "darwin":
        info = _mac_task_info(20, _MachTaskBasicInfo)
        return info.resident_size / _MB if info is not None else None
    if sys.platform != "win32":
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    info = ProcessMemoryCounters()
    info.cb = ctypes.sizeof(info)
    # Explicit 64-bit handle signatures prevent pointer truncation on Windows x64.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD,
    ]
    handle = kernel32.GetCurrentProcess()
    ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(info), info.cb)
    return info.WorkingSetSize / (1024 * 1024) if ok else None


def memory_peak_working_set_mb():
    """Peak process resident size on Windows or macOS, if available."""
    if sys.platform == "darwin":
        info = _mac_task_info(20, _MachTaskBasicInfo)
        return info.resident_size_max / _MB if info is not None else None
    if sys.platform != "win32":
        return None
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]
    info = ProcessMemoryCounters()
    info.cb = ctypes.sizeof(info)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD,
    ]
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(info), info.cb):
        return None
    return info.PeakWorkingSetSize / (1024 * 1024)


def memory_private_mb():
    """Windows private committed bytes; macOS physical footprint (different metric)."""
    if sys.platform == "darwin":
        info = _mac_task_info(22, _MachTaskVMInfoRev1)
        return info.phys_footprint / _MB if info is not None else None
    if sys.platform != "win32":
        return None

    class ProcessMemoryCountersEx(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    info = ProcessMemoryCountersEx()
    info.cb = ctypes.sizeof(info)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCountersEx), wintypes.DWORD,
    ]
    ok = psapi.GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(), ctypes.byref(info), info.cb,
    )
    return info.PrivateUsage / (1024 * 1024) if ok else None
