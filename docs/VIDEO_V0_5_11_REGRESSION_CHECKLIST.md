# MontaSpace Studio v0.5.11 — Windows regression checklist

Use a photograph and the same portrait MP4 that passed v0.5.7.

## Resize (not crop)
- [ ] Photo: drag at top/bottom/left/right **between** visible handle boxes; all four resize.
- [ ] Video: drag at top/bottom/left/right **between** visible handle boxes; all four resize.
- [ ] Photo and video: directional two-way arrows appear on each edge, including between handles.
- [ ] All 4 photo corners and all 4 video corners are easy to grab, including slightly **inside** each corner.
- [ ] Photo and video keep their aspect ratio while resizing by an edge.
- [ ] Handle squares stay small and consistent during enlargement/reduction.

## Crop
- [ ] Photo double-click enters crop mode; video Ctrl+double-click enters crop mode.
- [ ] Both: crop from any of four edges and four corners; diagonal cursor appears near corners.
- [ ] Enter applies and Esc cancels; blue outlines do not leave artifacts.
- [ ] Photo rotation handle and photo duplication/Undo still work.

## Help and window boundary
- [ ] Ctrl+H opens the redesigned shortcut help; Esc closes it.
- [ ] F1 opens help on keyboards with a dedicated F1 key (Fn+F1 if required).
- [ ] Ctrl+Shift+B hides the subtle outside window border; repeat to show it.
- [ ] Border and help do not interfere with window resizing or whiteboard dragging.

## Existing critical functions
- [ ] Video double-click play/pause, middle-click controls, A/B loop unchanged.
- [ ] No portrait video distortion when opening/closing playback controls.
- [ ] Save/reopen .mstudio and .mstudiopack with crops and zoom retained.
- [ ] No extra video decoding or forced pausing introduced.
