# MontaSpace Studio v0.5.24

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
- `build_installer.bat` — builds the app and the free NSIS installer (`installer-output/MontaSpaceStudio_Setup_0.5.24.exe`).
- The scripts expect a project-local `.venv` and required packaging tools.
- Generated `build/`, `dist/`, `installer-output/` and `.venv/` are ignored by Git.

## Project layout

- `app/` — UI, project storage, image/video behavior, thumbnails and geometry.
- `assets/` — Studio icon.
- `tests/` — automated checks.
- `docs/` — version-specific test checklists and archived release notes.
- `installer/` — NSIS installer recipe.

Historical implementation notes and release changes: [`docs/RELEASE_NOTES_v0.4.2_to_v0.5.20.md`](docs/RELEASE_NOTES_v0.4.2_to_v0.5.20.md).


## v0.5.21 — Stability and performance verification

This update adds optional testing tools only, without changing photo/video
behavior. See `docs/VIDEO_V0_5_21_STABILITY_PLAN.md`.

Run `run_video_stability_test.bat "C:\path\to\sample.mp4"` to measure
5/10/20 video tiles and linked-project save/open behavior.


## v0.5.23 — Loop-seek guard and diagnostics

- Ensures at most one pending A/B seek across asynchronous Qt position and end-of-media signals.
- Per-video seek request/confirmation/suppression counters in Performance Info.
- No multimedia backend, project schema, or thumbnail changes.
- Test instructions: `docs/VIDEO_V0_5_22_LOOP_SEEK_TESTS.md`.


## v0.5.23 — Software decoding stability candidate

- On Windows, Qt FFmpeg software decoding is enabled **before Qt imports** for regular launches and installers.
- Native GPU decoding is available for troubleshooting by running `set MONTASPACE_STUDIO_DECODER=hardware` before launching `main.py`. Use `set MONTASPACE_STUDIO_DECODER=` to restore the default.
- The `QT_FFMPEG_DECODING_HW_DEVICE_TYPES` environment variable, if explicitly present, is respected in automatic mode.
- Mac/non-Windows platforms retain Qt's normal default.
- No changes to existing video editing/playback/thumbnail/project classes.
- `run_studio_loop_test.bat "C:\path\clip.mp4"` tests **the actual whiteboard** with five simultaneous loops, saving CSV and JSON under `Documents\MontaSpaceStudio_Test_Reports`. It runs five minutes and exits automatically. Optional: `--seconds 180`, `--decoder hardware`, or `--count 1`.
- The benchmark's temporary whiteboard never saves a project and does not modify the MP4. For safety, it stops if private memory reaches 6 GB.
- **Not a confirmed fix until real Windows comparison**: measure private memory at 1 and 5 minutes, CPU use and video behavior.

## Automated regression tests (v0.5.23 baseline)

Before committing changes, run `run_regression_tests.bat` from the project folder.
It checks the existing logic tests and real Qt whiteboard operations with
small bundled/temporary media. See `docs/AUTOMATED_REGRESSION_TESTS.md`.
The automated playback memory test is separate: `run_studio_loop_test.bat "video.mp4"`.


## v0.5.24 — Linked-project reliability

- Linked projects continue to use project-folder-relative media paths.
- Opening a linked Studio project or legacy photo project with missing files now offers
  **Locate Folder** before changing the current board. Cancel preserves the board.
- Folder recovery scans are bounded (4,000 entries), use exact filename matches,
  and refuse ambiguous duplicates rather than selecting the wrong picture/video.
- Recovered projects show an unsaved-change mark until the repaired paths are saved.
- Save verifies the staged linked JSON or portable ZIP before atomic replacement,
  preserving the previous project on verification failure.
- Project parsing rejects invalid extensions and non-positive photo crops.
- Existing Save/Discard/Cancel prompts and legacy import remain supported.
- Regression tests cover missing media, moved folders, ambiguous matches,
  staged saves, cancellation, project preservation and save/reload after recovery.
- **Note:** recovery requires the source media still exists somewhere on disk;
  it does not restore deleted files or alter original media.

Run `run_regression_tests.bat` before committing this version.
