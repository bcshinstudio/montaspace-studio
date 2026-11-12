# MontaSpace Studio — Automated regression test suite

Version: **0.5.23** (test-only enhancement; no application behavior changes).

## One command (Windows CMD)

From `C:\Users\baech\Projects\montaspace2`:

```bat
run_regression_tests.bat
```

The runner uses the existing `.venv`; no extra dependencies or user media needed.
It runs the existing 45 fast tests plus real PySide6 whiteboard smoke tests
using small, generated-in-test photos and a bundled 6 KB H.264 MP4.
Tests create temporary projects in the OS temp directory; they never touch
user projects or original media. Tests are kept independent and avoid autoplay.
A **PASS** means both subprocesses returned exit status 0. Failed, timed-out,
or unavailable GUI tests must never be treated as successful certification.

## Automated coverage

- Fast: loop-seek guard, thumbnail cache rules, Windows thumbnail integration,
  geometry/hit-testing, PySide API compatibility, decoder selection, timeline contract.
- Real Qt whiteboard: photo insert/transform/crop/duplicate/Undo/Redo;
  linked/portable photo roundtrip; video insert without autoplay; video Undo/Redo;
  view zoom/crop, A/B marker state, controls capturing pending seeks;
  linked project save/reopen with video settings; mixed photo+video portable
  save/reopen; cached JPEG poster; New clears media.

## Coverage limitations

The automated smoke suite verifies scene state, project formats and controls.
It **does not certify pixel-perfect interactive mouse drag, video/audio quality,
Windows hardware output, sustained memory stability, or installer behavior**.
Keep a very short manual visual check before release and run the existing
`run_studio_loop_test.bat "path-to-video.mp4"` when changing decoder/looping.

The project does not need a version bump solely for test additions. The
application stays at v0.5.23 until another functional change is approved.
