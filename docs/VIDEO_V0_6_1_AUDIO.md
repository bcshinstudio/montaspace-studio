# v0.6.1 — Independent video audio

Each video tile has its own volume (0–100%) and mute state. Open **Playback Controls...** for the slider and mute checkbox; right-click a video for **Mute Video / Unmute Video**. Audio changes work while playing. They are saved in both `.mstudio` and `.mstudiopack`, participate in Undo/Redo, and are independent between videos.

Existing projects without audio fields default to 65% and unmuted. Muting does not change volume, so unmuting restores the chosen level. No media files are modified.

Run `run_regression_tests.bat` on Windows. Then test two videos playing simultaneously, change each volume, mute one, save/reopen, Undo/Redo, and run the installer build if desired. Keep v0.6.0 as stable until verified.
