@echo off
setlocal

REM Lance la version reseau depuis la racine du projet.
set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%scripts\StartNetwork.ps1"

endlocal
