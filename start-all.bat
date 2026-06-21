@echo off
setlocal enableextensions enabledelayedexpansion

REM Le script doit être lancé depuis le dossier racine du projet.
set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

REM Utiliser Python du virtualenv si présent, sinon utiliser celui du PATH.
if exist "%ROOT_DIR%venv\Scripts\python.exe" (
  set PYTHON="%ROOT_DIR%venv\Scripts\python.exe"
) else (
  set PYTHON=python
)

start "Assets EquityBCDC Backend" cmd /k %PYTHON% -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
start "Assets EquityBCDC Frontend" cmd /k "cd /d ""%ROOT_DIR%frontend"" && npm run dev"

timeout /t 5 /nobreak >nul
start "Assets EquityBCDC UI" "http://localhost:5173"

endlocal
