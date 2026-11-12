# MontaSpace Studio v0.5.2 — Windows GUI test checklist

1. Open About; confirm version **0.5.2**.
2. Insert portrait MP4. After metadata loads, video selection/crop rectangle should match the portrait frame, not a landscape blank area.
3. Select the video; drag all four corner handles to enlarge/shrink it. Check while playing and paused.
4. Ctrl+wheel video scale still works; photo corner handles still work.
5. Double-click video plays/pauses; middle-click opens/closes controls.
6. Ctrl+double-click enters video crop mode; adjust top, left, right, bottom and corners.
7. Enter applies crop, Esc cancels, video resumes only if it was playing before crop.
8. Zoom content and Shift+left-drag to pan. Resize and crop again.
9. Save a portrait cropped video in .mstudio, reopen; verify frame aspect, crop, scale, zoom, A/B settings.
10. Save in .mstudiopack, reopen; verify the same.
11. Open a v0.5.1 crop project (pixel-coordinate crop) and a v0.5.0 project (symmetric crop) and verify.
12. Delete all videos, check Performance Info objects return to zero; test multiple simultaneous videos.
13. Build installer after verification; expected version **0.5.2**.

Do not tag v0.5.2 until on-Windows rendering and interaction tests pass.
