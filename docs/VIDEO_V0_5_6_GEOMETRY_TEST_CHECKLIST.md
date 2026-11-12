# MontaSpace Studio v0.5.6 — Video geometry / crop regression checklist

- [ ] Launch Studio; About displays v0.5.6.
- [ ] Insert portrait MP4 and play it; picture is undistorted.
- [ ] Select video. The blue selection border encloses **only** the visible video / crop.
- [ ] Middle-click to open controls, then close them (X). Border does not change.
- [ ] Ctrl+double-click, crop from top or bottom, press Enter. Video outside crop disappears.
- [ ] Repeat while playback is paused; crop still matches the video.
- [ ] Drag resize handles at top, bottom, left, right, and corners; no ghost trails.
- [ ] Click empty whiteboard: selection border and all handles disappear.
- [ ] Save/reopen `.mstudio` and `.mstudiopack`; crop and scaling persist.
- [ ] Keep 3 videos playing simultaneously; performance remains similar to v0.5.5.
- [ ] Right-click -> Performance Info -> Copy Report: read-only video geometry section appears.

If any selection/crop mismatch remains, paste only the `Video geometry (read-only)`
section of Performance Info with a screenshot. This gives actual Qt-reported
item size, native video size, first decoded frame ratio, and saved crop.
