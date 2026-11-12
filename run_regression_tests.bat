@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Missing .venv\Scripts\python.exe
  exit /b 2
)
".venv\Scripts\python.exe" -B tools\run_regressions.py
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (echo REGRESSION TESTS PASSED) else (echo REGRESSION TESTS FAILED)
exit /b %RESULT%
