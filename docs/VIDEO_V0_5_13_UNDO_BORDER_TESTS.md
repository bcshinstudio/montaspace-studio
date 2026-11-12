# MontaSpace Studio v0.5.13 — Windows test checklist

- [ ] Launch: clean whiteboard, thin frame border, no blank/blue rectangle artifact.
- [ ] Ctrl+Shift+B toggles the border; window resize hints still appear.
- [ ] Insert photo and video; both can be undone/redone (Ctrl+Z/Ctrl+Y).
- [ ] Resize photo, then resize video; Ctrl+Z undoes video first, photo second.
- [ ] Redo both in the correct order with Ctrl+Y.
- [ ] Move video, Ctrl+Z reverts position, Ctrl+Y restores it.
- [ ] Ctrl+double-click video, crop, Enter; Ctrl+Z restores crop, Ctrl+Y reapplies.
- [ ] Cancel video crop with Esc; no history entry should be created.
- [ ] Shift+drag zoomed video to pan; Undo/Redo restores pan.
- [ ] Set A, Set B and toggle Loop; Undo/Redo reverts those settings.
- [ ] Content Zoom slider drag; one Ctrl+Z reverts a drag to its previous value.
- [ ] Delete video; Ctrl+Z restores it from its original MP4 (paused), Ctrl+Y deletes it again.
- [ ] Save/reopen .mstudio and .mstudiopack with mixed media; files still load.
- [ ] Existing crop/resize handles and mouse playback gestures remain correct.
- [ ] Performance Info lifecycle counts after deletion/undo are sensible.
