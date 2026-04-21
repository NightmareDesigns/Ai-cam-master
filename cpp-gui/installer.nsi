; NSIS Installer Script for AI-Cam

!define APP_NAME "AI-Cam"
!define APP_VERSION "1.0.0"
!define PUBLISHER "AI-Cam"
!define WEB_SITE "https://github.com/NightmareDesigns/Ai-cam-master"
!define INSTALL_DIR "$PROGRAMFILES64\AI-Cam"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "AI-Cam-Setup-Windows.exe"
InstallDir "${INSTALL_DIR}"
RequestExecutionLevel admin

Page directory
Page instfiles

Section "Install"
    SetOutPath "$INSTDIR"

    File /r "build\Release\bundle\*.*"

    WriteUninstaller "$INSTDIR\Uninstall.exe"

    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\AI-Cam.exe"
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\AI-Cam.exe"

    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"

    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd
