# MontaSpace Studio v0.5.17 — Poster verification

1. Launch, confirm About shows v0.5.17.
2. Insert MP4 and leave it stopped. Poster or clean fallback should appear within several seconds.
3. Delete and Ctrl+Z; no repeated attempt or delay should occur if the first attempt failed.
4. Save and reopen `.mstudio`; verify position, crop, and fallback/poster.
5. Save/open `.mstudiopack`; verify portable poster if one was generated.
6. Play video, middle-click controls, crop, undo/redo; none should be affected.
7. Task Manager: thumbnail extraction should not leave growing processes or memory usage.
8. If no thumbnail appears, this is an allowed fallback. v0.5.17 bounds extraction; it cannot create thumbnails for unsupported codecs.
