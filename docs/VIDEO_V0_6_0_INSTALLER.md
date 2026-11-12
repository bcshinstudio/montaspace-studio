# v0.6.0 — Installer and clean-uninstall verification

This is an **installer/packaging update**, based on the working v0.5.24 source. No playback, image, project, or whiteboard logic changed; only the app version constant changes in that area.

## Build (Windows CMD)

1. Extract the complete source ZIP into the existing `C:\Users\baech\Projects\montaspace2` folder, keeping `.git` and `.venv`.
2. Run `run_regression_tests.bat` and require an overall PASS.
3. Run `build_installer.bat` with NSIS installed (existing build workflow).
4. Expected result: `installer-output\MontaSpaceStudio_Setup_0.6.0.exe`.
5. Inspect the installer in Windows Explorer (Properties > Details). Check product/executable version 0.6.0.

## Uninstall test

1. Install v0.6.0 with the default per-user installation folder. Confirm launch and playback.
2. Close MontaSpace Studio completely.
3. Uninstall through Settings > Installed apps. The uninstall wizard has an **unchecked by default** option to remove generated video thumbnail caches.
4. From CMD run `verify_uninstall.bat`. If you selected cache removal, run `verify_uninstall.bat --cache` instead.
5. A custom install directory can be verified with `verify_uninstall.bat --cache "D:\MyApps\MontaSpaceStudio"` (adjust to match your installation).
6. All checks should PASS; the script returns `errorlevel 1` if any checked locations remain. It is read-only.

## Data safety and scope

- Uninstall always removes only the program installation folder and registered shortcuts/uninstall entry, same as the existing installer.
- Optional cache cleanup removes `%%LOCALAPPDATA%%\MontaSpaceStudio\cache\video-posters` and the corresponding fallback `%%USERPROFILE%%\.montaspace-studio\cache\video-posters` if they exist. It removes parent directories only if empty.
- Projects (`.mstudio`, `.mstudiopack`) and original photos/videos outside the install folder are never targeted by cache cleanup.
- Do not save personal projects under the program installation directory: Windows uninstall removes that entire directory.
- Qt/Windows may create OS-managed caches outside this app-specific scope; this script intentionally does not delete arbitrary folders.
- The Windows installer cannot be executed in the Linux development environment. Build and uninstall must be verified on Windows before publishing a GitHub Release.
