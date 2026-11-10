@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing virtual environment.
  exit /b 1
)
set "COUNT=%~1"
if "%COUNT%"=="" set "COUNT=25"
".venv\Scripts\python.exe" "tools\stress_test.py" %COUNT%
if errorlevel 1 (
  echo Stress test failed. Check the error message above.
  exit /b 1
)
echo Stress test completed.
endlocal
