Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"

!define PRODUCT_NAME "MontaSpace Studio"
!define PRODUCT_VERSION "0.6.2"
!define PRODUCT_PUBLISHER "BC Shin Studio"
!define PRODUCT_URL "https://www.bcshinstudio.com"
!define PRODUCT_EXE "MontaSpaceStudio.exe"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\MontaSpaceStudio"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\installer-output\MontaSpaceStudio_Setup_${PRODUCT_VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\MontaSpaceStudio"
RequestExecutionLevel user
SetCompressor /SOLID lzma

VIProductVersion "0.6.2.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "FileDescription" "MontaSpace Studio Installer"
VIAddVersionKey "FileVersion" "0.6.2.0"
VIAddVersionKey "ProductVersion" "0.6.2"
VIAddVersionKey "LegalCopyright" "Copyright (C) 2026 BC Shin Studio. All rights reserved."

!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\MontaSpaceStudio.ico"
!define MUI_UNICON "..\assets\MontaSpaceStudio.ico"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${PRODUCT_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch MontaSpace Studio"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
UninstPage custom un.CacheCleanupPageCreate un.CacheCleanupPageLeave
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Var CacheCleanupCheck
Var RemoveCache

Function un.CacheCleanupPageCreate
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}
  ${NSD_CreateLabel} 0 2u 100% 32u "You may remove MontaSpace Studio's generated video thumbnail cache. Your project files, original photos, and videos will never be removed by this option."
  Pop $0
  ${NSD_CreateCheckbox} 0 44u 100% 18u "Remove cached thumbnails and app cache (optional)"
  Pop $CacheCleanupCheck
  ${NSD_Uncheck} $CacheCleanupCheck
  nsDialogs::Show
FunctionEnd

Function un.CacheCleanupPageLeave
  ${NSD_GetState} $CacheCleanupCheck $RemoveCache
FunctionEnd

Section "MontaSpace Studio application (required)" SecApp
  SetShellVarContext current
  SectionIn RO
  SetOutPath "$INSTDIR"
  ; Include the full PyInstaller one-folder bundle, including _internal.
  File /r "..\dist\MontaSpaceStudio\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\MontaSpace Studio"
  CreateShortCut "$SMPROGRAMS\MontaSpace Studio\MontaSpace Studio.lnk" "$INSTDIR\${PRODUCT_EXE}"
  CreateShortCut "$SMPROGRAMS\MontaSpace Studio\Uninstall MontaSpace Studio.lnk" "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "MontaSpace Studio ${PRODUCT_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "URLInfoAbout" "${PRODUCT_URL}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\${PRODUCT_EXE}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section /o "Desktop shortcut" SecDesktop
  CreateShortCut "$DESKTOP\MontaSpace Studio.lnk" "$INSTDIR\${PRODUCT_EXE}"
SectionEnd

LangString DESC_APP ${LANG_ENGLISH} "Install MontaSpace Studio and add Start menu shortcuts."
LangString DESC_DESKTOP ${LANG_ENGLISH} "Create an optional desktop shortcut."
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecApp} $(DESC_APP)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(DESC_DESKTOP)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  SetShellVarContext current
  Delete "$DESKTOP\MontaSpace Studio.lnk"
  Delete "$SMPROGRAMS\MontaSpace Studio\MontaSpace Studio.lnk"
  Delete "$SMPROGRAMS\MontaSpace Studio\Uninstall MontaSpace Studio.lnk"
  RMDir "$SMPROGRAMS\MontaSpace Studio"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  ; Only application files inside the install folder are removed.
  ; User projects saved elsewhere are not touched.
  RMDir /r "$INSTDIR"
  ${If} $RemoveCache == ${BST_CHECKED}
    ; QStandardPaths.CacheLocation with executable name MontaSpaceStudio.
    ; Delete ONLY the app's own thumbnail cache, never user media or projects.
    RMDir /r "$LOCALAPPDATA\MontaSpaceStudio\cache\video-posters"
    RMDir "$LOCALAPPDATA\MontaSpaceStudio\cache"
    RMDir "$LOCALAPPDATA\MontaSpaceStudio"
    ; Rare QStandardPaths fallback when no cache path is available.
    RMDir /r "$PROFILE\.montaspace-studio\cache\video-posters"
    RMDir "$PROFILE\.montaspace-studio\cache"
    RMDir "$PROFILE\.montaspace-studio"
  ${EndIf}
SectionEnd
