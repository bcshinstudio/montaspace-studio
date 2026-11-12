# Studio 0.5.1 Windows GUI verification

## Goal
Verify the new video crop interaction is consistent with photo cropping while preserving video playback usability.

## Test steps

- [ ] About dialog shows **v0.5.1**.
- [ ] Double-click a video: it **plays/pauses**.
- [ ] Middle-click a video: playback controls **open/close**.
- [ ] Ctrl + double-click a video: **crop mode** starts.
- [ ] In crop mode, **top / bottom / left / right** edges can all be dragged.
- [ ] In crop mode, **all four corners** can be dragged independently.
- [ ] Enter applies crop.
- [ ] Esc cancels crop.
- [ ] Context menu offers **Crop Video** for a selected video.
- [ ] Shift + left-drag still pans a zoomed video.
- [ ] Reset View restores full video, centered pan, and 1.00× zoom.
- [ ] Save and reopen `.mstudio`: video crop is restored.
- [ ] Save and reopen `.mstudiopack`: video crop is restored.
- [ ] Older v0.5.0 project with symmetric crop still opens.
- [ ] Installer build succeeds and reports v0.5.1.
