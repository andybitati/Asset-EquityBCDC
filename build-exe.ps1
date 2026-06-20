# PowerShell script to build launcher.exe using PyInstaller
# Run this from project root: Open PowerShell as admin then:
# .\build-exe.ps1

$ErrorActionPreference = 'Stop'
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ROOT

# Use venv python if present
$venvPython = Join-Path $ROOT 'venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = 'python'
}
Write-Host "Using python: $python"

# Ensure pyinstaller is installed
& $python -m pip install --upgrade pip
& $python -m pip install pyinstaller

# Build onefile exe (console enabled so you can see logs)
& $python -m PyInstaller --noconfirm --onefile --name AssetsEquityLauncher launcher.py

Write-Host "Build finished. Executable in dist\AssetsEquityLauncher.exe"
