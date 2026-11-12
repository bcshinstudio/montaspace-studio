# MontaSpace Studio v0.5.10 — Windows regression checklist

## Photos
- [ ] Photo selection shows 8 small handles (corners + edges), and one rotation dot.
- [ ] All four side handles proportionally resize the photo.
- [ ] All four corner handles resize the photo.
- [ ] Handles remain the same small screen-pixel size after enlarging/shrinking the photo.
- [ ] Horizontal/vertical resize cursors appear over side handles.
- [ ] Photo double-click enters crop mode; eight handles adjust each edge independently.
- [ ] Enter applies crop, Esc cancels; photo rotation, duplication and Undo still work.

## Videos
- [ ] Video initially has no selection handles. Select it to show 8 small handles.
- [ ] All four sides and four corners resize the video with the same formula as photos.
- [ ] Handles remain the same size even after making a portrait video much larger.
- [ ] Video is not stretched; border matches the visible frame before and after resizing.
- [ ] Double-click play/pause works; middle-click opens/closes playback controls.
- [ ] Ctrl + double-click opens crop; all eight handles crop the intended directions.
- [ ] Esc cancels crop, Enter applies; no ghost borders when deselecting.
- [ ] Several videos can play simultaneously without automatic pausing.

## F1 and persistence
- [ ] F1 shows shortcut help in a separate small window; F1 or Esc closes it.
- [ ] Playback controls no longer show shortcut instructions; Content Zoom and A-B loop remain.
- [ ] Save and reopen linked `.mstudio` with cropped/zoomed video and photos.
- [ ] Save and reopen portable `.mstudiopack` with the same geometry.
- [ ] Diagnostics, deletion cleanup and right-click selection still work.
