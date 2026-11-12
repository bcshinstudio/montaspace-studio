# MontaSpace Studio v0.5.16 — Windows native thumbnail test checklist

1. [ ] About reports v0.5.16.
2. [ ] Test `where ffmpeg`: **even if not found**, insert a video that shows a thumbnail in Windows Explorer; Studio should eventually show a poster **without playback**.
3. [ ] Insert the same video twice: poster cache should be reused; no autoplay.
4. [ ] Delete a poster-backed video and Ctrl+Z: poster should appear immediately.
5. [ ] Save and reopen a linked `.mstudio` project: layout and poster match.
6. [ ] Save and reopen a portable `.mstudiopack` project: poster is included if available at save time.
7. [ ] Insert a video whose thumbnail Windows cannot produce: show the clean fallback, no crash or freeze.
8. [ ] Double-click play/pause and middle-click playback controls.
9. [ ] Confirm resize/crop, Ctrl+Z/Ctrl+Y, and F1/Ctrl+H shortcut help.
10. [ ] Monitor resource usage while inserting several videos: extraction runs sequentially and does not autoplay videos.

Notes: Windows may not support thumbnails for every video codec, even when the player plays the video. The native API may take time on first encounter. FFmpeg remains optional.
