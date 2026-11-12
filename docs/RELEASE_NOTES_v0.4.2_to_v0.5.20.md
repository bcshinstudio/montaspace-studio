# MontaSpace Studio v0.5.20 — Thumbnail Compatibility Fix

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
Expected output: `installer-output/MontaSpaceStudio_Setup_0.5.20.exe`.
The build script removes its generated PyInstaller files after a successful build.

See `docs/VIDEO_V0_4_PROJECT_SAVING_TEST_CHECKLIST.md` before committing/tagging.

## v0.4.2 — Mouse-only video playback
- Double-left-click a video (including its unloaded placeholder) to play/pause.
- Middle-click a video to open/close its non-modal playback controls.
- No on-video control icons or overlays are added.
- Right-click menus, photo double-click crop, video saving, A–B loops, and simultaneous playback remain intact.

## v0.5.0 — Non-destructive video view adjustments

- Playback controls now provide **Content zoom** (1×–4×) and **Crop edges** (0–30% per side).
- Hold **Shift** and left-drag a zoomed video to pan its content. Ordinary left drag still moves the video.
- Both linked and portable projects retain zoom, pan and crop without modifying source MP4s.
- Old Studio v0.4.x projects import with default 1× zoom, no crop and centered pan.
- Middle-click playback controls, double-click play/pause and simultaneous playback are unchanged.
- Crop is a symmetric viewport trim, not freeform or exported-video cropping.


## v0.5.1 — Video crop mode consistency

- **Double-click** on video still plays/pauses.
- **Ctrl + double-click** on video enters crop mode.
- In video crop mode, you can drag **all four edges and all four corners**, similar to photo cropping.
- Video crop mode pauses the video while editing and resumes after applying/canceling if it was playing.
- Playback controls keep zoom/pan, and **Reset View** now resets zoom, pan, and crop.
- New saves store the video crop rectangle directly; older v0.5.0 projects with symmetric crop still open correctly.

## v0.5.5 — Consistent photo/video editing

- The video graphics item follows the actual MP4 native aspect ratio once media metadata becomes available. Portrait videos no longer keep the old 420×236 landscape hit/crop rectangle.
- Select a video to reveal four corner resize handles. Drag a corner to resize the video while preserving its aspect ratio, just as on a photo. Ctrl + mouse wheel still works.
- Ctrl + double-click enters four-edge/eight-handle video crop mode; Enter applies, Esc cancels. Regular video double-click still plays/pauses; middle-click still toggles playback controls.
- The new project format stores video crops as **relative geometry** so native-size detection does not invalidate a saved crop. Older v0.5.1 pixel rectangles and v0.5.0 inset settings continue to load.
- Videos are not autoplayed, modified, copied, or transcoded by cropping/resizing.
- Video geometry is resolved from Qt's media metadata; if media metadata is delayed, its initial placeholder may be wide until the aspect ratio is detected.


## v0.5.5 — Video frame and selection repaint correction

- Video geometry is updated from decoded frames, including supported rotation information for portrait recordings.
- The selection border and crop/resize handles are independent QGraphicsItems instead of being painted onto the video texture. This allows Qt to invalidate their former positions after dragging.
- The video renderer fills the correctly sized media frame, preventing pillarbox gaps inside the selection border.
- No additional decoder, video thumbnail renderer, or auto-play behavior was added.
- Mouse gestures and linked/portable project-saving formats remain unchanged.


## v0.5.5 — Aspect ratio regression fix

- Restores aspect-preserving Qt video rendering (no horizontal stretching).
- Do not derive display size from raw decoded frame dimensions; these may be rotated.
- When present, metadata rotation is used to determine portrait display geometry.
- Crop rectangles and mouse editing gestures are unchanged.
- All prior linked/portable project formats remain supported.

## v0.5.5 — Photo-aligned video editing

- Video selection now exposes all four sides and four corners for proportional resize.
- Handles accept a larger mouse grab area. Ctrl+wheel resize still works.
- Crop mode still uses Ctrl+double-click on video; drag any edge/corner and Apply/Cancel.
- Video aspect ratio now considers frame rotation as well as file metadata, without pixel decoding.
- Video geometry changes and deselection explicitly repaint the whiteboard to clear visual trails.
- Photo double-click crop and Ctrl+double-click crop are unchanged.
- No video icons are permanently overlaid and playback does not start automatically.


## v0.5.6 — Stable video crop/selection rendering

- Underlying Qt video graphics item is clipped to the active crop aperture. This
  prevents video frames displaying outside a cropped selection border.
- The expensive native crop clip is disabled for uncropped video.
- Frame orientation/size is inspected only on the **first valid frame**, not 30
  times per second. Later decoded frames do not mutate selection geometry.
