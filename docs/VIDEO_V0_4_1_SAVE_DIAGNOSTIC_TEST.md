# Studio v0.4.1 — Video save/restore verification

1. Insert one JPG and one MP4. Save as linked .mstudio.
2. Open .mstudio with Notepad. Under `items`, confirm both `"type": "image"` and `"type": "video"` entries.
3. Close/reopen Studio, open linked project. The video should appear as a dark labeled MP4 tile until playback begins. Right-click tile → Playback Controls → Play.
4. Verify A–B loop settings restored.
5. Save a new .mstudiopack and reopen it. Verify video tile, then playback.
6. In case of missing video, note the exact on-screen warning and whether `Videos on board` in Performance Info is zero.
7. Do not delete old test project files or original videos.
