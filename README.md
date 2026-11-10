# MontaSpace Studio v0.3.4

**MontaSpace Studio** is BC Shin Studio's separate photo-and-video whiteboard application.
Development folder: `montaspace2`. The original photo-only `montaspace` application is not modified.

## Current features
- Arrange photos on a frameless, resizable whiteboard; move, resize, crop, rotate, layer, duplicate, and undo/redo photo operations.
- Insert MP4 videos, move and scale videos, play/pause, seek, and skip 5 seconds.
- Configure A/B loop points for each video and loop playback between them.
- Play several videos simultaneously without automatic pausing.
- Right-click a different photo or video to select it and show its context menu.
- Performance Info includes per-process memory and Qt video-object lifecycle diagnostics with Copy Report.
- Open and save existing **photo-only** `.mspace` and `.mspacepack` projects.

## Important current limitation
**Video-containing boards cannot yet be saved.** This is intentionally blocked to avoid losing videos and A/B timestamps. Video project persistence is planned. Do not rely on A/B loop settings remaining after closing Studio.

## Run from source (Windows)
```cmd
cd C:\Users\baech\Projects\montaspace2
.venv\Scripts\python.exe main.py
```
The existing local `.venv` should be preserved during source updates.

## Windows installer
- `build_installer.bat` builds `MontaSpaceStudio.exe` with PyInstaller and packages it with NSIS using `installer/MontaSpaceStudio.nsi`.
- The expected result is `installer-output/MontaSpaceStudio_Setup_0.3.4.exe`.
- When build succeeds, the installer script removes generated `build/`, `dist/`, and `MontaSpaceStudio.spec` files; it keeps the installer.
- `build_windows.bat` separately builds a portable application folder under `dist/`.
- Keep `.venv/`, `.git/` and your personal projects locally; do not include them in Git.

Testing documentation is in `docs/`. Source was cleaned without changing application logic.