- Performance Info -> Copy Report now includes read-only per-video geometry
  diagnostics to troubleshoot unusual portrait recordings.
- Closing the playback-controls window does not alter crop, scale, playback,
  or video geometry.
- Existing photo/video interactions and project formats are retained.


## v0.5.8 — Video frame and selection improvements

- Video insertion no longer displays resize handles; **single-click selects** and shows them.
- Video presentation size is resolved using frame and rotation metadata, with one-time frame inspection.
- Once a valid display ratio is known, video rendering and resize/crop handles share the same aspect and size.
- Resizing uses the exact same scene-space QLineF distance/scale calculation as the photo editor.
- Middle-click controls, double-click playback, Ctrl+double-click cropping, A/B loop and video saving stay unchanged.
- No per-frame Python work, extra decoders, or polling.


## v0.5.8 — Clean video selection and crop borders

- Hide square resize and crop handles; retain a thin blue selection outline.
- Resize and crop from invisible easy-grab zones along all four edges and corners.
- Preserve v0.5.7 video geometry, crop behavior, mouse playback, and file formats.
- Eliminate eight extra graphics handle objects per video (no extra decoding).


## v0.5.9 — Photo-style video resize/crop handles

- Video selection now matches the photo editor more closely: **four small corner boxes** for resize and a **thin blue outline**.
- Video crop mode now shows **eight white crop handles** (four corners + four edge midpoints), like photo crop mode.
- The handles keep the existing generous invisible hit area, so grabbing them stays easier than before.
- Video resize remains **proportional only**, matching the design we agreed on for videos.
- Middle-click playback controls, double-click play/pause, Ctrl+double-click crop mode, linked/portable saving, and existing memory/resource safeguards are unchanged.


## v0.5.10 — Fixed-size photo/video handles and shortcut help

- Both photo and video selection show a **1 px blue border** and **eight small white handles**: four corners plus one at the middle of each side.
- Handle boxes use Qt's transform-ignoring graphics item flag to remain **8 screen pixels** regardless of media size.
- Dragging any resize handle scales the full photo/video using the existing formula; all four edges show horizontal or vertical resize cursors.
- Photo crop and Ctrl+double-click video crop keep the eight handles, independently trimming each edge/corner.
- The photo rotation control is retained. Invisible grab zones remain larger than the boxes.
- **F1** toggles a small non-modal Mouse & Keyboard Shortcuts reference window.
- Removed gesture instruction labels from the video playback controls; kept zoom, A/B loop, and playback buttons.
- Video decoding, aspect-ratio handling, memory cleanup, linked and portable saving remain unchanged.
- See `docs/VIDEO_V0_5_10_REGRESSION_CHECKLIST.md` before committing/tagging.


## v0.5.11 — Reliable photo/video edge editing, help and border

- Resize and crop both accept drags along the **entire four edges**, not just the eight visible handles. Corner grabs have a forgiving invisible 20-pixel screen hit area.
- Photo and video use **the same pure hit-test helper**; photo rotation stays available.
- The directional resize cursor also gets a viewport-level fallback for Qt video overlays.
- **Ctrl+H** (or F1) opens a redesigned, non-modal Mouse & Keyboard Shortcuts window. **Esc** closes it.
- **Ctrl+Shift+B** toggles the optional subtle one-pixel boundary around the otherwise white frameless workspace. It starts enabled.
- Project persistence, video sizing/orientation, playback, crop rendering, and A–B loops were not modified.

Do not tag this build until Windows GUI edge/corner tests pass.


## v0.5.12 — Cursor and drag behavior matched

- Fixed a mismatch where the whiteboard showed resize/crop cursors at a handle, but Qt dispatched the mouse press to another graphics item or no item.
- Both hover feedback and left-click drag start now use **one selected-media hit test** in Canvas.
- The whiteboard handles drag movement/release once a selected photo/video grip is captured; this also works in the invisible grab band just outside a border.
- All four corners and four edges in resize and crop mode share the same dispatch. Photo rotation still works, and photo resizes still enter Undo history.
- Existing item rendering, window boundary, help window, video decoding, A-B loop and project persistence are unchanged.


## v0.5.13 — Shared photo/video Undo/Redo and startup border

- One Ctrl+Z / Ctrl+Y history for both photos and videos. Supports move, resize, crop, insert, and delete of either media type.
- Video content zoom, pan, A/B marker edits and loop toggles are recorded. Continuous slider drags produce a single undo step. Play/pause and timeline seeking are not history actions.
- History snapshots keep only media references, file paths, and editing values. Video Undo does not hold released Qt players/decoders alive; a deleted video is reconstructed from its source path if undo restores it. If the original file was removed, it cannot be reconstructed.
- Photos retain the existing implicitly shared image-preview history. The Undo stack remains limited to 50 actions.
- The border is now painted directly on the whiteboard viewport, eliminating the window-sized transparent child overlay responsible for blank startup artifacts. Ctrl+Shift+B still toggles it.
- Existing .mstudio/.mstudiopack formats and video geometry handling are unchanged.


