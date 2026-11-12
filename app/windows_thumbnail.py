"""Optional Windows Explorer video thumbnail extraction.

Pure ctypes / Win32. Never call this on the Qt UI thread: the Shell may read
large video files or launch a codec to create the thumbnail. A failed or
unsupported thumbnail simply returns None; it never returns a file icon.
"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


MAX_NATIVE_SIDE = 1024  # Allow a larger Shell result, but avoid huge buffers.
MAX_NATIVE_PIXELS = 1024 * 1024


def extract_windows_thumbnail(filename: str, size: int = 360):
    """Return (BGRA bytes, width, height) or None; caller owns no Win32 handles.

    The pixel bytes are a top-down 32-bit DIB. Qt can create a QImage with
    Format_RGB32 (the alpha byte is ignored; Explorer thumbnails are opaque).
    """
    if os.name != 'nt' or not 32 <= size <= 512 or not os.path.isfile(filename):
        return None

    HRESULT = ctypes.c_long
    ULONG = wintypes.ULONG
    HBITMAP = wintypes.HANDLE

    class GUID(ctypes.Structure):
        _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD),
                    ('Data3', wintypes.WORD), ('Data4', ctypes.c_ubyte * 8)]

    class SIZE(ctypes.Structure):
        _fields_ = [('cx', ctypes.c_long), ('cy', ctypes.c_long)]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ('biSize', wintypes.DWORD), ('biWidth', ctypes.c_long),
            ('biHeight', ctypes.c_long), ('biPlanes', wintypes.WORD),
            ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
            ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', ctypes.c_long),
            ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', wintypes.DWORD),
            ('biClrImportant', wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]

    class BITMAP(ctypes.Structure):
        _fields_ = [
            ('bmType', ctypes.c_long), ('bmWidth', ctypes.c_long),
            ('bmHeight', ctypes.c_long), ('bmWidthBytes', ctypes.c_long),
            ('bmPlanes', wintypes.WORD), ('bmBitsPixel', wintypes.WORD),
            ('bmBits', ctypes.c_void_p),
        ]

    # IShellItemImageFactory: {bcc18b79-ba16-442f-80c4-8a59c30c463b}
    iid = GUID(0xbcc18b79, 0xba16, 0x442f,
               (ctypes.c_ubyte * 8)(0x80, 0xc4, 0x8a, 0x59, 0xc3, 0x0c, 0x46, 0x3b))
    ole32 = ctypes.WinDLL('ole32', use_last_error=True)
    shell32 = ctypes.WinDLL('shell32', use_last_error=True)
    gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)

    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole32.CoInitializeEx.restype = HRESULT
    ole32.CoUninitialize.argtypes = []
    shell32.SHCreateItemFromParsingName.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p,
                                                     ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    shell32.SHCreateItemFromParsingName.restype = HRESULT
    gdi32.GetObjectW.argtypes = [HBITMAP, ctypes.c_int, ctypes.c_void_p]
    gdi32.GetObjectW.restype = ctypes.c_int
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.DeleteDC.restype = wintypes.BOOL
    gdi32.GetDIBits.argtypes = [wintypes.HDC, HBITMAP, wintypes.UINT, wintypes.UINT,
                                ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wintypes.UINT]
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [HBITMAP]
    gdi32.DeleteObject.restype = wintypes.BOOL

    # COINIT_APARTMENTTHREADED: Shell thumbnail handlers may require an STA.
    hr = ole32.CoInitializeEx(None, 0x2)
    initialized = hr >= 0
    if not initialized:
        return None

    interface = ctypes.c_void_p()
    bitmap = HBITMAP()
    try:
        hr = shell32.SHCreateItemFromParsingName(str(filename), None,
                                                  ctypes.byref(iid), ctypes.byref(interface))
        if hr < 0 or not interface.value:
            return None

        vtable = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        # IShellItemImageFactory inherits IUnknown; GetImage is vtable[3].
        GetImage = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, SIZE,
                                     wintypes.DWORD, ctypes.POINTER(HBITMAP))(vtable[3])
        # SIIGBF_THUMBNAILONLY=8: never return Explorer's generic video icon.
        hr = GetImage(interface, SIZE(size, size), 0x8, ctypes.byref(bitmap))
        if hr < 0 or not bitmap:
            return None

        info = BITMAP()
        if gdi32.GetObjectW(bitmap, ctypes.sizeof(info), ctypes.byref(info)) == 0:
            return None
        width, height = abs(info.bmWidth), abs(info.bmHeight)
        if not (0 < width <= MAX_NATIVE_SIDE and 0 < height <= MAX_NATIVE_SIDE
                and width * height <= MAX_NATIVE_PIXELS):
            return None

        dib = BITMAPINFO()
        dib.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        dib.bmiHeader.biWidth = width
        dib.bmiHeader.biHeight = -height  # top-down, so no row flipping
        dib.bmiHeader.biPlanes = 1
        dib.bmiHeader.biBitCount = 32
        dib.bmiHeader.biCompression = 0  # BI_RGB
        length = width * height * 4
        pixels = (ctypes.c_ubyte * length)()
        dc = gdi32.CreateCompatibleDC(None)
        if not dc:
            return None
        try:
            rows = gdi32.GetDIBits(dc, bitmap, 0, height, pixels,
                                    ctypes.byref(dib), 0)
            if rows != height:
                return None
        finally:
            gdi32.DeleteDC(dc)
        return bytes(pixels), width, height
    except (OSError, ValueError, ctypes.ArgumentError):
        return None
    finally:
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if interface.value:
            vtable = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            Release = ctypes.WINFUNCTYPE(ULONG, ctypes.c_void_p)(vtable[2])
            Release(interface)
        ole32.CoUninitialize()
