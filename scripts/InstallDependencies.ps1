$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Installing Assets Equity BCDC dependencies in $root"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python is required. Install Python 3.11+ before continuing."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "Node.js/npm is required. Install Node.js LTS before continuing."
}

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
  python -m venv venv
}

.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt

npm install
npm --prefix frontend install

Write-Host "Dependencies installed."
