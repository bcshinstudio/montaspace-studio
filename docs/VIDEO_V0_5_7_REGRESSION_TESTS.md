# v0.5.7 — Aspect geometry / photo-style controls

Before testing, make a backup of the last working `montaspace2` folder and any important `.mstudio` or `.mstudiopack` projects.

1. Insert portrait video (rotated smartphone MP4); verify **no blue handles at insertion**.
2. Double-click the video and verify natural portrait playback, without horizontal stretching.
3. Single-click the video: border must enclose the exact displayed picture (not a wider landscape aperture or only its middle strip).
4. Drag all four corners and each edge; every resize uses the **same QLineF center-to-pointer scaling as photos**.
5. Click blank whiteboard: no border or ghost handles remain.
6. Middle-click to open and close the controls dialog; video geometry and selection must not change.
7. Ctrl + double-click enters crop; drag all four edges and four corners; Enter applies / Esc cancels.
8. Shift + left-drag pans when content zoom is above 1x.
9. Check landscape and square videos, not only portrait clips.
10. Save / reopen linked `.mstudio` and portable `.mstudiopack`, checking crop, scale, pan, A/B loop.
11. Load an older `.mstudio` project with a pre-existing crop and ensure it is restored.
12. Open Performance Info and watch RAM while deleting five videos; confirm media objects reach zero alive.

**If selection geometry still differs from the visible picture**, copy Performance Info > Video geometry report and a screenshot before committing. Qt backend differences can change rotation metadata availability.
