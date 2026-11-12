@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe
  exit /b 1
)
if "%~1"=="" (
  echo Usage: run_studio_loop_test.bat "C:\full\path\to\video.mp4"
  exit /b 2
)
".venv\Scripts\python.exe" "tools\studio_playback_benchmark.py" %*
set "RESULT=%ERRORLEVEL%"
echo.
echo Finished. Reports are in Documents\MontaSpaceStudio_Test_Reports.
exit /b %RESULT%
