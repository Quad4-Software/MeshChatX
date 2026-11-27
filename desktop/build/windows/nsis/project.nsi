Unicode true

!include "wails_tools.nsh"

VIProductVersion "${INFO_PRODUCTVERSION}.0"
VIFileVersion    "${INFO_PRODUCTVERSION}.0"

VIAddVersionKey "CompanyName"     "${INFO_COMPANYNAME}"
VIAddVersionKey "FileDescription" "${INFO_PRODUCTNAME} Installer"
VIAddVersionKey "ProductVersion"  "${INFO_PRODUCTVERSION}"
VIAddVersionKey "FileVersion"     "${INFO_PRODUCTVERSION}"
VIAddVersionKey "LegalCopyright"  "${INFO_COPYRIGHT}"
VIAddVersionKey "ProductName"     "${INFO_PRODUCTNAME}"

ManifestDPIAware true

!include "MUI.nsh"

!define MUI_ICON "..\icon.ico"
!define MUI_UNICON "..\icon.ico"
!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Name "${INFO_PRODUCTNAME}"
OutFile "..\..\..\bin\ReticulumMeshChatX-v${INFO_PRODUCTVERSION}-win32-${ARCH}-installer.exe"
!if "${WAILS_INSTALL_SCOPE}" == "user"
    InstallDir "$LOCALAPPDATA\Programs\${INFO_PRODUCTNAME}"
!else
    InstallDir "$PROGRAMFILES64\${INFO_COMPANYNAME}\${INFO_PRODUCTNAME}"
!endif
ShowInstDetails show

Function .onInit
   !insertmacro wails.checkArchitecture
FunctionEnd

Function CleanStrandedBackend
    Push $0
    Push $1
    FindFirst $0 $1 "$INSTDIR\*.*"
    cleanLoop:
        StrCmp $1 "" cleanDone
        StrCmp $1 "." cleanNext
        StrCmp $1 ".." cleanNext
        StrCmp $1 "backend" cleanNext
        StrCmp $1 "uninstall.exe" cleanNext
        StrCmp $1 "${PRODUCT_EXECUTABLE}" cleanNext
        IfFileExists "$INSTDIR\$1\*.*" cleanIsDir 0
        Delete "$INSTDIR\$1"
        Goto cleanNext
        cleanIsDir:
        RMDir /r "$INSTDIR\$1"
        cleanNext:
        FindNext $0 $1
        Goto cleanLoop
    cleanDone:
    FindClose $0
    Pop $1
    Pop $0
FunctionEnd

Section
    !insertmacro wails.setShellContext

    !insertmacro wails.webview2runtime

    SetOutPath $INSTDIR

    ; 4.12.0 and 4.12.1 extracted the backend into the install root. Clear
    ; that payload so it does not sit next to the real backend\ directory.
    IfFileExists "$INSTDIR\ReticulumMeshChatX.exe" 0 +2
    Call CleanStrandedBackend

    !insertmacro wails.files

    ; Bundle the frozen Python backend in backend\ next to the shell executable.
    ; CreateDirectory does not change $OUTDIR, so SetOutPath is required or
    ; File /r extracts into $INSTDIR and the shell cannot find the backend.
    SetOutPath "$INSTDIR\backend"
    File /r "..\..\..\bin\backend\*.*"
    SetOutPath $INSTDIR

    ; URL scheme handlers: lxmf:// and rns://
    DeleteRegKey HKCR "lxmf"
    WriteRegStr HKCR "lxmf" "" "URL:MeshChatX LXMF link"
    WriteRegStr HKCR "lxmf" "URL Protocol" ""
    WriteRegStr HKCR "lxmf\shell\open\command" "" '"$INSTDIR\${PRODUCT_EXECUTABLE}" "%1"'
    DeleteRegKey HKCR "rns"
    WriteRegStr HKCR "rns" "" "URL:MeshChatX RNS link"
    WriteRegStr HKCR "rns" "URL Protocol" ""
    WriteRegStr HKCR "rns\shell\open\command" "" '"$INSTDIR\${PRODUCT_EXECUTABLE}" "%1"'

    CreateShortcut "$SMPROGRAMS\${INFO_PRODUCTNAME}.lnk" "$INSTDIR\${PRODUCT_EXECUTABLE}"
    CreateShortCut "$DESKTOP\${INFO_PRODUCTNAME}.lnk" "$INSTDIR\${PRODUCT_EXECUTABLE}"

    !insertmacro wails.writeUninstaller
SectionEnd

Section "uninstall"
    !insertmacro wails.setShellContext

    RMDir /r "$AppData\${PRODUCT_EXECUTABLE}"

    RMDir /r $INSTDIR

    Delete "$SMPROGRAMS\${INFO_PRODUCTNAME}.lnk"
    Delete "$DESKTOP\${INFO_PRODUCTNAME}.lnk"

    DeleteRegKey HKCR "lxmf"
    DeleteRegKey HKCR "rns"

    !insertmacro wails.deleteUninstaller
SectionEnd
