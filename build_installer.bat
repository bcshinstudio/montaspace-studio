@echo off
setlocal
cd /d "%~dp0"

echo MontaSpace Studio v0.6.2 - installer validation candidate
echo.
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Missing .venv. Keep your existing Python virtual environment.
  goto :fail
)
if not exist "assets\MontaSpaceStudio.ico" (
  echo ERROR: assets\MontaSpaceStudio.ico not found.
  goto :fail
)

rem Refuse to create a release installer if required regression tests fail.
call "run_regression_tests.bat"
if errorlevel 1 goto :fail

if not exist "installer-output" mkdir "installer-output"
rem Remove only the installer for this version to prevent a stale file counting as success.
if exist "installer-output\MontaSpaceStudio_Setup_0.6.2.exe" del /q "installer-output\MontaSpaceStudio_Setup_0.6.2.exe"

rem Fail early if the HEIC decoder isn't installed in the build environment.
".venv\Scripts\python.exe" "tools\check_image_codecs.py"
if errorlevel 1 goto :fail

rem PyInstaller produces a folder with the EXE and its bundled dependencies.
".venv\Scripts\python.exe" -m pip install "PyInstaller>=6,<7"
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m PyInstaller --collect-all pillow_heif --clean --noconfirm --onedir --windowed --name MontaSpaceStudio --icon "assets\MontaSpaceStudio.ico" --add-data "assets\MontaSpaceStudio.ico;assets" --version-file "windows_version_info.txt" main.py
if errorlevel 1 goto :fail
if not exist "dist\MontaSpaceStudio\MontaSpaceStudio.exe" (
  echo ERROR: Standalone EXE missing; keeping build artifacts.
  goto :fail
)

set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if not exist "%MAKENSIS%" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"
if not exist "%MAKENSIS%" (
  for %%M in (makensis.exe) do set "MAKENSIS=%%~$PATH:M"
)
if not exist "%MAKENSIS%" (
  echo ERROR: Cannot locate makensis.exe.
  echo Check the standard NSIS installation folder.
  goto :fail
)

echo.
echo Compiling NSIS installer...
"%MAKENSIS%" "installer\MontaSpaceStudio.nsi"
if errorlevel 1 goto :fail

rem Never clean intermediate files unless the expected installer exists.
if not exist "installer-output\MontaSpaceStudio_Setup_0.6.2.exe" (
  echo ERROR: NSIS returned success, but the expected installer is missing.
  goto :fail
)

for %%F in ("installer-output\MontaSpaceStudio_Setup_0.6.2.exe") do if %%~zF LSS 1000000 (
  echo ERROR: Installer is suspiciously small. Keeping build artifacts.
  goto :fail
)

rem Build succeeded: remove only generated PyInstaller artifacts.
rem Keep installer-output, .venv, .git, all source files, and user projects.
echo.
echo Removing temporary build artifacts...
if exist "build\" rmdir /s /q "build"
if exist "dist\" rmdir /s /q "dist"
if exist "MontaSpaceStudio.spec" del /q "MontaSpaceStudio.spec"

if exist "build\" echo WARNING: Could not fully remove build\. Delete it later if unused.
if exist "dist\" echo WARNING: Could not fully remove dist\. Close running EXEs and retry later.
if exist "MontaSpaceStudio.spec" echo WARNING: Could not remove MontaSpaceStudio.spec.

echo.
echo SUCCESS: installer-output\MontaSpaceStudio_Setup_0.6.2.exe
echo NOTE: The installer is unsigned, so Windows may show a SmartScreen warning.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Check the error above. The source has not been deleted.
pause
exit /b 1
