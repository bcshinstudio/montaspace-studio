# Commit preparation — MontaSpace Studio v0.5.20

This is the **source-only** package. It excludes `.git/`, `.venv/`, bytecode caches, generated builds, logs and personal project/media files.

1. Keep the existing project directory and **do not delete `.git/` or `.venv/`**.
2. Close Studio; back up your project if desired.
3. Extract the provided ZIP into `C:\Users\baech\Projects\` and merge its `montaspace2` directory into the existing directory.
4. Run the tests and launch Studio to confirm the thumbnail, A/B timeline, and linked/portable save/load work.
5. Inspect Git changes, then commit:

```cmd
cd C:\Users\baech\Projects\montaspace2
.venv\Scripts\python.exe -m unittest discover -s tests -v
git status --short
git add -A
git diff --cached --stat
git diff --cached --check
git commit -m "MontaSpace Studio v0.5.20 - video thumbnails and timeline fixes"
git push origin main
```

If Git reports unexpected personal files, unstage them before committing. The source ZIP does not contain your `.git` history or Python environment.
