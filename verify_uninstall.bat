@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
rem Usage: verify_uninstall.bat [--cache] ["custom-install-folder"]
rem Read-only checks. Never deletes any files. Returns errorlevel 1 if traces remain.
set "CHECK_CACHE=0"
set "CUSTOM_DIR="
:parse
if "%~1"=="" goto :checks
if /I "%~1"=="--cache" (
  set "CHECK_CACHE=1"
) else (
  set "CUSTOM_DIR=%~1"
)
shift
goto :parse
:checks
set "FAIL=0"
echo.
echo === MontaSpace Studio uninstall verification ===
call :checkdir "%LOCALAPPDATA%\Programs\MontaSpaceStudio" "Default installation folder"
if defined CUSTOM_DIR call :checkdir "%CUSTOM_DIR%" "Custom installation folder"
call :checkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\MontaSpace Studio" "Start Menu shortcuts"
call :checkfile "%USERPROFILE%\Desktop\MontaSpace Studio.lnk" "Desktop shortcut"
call :checkfile "%PUBLIC%\Desktop\MontaSpace Studio.lnk" "Public desktop shortcut"
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\MontaSpaceStudio" >nul 2>&1
if not errorlevel 1 (
  echo FAIL: Uninstall registry entry still exists.
  set "FAIL=1"
) else (
  echo PASS: Uninstall registry entry absent.
)
if "%CHECK_CACHE%"=="1" (
  echo.
  echo === Optional cache cleanup verification ===
  call :checkdir "%LOCALAPPDATA%\MontaSpaceStudio\cache\video-posters" "Video thumbnail cache"
  call :checkdir "%USERPROFILE%\.montaspace-studio\cache\video-posters" "Fallback video thumbnail cache"
)
echo.
if "%FAIL%"=="0" (
  echo PASS: Checked uninstall locations are clean.
) else (
  echo FAIL: Some checked locations remain. Review the lines above.
)
exit /b %FAIL%

:checkdir
if exist "%~1\" (
  echo FAIL: %~2 remains: "%~1"
  set "FAIL=1"
) else (
  echo PASS: %~2 absent.
)
exit /b 0

:checkfile
if exist "%~1" (
  echo FAIL: %~2 remains: "%~1"
  set "FAIL=1"
) else (
  echo PASS: %~2 absent.
)
exit /b 0
