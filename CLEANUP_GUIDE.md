# MontaSpace Studio v0.3.4 — Clean replacement guide

The source archive intentionally does **not** contain `.venv/`, `.git/`, `build/`, `dist/`, `installer-output/`, generated `.spec` files or caches.

## Safe full-folder replacement
1. Close Studio, VS Code, and any installer/build command windows.
2. Rename `C:\Users\baech\Projects\montaspace2` to `montaspace2_backup`.
3. Extract the ZIP so the new folder is `C:\Users\baech\Projects\montaspace2` (check for an extra nested folder).
4. Copy the existing `.venv` directory from `montaspace2_backup` into the new folder.
5. **Only if it exists**, copy `.git` too (keep the new project repository separate from original MontaSpace).
6. Run `.venv\Scripts\python.exe main.py` from inside the new folder and verify About v0.3.4, photo controls, video A/B loop, and right-click selection.
7. Keep the backup until verified; copy any personal `.mspace` / `.mspacepack` files saved inside the old project directory separately if needed.

## If you prefer to merge rather than replace
After copying source files, old generated/obsolete files remain in the destination; merging does not clean it. Full-folder replacement is preferred for a genuinely clean layout.

## Removed from the source distribution
- Local Python environment `.venv`, Git history `.git`, generated `build`, `dist`, `installer-output`, `.spec`, bytecode caches.
- Legacy photo-only `installer/MontaSpace.nsi` and duplicate `assets/MontaSpace.ico` (Studio has its own installer and icon).
- Original photo-only `STEP_8_3_TEST_CHECKLIST.txt` and outdated cleanup instructions.

## Kept
- All Studio application modules, diagnostics, photo and video logic.
- Studio installer and build scripts; `tools/` and historical Studio checklists in `docs/`.
- `.gitignore` excludes generated output.

Installer version metadata and the build script were aligned to 0.3.4. Windows installer compilation has not been executed in this environment.
