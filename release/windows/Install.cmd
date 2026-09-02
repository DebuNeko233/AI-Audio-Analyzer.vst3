@echo off
setlocal
cd /d "%~dp0"
echo AI Audio Analyzer installer
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install.ps1"
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo Installation failed with exit code %ERR%.
  echo Read INSTALL.zh-CN.md or INSTALL.en.md for manual installation and troubleshooting.
) else (
  echo Installation finished successfully.
)
echo.
pause
exit /b %ERR%