## v0.5.14 — Lightweight video poster previews

- Replaces the long overflowing placeholder text with a compact, centered play symbol and short filename.
- Shows a small preview frame for new videos when an external `ffmpeg` executable is installed and accessible on PATH. This extraction is asynchronous and limited to **one process at a time**.
- Without external FFmpeg, the first frame rendered during **normal user-initiated playback** is used to create a preview. Studio does not autoplay or run another Qt video decoder.
- JPEG posters are downscaled to 360 pixels maximum and reused from a bounded disk cache across Undo and reopening linked projects on the same computer.
- Portable `.mstudiopack` files embed an available poster JPEG once per distinct video; older projects remain compatible.
- If no preview is available, an intentional compact fallback is shown.
- A–B looping, resize/crop, mouse controls, history, media extraction, and video resource cleanup retain their existing behavior.

## v0.5.15 — Stable saved geometry and menu polish

- New linked and portable project files remember verified video display dimensions.
- Restoring a video uses saved display geometry immediately, without starting playback.
- Video Undo/Redo history preserves verified display geometry without retaining decoder objects.
- Existing projects continue to open; if they lack saved display geometry, Qt metadata or a cached poster may still be needed to determine orientation.
- Right-click menu uses a minimal, modern appearance and aligned shortcuts.
- Poster preview remains optional: external FFmpeg on PATH or a previously captured frame is required; fallback stays lightweight.


## v0.5.20 — Windows native video thumbnails (no FFmpeg installation required)

- Cached posters remain first choice. On Windows, Studio now uses the **Windows Shell thumbnail service** to obtain an Explorer-style video thumbnail (thumbnail only, no file icon).
- Native thumbnail extraction is **off the main GUI thread**, serial (one at a time), and converts the result to a max-360px JPEG in the existing bounded poster cache.
- If Windows cannot produce a thumbnail for a codec/file, Studio falls back to optional `ffmpeg.exe`, then one captured frame during normal playback, then the clean poster card.
- No autoplay, additional permanent media player, external Python dependency, or MP4 duplication. Linked `.mstudio` and portable `.mstudiopack` project formats are unchanged; available posters still embed in portable projects.
- Platform-specific code lives in `app/windows_thumbnail.py`; on macOS/Linux it safely returns no native thumbnail and uses the existing FFmpeg/Qt playback fallback.

## Future macOS adaptation

PySide6's Qt GUI and multimedia code is mostly cross-platform. A macOS app will need native poster retrieval (Quick Look/AVFoundation if desired), packaging as `.app`/`.dmg`, icon conversions, and validation of frameless window mouse/resize behavior, video codecs, and keyboard shortcuts. Windows NSIS and Windows version resources do not carry over.


## v0.5.20 — One-time bounded video thumbnail attempts

- Check saved poster cache first. For an uncached file, try one native Windows Shell thumbnail request; use FFmpeg only if already installed.
- Limit each stage to a 3-second wait; never auto-play videos or create extra long-lived media players.
- Remember a failed extraction using a small `.failed` marker keyed to the video's path, size and modification timestamp. Reopening projects and Undo restoration do not retry failed sources.
- A changed/replaced MP4 gets a new key and can be tried once. Cached poster images and portable embedded posters override prior failure markers.
- Stop converting Qt video playback frames for posters. This avoids repeated conversion attempts on unsupported hardware-decoded frames.
- Windows Shell workers cannot be forcibly terminated inside the process; an unresponsive worker is abandoned after 3 seconds and no second Shell worker is started until the first returns.
- All playback, editing, project saving and Undo/Redo behavior is unchanged.


## v0.5.20 — Early scene thumbnail capture

- Added a Qt-based fallback thumbnail capture path that briefly samples the beginning of the video.
- Tries a few early timestamps (0.5s, 1.0s, 2.0s) and stores a small JPEG poster when successful.
- Keeps extraction bounded and one-at-a-time to avoid runaway CPU or memory use.
- Reuses the cached poster for undo and reopened projects.


## v0.5.20 — PySide6 thumbnail compatibility fix

- Fixes the `QImage.scaled(... transformMode=...)` exception that prevented Windows thumbnails from being cached.
- Handles Samsung video orientation metadata when the QtVideo::Rotation converter is unavailable.
- Ignores old failure markers produced by v0.5.17/v0.5.18, allowing one corrected extraction attempt.
