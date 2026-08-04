@echo off
rem ============================================================================
rem  Storm Mountain Training Grounds - one button.
rem
rem  Double-click this file, or run it from a prompt. It sets everything up and
rem  opens ArcGIS Pro on a project with all the layers loaded.
rem
rem  This wrapper exists because Windows blocks unsigned PowerShell scripts by
rem  default (execution policy Restricted), so running Start-StormMountain.ps1
rem  directly fails on a clean machine with a red wall of text that has nothing
rem  to do with anything. -ExecutionPolicy Bypass applies to THIS process only:
rem  it changes no machine setting and leaves nothing behind.
rem
rem  Any arguments are passed straight through, e.g.
rem      START.cmd -Force
rem      START.cmd -IncidentRoot C:\fire
rem      START.cmd -SkipFetch
rem
rem  TRAINING EXERCISE - NOT AN ACTUAL INCIDENT.
rem ============================================================================

setlocal
set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%Start-StormMountain.ps1"

if not exist "%PS1%" (
    echo.
    echo   Cannot find Start-StormMountain.ps1 next to this file.
    echo   Expected: %PS1%
    echo.
    pause
    exit /b 1
)

rem Prefer Windows PowerShell; fall back to PowerShell 7 if that is what is here.
set "PSEXE=powershell.exe"
where /q powershell.exe || set "PSEXE=pwsh.exe"
where /q %PSEXE% || (
    echo.
    echo   No PowerShell found on this machine.
    echo.
    pause
    exit /b 1
)

rem Clear the mark-of-the-web if this arrived as a downloaded zip rather than a
rem git clone. Harmless when there is no mark.
%PSEXE% -NoProfile -ExecutionPolicy Bypass -Command ^
    "Get-ChildItem -Path '%SCRIPT_DIR%' -Recurse -Include *.ps1 | Unblock-File -ErrorAction SilentlyContinue" 2>nul

%PSEXE% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -OpenPro %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
    echo   Finished with errors ^(exit code %RC%^). Scroll up for the failing step.
) else (
    echo   Done.
)

rem Keep the window open when double-clicked, but not when run from a prompt
rem that already has one.
echo %CMDCMDLINE% | find /i "/c" >nul && pause

endlocal
exit /b %RC%
