# MontaSpace Studio v0.5.23 — Decoding and actual-whiteboard benchmark

## Windows automated test

From the project folder, with the normal existing `.venv`:

```bat
run_studio_loop_test.bat "C:\full\path\to\your_samsung_video.mp4"
```

The tool launches a visible real Studio whiteboard, inserts five copies of the same MP4, activates independent A/B loops, and logs memory and CPU at 15-second intervals for five minutes. It closes automatically and writes CSV and JSON reports in Documents\MontaSpaceStudio_Test_Reports. Use the existing Samsung H.264 clip for a comparable test.

It does not overwrite or open existing project files. It makes no thumbnails intentionally (but ordinary Studio insertion may consult poster cache).

CPU percentages are of one CPU core; divide by logical CPU count for an approximate Task Manager total-CPU percentage.

Optional shorter test:

```bat
run_studio_loop_test.bat "C:\full\path\clip.mp4" --seconds 180
```

## Regression checklist on Windows

1. About displays v0.5.23.
2. Saved .mstudio and .mstudiopack open and posters appear.
3. Photo and video resize/crop/Undo/Redo still operate as in v0.5.22.
4. Video play/pause, timeline seek and A/B looping still operate.
5. After automated playback, memory stays reasonably stable; record result, don't infer stability from isolated tests alone.
6. If software decoding stutters on the target PC, compare via an explicitly requested hardware benchmark (`--decoder hardware`) before deciding on defaults.

## Normal application decoding override

```bat
set MONTASPACE_STUDIO_DECODER=hardware
.venv\Scripts\python.exe main.py
set MONTASPACE_STUDIO_DECODER=
```

This override affects only the launched process and current CMD session. The application remains fully functional without this override.
