@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Virtual environment not found. Create one with: python -m venv .venv
  pause
  exit /b 1
)
if not exist "main.py" (
  echo ERROR: main.py is missing.
  pause
  exit /b 1
)
if not exist "assets\MontaSpaceStudio.ico" (
  echo ERROR: app icon missing.
  pause
  exit /b 1
)
if not exist "windows_version_info.txt" (
  echo ERROR: Windows version information is missing.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install "PyInstaller>=6,<7"
if errorlevel 1 goto :fail

rem Fail early if the HEIC decoder isn't installed in the build environment.
".venv\Scripts\python.exe" "tools\check_image_codecs.py"
if errorlevel 1 goto :fail

".venv\Scripts\python.exe" -m PyInstaller --collect-all pillow_heif --noconfirm --onedir --windowed --name MontaSpaceStudio --icon "assets\MontaSpaceStudio.ico" --add-data "assets\MontaSpaceStudio.ico;assets" --version-file "windows_version_info.txt" main.py
if errorlevel 1 goto :fail

echo.
echo Build complete: dist\MontaSpaceStudio\MontaSpaceStudio.exe
echo Keep the entire dist\MontaSpaceStudio folder together when distributing.
pause
exit /b 0

:fail
echo Build failed. Your source files were not deleted.
pause
exit /b 1
