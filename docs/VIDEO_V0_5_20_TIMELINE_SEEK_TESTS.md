# v0.5.20 — Timeline click / A–B loop verification

1. Insert Samsung MP4; confirm thumbnail before playback.
2. Open controls, click **Set A** at 00:00.
3. Click the timeline track halfway (not the circle), then click **Set B**. B must reflect the clicked time (not 00:00).
4. Clear loop, drag the slider circle and set A/B, verifying both paths.
5. Test short video, seek +5s / -5s, Go A / Go B.
6. Confirm real video playback, zoom, crop, Undo, and saved project loading unchanged.

The timeline displays the requested time while Qt's asynchronous seek resolves.
