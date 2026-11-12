# v0.5.24 Project reliability verification

## Automated (Windows project environment)
Run `run_regression_tests.bat`. The suite includes 13 pure Python file-system tests
and 4 additional Qt whiteboard project-recovery tests.

## Short manual check (two minutes)
1. Save a linked `.mstudio` with one photo and one MP4.
2. Close the project, move the source media to another folder.
3. Open the linked project; confirm the **Missing project media** dialog appears.
4. Choose **Locate Folder…** and the moved media folder. The board layout,
   video controls and posters should reappear.
5. Confirm the project title shows `*`, then press Ctrl+S to repair the file links.
6. Reopen the project and verify it does not ask for missing media again.
7. Move one source away again, attempt to open, choose Cancel; the existing
   whiteboard should remain untouched.

## Important safety rules
- An ambiguous duplicate basename is never chosen automatically.
- The recovery search is bounded at 4000 entries; choose a narrower folder if
  no unique match is found.
- Never overwrite `.mspace`/`.mspacepack` when saving from Studio.
- Existing .mstudiopack portable files and older Studio schema v1 remain supported.
- Do not commit until Windows real-GUI regression and manual recovery pass.
