# MontaSpace Studio v0.4.2 — Project Saving

MontaSpace Studio is the photo + video whiteboard developed by BC Shin Studio.
The original lightweight photo-only MontaSpace remains a separate application.

## Saving projects

- **Linked** `.mstudio` (default): saves the board layout, photo/video file paths,
  and video A–B loop points. It does **not** copy original media. The media must
  remain at those locations for reopening to work.
- **Portable** `.mstudiopack`: embeds each distinct photo/video **once**, even
  when used more than once on the board. Original files are not modified.
  MP4 files are stored without recompression. Portable saves over 100 MiB ask
  for confirmation and may take time/disk space.
- Photo-only `.mspace` / `.mspacepack` can be **opened** for compatibility.
  When saving an imported photo-only project, Studio uses **Save As** into
  `.mstudio` or `.mstudiopack`; it will not overwrite the original format.
- Video playback state (playing/paused/current position) is **not** saved;
  video A/B points and the looping-enabled flag **are** saved.
- Portable archives are extracted into temporary storage for the lifetime of
  the opened project. Saving an opened portable project as linked creates
  permanent source copies in a matching `_assets` folder.

## Existing workspace functions

- Insert and arrange JPG/PNG/BMP/WebP photos and MP4 videos.
- Ctrl + mouse wheel resizes selected media; Alt + left drag moves the window.
- Right click selects the item under the pointer before opening its menu.
- Video playback: play, pause, seek, ±5 seconds, and A/B looping.
- Photos: non-destructive cropping, rotation, layer order, duplicate, Undo/Redo.
- Video resource cleanup and copyable Performance Info remain available.
- Users control playback; Studio never automatically pauses other videos.

## Run from source

Keep your existing `.venv` folder and run:

```cmd
cd C:\Users\baech\Projects\montaspace2
.venv\Scripts\python.exe main.py
```

## Build installer (after Windows verification)

Run `build_installer.bat` from the project root to build an NSIS installer.
Expected output: `installer-output/MontaSpaceStudio_Setup_0.4.2.exe`.
The build script removes its generated PyInstaller files after a successful build.

See `docs/VIDEO_V0_4_PROJECT_SAVING_TEST_CHECKLIST.md` before committing/tagging.

## v0.4.2 — Mouse-only video playback
- Double-left-click a video (including its unloaded placeholder) to play/pause.
- Middle-click a video to open/close its non-modal playback controls.
- No on-video control icons or overlays are added.
- Right-click menus, photo double-click crop, video saving, A–B loops, and simultaneous playback remain intact.
