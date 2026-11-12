# MontaSpace Studio v0.5.20

**MontaSpace Studio** is a lightweight, frameless Windows whiteboard for arranging photos and videos, by **BC Shin Studio**. It is a separate application from the photo-only MontaSpace.

## Requirements and start

- Windows 10/11; Python 3.11+; `PySide6>=6.8,<7`.
- From the project directory, create a virtual environment if necessary:

```cmd
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

To use an existing local virtual environment, omit the first two commands.

## Whiteboard controls

| Action | Gesture |
| --- | --- |
| Select/move photo or video | Click / left-drag |
| Resize media | Drag border/corner; Ctrl + mouse wheel |
| Move the frameless app window | Alt + drag |
| Open context menu | Right-click |
| Photo crop | Double-click photo |
| Video play/pause | Double-click video |
| Video playback and A/B loop controls | Middle-click video |
| Video crop | Ctrl + double-click video; Enter/Esc to apply/cancel |
| Pan enlarged video content | Shift + drag |
| Undo / redo | Ctrl + Z / Ctrl + Y |
| Save / Save As | Ctrl + S / Ctrl + Shift + S |
| Shortcut reference | F1 or Ctrl + H |
| Toggle whiteboard border | Ctrl + Shift + B |

Media cropping, size, rotation and video view settings are non-destructive. Studio does not modify or re-encode source video files. Each video is controlled independently.

## Project files

- **Linked (`.mstudio`)**: Saves media paths and whiteboard layout; originals must remain accessible.
- **Portable (`.mstudiopack`)**: Embeds media without video recompression; may become large. Available cached video JPEG posters are included.
- Older photo-only `.mspace` and `.mspacepack` projects can be **opened**, then saved in the Studio formats.
- Video current playback position and play/pause state are not saved; A/B loop settings, crop, zoom and layout are saved.

## Video thumbnails

Studio tries to obtain one small JPEG poster for each video and caches it. The pipeline uses the Windows native thumbnail service, a bounded Qt early-scene capture and optional external FFmpeg if available. It does not autoplay videos on the board. If all attempts fail, Studio shows a play-icon placeholder. The thumbnail cache is local and not part of source control.

## Testing

```cmd
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m compileall -q app main.py
```

See [`docs/VIDEO_V0_5_20_TIMELINE_SEEK_TESTS.md`](docs/VIDEO_V0_5_20_TIMELINE_SEEK_TESTS.md) for the timeline/loop regression check. Before release, also test photo/video insert, selection, crop/resize, Undo/Redo, linked/portable save/load, thumbnail display, and multi-video playback on Windows.

Automated tests cover algorithms and source-level contracts; they do not replace a Windows PySide6 GUI regression test.

## Windows packaging

- `build_windows.bat` — builds the PyInstaller one-directory app.
- `build_installer.bat` — builds the app and the free NSIS installer (`installer-output/MontaSpaceStudio_Setup_0.5.20.exe`).
- The scripts expect a project-local `.venv` and required packaging tools.
- Generated `build/`, `dist/`, `installer-output/` and `.venv/` are ignored by Git.

## Project layout

- `app/` — UI, project storage, image/video behavior, thumbnails and geometry.
- `assets/` — Studio icon.
- `tests/` — automated checks.
- `docs/` — version-specific test checklists and archived release notes.
- `installer/` — NSIS installer recipe.

Historical implementation notes and release changes: [`docs/RELEASE_NOTES_v0.4.2_to_v0.5.20.md`](docs/RELEASE_NOTES_v0.4.2_to_v0.5.20.md).
