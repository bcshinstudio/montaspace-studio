# MontaSpace Studio v0.5.19 — Thumbnail/PySide6 compatibility fix

Root cause shown by user's Windows CMD traceback:

- Windows native extraction returned image data and called `put_image()`.
- `QImage.scaled(..., transformMode=...)` raised `AttributeError` on installed PySide6.
- Samsung H.264 portrait video `QMediaMetaData.Key.Orientation` raised a separate `RuntimeError` because the QtVideo::Rotation converter is unavailable in this PySide6 build.

Fixes:

1. Use positional `QImage.scaled(width, height, aspect, transform)` API.
2. Catch optional media metadata converter errors; retain first decoded frame geometry behavior.
3. Version the failure markers (`.v519.failed`) so old extraction failures from the broken pipeline do not skip thumbnail generation after upgrade. Existing valid JPEG posters stay cached.

Test on Windows: open an affected Samsung MP4, confirm native poster appears, Undo/Redo and project reopen; observe CMD for exceptions.
