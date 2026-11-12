# v0.5.22 A/B loop-seek reliability test

## Scope
No changes to thumbnails, video decoding, project storage, photo editing, A/B user controls or resource cleanup.

1. Start a single video, set A=2 seconds, B=8 seconds, enable loop; verify the player repeats between these times.
2. Keep it playing for at least 3 minutes and open Performance Info. Check loop_seek_requests and duplicate_events_suppressed in video geometry.
3. Pause, resume, disable/re-enable loop; seek using timeline clicks, confirm Set A and Set B still capture the chosen time.
4. Repeat with five independently looping videos for 5 minutes and compare working-set/private memory over time.
5. Delete, Undo, save/reopen a linked and portable project; check thumbnails, geometry and loop settings.
6. Check cropped videos still play and edit normally; check photo tools.

## Interpreting diagnostics
- loop_seek_requests: actual jumps requested by our A/B logic, per video (counter survives state toggles until video object destroyed).
- seek_confirmations: Qt-reported return near A; should increase each normal loop.
- duplicate_events_suppressed: near-B events while a jump is pending or during brief seek cooldown.
- seek_pending: true temporarily while waiting for Qt to report A. If stuck true, the seek did not confirm; do not interpret memory results as a loop-seeking fix.
- Growing memory with healthy counters suggests another multimedia/backend cause.

Qt/FFmpeg runtime behavior must be tested on Windows; automated tests do not prove memory is fixed.
