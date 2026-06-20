#!/usr/bin/env python3
"""
Launcher for Assets EquityBCDC
Starts backend and frontend in separate consoles and opens the UI in the default browser.
Build into a single EXE with PyInstaller if desired.
"""
import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / "venv" / "Scripts" / "python.exe"

def python_executable():
    if VENV_PY.exists():
        return str(VENV_PY)
    return sys.executable

def start_backend(python_exec):
    cmd = [python_exec, "-m", "uvicorn", "backend.app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    # Open in new console window on Windows
    if os.name == 'nt':
        subprocess.Popen(["cmd.exe", "/c", "start", "", *cmd], cwd=str(ROOT))
    else:
        subprocess.Popen(cmd, cwd=str(ROOT))
    print("Backend démarré")

def start_frontend():
    # Run npm run dev in frontend folder
    frontend_dir = ROOT / "frontend"
    if os.name == 'nt':
        # Use cmd start to open new window and run npm
        subprocess.Popen(["cmd.exe", "/c", "start", "", "npm", "run", "dev"], cwd=str(frontend_dir))
    else:
        subprocess.Popen(["npm", "run", "dev"], cwd=str(frontend_dir))
    print("Frontend démarré")

if __name__ == '__main__':
    python_exec = python_executable()
    print(f"Utilise Python: {python_exec}")

    start_backend(python_exec)
    time.sleep(1)
    start_frontend()

    # Wait a few seconds then open browser
    time.sleep(6)
    url = "http://localhost:5173"
    print(f"Ouverture du navigateur: {url}")
    webbrowser.open(url)

    print("Launched. Press Ctrl+C to exit this launcher (child processes continue running).")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting launcher")
