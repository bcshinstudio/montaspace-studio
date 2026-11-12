# v0.5.12 — Cursor and drag must agree

## Highest priority

- [ ] Photo selected: hover left/top/right/bottom edge or its box; whenever a resize cursor appears, left-drag actually resizes the photo.
- [ ] Photo selected: hover each of the four corner boxes; whenever a diagonal cursor appears, left-drag actually resizes the photo.
- [ ] Video selected: repeat these eight edge/corner resize checks.
- [ ] Photo crop mode: all eight edge/corner grips work where the cursor appears; Ctrl+double-click also enters crop mode.
- [ ] Video crop mode: all eight edge/corner grips work where the cursor appears.
- [ ] Edge-grab on the blank side of the border (just outside photo/video) still works.
- [ ] Moving the pointer well away from an edge removes the resize cursor.

## Other regression checks

- [ ] Photo move and rotate remain functional; Undo reverses photo resizing.
- [ ] Video double-click play/pause and middle-click playback controls still work.
- [ ] Ctrl+H help and Ctrl+Shift+B window border still work.
- [ ] .mstudio and .mstudiopack still save and reopen correctly.
- [ ] No new ghost borders or video aspect ratio changes.
