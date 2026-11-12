# v0.5.21: stability and performance verification

## Product boundary
This is a lightweight photo/video **display and arrangement** app. No trimming,
re-encoding, exporting edited video, quality enhancement, or new video editors.

## Automated test on Windows
From project root, with the application's `.venv` already installed:

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
run_video_stability_test.bat "C:\full\path\to\video.mp4"
```

The video stress script creates a *separate hidden whiteboard* and runs 5, 10,
and 20 video-tile cases. It measures memory and save/open time, validates that
all tiles survive linked `.mstudio` reopening, and records native Qt object
counts after scene cleanup. It **never changes the MP4**, starts playback, or
writes into an existing project. Reports go to
`Documents\MontaSpaceStudio_Test_Reports`.

For small videos, optionally run a portable save/reopen test (embedding media
can take substantial time and disk):

```bat
run_video_stability_test.bat "C:\full\path\to\video.mp4" --counts 5 --portable
```

Run the optional portable test only with a small MP4. Stop if Windows reports
very high memory use; no performance thresholds are claimed in advance.

## Interactive validation
1. Insert 5, then 10, then 20 videos. Confirm the UI remains responsive.
2. Insert photos into the same board; verify both kinds of media can be moved,
   resized, cropped, and Undo/Redo restores the right item.
3. Check thumbnails on insert, Undo, linked reopen, and portable reopen.
4. Play several videos simultaneously, then pause/stop them; check audio and
   that other videos are not paused unexpectedly.
5. Save/reopen linked `.mstudio` and portable `.mstudiopack` projects.
6. Delete videos, open **Performance Info**, and review the lifecycle counts.
7. Close Studio and confirm the application process exits normally.

## How to interpret the report
- `after_cleanup` working-set RAM may remain elevated because Windows, codecs,
  and memory allocators can retain buffers; this alone **does not prove a leak**.
- `qt_alive_after_cleanup` should not keep increasing across isolated runs.
- Compare runs on the same Windows device with the same MP4 and background apps.
- The GUI and Windows multimedia backend **must be checked on Windows**; source
  tests run on another platform do not establish Windows performance.
