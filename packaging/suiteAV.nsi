; =====================================================================
;  suiteAV - installer NSIS (dal modello di MarkMirror / Zenith)
;
;  Funzionalità:
;    - scelta della lingua all'avvio (italiano / inglese), ricordata
;      anche dal disinstallatore
;    - installazione per utente, senza diritti di amministratore
;      (%LOCALAPPDATA%\Programs\suiteAV)
;    - componenti: programma, collegamento sul desktop, collegamento
;      nel menu Start
;    - voce in "App installate" / "Programmi e funzionalità"
;    - disinstallatore, con opzione per rimuovere anche impostazioni e
;      cache; i file scaricati non vengono mai toccati
;
;  Build (dalla root del progetto, dopo `pyinstaller packaging/suiteAV.spec`):
;    makensis /DVERSION=4.1.0 packaging\suiteAV.nsi
;  Output: dist\suiteAV-<versione>-windows-x64-installer.exe
;
;  makensis lavora nella cartella di questo file: i percorsi relativi
;  qui sotto partono da packaging\.
; =====================================================================

Unicode true
ManifestDPIAware true
SetCompressor /SOLID lzma

; ---------------------------------------------------------------------
;  Configurazione
; ---------------------------------------------------------------------
!define APP_NAME     "suiteAV"
!define APP_EXE      "suiteAV.exe"
!define COMPANY      "Alessio Abrugiati"
!define APP_URL      "https://github.com/alexis-82/suiteAV"
!ifndef VERSION
  !define VERSION    "0.0.0"          ; formato x.y.z, da riga di comando
!endif

!define SOURCE_DIR   "..\dist\suiteAV"   ; build a cartella di PyInstaller
!define ICON_FILE    "suiteav.ico"

; Chiavi di registro (HKCU: installazione per utente)
!define APP_REG_KEY  "Software\${APP_NAME}"
!define UNINST_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

; config.toml e cache (platformdirs: user_config_dir / user_cache_dir)
!define SETTINGS_DIR "$LOCALAPPDATA\suiteav"

; ---------------------------------------------------------------------
;  Impostazioni generali
; ---------------------------------------------------------------------
Name "${APP_NAME}"
OutFile "..\dist\${APP_NAME}-${VERSION}-windows-x64-installer.exe"
InstallDir "$LOCALAPPDATA\Programs\${APP_NAME}"
InstallDirRegKey HKCU "${APP_REG_KEY}" "InstallDir"
RequestExecutionLevel user
BrandingText "${APP_NAME} ${VERSION}"
ShowInstDetails show
ShowUninstDetails show

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ---------------------------------------------------------------------
;  Interfaccia (Modern UI 2)
; ---------------------------------------------------------------------
!define MUI_ICON   "${ICON_FILE}"
!define MUI_UNICON "${ICON_FILE}"
!define MUI_ABORTWARNING
!define MUI_UNABORTWARNING

; Lingua scelta: salvata in HKCU, così il disinstallatore la riusa
!define MUI_LANGDLL_REGISTRY_ROOT      HKCU
!define MUI_LANGDLL_REGISTRY_KEY       "${APP_REG_KEY}"
!define MUI_LANGDLL_REGISTRY_VALUENAME "Language"
!define MUI_LANGDLL_ALLLANGUAGES       ; mostra sempre tutte le lingue

; Ultima pagina: casella "Avvia suiteAV"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"

; Pagine dell'installer
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Pagine del disinstallatore
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_COMPONENTS
!insertmacro MUI_UNPAGE_INSTFILES

; Lingue (la prima è quella predefinita)
!insertmacro MUI_LANGUAGE "Italian"
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_RESERVEFILE_LANGDLL

; ---------------------------------------------------------------------
;  Testi tradotti
; ---------------------------------------------------------------------
LangString SecAppName      ${LANG_ITALIAN} "${APP_NAME} (obbligatorio)"
LangString SecAppName      ${LANG_ENGLISH} "${APP_NAME} (required)"
LangString SecAppDesc      ${LANG_ITALIAN} "Il programma ${APP_NAME}. Per scaricare e convertire serve anche ffmpeg (winget install --source winget Gyan.FFmpeg)."
LangString SecAppDesc      ${LANG_ENGLISH} "The ${APP_NAME} application. Downloading and converting also need ffmpeg (winget install --source winget Gyan.FFmpeg)."
LangString SecDesktopName  ${LANG_ITALIAN} "Collegamento sul desktop"
LangString SecDesktopName  ${LANG_ENGLISH} "Desktop shortcut"
LangString SecDesktopDesc  ${LANG_ITALIAN} "Crea un collegamento a ${APP_NAME} sul desktop."
LangString SecDesktopDesc  ${LANG_ENGLISH} "Creates a ${APP_NAME} shortcut on the desktop."
LangString SecStartName    ${LANG_ITALIAN} "Collegamento nel menu Start"
LangString SecStartName    ${LANG_ENGLISH} "Start menu shortcut"
LangString SecStartDesc    ${LANG_ITALIAN} "Aggiunge ${APP_NAME} al menu Start."
LangString SecStartDesc    ${LANG_ENGLISH} "Adds ${APP_NAME} to the Start menu."

