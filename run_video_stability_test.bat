@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe
  exit /b 1
)
if "%~1"=="" (
  echo Usage: run_video_stability_test.bat "C:\path\to\video.mp4"
  echo Optional: append --portable for portable video project testing.
  exit /b 2
)
".venv\Scripts\python.exe" "tools\video_stability_test.py" %*
exit /b %errorlevel%
