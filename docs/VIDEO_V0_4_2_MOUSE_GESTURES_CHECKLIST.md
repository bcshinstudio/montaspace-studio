# MontaSpace Studio v0.4.2 — mouse gesture checks

1. Double-left-click a newly restored (dark placeholder) MP4: it starts playing without opening controls.
2. Double-left-click the playing video: playback pauses; double-left-click again: resumes.
3. Middle-click the video: playback-controls dialog opens. Middle-click again: it closes without pausing playback.
4. Middle-click after closing the dialog: controls reopen and A/B settings are retained.
5. Right-click video: existing context menu still works.
6. Double-left-click photo: existing crop behavior still works.
7. Middle-click photo or empty whiteboard: no video controls open.
8. Test on two different videos; controls target the video under the pointer.
9. Save and reopen both .mstudio and .mstudiopack; test gestures and A/B loop persistence.
10. Remove all videos and check Performance Info shows zero remaining Qt objects.