LangString UnSecAppName       ${LANG_ITALIAN} "${APP_NAME}"
LangString UnSecAppName       ${LANG_ENGLISH} "${APP_NAME}"
LangString UnSecAppDesc       ${LANG_ITALIAN} "Rimuove il programma e i collegamenti."
LangString UnSecAppDesc       ${LANG_ENGLISH} "Removes the application and its shortcuts."
LangString UnSecSettingsName  ${LANG_ITALIAN} "Impostazioni"
LangString UnSecSettingsName  ${LANG_ENGLISH} "Settings"
LangString UnSecSettingsDesc  ${LANG_ITALIAN} "Rimuove anche le impostazioni (cartella dei download, lingua) e la cache. I file scaricati e convertiti non vengono mai eliminati."
LangString UnSecSettingsDesc  ${LANG_ENGLISH} "Also removes the settings (downloads folder, language) and the cache. Downloaded and converted files are never deleted."

; Proprietà dell'installer (tasto destro > Proprietà > Dettagli)
VIProductVersion "${VERSION}.0"
VIFileVersion    "${VERSION}.0"
VIAddVersionKey /LANG=${LANG_ITALIAN} "ProductName"     "${APP_NAME}"
VIAddVersionKey /LANG=${LANG_ITALIAN} "CompanyName"     "${COMPANY}"
VIAddVersionKey /LANG=${LANG_ITALIAN} "FileDescription" "${APP_NAME} Setup"
VIAddVersionKey /LANG=${LANG_ITALIAN} "FileVersion"     "${VERSION}"
VIAddVersionKey /LANG=${LANG_ITALIAN} "ProductVersion"  "${VERSION}"
VIAddVersionKey /LANG=${LANG_ITALIAN} "LegalCopyright"  "${COMPANY}"

; ---------------------------------------------------------------------
;  Installazione
; ---------------------------------------------------------------------
Section "!$(SecAppName)" SecApp
  SectionIn RO
  SetShellVarContext current

  ; Aggiornamento: via le librerie della versione precedente, così in
  ; _internal non restano file che la nuova non usa più
  RMDir /r "$INSTDIR\_internal"

  SetOutPath "$INSTDIR"
  File "${SOURCE_DIR}\${APP_EXE}"
  File "${SOURCE_DIR}\deno.exe"
  File /r "${SOURCE_DIR}\_internal"
  WriteUninstaller "$INSTDIR\uninstall.exe"

  WriteRegStr HKCU "${APP_REG_KEY}" "InstallDir" "$INSTDIR"

  ; Voce in "App installate" / "Programmi e funzionalità"
  WriteRegStr   HKCU "${UNINST_KEY}" "DisplayName"          "${APP_NAME}"
  WriteRegStr   HKCU "${UNINST_KEY}" "DisplayVersion"       "${VERSION}"
  WriteRegStr   HKCU "${UNINST_KEY}" "DisplayIcon"          "$INSTDIR\${APP_EXE}"
  WriteRegStr   HKCU "${UNINST_KEY}" "Publisher"            "${COMPANY}"
  WriteRegStr   HKCU "${UNINST_KEY}" "URLInfoAbout"         "${APP_URL}"
  WriteRegStr   HKCU "${UNINST_KEY}" "InstallLocation"      "$INSTDIR"
  WriteRegStr   HKCU "${UNINST_KEY}" "UninstallString"      "$\"$INSTDIR\uninstall.exe$\""
  WriteRegStr   HKCU "${UNINST_KEY}" "QuietUninstallString" "$\"$INSTDIR\uninstall.exe$\" /S"
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKCU "${UNINST_KEY}" "EstimatedSize" $0
SectionEnd

Section "$(SecDesktopName)" SecDesktop
  SetShellVarContext current
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
SectionEnd

Section "$(SecStartName)" SecStart
  SetShellVarContext current
  CreateShortcut "$SMPROGRAMS\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecApp}     $(SecAppDesc)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(SecDesktopDesc)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStart}   $(SecStartDesc)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Function .onInit
  !insertmacro MUI_LANGDLL_DISPLAY
FunctionEnd

; ---------------------------------------------------------------------
;  Disinstallazione
; ---------------------------------------------------------------------
Section "un.$(UnSecAppName)" UnSecApp
  SectionIn RO
  SetShellVarContext current

  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}.lnk"

  ; Solo i file installati: se l'utente ha scelto una cartella con altro
  ; dentro, il resto non si tocca
  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\deno.exe"
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\uninstall.exe"
  RMDir "$INSTDIR"                      ; solo se vuota

  DeleteRegKey HKCU "${UNINST_KEY}"
  DeleteRegKey HKCU "${APP_REG_KEY}"
SectionEnd

Section /o "un.$(UnSecSettingsName)" UnSecSettings
  RMDir /r "${SETTINGS_DIR}"
SectionEnd

!insertmacro MUI_UNFUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${UnSecApp}      $(UnSecAppDesc)
  !insertmacro MUI_DESCRIPTION_TEXT ${UnSecSettings} $(UnSecSettingsDesc)
!insertmacro MUI_UNFUNCTION_DESCRIPTION_END

Function un.onInit
  !insertmacro MUI_UNGETLANGUAGE
FunctionEnd
