# MontaSpace Studio v0.3.2 — Memory & Regression Test

1. Start fresh: Performance Info should show Videos on board: 0 and Videos currently playing: 0. Record RAM.
2. Insert and play three MP4s: Performance Info should show 3 videos and 3 playing. Record RAM.
3. Delete each video: controls should close, and Performance Info should show 0 videos, 0 playing.
4. Wait 30 seconds with the event loop active. Record RAM (Task Manager and Performance Info).
5. Repeat insert/play/delete once more; watch for progressively retained RAM.
6. Reinsert a video, set A and B, enable A–B looping, confirm looping still works.
7. Close and reopen the controls of a playing video, confirm playback continues.
8. Open an old photo-only project. Check JPG/PNG insert, Ctrl+D, crop, project save and reopen.
9. Verify that Ctrl+S on a project with videos still warns and does not silently omit them.
10. Confirm simultaneous playback remains possible; no automatic pause behavior was added.

These tests measure actual Windows behavior. Qt/FFmpeg or the OS may retain
some allocated pages even after cleanup; lower memory is expected but not guaranteed.
