# MontaSpace Studio v0.4.1 — Replacement instructions

This source package is independent of the original photo-only MontaSpace project.
It contains the Studio source, installer script, icon, and documentation.

1. Close Studio and back up `C:\Users\baech\Projects\montaspace2`.
2. Extract the ZIP into `C:\Users\baech\Projects\` and merge its
   `montaspace2` folder into your existing Studio folder.
3. Keep your local `.git` and `.venv` folders; they are not in this ZIP.
4. Run `.venv\Scripts\python.exe main.py` and check About v0.4.1.
5. Test **Save As** to `.mstudio` and `.mstudiopack` with copies of media.
6. Do not tag v0.4.1 or build the public installer until Windows testing passes.

Build artifacts (`build/`, `dist/`, `installer-output/`, `*.spec`) are excluded.
Both Studio project formats are ignored by Git to avoid committing user media.
