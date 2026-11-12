# Studio 0.5.0 Windows GUI verification

- [ ] Existing v0.4.2 video renders and plays normally at 1× zoom and 0% crop.
- [ ] Double-click plays/pauses, middle-click toggles playback controls.
- [ ] Zoom slider magnifies moving video inside its fixed whiteboard frame (not the entire item).
- [ ] Shift + left-drag pans when zoomed. Plain drag moves the item.
- [ ] Crop slider trims edges; cropped portions cannot be selected by right-click.
- [ ] Reset View returns to original, center, uncropped.
- [ ] Save and reopen `.mstudio`: zoom, pan, crop and A–B markers persist.
- [ ] Save and reopen `.mstudiopack` without originals: same behavior.
- [ ] Open an older v0.4.x Studio project without view settings.
- [ ] Play multiple clips simultaneously; deleting videos still releases Qt objects.
- [ ] Original MontaSpace photo crop and photos-only project import still work.
- [ ] Installer build succeeds and reports v0.5.0.

Note: Qt/Windows media playback cannot be verified by syntax checks alone.
