# MontaSpace Studio v0.4.0 — Windows acceptance test

Start with **copies** of your media and projects. Keep existing originals safe.

- [ ] About displays v0.4.0.
- [ ] Insert a photo and two MP4 videos. Move and resize all three.
- [ ] Set A and B on one video, enable A–B looping.
- [ ] Save as **Linked** `test.mstudio`. Check file stays small (does not embed videos).
- [ ] Close/reopen linked project; confirm both videos, photo, transforms, Z order, loop A/B points and loop checkbox restore.
- [ ] Open playback controls; confirm imported videos do NOT autoplay.
- [ ] Change loop A or B and confirm the window indicates unsaved changes.
- [ ] Save as **Portable** `test.mstudiopack` and confirm the estimated size prompt for a large project.
- [ ] Open portable project and confirm images, videos, and loops load from archive.
- [ ] Add the exact same MP4 twice and save portable; inspect archive if desired — only one video entry should exist.
- [ ] Save opened portable project as **Linked**; verify `_assets` copies allow it to open again after closing the original portable project.
- [ ] Open an existing `.mspace` photo project. Save uses **Save As** and preserves the original `.mspace`.
- [ ] Open an existing `.mspacepack` photo project; photos and crop/layer settings restore.
- [ ] Delete a video and check it no longer appears after saving/reopening.
- [ ] Right click selects another media item; A–B looping and multiple simultaneous videos still work.
- [ ] Check Performance Info and Copy Report continue to work.
- [ ] Repeat a few open/close cycles and compare process RAM; track native memory retention as an open performance issue.
